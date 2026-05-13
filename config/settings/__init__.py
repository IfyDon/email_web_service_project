# Root cause 2 fix:
# When Django resolves "config.settings" it executes this __init__.py.
# Without an import here the package is empty — INSTALLED_APPS is never set,
# so none of our apps are visible to makemigrations / runserver.
#
# We re-export everything from dev for local development.
# In production, set DJANGO_SETTINGS_MODULE=config.settings.prod instead.

from .dev import *   # noqa: F401, F403