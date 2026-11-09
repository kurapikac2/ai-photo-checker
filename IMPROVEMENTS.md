> **Historical engineering notes, not validation evidence.** Numerical examples and threshold changes below do not establish accuracy, calibration or a measured false-positive reduction. Any probability or reliability claims are superseded by [the current evaluation status](CALIBRATION.md). Use [README](README.md) for supported setup and privacy behavior.

# Улучшения детектора - максимальная точность

## Что добавлено для идеальной работы

### 1. Продвинутый forensic-анализ отредактированных областей

#### Анализ шума (Noise Inconsistency Detection)
- **Что проверяет**: Разбивает изображение на блоки 64x64 и анализирует уровень шума в каждом
- **Как работает**: Отредактированные области имеют другой уровень шума, чем оригинальные
- **Триггер**: Если разброс шума > 40 → риск +22%, добавляется причина "Noise inconsistency detected"
- **Применение**: Находит вставленные объекты, клонированные области, ретушь

#### Анализ частотной области (Frequency Domain Analysis)
- **Что проверяет**: FFT-преобразование для анализа частотного спектра
- **Как работает**: AI-изображения и отредактированные фото имеют аномальное распределение частот
- **Триггер**: 
  - Очень низкие высокие частоты (< 0.001) → 85% риск (признак AI-сглаживания)
  - Низкие высокие частоты (< 0.005) → 65% риск
  - Очень высокие (> 0.5) → 45% риск (признак пережатия)
- **Применение**: Детектирует AI-генерацию, сильную обработку, неестественное сглаживание

#### Copy-Move Detection (Поиск клонированных областей)
- **Что проверяет**: Использует SIFT для поиска дублированных участков изображения
- **Как работает**: Находит keypoints и ищет похожие на расстоянии 30-300 пикселей
- **Триггер**: Если найдено > 30 подозрительных совпадений → риск +20%
- **Применение**: Находит copy-move forgery (клонирование штампом, удаление объектов)

### 2. OCR и анализ текста в изображениях

#### Распознавание текста (pytesseract)
- **Языки**: Русский + Английский
- **Что извлекает**: 
  - Весь текст из изображения
  - Уверенность распознавания (0-100%)
  - Количество текстовых блоков

#### Детект подозрительного AI-текста
- **Паттерны**: "lorem ipsum", "sample text", "placeholder", "xxx", "test", "dummy"
- **Применение**: AI-генераторы часто создают бессмысленный текст или placeholder'ы
- **Триггер**: Если найден подозрительный текст → добавляется в reasons и verdict не может быть "real"

#### Интеграция в скоринг
- **Если есть текст с confidence > 70%**: Добавляется в reasons для информирования
- **Если подозрительный текст**: Автоматически verdict = suspicious минимум
- **Текст учитывается в textual_signal**: Ключевые слова "text found", "suspicious text" повышают риск

### 3. Усиленный AI-анализ через OpenRouter

#### Новый детальный промпт
Модель теперь проверяет **7 категорий обязательно**:

1. **Отредактированные области**
   - Разные уровни сжатия
   - Несовпадающие границы
   - Клонированные участки
   - Вставленные объекты

2. **AI-артефакты**
   - Неестественные текстуры
   - Странная анатомия (лишние пальцы, кривые зубы)
   - Повторяющиеся паттерны
   - "Пластиковая" кожа
   - Нереалистичные волосы
   - Размытые детали фона

3. **Освещение и тени**
   - Нелогичные тени
   - Несовпадающие источники света
   - Отсутствие теней где должны быть

4. **Фон и композиция**
   - Аномалии фона
   - Размытость
   - Композитность (склейка элементов)
   - Нереалистичная глубина

5. **Текст в изображении**
   - Описание содержания
   - Проверка на искаженные буквы
   - Бессмысленные символы
   - Признаки AI-генерации текста

6. **Цвета и насыщенность**
   - Неестественная насыщенность
   - Странные цветовые переходы
   - Пересвет/недосвет

