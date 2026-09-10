from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if not DEBUG:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY for production.')
    import secrets
    secret_file = BASE_DIR / '.local-secret'
    if not secret_file.exists():
        try:
            with secret_file.open('x', encoding='utf-8') as file:
                file.write(secrets.token_urlsafe(64))
        except FileExistsError:
            pass
    SECRET_KEY = secret_file.read_text(encoding='utf-8').strip()
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY == 'dev-only-change-me'):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured('Use a random DJANGO_SECRET_KEY of at least 50 characters.')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]
CSRF_TRUSTED_ORIGINS = [u.strip() for u in os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if u.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'workbooks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uk'
TIME_ZONE = 'Europe/Kyiv'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# For production set SECURE_PROXY_SSL_HEADER / HTTPS settings at the hosting layer.

MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('DJANGO_MEDIA_ROOT', str(BASE_DIR / 'media')))

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if (not DEBUG or os.getenv('DJANGO_COLLECTSTATIC') == '1') else 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if not DEBUG:
    if not os.getenv('CREDENTIAL_ENCRYPTION_KEY'):
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured('Set CREDENTIAL_ENCRYPTION_KEY for production.')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    # Enable only behind a trusted reverse proxy that strips client-supplied headers.
    if os.getenv('DJANGO_TRUST_PROXY', '0') == '1':
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000
