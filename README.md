# Fake Image Checker

Django MVP для проверки изображений на признаки AI-генерации, редактирования и визуальных аномалий.

## Что умеет

- загрузка JPG, PNG, WEBP
- проверка размера и базовой сигнатуры файла
- локальный анализ EXIF, ELA и простых визуальных артефактов
- отправка изображения в vision-модель через OpenRouter
- сохранение результатов в SQLite
- страницы результата, истории и Django admin

## Запуск

1. Создай и активируй виртуальное окружение.
2. Установи зависимости:

```powershell
pip install -r requirements.txt
```

3. Прогони миграции:

```powershell
python manage.py migrate
```

4. Создай админа:

```powershell
python manage.py createsuperuser
```

5. Запусти сервер:

```powershell
python manage.py runserver
```

## Маршруты

- `/` — главная
- `/check/` — POST-проверка
- `/result/<id>/` — результат
- `/history/` — история
- `/admin/` — админка

## Примечание

OpenRouter API key читается из `.env`. Если `.env` удалить, приложение попробует взять ключ из файла `txt` в корне проекта.
