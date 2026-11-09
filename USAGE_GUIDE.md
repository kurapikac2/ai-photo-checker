> **Historical engineering notes, not validation evidence.** Numerical examples and threshold changes below do not establish accuracy, calibration or a measured false-positive reduction. Any probability or reliability claims are superseded by [the current evaluation status](CALIBRATION.md). Use [README](README.md) for supported setup and privacy behavior.

# Полное руководство по использованию Fake Image Checker

## Что проверяет система

### 1. Локальный анализ (без интернета)
- **EXIF метаданные**: проверка камеры, софта, GPS, даты съемки
- **ELA (Error Level Analysis)**: поиск отредактированных областей через сжатие
- **Визуальные артефакты**: 
  - Blockiness (блочность 8x8 пикселей - признак AI)
  - Clipping ratio (пересвет/недосвет)
  - High saturation (неестественная насыщенность)
  - Laplacian variance (резкость)
  - Edge density (плотность границ)
  - Noise std (шум)

### 2. AI-анализ через OpenRouter
- **Модель**: Google Gemini 2.5 Pro (vision)
- **Консенсус**: 2 прогона с усреднением результатов
- **Что проверяет**:
  - Неестественные текстуры
  - Странная анатомия
  - Артефакты генерации
  - Нелогичные тени и освещение
  - Аномалии фона
  - Композитность (склейка элементов)

### 3. Финальный скоринг
- **Вес AI-сигнала**: 60%
- **Вес локального анализа**: 40%
- **Текстовый риск**: анализ ключевых слов в причинах
- **Rule-based калибровка**: жесткие правила для явных AI-кейсов

## Как запустить

### Первый запуск

```powershell
# 1. Установи зависимости
pip install -r requirements.txt

# 2. Примени миграции
python manage.py migrate

# 3. Создай админа (опционально)
python manage.py createsuperuser

# 4. Запусти сервер
python manage.py runserver
```

### Каждый раз

```powershell
python manage.py runserver
```

Открой в браузере: `http://127.0.0.1:8000`

## Как проверить фото

1. Открой главную страницу `/`
2. Загрузи изображение (JPG, PNG, WEBP до 10MB)
3. Нажми "Проверить изображение"
4. Дождись результата (10-30 секунд)

## Что означают результаты

### Вердикты

- **Вероятно настоящее** (`likely_real`) - мало признаков фейка
- **Подозрительное** (`suspicious`) - есть сомнительные сигналы
- **Возможно AI-generated** (`likely_ai_generated`) - признаки AI-генерации
- **Возможно отредактировано** (`likely_edited`) - признаки редактирования
- **Недостаточно данных** (`uncertain`) - не хватает информации

### Метрики

- **Уверенность (Confidence)**: 0-100%, насколько система уверена в вердикте
- **AI probability**: 0-100%, вероятность AI-генерации
- **Manipulation probability**: 0-100%, вероятность редактирования
- **Метаданные/EXIF**: 0-100%, риск по метаданным (выше = подозрительнее)
- **ELA-анализ**: 0-100%, риск по сжатию
- **Визуальные артефакты**: 0-100%, риск по артефактам
- **Финальный риск**: 0-100%, итоговая оценка

### Причины и признаки

- **Причины**: текстовые объяснения от AI-модели и локального анализа
- **Визуальные признаки**: конкретные аномалии (inconsistent lighting, unnatural textures и т.д.)

## Настройка точности

### Файл `.env`

```bash
# Модель OpenRouter (можно менять)
OPENROUTER_MODEL=google/gemini-2.5-pro

# Количество прогонов для консенсуса (1-5)
# Больше = стабильнее, но медленнее и дороже
OPENROUTER_ANALYSIS_RUNS=2

# API ключ OpenRouter (обязательно)
OPENROUTER_API_KEY=sk-or-v1-...
```

### Альтернативные модели

Можешь попробовать другие vision-модели через OpenRouter:

- `google/gemini-2.5-pro` - текущая, сильная и стабильная
- `google/gemini-2.5-flash` - быстрее, но слабее
- `anthropic/claude-3.5-sonnet` - хорошая альтернатива
- `openai/gpt-4o` - тоже сильная

### Увеличить точность

1. **Увеличь прогоны**: `OPENROUTER_ANALYSIS_RUNS=3` (медленнее, но стабильнее)
2. **Используй сильную модель**: `google/gemini-2.5-pro` или `anthropic/claude-3.5-sonnet`
3. **Проверяй высокое разрешение**: AI-артефакты лучше видны на больших фото

### Уменьшить стоимость/время

1. **Уменьши прогоны**: `OPENROUTER_ANALYSIS_RUNS=1`
2. **Используй flash-модель**: `google/gemini-2.5-flash`

## Ограничения системы

### Что НЕ может детектор

- **100% точность невозможна**: это вероятностная оценка, не гарантия
- **Новые AI-модели**: очень свежие генераторы могут обманывать систему
- **Профессиональная обработка**: качественный фотошоп может быть незаметен
- **Низкое разрешение**: на маленьких фото артефакты не видны
- **Сильное сжатие**: JPEG-артефакты маскируют AI-артефакты

