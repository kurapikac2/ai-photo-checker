from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

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


def home(request):
    form = ImageUploadForm()
    return render(request, 'detector/home.html', {'form': form})


def check_image(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    form = ImageUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, 'detector/home.html', {'form': form}, status=400)

    obj = form.save()
    obj.processing_status = 'processing'
    obj.save(update_fields=['processing_status'])

    try:
        local_result = run_local_analysis(obj.original_image.path)
        ai_result = analyze_with_openrouter(obj.original_image.path)
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
        obj.model_raw_response = ai_result
        obj.processing_status = 'completed'
        obj.error_message = ''
        obj.save()
        return redirect('detector:result', pk=obj.pk)
    except Exception as exc:
        obj.processing_status = 'failed'
        obj.error_message = str(exc)
        obj.save(update_fields=['processing_status', 'error_message'])
        messages.error(request, 'Не удалось проанализировать изображение.')
        return redirect('detector:result', pk=obj.pk)


def result_view(request, pk):
    image_check = get_object_or_404(ImageCheck, pk=pk)
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


def history_view(request):
    checks = ImageCheck.objects.all()[:50]
    return render(request, 'detector/history.html', {'checks': checks, 'verdict_meta': VERDICT_META})
