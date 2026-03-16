def _normalize_probability(value):
    if value is None:
        return 0
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0
    if 0 <= numeric <= 1:
        numeric *= 100
    return numeric


def _clamp(value):
    return max(0, min(100, int(round(_normalize_probability(value)))))


def _textual_signal(reasons, visual_signs):
    reason_text = ' '.join(str(item).lower() for item in reasons)
    signs_text = ' '.join(str(item).lower() for item in visual_signs)
    combined = f'{reason_text} {signs_text}'

    critical_tokens = [
        'cloned', 'copy-move', 'forgery', 'duplicated regions', 'клонированн',
        'noise inconsistency', 'frequency anomaly', 'frequency domain'
    ]
    high_risk_tokens = [
        'ai', 'generated', 'synthetic', 'deepfake', 'inconsistent lighting',
        'unnatural textures', 'background anomalies', 'composite', 'artifact',
        'anatom', 'blend seamlessly', 'montage', 'edited regions', 'compression differences',
        'plastic', 'unnatural', 'suspicious text', 'несовпадающ', 'отредактир'
    ]
    medium_risk_tokens = [
        'suspicious', 'edited', 'manipulated', 'strange', 'asymmetry', 'shadow',
        'texture', 'background', 'reflection', 'unusual', 'text found'
    ]

    score = 0
    for token in critical_tokens:
        if token in combined:
            score += 18
    for token in high_risk_tokens:
        if token in combined:
            score += 12
    for token in medium_risk_tokens:
        if token in combined:
            score += 6
    return _clamp(score)


VERDICT_LABELS = {
    'real': 'likely_real',
    'suspicious': 'suspicious',
    'ai_generated': 'likely_ai_generated',
    'edited': 'likely_edited',
    'uncertain': 'uncertain',
}


def calculate_final_score(local_result, ai_result):
    ai_failed = bool(ai_result.get('error'))
    ai_confidence = _clamp(ai_result.get('confidence', 0))
    ai_generation_probability = _clamp(ai_result.get('ai_generation_probability', 0))
    ai_manipulation_probability = _clamp(ai_result.get('manipulation_probability', 0))
    ai_signal = max(ai_confidence, ai_generation_probability, ai_manipulation_probability)
    metadata_score = local_result.get('metadata_score', 0)
    ela_score = local_result.get('ela_score', 0)
    artifact_score = local_result.get('artifact_score', 0)

    local_signal = _clamp(
        0.35 * metadata_score +
        0.30 * ela_score +
        0.35 * artifact_score
    )

    final_score = _clamp(
        0.55 * ai_signal +
        0.45 * local_signal
    )

    ai_probability = ai_generation_probability or ai_signal
    manipulation_probability = ai_manipulation_probability or _clamp(max(ela_score, artifact_score))
    textual_signal = _textual_signal(ai_result.get('reasons', []), ai_result.get('visual_signs', []))

    raw_verdict = ai_result.get('verdict', 'uncertain')
    verdict = VERDICT_LABELS.get(raw_verdict, 'uncertain')

    strong_visual_reasons = len(ai_result.get('reasons', [])) >= 2 or len(ai_result.get('visual_signs', [])) >= 2
    suspicious_local = metadata_score >= 50 or artifact_score >= 35 or ela_score >= 35
    
    has_text = bool(local_result.get('text_info', {}).get('has_text'))
    suspicious_text = bool(local_result.get('text_info', {}).get('suspicious_text'))
    
    artifact_details = local_result.get('details', {}).get('artifacts', {})
    advanced_forensics = (
        artifact_details.get('noise_inconsistency', 0) > 65 or
        artifact_details.get('frequency_anomaly', 0) > 75 or
        artifact_details.get('copy_move_score', 0) > 50
    )

    if advanced_forensics:
        if ai_probability >= 50:
            default_verdict = 'likely_ai_generated'
        elif manipulation_probability >= 50 or ela_score >= 60:
            default_verdict = 'likely_edited'
        else:
            default_verdict = 'suspicious'
    elif ai_probability >= 60:
        default_verdict = 'likely_ai_generated'
    elif manipulation_probability >= 50:
        default_verdict = 'likely_edited'
    elif ai_probability >= 30 and strong_visual_reasons:
        default_verdict = 'likely_ai_generated'
    elif manipulation_probability >= 30 and strong_visual_reasons:
        default_verdict = 'likely_edited'
    elif suspicious_text:
        default_verdict = 'suspicious'
    elif final_score < 25 and not suspicious_local and not has_text:
        default_verdict = 'likely_real'
    elif final_score < 50:
        default_verdict = 'suspicious'
    elif ai_probability >= manipulation_probability:
        default_verdict = 'likely_ai_generated'
    else:
        default_verdict = 'likely_edited'

    if textual_signal >= 30:
        final_score = _clamp(max(final_score, textual_signal, ai_probability, manipulation_probability))
        if default_verdict == 'likely_real':
            default_verdict = 'suspicious'
    
    if advanced_forensics and default_verdict == 'likely_real':
        default_verdict = 'suspicious'
        final_score = _clamp(max(final_score, 55))

    if ai_failed:
        local_only_score = _clamp(max(metadata_score, ela_score, artifact_score, final_score))
        if local_only_score >= 60:
            verdict = 'suspicious'
            final_score = max(final_score, local_only_score)
        else:
            verdict = 'uncertain'
        confidence = _clamp(max(final_score, local_only_score))
    elif verdict == 'uncertain':
        verdict = default_verdict
        confidence = max(final_score, ai_confidence)
    else:
        confidence = max(final_score, ai_confidence)

    if verdict == 'likely_real' and (ai_probability >= 25 or manipulation_probability >= 25 or strong_visual_reasons or advanced_forensics or suspicious_text):
        verdict = 'suspicious'
        confidence = max(confidence, final_score, ai_probability, manipulation_probability)
    
    if verdict == 'suspicious' and (ai_probability >= 55 or (ai_probability >= 40 and advanced_forensics)):
        verdict = 'likely_ai_generated'
        confidence = max(confidence, ai_probability)
    
    if verdict == 'suspicious' and (manipulation_probability >= 55 or (manipulation_probability >= 40 and advanced_forensics)):
        verdict = 'likely_edited'
        confidence = max(confidence, manipulation_probability)

    reasons = []
    reasons.extend(local_result.get('reasons', []))
    reasons.extend(ai_result.get('reasons', []))
    seen = set()
    unique_reasons = []
    for reason in reasons:
        if reason and reason not in seen:
            seen.add(reason)
            unique_reasons.append(reason)

    return {
        'verdict': verdict,
        'confidence': confidence,
        'ai_generation_probability': ai_probability,
        'manipulation_probability': manipulation_probability,
        'final_score': final_score,
        'reasons': unique_reasons[:8],
        'visual_signs': ai_result.get('visual_signs', []),
    }
