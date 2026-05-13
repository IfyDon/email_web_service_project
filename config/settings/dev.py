"""
Development settings – extend base.py.
Use: python manage.py runserver --settings=config.settings.dev
"""

from .base import *  # noqa: F401, F403

DEBUG = True

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
]

MIDDLEWARE = [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE  # noqa: F405

INTERNAL_IPS = ["127.0.0.1"]

# ── Dev email: print to console ───────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ── Disable throttling in development ────────────────────────────────────────
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []  # noqa: F405

# ── Allow all CORS origins in development ────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Django Debug Toolbar ──────────────────────────────────────────────────────
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}