import base64
import json
import math
from collections import Counter
from pathlib import Path

import requests
from django.conf import settings


def _load_api_key():
    if settings.OPENROUTER_API_KEY:
        return settings.OPENROUTER_API_KEY.strip()

    txt_path = Path(settings.BASE_DIR) / 'txt'
    if txt_path.exists():
        return txt_path.read_text(encoding='utf-8').strip()
    return ''


def _extract_json_payload(text_content):
    if not text_content:
        raise ValueError('Empty response content from model.')

    text_content = text_content.strip()

    try:
        return json.loads(text_content)
    except json.JSONDecodeError:
        pass

    if '```json' in text_content:
        candidate = text_content.split('```json', 1)[1].split('```', 1)[0].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    if '```' in text_content:
        candidate = text_content.split('```', 1)[1].split('```', 1)[0].strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    start = text_content.find('{')
    end = text_content.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text_content[start:end + 1]
        return json.loads(candidate)

    raise ValueError(f'Could not extract JSON from model response: {text_content[:300]}')


def _normalize_percentage(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0
    if not math.isfinite(number):
        return 0
    if 0 <= number <= 1:
        number *= 100
    return int(max(0, min(100, round(number))))


def _run_openrouter_once(encoded_image, api_key):
    prompt = (
        'Ты профессиональный forensic-эксперт для детального анализа изображений на признаки AI-генерации, редактирования и манипуляций. '
        'Твоя задача — максимально тщательно проверить изображение и найти ВСЕ подозрительные признаки. '
        '\n\nЧТО ПРОВЕРЯТЬ ОБЯЗАТЕЛЬНО:\n'
        '1. ОТРЕДАКТИРОВАННЫЕ ОБЛАСТИ: разные уровни сжатия, несовпадающие границы, клонированные участки, вставленные объекты\n'
        '2. AI-АРТЕФАКТЫ: неестественные текстуры, странная анатомия (лишние пальцы, кривые зубы), артефакты генерации, '
        'повторяющиеся паттерны, "пластиковая" кожа, нереалистичные волосы, размытые детали фона\n'
        '3. ОСВЕЩЕНИЕ И ТЕНИ: нелогичные тени, несовпадающие источники света, отсутствие теней где должны быть\n'
        '4. ФОН И КОМПОЗИЦИЯ: аномалии фона, размытость, композитность (склейка элементов), нереалистичная глубина\n'
        '5. ТЕКСТ В ИЗОБРАЖЕНИИ: если есть текст - опиши его содержание, проверь на нереалистичность (искаженные буквы, '
        'бессмысленные символы, признаки AI-генерации текста)\n'
        '6. ЦВЕТА И НАСЫЩЕННОСТЬ: неестественная насыщенность, странные цветовые переходы, пересвет/недосвет\n'
        '7. ДЕТАЛИ: проверь мелкие детали (украшения, одежда, предметы) на реалистичность и согласованность\n'
        '\nВерни только JSON без markdown:\n'
        '{"verdict":"real|suspicious|ai_generated|edited|uncertain","confidence":0,'
        '"reasons":[],"visual_signs":[],"manipulation_probability":0,"ai_generation_probability":0}\n\n'
        'ПРАВИЛА:\n'
        '- confidence, manipulation_probability, ai_generation_probability: целые числа 0-100\n'
        '- Если нашел ЛЮБЫЕ признаки AI или редактирования - НЕ ставь real, ставь минимум suspicious\n'
        '- Если видишь явные AI-артефакты или отредактированные области - ставь ai_generated или edited с высокой вероятностью (60-95%)\n'
        '- reasons: детальные конкретные причины ("несовпадающие тени на лице и фоне", "клонированная текстура в левом углу")\n'
        '- visual_signs: короткие теги ("inconsistent lighting", "cloned regions", "ai texture artifacts", "unnatural anatomy")\n'
        '- Если есть текст - обязательно упомяни его в reasons\n'
        '- Будь СТРОГИМ и ВНИМАТЕЛЬНЫМ - лучше пометить подозрительное, чем пропустить фейк\n'
        'Ответ только JSON.'
    )

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:8000',
        'X-Title': 'Fake Image Checker',
    }

    payload = {
        'model': settings.OPENROUTER_MODEL,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/jpeg;base64,{encoded_image}'
                        },
                    },
                ],
            }
        ],
        'temperature': 0,
    }

    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=90,
        )
        if not response.ok:
            return {
                'verdict': 'uncertain',
                'confidence': 0,
                'reasons': ['External model analysis is unavailable.'],
                'visual_signs': [],
                'manipulation_probability': 0,
                'ai_generation_probability': 0,
                'error': 'openrouter_failure',
            }
        data = response.json()
        content = data['choices'][0]['message']['content']
        if isinstance(content, list):
            text_content = ''.join(item.get('text', '') for item in content if isinstance(item, dict))
        else:
            text_content = content or ''
        parsed = _extract_json_payload(text_content)
        if not isinstance(parsed, dict):
            raise ValueError('Model response must be an object.')
        if parsed.get('verdict') not in {'real', 'suspicious', 'ai_generated', 'edited', 'uncertain'}:
            parsed['verdict'] = 'uncertain'
        for field in ('reasons', 'visual_signs'):
            items = parsed.get(field, [])
            parsed[field] = ([item.strip()[:300] for item in items[:8]
                              if isinstance(item, str) and item.strip()]
                             if isinstance(items, list) else [])
        parsed['confidence'] = _normalize_percentage(parsed.get('confidence', 0))
        parsed['ai_generation_probability'] = _normalize_percentage(parsed.get('ai_generation_probability', 0))
        parsed['manipulation_probability'] = _normalize_percentage(parsed.get('manipulation_probability', 0))
        return {
            field: parsed[field]
            for field in (
                'verdict', 'confidence', 'reasons', 'visual_signs',
                'ai_generation_probability', 'manipulation_probability',
            )
        }
    except Exception:
        return {
            'verdict': 'uncertain',
            'confidence': 0,
            'reasons': ['External model analysis is unavailable.'],
            'visual_signs': [],
            'manipulation_probability': 0,
            'ai_generation_probability': 0,
            'error': 'openrouter_failure',
        }


