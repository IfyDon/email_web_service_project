#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    # Root cause 1 fix:
    # The original generated manage.py pointed to "config.settings" (a single
    # file that no longer exists after we split it into base/dev/prod).
    # Point directly at config.settings.dev for local development.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()