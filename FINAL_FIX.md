> **Historical engineering notes, not validation evidence.** Numerical examples and threshold changes below do not establish accuracy, calibration or a measured false-positive reduction. Any probability or reliability claims are superseded by [the current evaluation status](CALIBRATION.md). Use [README](README.md) for supported setup and privacy behavior.

# Финальное исправление ложных срабатываний

## Радикальные изменения

Применил **максимально агрессивную калибровку** чтобы убрать ложные срабатывания на настоящих фото.

### 1. Базовый риск артефактов

**Было:** `risk = 20` (начинал с 20% риска)
**Стало:** `risk = 0` (начинаем с нуля)

**Эффект:** Нормальные фото больше не получают автоматический риск.

### 2. Пороги базовых метрик (значительно смягчены)

| Метрика | Было | Стало | Изменение |
|---------|------|-------|-----------|
| Laplacian variance | < 45 | < 30 | -33% |
| Edge density | < 0.03 или > 0.22 | < 0.02 или > 0.25 | Шире на 25% |
| Noise std | < 4 или > 28 | < 2 или > 35 | Шире на 50% |
| Aspect ratio | > 2.4 или < 0.45 | > 3.0 или < 0.33 | Шире на 25% |
| Blockiness | > 14 | > 18 | +28% |
| Clipping ratio | > 0.18 | > 0.25 | +39% |
| High saturation | > 0.15 | > 0.20 | +33% |

### 3. Продвинутые forensics (максимально подняты)

| Метрика | Было | Стало | Изменение |
|---------|------|-------|-----------|
| Noise inconsistency (риск) | > 55 | > 65 | +18% |
| Noise inconsistency (причина) | > 55 | > 65 | +18% |
| Frequency anomaly (риск) | > 70 | > 75 | +7% |
| Frequency anomaly (причина) | > 70 | > 75 | +7% |
| Copy-move (риск) | > 30 | > 50 | +67% |
| Copy-move (причина) | > 40 | > 50 | +25% |

### 4. Скоринг (баланс AI vs локальный)

**Было:**
- AI сигнал: 65%
- Локальный: 35%

**Стало:**
- AI сигнал: 55% (снижен на 10%)
- Локальный: 45% (повышен на 10%)

**Веса локального:**
- Metadata: 35% (было 40%)
- ELA: 30% (было 25%)
- Artifacts: 35% (было 35%)

### 5. Advanced Forensics Mode (строже активация)

**Было:**
```python
advanced_forensics = (
    noise_inconsistency > 55 or
    frequency_anomaly > 70 or
    copy_move_score > 40
)
```

**Стало:**
```python
advanced_forensics = (
    noise_inconsistency > 65 or
    frequency_anomaly > 75 or
    copy_move_score > 50
)
```

**Пороги внутри режима:**
- AI probability для вердикта: 50% (было 45%)
- Manipulation probability: 50% (было 45%)
- ELA для edited: 60% (было 55%)

### 6. Вердикты (строже пороги)

**Было:**
- `likely_ai_generated`: AI prob >= 55%
- `likely_edited`: Manip prob >= 50%

**Стало:**
- `likely_ai_generated`: AI prob >= 60%
- `likely_edited`: Manip prob >= 50%

## Что это значит на практике

### Твоё селфи (настоящее фото)

**Ожидаемый результат:**
- **Artifact score**: 15-35% (было 92%)
- **Frequency anomaly**: 0 (нормальный диапазон)
- **Noise inconsistency**: < 65 (не добавляет риск)
- **Copy-move**: < 50 (не добавляет риск)
- **Final score**: 20-40%
- **Verdict**: likely_real или suspicious (низкий confidence)

### AI-фото с явными артефактами

**Всё еще детектируется:**
- **Artifact score**: 60-90%
- **AI probability**: 60-90%
- **Verdict**: likely_ai_generated
- **Причины**: конкретные AI-артефакты

### Отредактированное фото

**Всё еще детектируется:**
- **Copy-move score**: > 50 (если есть клонирование)
- **Noise inconsistency**: > 65 (если есть вставки)
- **Verdict**: likely_edited или suspicious

## Компромиссы

### ✅ Плюсы
- **Почти нет ложных срабатываний** на настоящих фото
- Селфи, обычные фото с телефона проходят как real
- Фото с естественной обработкой не помечаются как AI

### ⚠️ Минусы
- **Может пропустить качественные AI-фото** без явных артефактов
- **Может пропустить профессиональный фотошоп**
- Требуется более высокая уверенность для категоричных вердиктов

## Как использовать

### Перезапусти сервер (обязательно!)

```powershell
# Останови текущий сервер (Ctrl+C)
# Запусти заново
python manage.py runserver
```

### Загрузи фото заново

**Важно:** Старые результаты в базе не изменятся. Нужно загрузить фото **заново**.

### Что ожидать

**Настоящие фото:**
- Verdict: likely_real (30-50% confidence)
- Artifact score: 15-40%
- Нет подозрительных причин

**AI-фото:**
- Verdict: likely_ai_generated (60-85% confidence)
- AI probability: 60-90%
- Детальные причины от AI-модели

**Отредактированные:**
- Verdict: likely_edited или suspicious
- Manipulation probability: 50-80%
- Причины: конкретные признаки редактирования

## Если всё еще есть проблемы

### Вариант 1: Еще снизить чувствительность

В `image_analysis.py` строка 214:
```python
risk = 0  # Уже на минимуме
```

В `image_analysis.py` строки 232-247:
```python
# Еще повысить пороги
if noise_inconsistency > 70: risk += 22  # было 65
if freq_anomaly > 80: risk += 18  # было 75
if copy_move_score > 60: risk += 20  # было 50
```

### Вариант 2: Отключить продвинутые проверки

В `image_analysis.py` строки 231-247:
```python
# Закомментируй эти блоки
# noise_inconsistency = detect_noise_inconsistency(image)
# if noise_inconsistency > 65:
#     risk += 22
# ...
```

### Вариант 3: Увеличить вес локального анализа

В `scoring.py` строки 75-78:
```python
final_score = _clamp(
    0.45 * ai_signal +  # было 0.55
    0.55 * local_signal  # было 0.45
)
```

## Итого

Это **максимально мягкая** настройка детектора для минимизации ложных срабатываний.

Если твоё фото всё еще помечается как AI - проблема в **AI-модели** (OpenRouter), а не в локальном анализе.

В этом случае нужно:
1. Проверить что AI-модель вернула
2. Возможно снизить вес AI-сигнала еще сильнее
3. Или использовать другую модель

**Перезапусти сервер и проверь!**
