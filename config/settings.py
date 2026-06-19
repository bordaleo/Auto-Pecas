"""
Django settings for config project.
"""
from pathlib import Path
import os
import dj_database_url
import cloudinary
from dotenv import load_dotenv


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'
SERVE_REACT_SPA = os.getenv('SERVE_REACT_SPA', '').lower() in ('1', 'true', 'yes')

# Carrega .env apenas em desenvolvimento (não sobrescreve variáveis do Render/Heroku)
# No Render, variáveis vêm do Environment; .env não é commitado
if not os.getenv('RENDER'):
    env_path = BASE_DIR / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    
    # Local apps
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Alertas em falhas não tratadas (último na lista = primeiro em process_exception)
    'config.middleware.ops_alert_middleware.OpsAlertMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.site_domain',
                'config.context_processors.mercadopago_public_key',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# PostgreSQL obrigatório - usa dj-database-url (compatível com Render, Heroku, etc.)
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL não configurado. PostgreSQL é obrigatório. "
        "No Render: crie um banco PostgreSQL e vincule ao serviço (DATABASE_URL é injetado automaticamente). "
        "Localmente: configure no .env no formato postgresql://usuario:senha@host:porta/nome_do_banco"
    )

# dj-database-url lida com postgres://, postgresql://, SSL (Render adiciona sslmode na URL)
DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 6,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Custom User Model
AUTH_USER_MODEL = 'api.User'


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Editor envia fotos em base64 no JSON (hero + polaroids); limite padrão (2,5 MB) quebra no celular
_DATA_UPLOAD_MB = int(os.getenv('DATA_UPLOAD_MAX_MB', '20'))
DATA_UPLOAD_MAX_MEMORY_SIZE = _DATA_UPLOAD_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE


# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'api.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
}


# CORS Configuration
_cors_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://127.0.0.1:8000')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True

# CSRF - necessário para produção com HTTPS
_csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'cache-control',  # Permite Cache-Control header
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]


# JWT Settings
JWT_SECRET_KEY = SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '10080'))


# Email Configuration (SMTP)
# IMPORTANTE: O Render bloqueia conexões SMTP para Gmail (erro 101)
# SOLUÇÃO: Use Brevo ou SendGrid SMTP no Render (ainda é SMTP, mas funciona!)
# 
# Para Gmail (desenvolvimento local):
#   SMTP_HOST=smtp.gmail.com
#   SMTP_PORT=587
#   SMTP_USER=seu-email@gmail.com
#   SMTP_PASSWORD=senha-de-app
#   SMTP_FROM_EMAIL=seu-email@gmail.com
#
# Para Brevo (produção no Render):
#   IMPORTANTE: Se a porta 587 der timeout, use a porta 465 com SSL!
#   SMTP_HOST=smtp-relay.brevo.com (ou smtp.brevo.com)
#   SMTP_PORT=465 (recomendado para Render - use SSL) ou 587 (TLS - pode dar timeout)
#   SMTP_USER=seu-email@exemplo.com (email de login da conta Brevo, formato: xxxxx@smtp-brevo.com)
#   SMTP_PASSWORD=sua-senha-SMTP (senha SMTP específica, não a senha da conta)
#   SMTP_FROM_EMAIL=seu-email@exemplo.com (email verificado no Brevo)
#   SMTP_USE_SSL=true (OBRIGATÓRIO para porta 465, false para porta 587 com TLS)
#   SMTP_TIMEOUT=180 (aumentado para evitar timeout - Render pode ser lento)
#
# Para SendGrid (produção no Render):
#   SMTP_HOST=smtp.sendgrid.net
#   SMTP_PORT=2525 (ou 587 - tente 2525 se 587 der timeout)
#   SMTP_USER=apikey
#   SMTP_PASSWORD=SG.sua-api-key-do-sendgrid
#   SMTP_FROM_EMAIL=suporte.amorlize@gmail.com (email verificado no SendGrid)
#   SMTP_TIMEOUT=120 (aumentado para evitar timeout)
    
EMAIL_BACKEND = 'config.email_backends.EmailBackend'
EMAIL_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('SMTP_PORT', '587'))

# Configuração TLS/SSL automática baseada no host
# Gmail/SendGrid na porta 587 usa TLS, porta 465 usa SSL
# Brevo: porta 587 (TLS) pode dar timeout no Render, use 465 (SSL) como alternativa
_smtp_host = os.getenv('SMTP_HOST', '').lower()
_smtp_use_ssl = os.getenv('SMTP_USE_SSL', '').lower() in ('true', '1', 'yes')

