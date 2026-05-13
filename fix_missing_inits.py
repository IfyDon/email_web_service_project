"""
Run from the email_web_service/ directory:

    python fix_missing_inits.py

Creates every __init__.py that might be missing after:
  - The folder renames (auth→authentication, messages_app→email_messages)
  - The setup script not generating __init__.py inside some subdirs
"""

from pathlib import Path
import sys
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent  # email_web_service/

REQUIRED: list[str] = [
    # ── Top-level packages ────────────────────────────────────────────────────
    "apps/__init__.py",
    "api/__init__.py",
    "api/v1/__init__.py",
    "api/v1/views/__init__.py",
    "api/v1/serializers/__init__.py",
    "core/__init__.py",
    "core/models/__init__.py",
    "core/utils/__init__.py",
    "core/permissions/__init__.py",
    "core/pagination/__init__.py",
    "core/exceptions/__init__.py",
    "core/middleware/__init__.py",
    "services/__init__.py",
    "web/__init__.py",
    "web/views/__init__.py",
    "web/forms/__init__.py",
    "tracking/__init__.py",
    "workers/__init__.py",
    "workers/tasks/__init__.py",
    "integrations/__init__.py",
    "integrations/ses/__init__.py",
    "integrations/smtp/__init__.py",
    "integrations/storage/__init__.py",

    # ── Domain apps (including renamed ones) ──────────────────────────────────
    "apps/accounts/__init__.py",
    "apps/authentication/__init__.py",   # renamed from apps/auth/
    "apps/domains/__init__.py",
    "apps/streams/__init__.py",
    "apps/templates_app/__init__.py",
    "apps/email_messages/__init__.py",   # renamed from apps/messages_app/
    "apps/events/__init__.py",
    "apps/analytics/__init__.py",
    "apps/webhooks/__init__.py",
    "apps/suppressions/__init__.py",
    "apps/inbound/__init__.py",

    # ── Management commands ───────────────────────────────────────────────────
    "core/management/__init__.py",
    "core/management/commands/__init__.py",
]

created = 0
for rel in REQUIRED:
    path = ROOT / rel
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        print(f"  ✅  created  {rel}")
        created += 1
    else:
        print(f"  ✔   exists   {rel}")

print(f"\nDone — {created} file(s) created.")
