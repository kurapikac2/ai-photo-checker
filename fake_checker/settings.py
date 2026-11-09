import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

DEBUG = os.getenv('DEBUG', 'False').strip().lower() == 'true'
configured_secret = os.getenv('DJANGO_SECRET_KEY', '').strip()
if DEBUG:
    # Local development only. Never rely on this fallback with DEBUG disabled.
    SECRET_KEY = configured_secret or 'django-insecure-fake-image-checker-local-dev-only'
else:
    if len(configured_secret) < 32 or configured_secret == 'change-me':
        raise ImproperlyConfigured(
            'Set a unique DJANGO_SECRET_KEY of at least 32 characters when DEBUG=False.'
        )
    SECRET_KEY = configured_secret
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if host.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'detector',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fake_checker.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fake_checker.wsgi.application'
ASGI_APPLICATION = 'fake_checker.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MAX_UPLOAD_SIZE_BYTES = int(float(os.getenv('MAX_UPLOAD_SIZE_MB', '10')) * 1024 * 1024)
MAX_UPLOAD_PIXELS = int(os.getenv('MAX_UPLOAD_PIXELS', '20000000'))
ANALYSIS_RETENTION_HOURS = max(1, int(os.getenv('ANALYSIS_RETENTION_HOURS', '24')))
# Keep same-origin form Origin headers usable for CSRF checks in Chromium,
# while withholding referrers from other origins.
SECURE_REFERRER_POLICY = 'same-origin'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.5-pro')
OPENROUTER_ANALYSIS_RUNS = max(1, int(os.getenv('OPENROUTER_ANALYSIS_RUNS', '2')))