# Detecção automática para Brevo: se for Brevo e porta 587, tenta usar SSL na porta 465
if 'brevo' in _smtp_host and EMAIL_PORT == 587 and not _smtp_use_ssl:
    # Para Brevo no Render, porta 465 com SSL é mais confiável que 587 com TLS
    # Mas só muda se SMTP_USE_SSL não estiver explicitamente configurado
    # O usuário pode forçar SSL configurando SMTP_USE_SSL=true
    pass  # Mantém TLS na 587 por padrão, mas permite override com SMTP_USE_SSL

if _smtp_use_ssl:
    # SSL na porta 465
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
    if EMAIL_PORT == 587:
        EMAIL_PORT = 465
else:
    # TLS na porta 587 (padrão Gmail, SendGrid e Brevo)
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False

# Timeout para SMTP
# IMPORTANTE: No Render, conexões SMTP podem ser bloqueadas. 
# Se houver timeout, o email será enviado de forma assíncrona para não bloquear o registro.
# Timeout menor (30s) evita esperar muito tempo quando há bloqueio de rede
EMAIL_TIMEOUT = int(os.getenv('SMTP_TIMEOUT', '30'))
EMAIL_HOST_USER = os.getenv('SMTP_USER', None)
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASSWORD', None)
DEFAULT_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL', EMAIL_HOST_USER or 'suporte.amorlize@gmail.com')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:8000')


# Password Reset
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(os.getenv('PASSWORD_RESET_TOKEN_EXPIRE_HOURS', '24'))


# Mercado Pago Configuration
MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN', None)
MERCADOPAGO_WEBHOOK_SECRET = os.getenv('MERCADOPAGO_WEBHOOK_SECRET', None)
# Public Key para o frontend (Bricks). Em produção use a chave de PRODUÇÃO para evitar 401 na API de CEP (boleto).
# Configure via variável de ambiente MERCADOPAGO_PUBLIC_KEY no Render.
# Public Key de produção: APP_USR-77e67d38-7d72-45f6-900d-43be585effcd
MERCADOPAGO_PUBLIC_KEY = os.getenv('MERCADOPAGO_PUBLIC_KEY', '') or None

# Cloudinary — imagens de produtos
CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME', None)
CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY', None)
CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET', None)

CLOUDINARY_ENABLED = all([
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
])

CLOUDINARY_PRODUCTS_PREFIX = os.getenv('CLOUDINARY_PRODUCTS_PREFIX', 'galelugi/products').strip().strip('/')

if CLOUDINARY_ENABLED:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


# Django Admin Configuration
ADMIN_SITE_HEADER = "Galelugi Peças — Administração"
ADMIN_SITE_TITLE = "Galelugi Admin"
ADMIN_INDEX_TITLE = "Painel de Controle"

# X-Frame-Options
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Segurança HTTPS (Render usa proxy reverso)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SAMESITE = 'Lax'

# --- Alertas operacionais (marketing / produção) ---
# OPS_ALERT_WEBHOOK_URL: Discord (…/api/webhooks/…), Slack ou URL JSON genérica — definir no Render (segredo).
# OPS_ALERT_EMAIL: por defeito suporte; override com env.
# OPS_ALERT_IN_DEBUG=1: também alertar em desenvolvimento (evitar ruído no dia a dia).
OPS_ALERT_WEBHOOK_URL = os.getenv('OPS_ALERT_WEBHOOK_URL', '').strip()
OPS_ALERT_EMAIL = os.getenv(
    'OPS_ALERT_EMAIL',
    'suporte.amorlize@gmail.com',
).strip()
OPS_ALERT_IN_DEBUG = os.getenv('OPS_ALERT_IN_DEBUG', '').lower() in ('1', 'true', 'yes')

# Senha do painel operacional (/painel/) — sessão; não exige login no site. Override em produção.
PAINEL_GATE_PASSWORD = os.getenv('PAINEL_GATE_PASSWORD', 'borlaria')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'ops_alert': {
            'class': 'api.logging_handlers.OpsAlertLogHandler',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'ops_alert'],
            'level': 'ERROR',
            'propagate': False,
        },
        'api': {
            'handlers': ['ops_alert'],
            'level': 'ERROR',
            'propagate': True,
        },
        'services': {
            'handlers': ['ops_alert'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Sentry (opcional): pip install sentry-sdk; defina SENTRY_DSN no Render.
_sentry_dsn = os.getenv('SENTRY_DSN', '').strip()
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0')),
            send_default_pii=False,
            environment=os.getenv('SENTRY_ENVIRONMENT', 'production' if not DEBUG else 'development'),
        )
    except ImportError:
        import warnings

        warnings.warn(
            'SENTRY_DSN está definido mas sentry-sdk não está instalado. '
            'Execute: pip install "sentry-sdk[django]"',
            RuntimeWarning,
            stacklevel=1,
        )