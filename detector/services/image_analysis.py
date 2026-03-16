from io import BytesIO

import cv2
import numpy as np
import piexif
from PIL import Image, ImageChops, ImageStat
from scipy import fftpack, ndimage
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


def _safe_score(value):
    return max(0, min(100, int(round(value))))


def extract_metadata(image_path):
    metadata = {
        'has_exif': False,
        'camera_fields': [],
        'software': '',
        'warning_flags': [],
    }
    score = 55
    try:
        exif_dict = piexif.load(image_path)
        zeroth = exif_dict.get('0th', {}) or {}
        exif = exif_dict.get('Exif', {}) or {}
        metadata['has_exif'] = any([zeroth, exif])

        make = zeroth.get(piexif.ImageIFD.Make)
        model = zeroth.get(piexif.ImageIFD.Model)
        software = zeroth.get(piexif.ImageIFD.Software)

        if make:
            metadata['camera_fields'].append(f"Make: {make.decode(errors='ignore') if isinstance(make, bytes) else make}")
        if model:
            metadata['camera_fields'].append(f"Model: {model.decode(errors='ignore') if isinstance(model, bytes) else model}")
        if software:
            metadata['software'] = software.decode(errors='ignore') if isinstance(software, bytes) else str(software)

        if metadata['has_exif']:
            score -= 20
        else:
            metadata['warning_flags'].append('No EXIF metadata found.')

        software_text = metadata['software'].lower()
        suspicious_tools = ['photoshop', 'gimp', 'canva', 'midjourney', 'stable diffusion', 'comfyui']
        if any(tool in software_text for tool in suspicious_tools):
            metadata['warning_flags'].append('Editing or generation software found in metadata.')
            score += 25
    except Exception:
        metadata['warning_flags'].append('Metadata unavailable or stripped.')

    return _safe_score(score), metadata


def compute_ela_score(image_path, quality=90):
    original = Image.open(image_path).convert('RGB')
    buffer = BytesIO()
    original.save(buffer, 'JPEG', quality=quality)
    recompressed = Image.open(BytesIO(buffer.getvalue()))
    diff = ImageChops.difference(original, recompressed)
    stat = ImageStat.Stat(diff)
    mean_diff = sum(stat.mean) / len(stat.mean)
    extrema = diff.getextrema()
    max_diff = max(channel[1] for channel in extrema)
    normalized = (mean_diff * 1.6) + (max_diff * 0.35)
    return _safe_score(normalized), {
        'mean_diff': round(mean_diff, 2),
        'max_diff': round(max_diff, 2),
        'jpeg_quality': quality,
    }


