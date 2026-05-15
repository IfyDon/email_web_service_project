"""
Base settings shared across all environments.
Load environment-specific settings by importing from dev.py or prod.py.
"""

from pathlib import Path
from decouple import config, Csv

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # email_web_service/

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# ── Application registry ──────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",          # required by allauth
]

THIRD_PARTY_APPS = [
    # REST framework
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    # Auth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Celery results
    "django_celery_results",
    "django_celery_beat",
]

LOCAL_APPS = [
    "core",
     "apps.accounts.apps.AccountsConfig",
    "apps.authentication.apps.AuthenticationConfig",
    "apps.domains.apps.DomainsConfig",
    "apps.streams.apps.StreamsConfig",
    "apps.templates_app.apps.TemplatesAppConfig",
    "apps.email_messages.apps.EmailMessagesConfig",
    "apps.events.apps.EventsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.webhooks.apps.WebhooksConfig",
    "apps.suppressions.apps.SuppressionsConfig",
    "apps.inbound.apps.InboundConfig",
    "api",
    "web",
    "tracking",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",          # serve static files
    "corsheaders.middleware.CorsMiddleware",               # CORS – must be high
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",                 # 2FA
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.request_id.RequestIDMiddleware",      # attaches X-Request-ID
    "allauth.account.middleware.AccountMiddleware",        # required by allauth
]

# ── URL configuration ─────────────────────────────────────────────────────────
ROOT_URLCONF = "config.urls"

# ── Templates ─────────────────────────────────────────────────────────────────
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.quota_context",   # inject usage quota
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ── Database – SQLite for early development ───────────────────────────────────
# Phase 1.2: using SQLite; switch to PostgreSQL in Phase 6 (prod.py).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Static & media files ──────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# ── Default primary key ───────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Custom user model ─────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

# ── Sites framework (allauth) ─────────────────────────────────────────────────
SITE_ID = 1

# ── Django Allauth ────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.APIKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "100/min",
    },
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardResultsPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# ── DRF Spectacular (OpenAPI) ─────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "Email Delivery Service API",
    "DESCRIPTION": "Transactional & bulk email delivery – versioned REST API.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "django-cache"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ── Cache (Redis) ─────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True

# ── Email backend (console for dev, overridden in prod) ──────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@localhost")

# ── Logging placeholder (overridden per environment) ─────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# ── Minimal checklist for base.py ────────────────────────────────────────────

REQUIRED_BASE_SETTINGS = """
AUTH_USER_MODEL = "accounts.User"
SITE_ID = 1
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
"""

"""
ADD / REPLACE only these blocks inside config/settings/base.py.
Do not replace the entire file — merge these settings in.

Place: config/settings/base.py  (additions only)
"""

# ── After the existing CELERY block, add these lines ─────────────────────────

# Email dispatch backend: "ses" | "smtp"
# Switch to "ses" in prod.py once AWS credentials are configured
EMAIL_DISPATCH_BACKEND = "smtp"

# Public base URL used in tracking links and unsubscribe URLs
APP_BASE_URL = "http://localhost:8000"   # override in prod.py

# ── Anymail (optional – alternative ESP abstraction) ──────────────────────────
# Uncomment and configure if using django-anymail instead of raw boto3/SMTP
# ANYMAIL = {
#     "SENDGRID_API_KEY":  config("SENDGRID_API_KEY",  default=""),
#     "MAILGUN_API_KEY":   config("MAILGUN_API_KEY",   default=""),
#     "MAILGUN_SENDER_DOMAIN": config("MAILGUN_DOMAIN", default=""),
# }

# ── AWS SES (used when EMAIL_DISPATCH_BACKEND = "ses") ───────────────────────
AWS_ACCESS_KEY_ID     = config("AWS_ACCESS_KEY_ID",     default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_SES_REGION        = config("AWS_SES_REGION",        default="eu-west-1")

# ── SMTP fallback (dev / CI) ──────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# For production SMTP relay:
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST    = config("EMAIL_HOST",     default="smtp.mailgun.org")
# EMAIL_PORT    = config("EMAIL_PORT",     default=587, cast=int)
# EMAIL_USE_TLS = config("EMAIL_USE_TLS",  default=True, cast=bool)
# EMAIL_HOST_USER     = config("EMAIL_HOST_USER",     default="")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")