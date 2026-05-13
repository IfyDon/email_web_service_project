from .base import *  # noqa
import sentry_sdk

DEBUG = False

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

sentry_sdk.init(dsn=config('SENTRY_DSN', default=''))  # noqa: F405
