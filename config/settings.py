"""
Django settings for config project.
"""
from pathlib import Path
import os
import dj_database_url
import cloudinary
from dotenv import load_dotenv

from config.secrets import cfg, cfg_bool


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'

# .env na raiz (local e Render) + credentials.py para segredos sem painel do Render
env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)

_serve_spa_env = cfg_bool('SERVE_REACT_SPA', False)
_spa_index = FRONTEND_DIST / 'index.html'
SERVE_REACT_SPA = _serve_spa_env or (
    bool(os.getenv('RENDER')) and _spa_index.is_file()
)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = cfg('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = cfg_bool('DEBUG', False)

ALLOWED_HOSTS = [h.strip() for h in str(cfg('ALLOWED_HOSTS', '127.0.0.1,localhost')).split(',') if h.strip()]
_render_host = os.getenv('RENDER_EXTERNAL_HOSTNAME', '').strip()
if _render_host and _render_host not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_host)


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
DATABASE_URL = cfg('DATABASE_URL')

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
_DATA_UPLOAD_MB = int(cfg('DATA_UPLOAD_MAX_MB', '20'))
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
    'DEFAULT_THROTTLE_RATES': {
        # Janelas curtas (por minuto), estilo varejo — bloqueio temporário, não espera de horas.
        'auth_login': '30/minute',
        'auth_register': '20/minute',
        'auth_password': '10/minute',
        'auth_verify': '60/minute',
        'auth_email_target': '5/minute',
    },
}


# CORS Configuration
_render_url = os.getenv('RENDER_EXTERNAL_URL', '').strip()
_cors_origins = cfg('CORS_ALLOWED_ORIGINS', 'http://127.0.0.1:3000,http://127.0.0.1:8000')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]
if _render_url and _render_url not in CORS_ALLOWED_ORIGINS:
    CORS_ALLOWED_ORIGINS.append(_render_url)
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True

# CSRF - necessário para produção com HTTPS
_csrf_origins = cfg('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
if _render_url and _render_url not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(_render_url)

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
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(cfg('ACCESS_TOKEN_EXPIRE_MINUTES', '10080'))


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
EMAIL_HOST = cfg('SMTP_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(cfg('SMTP_PORT', '587'))

# Configuração TLS/SSL automática baseada no host
_smtp_host = str(cfg('SMTP_HOST', '')).lower()
_smtp_use_ssl = cfg_bool('SMTP_USE_SSL', False)

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
EMAIL_TIMEOUT = int(cfg('SMTP_TIMEOUT', '30'))
EMAIL_HOST_USER = cfg('SMTP_USER', None)
EMAIL_HOST_PASSWORD = cfg('SMTP_PASSWORD', None)
DEFAULT_FROM_EMAIL = cfg('SMTP_FROM_EMAIL', EMAIL_HOST_USER or 'suporte.amorlize@gmail.com')
FRONTEND_URL = cfg('FRONTEND_URL') or _render_url or 'http://localhost:3000'
BACKEND_URL = cfg('BACKEND_URL') or _render_url or 'http://localhost:8000'


# Password Reset
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = int(cfg('PASSWORD_RESET_TOKEN_EXPIRE_HOURS', '24'))


# Mercado Pago Configuration
MERCADOPAGO_ACCESS_TOKEN = cfg('MERCADOPAGO_ACCESS_TOKEN', None)
MERCADOPAGO_WEBHOOK_SECRET = cfg('MERCADOPAGO_WEBHOOK_SECRET', None)
MERCADOPAGO_PUBLIC_KEY = cfg('MERCADOPAGO_PUBLIC_KEY', '') or None

# Nuvem Fiscal (NF-e) — https://dev.nuvemfiscal.com.br/docs/
# NUVEM_FISCAL_CLIENT_ID, NUVEM_FISCAL_CLIENT_SECRET, NUVEM_FISCAL_EMITTER_CNPJ no .env
# NUVEM_FISCAL_MOCK=true desliga a API real e simula emissão de NF-e (dev)
NUVEM_FISCAL_SANDBOX = cfg_bool('NUVEM_FISCAL_SANDBOX', True)

# Cloudinary — imagens de produtos
CLOUDINARY_CLOUD_NAME = cfg('CLOUDINARY_CLOUD_NAME', None)
CLOUDINARY_API_KEY = cfg('CLOUDINARY_API_KEY', None)
CLOUDINARY_API_SECRET = cfg('CLOUDINARY_API_SECRET', None)

CLOUDINARY_ENABLED = all([
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
])

CLOUDINARY_PRODUCTS_PREFIX = str(cfg('CLOUDINARY_PRODUCTS_PREFIX', 'galelugi/products')).strip().strip('/')

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
OPS_ALERT_WEBHOOK_URL = str(cfg('OPS_ALERT_WEBHOOK_URL', '')).strip()
OPS_ALERT_EMAIL = str(cfg('OPS_ALERT_EMAIL', 'suporte.amorlize@gmail.com')).strip()
OPS_ALERT_IN_DEBUG = cfg_bool('OPS_ALERT_IN_DEBUG', False)

# Senha do painel operacional (/painel/) — sessão; não exige login no site.
PAINEL_GATE_PASSWORD = cfg('PAINEL_GATE_PASSWORD', 'borlaria')

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
_sentry_dsn = str(cfg('SENTRY_DSN', '')).strip()
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=_sentry_dsn,
            integrations=[DjangoIntegration()],
            traces_sample_rate=float(cfg('SENTRY_TRACES_SAMPLE_RATE', '0')),
            send_default_pii=False,
            environment=cfg('SENTRY_ENVIRONMENT', 'production' if not DEBUG else 'development'),
        )
    except ImportError:
        import warnings

        warnings.warn(
            'SENTRY_DSN está definido mas sentry-sdk não está instalado. '
            'Execute: pip install "sentry-sdk[django]"',
            RuntimeWarning,
            stacklevel=1,
        )