7. **Детали**
   - Украшения, одежда, предметы
   - Реалистичность и согласованность

#### Строгие правила для модели
- **НЕ ставить "real"** если найдены ЛЮБЫЕ признаки AI или редактирования
- **Минимум "suspicious"** при любых сомнениях
- **60-95% вероятность** для явных AI-артефактов или отредактированных областей
- **Детальные причины** с конкретными описаниями ("несовпадающие тени на лице и фоне")
- **Обязательно упоминать текст** если он есть в изображении

### 4. Ужесточенный скоринг

#### Новые веса
- **AI-сигнал**: 65% (было 60%)
- **Локальный анализ**: 35% (было 40%)
- **ELA**: 25% (было 20%)
- **Artifacts**: 35% (было 35%)
- **Metadata**: 40% (было 45%)

#### Критические токены (каждый +18%)
- "cloned", "copy-move", "forgery", "duplicated regions"
- "клонированн", "noise inconsistency", "frequency anomaly"

#### Высокий риск токены (каждый +12%)
- "ai", "generated", "synthetic", "deepfake"
- "inconsistent lighting", "unnatural textures"
- "edited regions", "compression differences"
- "несовпадающ", "отредактир"

#### Advanced Forensics Mode
Активируется если:
- Noise inconsistency > 40
- Frequency anomaly > 60
- Copy-move score > 30

**Эффект**:
- Снижает порог для AI-вердикта: 40% вместо 50%
- Снижает порог для edited-вердикта: 40% вместо 50%
- Автоматически блокирует "likely_real" → минимум "suspicious"
- Поднимает final_score до минимум 55%

#### Новые правила вердикта

**Блокировка "likely_real"**:
- AI probability >= 25% (было 30%)
- Manipulation probability >= 25% (было 30%)
- Есть strong_visual_reasons
- Есть advanced_forensics
- Есть suspicious_text

**Автоматический upgrade "suspicious" → "likely_ai_generated"**:
- AI probability >= 55%
- ИЛИ AI probability >= 40% + advanced_forensics

**Автоматический upgrade "suspicious" → "likely_edited"**:
- Manipulation probability >= 55%
- ИЛИ Manipulation probability >= 40% + advanced_forensics

### 5. Новые зависимости

```bash
pip install -r requirements.txt
```

Добавлено:
- **pytesseract==0.3.10** - OCR для распознавания текста
- **scipy==1.14.1** - FFT для частотного анализа

**ВАЖНО для pytesseract**:
Нужно установить Tesseract OCR отдельно:
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- После установки добавить в PATH или указать путь в коде

Если Tesseract не установлен - OCR просто не будет работать, остальное работает нормально.

## Как это работает на практике

### Пример 1: AI-сгенерированное фото

**Старая версия**:
- Verdict: likely_real
- Confidence: 32%
- AI probability: 40%
- Reasons: "inconsistent lighting", "unnatural textures"

**Новая версия**:
- Verdict: likely_ai_generated
- Confidence: 72%
- AI probability: 65%
- Reasons: 
  - "Frequency domain anomalies suggest AI generation"
  - "Unnatural textures detected - plastic skin appearance"
  - "Inconsistent lighting and shadows across face and background"
  - "Background shows typical AI generation blur patterns"

### Пример 2: Отредактированное фото (клонирование штампом)

**Старая версия**:
- Verdict: suspicious
- Confidence: 45%
- Manipulation probability: 30%

**Новая версия**:
- Verdict: likely_edited
- Confidence: 78%
- Manipulation probability: 68%
- Reasons:
  - "Potential copy-move forgery detected - duplicated regions found"
  - "Noise inconsistency detected across image regions - possible editing"
  - "Compression differences suggest potential edited regions"

### Пример 3: Фото с AI-текстом

**Старая версия**:
- Verdict: likely_real
- Не замечает текст

**Новая версия**:
- Verdict: suspicious
- Reasons:
  - "Text found in image: 'Lorem ipsum dolor sit amet'"
  - "Suspicious text detected - AI placeholder pattern"
  - "Text shows typical AI generation artifacts - distorted characters"