### Когда результат может быть неточным

- Фото сильно сжато (много JPEG-артефактов)
- Фото очень маленькое (< 512px)
- Фото прошло через соцсети (Instagram, Facebook пережимают)
- Художественная обработка (HDR, фильтры)
- Сканы старых фото

## Примеры использования

### Проверка AI-фото

**Признаки AI-генерации:**
- Нет EXIF метаданных
- Неестественные текстуры (слишком гладкие или слишком детальные)
- Странная анатомия (лишние пальцы, кривые зубы)
- Артефакты фона (размытость, повторяющиеся паттерны)
- Нелогичные тени и освещение
- Высокая насыщенность цветов

**Ожидаемый результат:**
- Verdict: `likely_ai_generated` или `suspicious`
- AI probability: 40-90%
- Reasons: "unnatural textures", "inconsistent lighting", "background anomalies"

### Проверка отредактированного фото

**Признаки редактирования:**
- EXIF показывает Photoshop/GIMP
- ELA показывает разные уровни сжатия в разных областях
- Blockiness в отдельных зонах
- Clipping (пересвет/недосвет) в неестественных местах

**Ожидаемый результат:**
- Verdict: `likely_edited` или `suspicious`
- Manipulation probability: 40-90%
- ELA score: 45-100%
- Reasons: "Compression differences suggest potential edited regions"

### Проверка настоящего фото

**Признаки настоящего фото:**
- Полные EXIF метаданные (камера, дата, GPS)
- Равномерное сжатие по всему изображению
- Естественный шум и артефакты
- Логичные тени и освещение

**Ожидаемый результат:**
- Verdict: `likely_real`
- Confidence: 20-60%
- AI probability: 0-30%
- Metadata score: 20-40% (низкий риск)

## Советы по использованию

1. **Не полагайся только на вердикт** - смотри на все метрики и причины
2. **Проверяй оригинал** - не пережатые копии из соцсетей
3. **Сравнивай несколько проверок** - загрузи фото 2-3 раза и сравни результаты
4. **Читай причины** - они важнее итогового процента
5. **Учитывай контекст** - откуда фото, кто автор, какая цель

## История и админка

- **История**: `/history/` - последние 50 проверок
- **Админка**: `/admin/` - полный доступ к базе данных
- **Результат**: `/result/<id>/` - детальный отчет по проверке

## Техническая информация

### Архитектура

```
Загрузка фото
    ↓
Валидация (формат, размер)
    ↓
Локальный анализ (EXIF, ELA, артефакты)
    ↓
AI-анализ через OpenRouter (2 прогона)
    ↓
Консенсус и усреднение
    ↓
Финальный скоринг (60% AI + 40% локальный)
    ↓
Rule-based калибровка вердикта
    ↓
Сохранение в БД + отображение результата
```

### Формула финального скора

```python
local_signal = 0.45 * metadata + 0.20 * ela + 0.35 * artifact
final_score = 0.60 * ai_signal + 0.40 * local_signal
textual_risk = анализ ключевых слов в reasons/visual_signs

if textual_risk >= 35:
    final_score = max(final_score, textual_risk, ai_prob, manip_prob)
```

### Правила вердикта

```python
if ai_probability >= 55: verdict = likely_ai_generated
elif manipulation_probability >= 55: verdict = likely_edited
elif ai_probability >= 35 AND strong_visual_reasons: verdict = likely_ai_generated
elif manipulation_probability >= 35 AND strong_visual_reasons: verdict = likely_edited
elif final_score < 30 AND not suspicious_local: verdict = likely_real
elif final_score < 55: verdict = suspicious
else: verdict = likely_ai_generated or likely_edited (зависит от ai_prob vs manip_prob)

# Safeguard
if verdict == likely_real AND (ai_prob >= 30 OR manip_prob >= 30 OR strong_reasons):
    verdict = suspicious
```

## Устранение проблем

### Ошибка "OpenRouter analysis failed"

- Проверь API ключ в `.env`
- Проверь интернет-соединение
- Проверь баланс на OpenRouter

### Ошибка "Файл слишком большой"

- Максимум 10MB
- Сожми фото или измени `MAX_UPLOAD_SIZE_MB` в `.env`

### Результат всегда "uncertain"

- Проверь, что OpenRouter API работает
- Проверь логи Django в консоли
- Проверь `/admin/` - есть ли `error_message` в записи

### Разные результаты на одном фото

- Это нормально для LLM vision-моделей
- Увеличь `OPENROUTER_ANALYSIS_RUNS` до 3-5
- Используй более стабильную модель (`gemini-2.5-pro`)

## Контакты и поддержка

Проект создан как MVP для демонстрации возможностей hybrid AI+forensic детектора фейковых изображений.

Для production использования рекомендуется:
- Добавить специализированные forensic-модели
- Добавить deepfake detection
- Добавить watermark detection
- Добавить reverse image search
- Увеличить количество локальных эвристик
