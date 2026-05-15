"""
Celery application — full production configuration.

Place: config/celery.py
"""

import os
from celery import Celery
from celery.utils.log import get_task_logger
from kombu import Queue, Exchange

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("email_web_service")

# Pull all CELERY_* keys from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in every installed app
app.autodiscover_tasks()

# ── Queue definitions ─────────────────────────────────────────────────────────
default_exchange = Exchange("default",  type="direct")
email_exchange   = Exchange("email",    type="direct")
webhook_exchange = Exchange("webhooks", type="direct")

app.conf.task_queues = (
    Queue("default",       default_exchange,  routing_key="default"),
    Queue("email.send",    email_exchange,    routing_key="email.send"),
    Queue("email.bulk",    email_exchange,    routing_key="email.bulk"),
    Queue("webhooks",      webhook_exchange,  routing_key="webhooks"),
)

app.conf.task_default_queue       = "default"
app.conf.task_default_exchange    = "default"
app.conf.task_default_routing_key = "default"

# ── Task routing ──────────────────────────────────────────────────────────────
app.conf.task_routes = {
    "workers.tasks.send_email.dispatch_send_task": {
        "queue":       "email.send",
        "routing_key": "email.send",
    },
    "workers.tasks.webhook_dispatch.*": {
        "queue":       "webhooks",
        "routing_key": "webhooks",
    },
}

# ── Worker settings ───────────────────────────────────────────────────────────
app.conf.update(
    # Serialisation
    task_serializer          = "json",
    result_serializer        = "json",
    accept_content           = ["json"],
    # Reliability
    task_acks_late           = True,
    task_reject_on_worker_lost = True,
    worker_prefetch_multiplier = 1,     # fair dispatch for long tasks
    # Results
    result_expires           = 86_400,  # 24 h
    # Timezone
    timezone                 = "UTC",
    enable_utc               = True,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")