def detect_noise_inconsistency(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    block_size = 64
    noise_stds = []
    
    for y in range(0, h - block_size, block_size):
        for x in range(0, w - block_size, block_size):
            block = gray[y:y+block_size, x:x+block_size].astype(np.float32)
            denoised = cv2.GaussianBlur(block, (5, 5), 0)
            noise = block - denoised
            noise_stds.append(float(np.std(noise)))
    
    if not noise_stds:
        return 0.0
    
    noise_variance = float(np.var(noise_stds))
    noise_range = float(np.max(noise_stds) - np.min(noise_stds))
    inconsistency_score = min(100, (noise_variance * 1.8) + (noise_range * 1.2))
    return inconsistency_score


def detect_frequency_anomalies(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    f_transform = fftpack.fft2(gray)
    f_shift = fftpack.fftshift(f_transform)
    magnitude_spectrum = np.abs(f_shift)
    
    h, w = magnitude_spectrum.shape
    center_y, center_x = h // 2, w // 2
    
    low_freq = magnitude_spectrum[center_y-20:center_y+20, center_x-20:center_x+20]
    high_freq_top = magnitude_spectrum[0:30, :]
    high_freq_bottom = magnitude_spectrum[-30:, :]
    
    low_freq_energy = float(np.mean(low_freq))
    high_freq_energy = float(np.mean(np.concatenate([high_freq_top.flatten(), high_freq_bottom.flatten()])))
    
    if low_freq_energy == 0:
        return 0.0
    
    freq_ratio = high_freq_energy / low_freq_energy
    
    if freq_ratio < 0.0005:
        anomaly_score = 85.0
    elif freq_ratio < 0.002:
        anomaly_score = 65.0
    elif freq_ratio > 0.8:
        anomaly_score = 45.0
    else:
        anomaly_score = 0.0
    
    return anomaly_score


def detect_copy_move(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create(nfeatures=500)
    keypoints, descriptors = sift.detectAndCompute(gray, None)
    
    if descriptors is None or len(descriptors) < 10:
        return 0.0
    
    bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
    matches = bf.knnMatch(descriptors, descriptors, k=3)
    
    suspicious_matches = 0
    for match_group in matches:
        if len(match_group) >= 2:
            m, n = match_group[0], match_group[1]
            if m.queryIdx != m.trainIdx:
                kp1 = keypoints[m.queryIdx]
                kp2 = keypoints[m.trainIdx]
                distance = np.sqrt((kp1.pt[0] - kp2.pt[0])**2 + (kp1.pt[1] - kp2.pt[1])**2)
                if 30 < distance < 300 and m.distance < 0.6 * n.distance:
                    suspicious_matches += 1
    
    copy_move_score = min(100, suspicious_matches * 8)
    return float(copy_move_score)


def detect_text_in_image(image_path):
    if not TESSERACT_AVAILABLE:
        return {'has_text': False, 'text_content': '', 'text_confidence': 0, 'warning': 'OCR not available'}
    
    try:
        image = Image.open(image_path)
        text_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, lang='eng+rus')
        
        confidences = [int(conf) for conf in text_data['conf'] if conf != '-1']
        texts = [text.strip() for text, conf in zip(text_data['text'], text_data['conf']) if conf != '-1' and text.strip()]
        
        has_text = len(texts) > 0
        text_content = ' '.join(texts) if has_text else ''
        avg_confidence = int(np.mean(confidences)) if confidences else 0
        
        ai_text_patterns = ['lorem ipsum', 'sample text', 'placeholder', 'xxx', 'test', 'dummy']
        suspicious_text = any(pattern in text_content.lower() for pattern in ai_text_patterns)
        
        return {
            'has_text': has_text,
            'text_content': text_content[:500],
            'text_confidence': avg_confidence,
            'text_count': len(texts),
            'suspicious_text': suspicious_text
        }
    except Exception as e:
        return {'has_text': False, 'text_content': '', 'text_confidence': 0, 'warning': str(e)}


def detect_artifact_score(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return 50, {'warning_flags': ['Unable to load image with OpenCV.']}

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    noise = gray.astype(np.float32) - cv2.GaussianBlur(gray, (5, 5), 0).astype(np.float32)
    noise_std = float(np.std(noise))
    clipping_ratio = float(np.mean((gray <= 3) | (gray >= 252)))

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    high_saturation_ratio = float(np.mean(hsv[:, :, 1] > 220))

    h, w = gray.shape
    aspect_ratio = w / h if h else 1
    blockiness_values = []
    for row in range(8, h, 8):
        blockiness_values.append(np.mean(np.abs(gray[row, :].astype(np.float32) - gray[row - 1, :].astype(np.float32))))
    for col in range(8, w, 8):
        blockiness_values.append(np.mean(np.abs(gray[:, col].astype(np.float32) - gray[:, col - 1].astype(np.float32))))
    blockiness_score = float(np.mean(blockiness_values)) if blockiness_values else 0.0

    risk = 0

    if laplacian_var < 30:
        risk += 18
    if edge_density < 0.02 or edge_density > 0.25:
        risk += 20
    if noise_std < 2 or noise_std > 35:
        risk += 16
    if aspect_ratio > 3.0 or aspect_ratio < 0.33:
        risk += 10
    if blockiness_score > 18:
        risk += 16
    if clipping_ratio > 0.25:
        risk += 12
    if high_saturation_ratio > 0.20:
        risk += 8
    
    noise_inconsistency = detect_noise_inconsistency(image)
    if noise_inconsistency > 65:
        risk += 22
    elif noise_inconsistency > 50:
        risk += 12
    
    freq_anomaly = detect_frequency_anomalies(image)
    if freq_anomaly > 75:
        risk += 18
    elif freq_anomaly > 60:
        risk += 10
    
    copy_move_score = detect_copy_move(image)
    if copy_move_score > 50:
        risk += 20
    elif copy_move_score > 30:
        risk += 10

    return _safe_score(risk), {
        'laplacian_variance': round(laplacian_var, 2),
        'edge_density': round(edge_density, 4),
        'noise_std': round(noise_std, 2),
        'blockiness_score': round(blockiness_score, 2),
        'clipping_ratio': round(clipping_ratio, 4),
        'high_saturation_ratio': round(high_saturation_ratio, 4),
        'noise_inconsistency': round(noise_inconsistency, 2),
        'frequency_anomaly': round(freq_anomaly, 2),
        'copy_move_score': round(copy_move_score, 2),
        'width': int(w),
        'height': int(h),
        'aspect_ratio': round(aspect_ratio, 3),
    }


def run_local_analysis(image_path):
    metadata_score, metadata_details = extract_metadata(image_path)
    ela_score, ela_details = compute_ela_score(image_path)
    artifact_score, artifact_details = detect_artifact_score(image_path)
    text_info = detect_text_in_image(image_path)

    reasons = []
    reasons.extend(metadata_details.get('warning_flags', []))

    if ela_score >= 45:
        reasons.append('Compression differences suggest potential edited regions.')
    if artifact_score >= 45:
        reasons.append('Visual artifact patterns look unusual for a natural photo.')
    
    if artifact_details.get('noise_inconsistency', 0) > 65:
        reasons.append('Noise inconsistency detected across image regions - possible editing.')
    if artifact_details.get('frequency_anomaly', 0) > 75:
        reasons.append('Frequency domain anomalies suggest AI generation or heavy processing.')
    if artifact_details.get('copy_move_score', 0) > 50:
        reasons.append('Potential copy-move forgery detected - duplicated regions found.')
    
    if text_info.get('has_text'):
        if text_info.get('suspicious_text'):
            reasons.append(f"Suspicious text detected: '{text_info.get('text_content', '')[:100]}'")
        elif text_info.get('text_confidence', 0) > 70:
            reasons.append(f"Text found in image: '{text_info.get('text_content', '')[:100]}'")
    
    if not reasons:
        reasons.append('Local analysis found limited suspicious signals.')

    return {
        'metadata_score': metadata_score,
        'ela_score': ela_score,
        'artifact_score': artifact_score,
        'text_info': text_info,
        'reasons': reasons,
        'details': {
            'metadata': metadata_details,
            'ela': ela_details,
            'artifacts': artifact_details,
            'text': text_info,
        },
    }
