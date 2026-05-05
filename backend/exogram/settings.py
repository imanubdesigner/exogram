"""
Django settings for exogram project.
"""
from datetime import timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')  # MUST be set in .env — no default for security
DEBUG = config('DEBUG', default=False, cast=bool)  # Default to False for safety
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
SENTRY_DSN = config('SENTRY_DSN', default='').strip()

# Sentry solo se activa si hay DSN. En dev/CI con DSN vacío queda en no-op.
if SENTRY_DSN and SENTRY_DSN.startswith('https://'):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=0.1,
        # Si el volumen transaccional crece mucho en producción, bajar a 0.01
        # o menos para controlar costo/ruido de performance traces.
    )

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'pgvector',
    'django_celery_beat',

    # Local apps
    'accounts',
    'books',
    'discovery',
    'social',
    'affinity',
    'articles',
    'threads',
    # App "sin modelos" para migraciones operativas del proyecto (extensiones DB).
    'exogram',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    # Con auth basada en cookies, este middleware es obligatorio. DRF no
    # aplica protección CSRF automática en vistas autenticadas por cookie.
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # CSP: cubre admin y dev server. En producción Caddy también lo emite.
    'exogram.middleware.ContentSecurityPolicyMiddleware',
]

ROOT_URLCONF = 'exogram.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'exogram.wsgi.application'

# Database
# CONN_MAX_AGE: reutilizar conexiones TCP por 10 minutos en vez de abrir/cerrar
# por request. Reduce latencia ~3-5ms por request y contención de conexiones.
database_url = config('DATABASE_URL', default='')
if database_url:
    parsed = urlparse(database_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname or '',
            'PORT': str(parsed.port or '5432'),
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB', default='exogram'),
            'USER': config('POSTGRES_USER', default='exogram'),
            'PASSWORD': config('POSTGRES_PASSWORD'),
            'HOST': config('DB_HOST', default='db'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,
        }
    }

# Test runner personalizado que habilita pgvector antes de crear tablas.
# Sin esto, VectorField falla con "type vector does not exist" en test runs.
TEST_RUNNER = 'exogram.test_runner.PgVectorTestRunner'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# CORS settings
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173'
).split(',')
CORS_ALLOW_CREDENTIALS = True  # Required for HttpOnly cookies

# Cookies de sesión/csrf endurecidas para flujos basados en cookies.
SESSION_COOKIE_SAMESITE = 'Lax'  # Mitiga CSRF cross-site manteniendo navegación same-site
CSRF_COOKIE_SAMESITE = 'Lax'  # Misma protección para cookie de CSRF
CSRF_COOKIE_HTTPONLY = False  # Debe leerse desde JS para Double Submit Cookie

# CSRF trusted origins sin wildcards: listar explícitamente dominios permitidos.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='http://localhost:5173,http://127.0.0.1:5173,https://exogram.app'
).split(',')

# CSRF_COOKIE_HTTPONLY=False es intencional: el token CSRF está diseñado para
# ser leído por JS. El JWT permanece HttpOnly; cumplen funciones de seguridad distintas.

# Security Headers
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME sniffing
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content-Security-Policy aplicado vía middleware propio (sin dependencias extra).
# En producción Caddy también lo emite; esta capa cubre el admin y el dev server.
# 'unsafe-inline' en style-src es necesario para Django admin y estilos dinámicos de Vue.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob: https://covers.openlibrary.org; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

# HTTPS hardening se habilita explícitamente en entornos con TLS.
FORCE_HTTPS = config('FORCE_HTTPS', default=False, cast=bool)
if FORCE_HTTPS:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Admin URL - Obfuscate to prevent enumeration
ADMIN_URL = config('ADMIN_URL', default='admin/')

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
# DatabaseScheduler persiste estado de beat en PostgreSQL: sobrevive reinicios
# de contenedor y permite inspección/edición desde Django admin.
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Modelo C: promoción automática de nivel de confianza (diaria)
# Activa: promote_trust_levels_task queda programada diariamente.
#
# NOTA: Esta schedule en código actúa como seed inicial. El DatabaseScheduler
# la persiste en PostgreSQL tras la primera ejecución. Para cambios posteriores
# a la frecuencia, editar desde Django admin → Periodic Tasks (fuente de verdad
# es la DB, no este dict).
CELERY_BEAT_SCHEDULE = {
    'promote-trust-levels-daily': {
        'task': 'books.tasks.promote_trust_levels_task',
        'schedule': 86400,  # cada 24hs en segundos
    },
    'beat-heartbeat': {
        'task': 'books.tasks.beat_heartbeat',
        'schedule': 60.0,  # cada 60 segundos
    },
}

# OpenLibrary API
OPENLIBRARY_API_URL = config('OPENLIBRARY_API_URL', default='https://openlibrary.org/api')


# Authentication Backend
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Auth cookies (JWT en HttpOnly cookies)
JWT_ACCESS_COOKIE_NAME = config('JWT_ACCESS_COOKIE_NAME', default='exo_access')
JWT_REFRESH_COOKIE_NAME = config('JWT_REFRESH_COOKIE_NAME', default='exo_refresh')
JWT_ACCESS_COOKIE_PATH = config('JWT_ACCESS_COOKIE_PATH', default='/api/')
JWT_REFRESH_COOKIE_PATH = config('JWT_REFRESH_COOKIE_PATH', default='/api/auth/')
JWT_COOKIE_SECURE = config('JWT_COOKIE_SECURE', default=FORCE_HTTPS, cast=bool)
JWT_AUTH_COOKIE_SAMESITE = 'Lax'  # Restringe envío cross-site del JWT cookie
JWT_COOKIE_SAMESITE = config('JWT_COOKIE_SAMESITE', default=JWT_AUTH_COOKIE_SAMESITE)
JWT_COOKIE_DOMAIN = config('JWT_COOKIE_DOMAIN', default='') or None

# Frontend URL para links en emails de invitación
FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:5173')
PASSWORD_RESET_TOKEN_TTL_HOURS = config('PASSWORD_RESET_TOKEN_TTL_HOURS', default=2, cast=int)

# Email backend
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='postal')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@tudominio.com')

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_TOKEN_MINUTES', default=20, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_TOKEN_DAYS', default=7, cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# REST Framework (única declaración — JWT + paginación)
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'accounts.authentication.CookieJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Rate Limiting - Critical security controls
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'exogram.throttles.DefaultUserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/hour',      # Public endpoints: 20 requests per hour
        # El límite global anterior (100/h) rompía sesiones largas de chat con polling.
        # Estos scopes separan patrones de uso reales: chat (alto volumen), auth (estricto),
        # búsqueda semántica (costosa) y un default de usuario más razonable.
        'default_user': '500/hour',
        'chat_polling': '2000/hour',
        'auth': '20/hour',
        'search': '200/hour',
        'user': '500/hour',     # Alias legacy para cualquier UserRateThrottle explícito
    }
}

# Invitaciones
INVITATION_EXPIRY_DAYS = 30
MAX_INVITATIONS_PER_USER = 10

# ──────────────────────────────────────────────────────────────────────────────
# Logging — Structured JSON en producción para observabilidad.
# En desarrollo con DEBUG=True se usa formato legible por humanos.
# ──────────────────────────────────────────────────────────────────────────────
_LOG_FORMAT = (
    '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    if DEBUG
    else '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': _LOG_FORMAT,
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        # App loggers
        'books': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'affinity': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
