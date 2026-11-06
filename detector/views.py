import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from PIL import Image

from .forms import ImageUploadForm
from .models import ImageCheck
from .services.image_analysis import run_local_analysis
from .services.openrouter_client import analyze_with_openrouter
from .services.scoring import calculate_final_score


VERDICT_META = {
    'likely_real': {'label': 'Вероятно настоящее', 'badge': 'bg-emerald-100 text-emerald-700'},
    'suspicious': {'label': 'Подозрительное', 'badge': 'bg-amber-100 text-amber-700'},
    'likely_ai_generated': {'label': 'Возможно AI-generated', 'badge': 'bg-rose-100 text-rose-700'},
    'likely_edited': {'label': 'Возможно отредактировано', 'badge': 'bg-fuchsia-100 text-fuchsia-700'},
    'uncertain': {'label': 'Недостаточно данных', 'badge': 'bg-slate-100 text-slate-700'},
}


def owned_checks(request):
    token = request.session.get('analysis_owner')
    if not token:
        return ImageCheck.objects.none()
    cutoff = timezone.now() - timedelta(hours=settings.ANALYSIS_RETENTION_HOURS)
    return ImageCheck.objects.filter(owner_token=token, uploaded_at__gt=cutoff)


@never_cache
def home(request):
    form = ImageUploadForm()
    return render(request, 'detector/home.html', {
        'form': form, 'retention_hours': settings.ANALYSIS_RETENTION_HOURS,
    })


@never_cache
def check_image(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    form = ImageUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'detector/home.html', {'form': form}, status=400)

    if not request.session.get('analysis_owner'):
        request.session['analysis_owner'] = secrets.token_hex(32)
    obj = form.save(commit=False)
    obj.owner_token = request.session['analysis_owner']
    obj.processing_status = 'processing'
    obj.save()

    try:
        local_result = run_local_analysis(obj.original_image.path)
        if not owned_checks(request).filter(pk=obj.pk).exists():
            return redirect('detector:history')
        if form.cleaned_data['allow_external_analysis']:
            ai_result = analyze_with_openrouter(obj.original_image.path)
            if ai_result.get('error'):
                ai_result = {
                    'error': 'external_analysis_unavailable', 'verdict': 'uncertain',
                    'reasons': ['External model analysis is unavailable.'],
                }
        else:
            ai_result = {
                'error': 'external_analysis_disabled', 'verdict': 'uncertain',
                'reasons': ['External model analysis was not requested.'],
            }
        final_result = calculate_final_score(local_result, ai_result)

        obj.verdict = final_result['verdict']
        obj.confidence = final_result['confidence']
        obj.ai_generation_probability = final_result['ai_generation_probability']
        obj.manipulation_probability = final_result['manipulation_probability']
        obj.metadata_score = local_result['metadata_score']
        obj.ela_score = local_result['ela_score']
        obj.artifact_score = local_result['artifact_score']
        obj.final_score = final_result['final_score']
        obj.reasons = final_result['reasons']
        obj.visual_signs = final_result['visual_signs']
        obj.local_analysis = local_result['details']
        obj.model_raw_response = {}
        obj.processing_status = 'completed'
        obj.error_message = ''
        result_fields = (
            'verdict', 'confidence', 'ai_generation_probability',
            'manipulation_probability', 'metadata_score', 'ela_score',
            'artifact_score', 'final_score', 'reasons', 'visual_signs',
            'local_analysis', 'model_raw_response', 'processing_status', 'error_message',
        )
        updated = ImageCheck.objects.filter(pk=obj.pk).update(
            **{field: getattr(obj, field) for field in result_fields}
        )
        if not updated:
            return redirect('detector:history')
        return redirect('detector:result', pk=obj.pk)
    except Exception:
        obj.processing_status = 'failed'
        obj.error_message = 'Не удалось обработать изображение. Попробуйте другой файл.'
        updated = ImageCheck.objects.filter(pk=obj.pk).update(
            processing_status=obj.processing_status, error_message=obj.error_message,
        )
        if not updated:
            return redirect('detector:history')
        messages.error(request, 'Не удалось проанализировать изображение.')
        return redirect('detector:result', pk=obj.pk)


@never_cache
def result_view(request, pk):
    image_check = get_object_or_404(owned_checks(request), pk=pk)
    verdict_meta = VERDICT_META.get(image_check.verdict or 'uncertain', VERDICT_META['uncertain'])
    checks = [
        ('Метаданные / EXIF', image_check.metadata_score),
        ('ELA-анализ', image_check.ela_score),
        ('Визуальные артефакты', image_check.artifact_score),
        ('Финальный риск', image_check.final_score),
    ]
    return render(
        request,
        'detector/result.html',
        {
            'image_check': image_check,
            'verdict_meta': verdict_meta,
            'checks': checks,
        },
    )


@never_cache
def history_view(request):
    checks = owned_checks(request)[:50]
    return render(request, 'detector/history.html', {'checks': checks, 'verdict_meta': VERDICT_META})


@never_cache
def image_view(request, pk):
    record = get_object_or_404(owned_checks(request), pk=pk)
    try:
        file = record.original_image.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404
    try:
        with Image.open(file) as image:
            content_type = Image.MIME.get(image.format, 'application/octet-stream')
        file.seek(0)
    except (OSError, ValueError):
        file.close()
        raise Http404
    response = FileResponse(file, content_type=content_type)
    response['X-Content-Type-Options'] = 'nosniff'
    response['Referrer-Policy'] = 'no-referrer'
    return response


@require_POST
@never_cache
def delete_view(request, pk):
    record = get_object_or_404(owned_checks(request), pk=pk)
    record.delete_with_image()
    return redirect('detector:history')
