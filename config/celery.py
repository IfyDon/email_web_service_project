"""
Celery application entry point.
The app is imported in config/__init__.py so it is available
as soon as Django starts.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("email_web_service")

# Read CELERY_* settings from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in every installed app's tasks.py
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")