def _aggregate_openrouter_results(results):
    verdict_counter = Counter()
    for result in results:
        verdict_counter[result.get('verdict', 'uncertain')] += 1

    aggregated_verdict = verdict_counter.most_common(1)[0][0]
    confidence_values = [_normalize_percentage(item.get('confidence', 0)) for item in results]
    ai_values = [_normalize_percentage(item.get('ai_generation_probability', 0)) for item in results]
    manipulation_values = [_normalize_percentage(item.get('manipulation_probability', 0)) for item in results]

    merged_reasons = []
    merged_visual_signs = []
    for result in results:
        merged_reasons.extend(result.get('reasons', []))
        merged_visual_signs.extend(result.get('visual_signs', []))

    def _unique(items):
        seen = set()
        output = []
        for item in items:
            normalized = str(item).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                output.append(normalized)
        return output

    unique_reasons = _unique(merged_reasons)
    unique_visual_signs = _unique(merged_visual_signs)

    return {
        'verdict': aggregated_verdict,
        'confidence': int(round(sum(confidence_values) / max(1, len(confidence_values)))),
        'reasons': unique_reasons[:8],
        'visual_signs': unique_visual_signs[:8],
        'manipulation_probability': int(round(sum(manipulation_values) / max(1, len(manipulation_values)))),
        'ai_generation_probability': int(round(sum(ai_values) / max(1, len(ai_values)))),
        'consensus_runs': len(results),
    }


def analyze_with_openrouter(image_path):
    api_key = _load_api_key()
    if not api_key:
        return {
            'verdict': 'uncertain',
            'confidence': 0,
            'reasons': ['OpenRouter API key is not configured.'],
            'visual_signs': [],
            'manipulation_probability': 0,
            'ai_generation_probability': 0,
            'error': 'missing_api_key',
        }

    with open(image_path, 'rb') as image_file:
        encoded = base64.b64encode(image_file.read()).decode('utf-8')

    run_count = max(1, int(getattr(settings, 'OPENROUTER_ANALYSIS_RUNS', 1)))
    successful = []
    errors = []

    for _ in range(run_count):
        result = _run_openrouter_once(encoded, api_key)
        if result.get('error'):
            errors.append(result)
        else:
            successful.append(result)

    if successful:
        return _aggregate_openrouter_results(successful)
    return errors[-1] if errors else {
        'verdict': 'uncertain',
        'confidence': 0,
        'reasons': ['OpenRouter analysis failed without detailed error.'],
        'visual_signs': [],
        'manipulation_probability': 0,
        'ai_generation_probability': 0,
        'error': 'openrouter_failure',
    }