## Настройка агрессивности

### Текущие настройки (баланс точность/ложные срабатывания)

```python
# .env
OPENROUTER_ANALYSIS_RUNS=2  # Консенсус из 2 прогонов
OPENROUTER_MODEL=google/gemini-2.5-pro  # Сильная модель
```

### Для максимальной агрессивности (меньше пропусков, больше ложных срабатываний)

Можно вручную в `scoring.py` изменить:

```python
# Строка 116: Снизить порог для "real"
elif final_score < 20 and not suspicious_local and not has_text:  # было 25

# Строка 148: Снизить порог блокировки "real"
if verdict == 'likely_real' and (ai_probability >= 20 or ...):  # было 25

# Строка 152-158: Снизить пороги upgrade
if verdict == 'suspicious' and (ai_probability >= 45 or ...):  # было 55
if verdict == 'suspicious' and (manipulation_probability >= 45 or ...):  # было 55
```

### Для меньших ложных срабатываний (строже, но может пропустить)

```python
# Увеличить пороги обратно до 30-35
# Увеличить OPENROUTER_ANALYSIS_RUNS=3 для большей стабильности
```

## Тестирование

### Проверка работы всех компонентов

```powershell
# 1. Проверка импортов
python -c "from detector.services.image_analysis import detect_noise_inconsistency, detect_frequency_anomalies, detect_copy_move, detect_text_in_image; print('OK')"

# 2. Проверка Django
python manage.py check

# 3. Запуск сервера
python manage.py runserver
```

### Что проверить на реальных фото

1. **AI-сгенерированное фото**
   - Ожидается: likely_ai_generated, 60-90% AI probability
   - Причины должны включать: frequency anomaly, unnatural textures, AI artifacts

2. **Отредактированное фото (Photoshop)**
   - Ожидается: likely_edited, 50-80% manipulation probability
   - Причины должны включать: noise inconsistency, compression differences, copy-move

3. **Фото с текстом**
   - Ожидается: Текст распознан и упомянут в reasons
   - Если текст подозрительный → suspicious минимум

4. **Настоящее фото с камеры**
   - Ожидается: likely_real, 20-40% confidence
   - Низкие AI/manipulation probabilities

## Ограничения и известные проблемы

### OCR (pytesseract)
- **Требует установки Tesseract** отдельно
- Если не установлен: text_info будет пустым, но остальное работает
- Точность зависит от качества и языка текста

### Copy-Move Detection
- **Медленнее** чем другие проверки (SIFT вычисления)
- Может давать false positives на повторяющихся паттернах (обои, текстуры)
- Лучше работает на фото > 1000x1000 пикселей

### Frequency Domain Analysis
- Может давать высокий риск на **легально обработанных** фото (HDR, фильтры)
- Не различает "художественная обработка" vs "фейк"

### Общие
- **Не 100% точность** - это вероятностная оценка
- Новые AI-модели могут обманывать систему
- Профессиональный фотошоп может быть незаметен
- Сильно сжатые фото (из соцсетей) дают много ложных срабатываний

## Итого: что изменилось

### Было (старая версия)
- Базовый EXIF, ELA, простые артефакты
- Один прогон модели
- Мягкий скоринг
- Много AI-фото проходили как "real"

### Стало (новая версия)
- **+3 продвинутых forensic-метода** (noise, frequency, copy-move)
- **+OCR и анализ текста**
- **Консенсус из 2 прогонов** модели
- **Детальный промпт** с 7 обязательными категориями проверки
- **Строгий скоринг** с advanced forensics mode
- **Агрессивные правила** блокировки "real" вердикта
- **Критические токены** для детекта клонирования и манипуляций

### Результат
- **Значительно меньше пропусков** AI-фото и отредактированных изображений
- **Детальные причины** с конкретными описаниями проблем
- **Распознавание текста** в изображениях
- **Детект клонированных областей** (copy-move forgery)
- **Частотный анализ** для AI-генерации
- **Анализ шума** для поиска вставок и ретуши
