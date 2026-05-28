# Email Delivery Service — Production-Ready Build Phases
> Full stack: Django REST API + React (Vite) Frontend  
> Security-hardened · Step-by-step · File-level detail

---

## Quick Reference — Services & Ports

| Service        | Port  | Command                                          |
|----------------|-------|--------------------------------------------------|
| Django dev     | 8000  | `python manage.py runserver`                     |
| React (Vite)   | 5173  | `npm run dev` (inside `frontend/`)               |
| PostgreSQL      | 5432  | `pg_ctl start` or Docker                         |
| Redis          | 6379  | `redis-server`                                   |
| Celery worker  | —     | `celery -A config.celery worker --loglevel=info` |
| Celery beat    | —     | `celery -A config.celery beat --loglevel=info`   |
| Flower (tasks) | 5555  | `celery -A config.celery flower`                 |

---

## ⚠️ Windows Developer Notes (read before starting)

```powershell
# Fix Unicode/emoji encoding errors in PowerShell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Set permanently for your user
[System.Environment]::SetEnvironmentVariable("PYTHONIOENCODING","utf-8","User")
```

---

---

# PHASE 1 — Project Foundation & Environment

**Goal:** Runnable Django project + React scaffold, correct folder structure, SQLite dev DB, all tooling installed.

---

## 1.1 — Repository & Virtual Environment

### Tasks

1. Create the project root folder
2. Initialise Git
3. Create and activate virtual environment
4. Set Python encoding permanently

### Commands

```bash
mkdir email_web_service && cd email_web_service
git init
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### Files to create

| File | Purpose |
|------|---------|
| `.gitignore` | Exclude `.venv/`, `*.pyc`, `.env`, `db.sqlite3`, `node_modules/`, `dist/` |
| `.env.example` | Template for all environment variables (never commit real `.env`) |
| `README.md` | Project overview, setup steps, architecture diagram |

### `.gitignore` content (minimum)

```gitignore
.venv/
__pycache__/
*.pyc
.env
db.sqlite3
staticfiles/
media/
node_modules/
dist/
.DS_Store
```

---

## 1.2 — Django Project Scaffold

### Tasks

1. Install Django and core dependencies
2. Create the project with `config/` as the settings package
3. Create the `requirements/` split files

### Commands

```bash
pip install django python-decouple
django-admin startproject config .
```

### Files to create / configure

| File | Action |
|------|--------|
| `requirements/base.txt` | Core packages (Django, DRF, Celery, boto3, etc.) |
| `requirements/dev.txt` | `-r base.txt` + pytest, debug-toolbar, faker |
| `requirements/prod.txt` | `-r base.txt` + gunicorn, sentry-sdk, whitenoise |
| `manage.py` | Generated — change default settings path to `config.settings.dev` |

### `requirements/base.txt`

```text
Django==5.0.6
djangorestframework==3.15.2
python-decouple==3.8
celery==5.4.0
django-celery-results==2.5.1
redis==5.0.6
django-redis==5.4.0
boto3==1.34.144
dnspython==2.6.1
django-cors-headers==4.4.0
django-ratelimit==4.1.0
django-storages==1.14.4
django-allauth==0.63.6
django-otp==1.5.0
drf-spectacular==0.27.2
psycopg2-binary==2.9.9
Pillow==10.4.0
requests==2.32.3
```

### `requirements/dev.txt`

```text
-r base.txt
pytest==8.2.2
pytest-django==4.8.0
factory-boy==3.3.0
coverage==7.5.4
django-debug-toolbar==4.4.2
Faker==25.8.0
```

### `requirements/prod.txt`

```text
-r base.txt
gunicorn==22.0.0
sentry-sdk==2.6.0
whitenoise==6.7.0
```

### Install everything

```bash
pip install -r requirements/dev.txt
```

---

## 1.3 — Settings Split (base / dev / prod)

### Files to create / configure

| File | Purpose |
|------|---------|
| `config/settings/__init__.py` | Empty |
| `config/settings/base.py` | Shared settings across all environments |
| `config/settings/dev.py` | `from .base import *` + DEBUG=True, SQLite, no HTTPS |
| `config/settings/prod.py` | `from .base import *` + security headers, PostgreSQL, WhiteNoise |

### `config/settings/base.py` — critical sections

```python
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── SECURITY ───────────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")
DEBUG       = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost").split(",")

# ── INSTALLED_APPS ─────────────────────────────────────────────────────
# Use full AppConfig paths so app labels (e.g. "accounts") are correct
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

# ── AUTH ────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"   # matches AccountsConfig.label

# ── DATABASES ──────────────────────────────────────────────────────────
# Overridden per environment (see dev.py / prod.py)
```

### `config/settings/dev.py`

```python
from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

# SQLite — zero external dependencies for dev
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
INTERNAL_IPS = ["127.0.0.1"]
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
CORS_ALLOW_ALL_ORIGINS = True
```

### `config/settings/prod.py`

```python
from .base import *
from decouple import config

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     config("DB_NAME"),
        "USER":     config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST":     config("DB_HOST", default="localhost"),
        "PORT":     config("DB_PORT", default="5432"),
    }
}

# ── SECURITY HEADERS ────────────────────────────────────────────────────
SECURE_HSTS_SECONDS            = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD            = True
SECURE_SSL_REDIRECT            = True
SESSION_COOKIE_SECURE          = True
CSRF_COOKIE_SECURE             = True
X_FRAME_OPTIONS                = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF    = True

MIDDLEWARE = ["whitenoise.middleware.WhiteNoiseMiddleware"] + MIDDLEWARE
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", default="").split(",")
```

### `.env.example`

```ini
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (prod only)
DB_NAME=emailservice
DB_USER=emailuser
DB_PASSWORD=emailpass
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# AWS SES
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_SES_REGION_NAME=us-east-1
AWS_STORAGE_BUCKET_NAME=

# Tracking
TRACKING_DOMAIN=http://localhost:8000
UNSUBSCRIBE_BASE_URL=http://localhost:8000/unsubscribe

# Sentry (prod)
SENTRY_DSN=

# CORS (prod)
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

---

## 1.4 — App Folder Structure & Renames

### ⚠️ Critical renames from the original plan

The original scaffold uses reserved Python/Django names that **cause conflicts**:

| Original folder | Renamed to | Why |
|----------------|------------|-----|
| `apps/auth/` | `apps/authentication/` | `auth` is a built-in Django module |
| `apps/messages/` | `apps/email_messages/` | `messages` is a built-in Django app |
| `apps/templates/` | `apps/templates_app/` | `templates` is a reserved Django folder name |

### Commands

```bash
# Create all app folders
mkdir -p apps/accounts apps/authentication apps/domains apps/streams
mkdir -p apps/templates_app apps/email_messages apps/events
mkdir -p apps/analytics apps/webhooks apps/suppressions apps/inbound
mkdir -p api/v1/views api/v1/serializers
mkdir -p web/views web/forms
mkdir -p core/models core/utils core/permissions core/pagination
mkdir -p core/exceptions core/middleware
mkdir -p services workers/tasks integrations/ses integrations/smtp integrations/storage
mkdir -p tracking tests/unit tests/integration tests/e2e
mkdir -p templates/registration templates/dashboard templates/tracking
mkdir -p static/css static/js static/img
```

### Each app needs these files

For **every** folder under `apps/`:

```
apps/<appname>/
├── __init__.py          ← default_app_config = "apps.<appname>.apps.<Name>Config"
├── apps.py              ← AppConfig with name="apps.<appname>" label="<appname>"
├── models.py
├── admin.py
└── migrations/
    └── __init__.py
```

### Example `apps/accounts/apps.py`

```python
from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name  = "apps.accounts"
    label = "accounts"          # ← used in AUTH_USER_MODEL and ForeignKeys
    verbose_name = "Accounts"
```

---

## 1.5 — React Frontend Scaffold (Vite — NOT Create React App)

> **Why Vite?** CRA is deprecated and unmaintained. Vite starts in <300 ms and has first-class HMR.

### Commands

```bash
# From the project root (email_web_service/)
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install axios react-router-dom recharts @headlessui/react
npm install -D @types/react @types/react-dom
```

### Files to configure after scaffold

| File | Change |
|------|--------|
| `frontend/tailwind.config.js` | Add `content: ["./index.html","./src/**/*.{js,jsx}"]` |
| `frontend/src/index.css` | Add Tailwind directives `@tailwind base/components/utilities` |
| `frontend/vite.config.js` | Add `proxy` to forward `/api` → `http://localhost:8000` |
| `frontend/src/main.jsx` | Wrap app in `<BrowserRouter>` |
| `frontend/src/api/client.js` | Axios instance with `baseURL` and auth token interceptor |

### `frontend/vite.config.js` — API proxy (fixes CORS in dev)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### `frontend/src/api/client.js`

```js
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach Bearer token from localStorage on every request
client.interceptors.request.use(config => {
  const token = localStorage.getItem('api_key')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export default client
```

### Page routing skeleton — `frontend/src/main.jsx`

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
```

### `frontend/src/App.jsx` — route map

```jsx
import { Routes, Route, Navigate } from 'react-router-dom'
import Login         from './pages/Login'
import Signup        from './pages/Signup'
import Dashboard     from './pages/Dashboard'
import Messages      from './pages/Messages'
import Domains       from './pages/Domains'
import Templates     from './pages/Templates'
import Analytics     from './pages/Analytics'
import Webhooks      from './pages/Webhooks'
import APIKeys       from './pages/APIKeys'
import Suppressions  from './pages/Suppressions'
import PrivateRoute  from './components/PrivateRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/login"  element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route element={<PrivateRoute />}>
        <Route path="/dashboard"    element={<Dashboard />} />
        <Route path="/messages"     element={<Messages />} />
        <Route path="/domains"      element={<Domains />} />
        <Route path="/templates"    element={<Templates />} />
        <Route path="/analytics"    element={<Analytics />} />
        <Route path="/webhooks"     element={<Webhooks />} />
        <Route path="/api-keys"     element={<APIKeys />} />
        <Route path="/suppressions" element={<Suppressions />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" />} />
    </Routes>
  )
}
```

### `frontend/src/components/PrivateRoute.jsx`

```jsx
import { Navigate, Outlet } from 'react-router-dom'

export default function PrivateRoute() {
  const apiKey = localStorage.getItem('api_key')
  return apiKey ? <Outlet /> : <Navigate to="/login" replace />
}
```

---

## 1.6 — First Verification Run

### Services to start

```bash
# Terminal 1 — Django
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver          # → http://localhost:8000

# Terminal 2 — React
cd frontend
npm run dev                         # → http://localhost:5173
```

### Checklist

- [ ] `http://localhost:8000/admin/` loads Django admin
- [ ] `http://localhost:5173/` loads the React app
- [ ] `http://localhost:5173/login` renders without console errors
- [ ] No migration errors in terminal 1

---

---

# PHASE 2 — Core Backend (Auth, Domains, Templates)

**Goal:** Secure user accounts, API key system, domain verification, template engine, suppression list.

---

## 2.1 — Custom User Model & API Key System

> **Do this before any migrations.** Changing AUTH_USER_MODEL after migrations exist requires a full DB reset.

### Files to create / modify

| File | Action |
|------|--------|
| `apps/accounts/models.py` | `User(AbstractUser)` + `APIKey` model |
| `apps/accounts/apps.py` | `label = "accounts"` |
| `apps/accounts/admin.py` | Register both models |
| `config/settings/base.py` | `AUTH_USER_MODEL = "accounts.User"` |
| `core/permissions/api_key_auth.py` | DRF `BaseAuthentication` subclass |
| `core/middleware/api_key.py` | Log API key usage per request |

### `apps/accounts/models.py` — key sections

```python
import hashlib, secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from core.models.base import BaseModel

class User(AbstractUser):
    email          = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    monthly_quota  = models.PositiveIntegerField(default=10_000)
    emails_sent    = models.PositiveIntegerField(default=0)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username"]

    def has_quota(self, n=1):
        return (self.emails_sent + n) <= self.monthly_quota

class APIKey(BaseModel):
    ROLE_FULL = "full"; ROLE_SEND = "send"; ROLE_READ = "read"
    ROLES = [(ROLE_FULL,"Full"),(ROLE_SEND,"Send only"),(ROLE_READ,"Read only")]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    label      = models.CharField(max_length=100)
    key_hash   = models.CharField(max_length=64, unique=True, db_index=True)
    key_prefix = models.CharField(max_length=8)   # shown to user for identification
    role       = models.CharField(max_length=20, choices=ROLES, default=ROLE_FULL)
    is_active  = models.BooleanField(default=True)
    last_used  = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    @classmethod
    def generate(cls, user, label, role=ROLE_FULL):
        raw = "es_" + secrets.token_urlsafe(32)
        obj = cls.objects.create(
            user=user, label=label, role=role,
            key_hash=cls.hash_key(raw),
            key_prefix=raw[:8],
        )
        return obj, raw   # raw shown ONCE then discarded
```

### Security rules for API keys

- **Never store the raw key** — only the SHA-256 hash
- **Show the raw key once** on creation, then discard
- **Prefix** (`es_abc12345`) is stored in plaintext for display only
- **Revoke** = set `is_active = False` (never delete, for audit trail)

---

## 2.2 — Authentication App (Login, 2FA, Password Reset)

### Files to create / modify

| File | Action |
|------|--------|
| `apps/authentication/models.py` | 2FA device model (or use django-otp) |
| `apps/authentication/views.py` | Login, logout, signup, password-reset views |
| `apps/authentication/urls.py` | URL routes for above |
| `apps/authentication/serializers.py` | DRF serializers for auth API endpoints |
| `config/settings/base.py` | Add `allauth` and `otp` config |

### `config/settings/base.py` — allauth config

```python
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
ACCOUNT_EMAIL_REQUIRED       = True
ACCOUNT_USERNAME_REQUIRED    = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_VERIFICATION   = "mandatory"

OTP_TOTP_ISSUER = "EmailService"   # shows in authenticator apps
```

### Security rules

- Require email verification before API key creation
- Lock accounts after 5 failed login attempts (`django-axes` package)
- 2FA required for production (optional in dev)
- Password reset tokens expire in 1 hour

---

## 2.3 — Domain Verification (DNS — SPF / DKIM / DMARC)

### Files to create / modify

| File | Action |
|------|--------|
| `apps/domains/models.py` | `SendingDomain` model with verification status fields |
| `apps/domains/admin.py` | Django admin registration |
| `core/utils/dns_utils.py` | `verify_spf()`, `verify_dkim()`, `verify_dmarc()` using `dnspython` |
| `api/v1/views/domains.py` | REST endpoints: list, add, trigger-verify |
| `api/v1/serializers/domains.py` | DRF serializers |

### `core/utils/dns_utils.py`

```python
import dns.resolver, dns.exception

def query_txt(domain: str) -> list[str]:
    try:
        return [b.decode() for r in dns.resolver.resolve(domain,"TXT") for b in r.strings]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.DNSException):
        return []

def verify_spf(domain):
    recs = query_txt(domain)
    spf  = [r for r in recs if r.startswith("v=spf1")]
    return {"verified": bool(spf), "record": spf[0] if spf else None}

def verify_dkim(domain, selector="mail"):
    recs = query_txt(f"{selector}._domainkey.{domain}")
    ok   = any("p=" in r for r in recs)
    return {"verified": ok, "record": recs[0] if recs else None}

def verify_dmarc(domain):
    recs = query_txt(f"_dmarc.{domain}")
    dmarc = [r for r in recs if r.startswith("v=DMARC1")]
    return {"verified": bool(dmarc), "record": dmarc[0] if dmarc else None}

def full_dns_check(domain, selector="mail"):
    return {
        "spf":   verify_spf(domain),
        "dkim":  verify_dkim(domain, selector),
        "dmarc": verify_dmarc(domain),
    }
```

---

## 2.4 — Suppression List

### Files to create / modify

| File | Action |
|------|--------|
| `apps/suppressions/models.py` | `Suppression(email, reason, user)` |
| `services/email_service.py` | Check suppression BEFORE enqueuing a send |
| `tracking/views.py` | Unsubscribe landing page — adds to suppression table |
| `templates/tracking/unsubscribed.html` | Confirmation page |

### Suppression reasons to handle

- `bounce` — hard bounce from relay
- `complaint` — spam report
- `unsubscribe` — recipient clicked unsubscribe link
- `manual` — admin or user added manually

---

---

# PHASE 3 — Email Sending Pipeline & Events

**Goal:** Async dispatch via Celery, retries, open/click tracking, webhook outbound dispatch.

---

## 3.1 — Celery & Redis Setup

### Services to start (in separate terminals)

```bash
# Start Redis (must be running before Celery)
redis-server                                              # macOS/Linux
# Windows: use Redis via WSL or Docker

# Celery worker
celery -A config.celery worker --loglevel=info --concurrency=4

# Celery beat (periodic tasks)
celery -A config.celery beat --loglevel=info

# Flower (task monitoring UI at http://localhost:5555)
celery -A config.celery flower --port=5555
```

### Files to create / modify

| File | Action |
|------|--------|
| `config/celery.py` | Celery app instance, autodiscover tasks |
| `config/settings/base.py` | `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| `workers/tasks/send_email.py` | Main send task with retry + backoff |
| `workers/tasks/process_events.py` | Handle bounce/complaint SNS notifications |
| `workers/tasks/webhook_dispatch.py` | POST to user's webhook URL |

### `config/celery.py`

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("emailservice")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

### `config/settings/base.py` — Celery config

```python
CELERY_BROKER_URL         = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND     = "django-db"
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TASK_SERIALIZER    = "json"
CELERY_RESULT_SERIALIZER  = "json"
CELERY_TIMEZONE           = "UTC"
CELERY_TASK_ALWAYS_EAGER  = False   # set True in tests to run tasks inline
```

### `workers/tasks/send_email.py` — retry with backoff

```python
from celery import shared_task
from django.utils import timezone
from apps.email_messages.models import Message
from apps.suppressions.models import Suppression
from integrations.ses.client import SESClient

@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,   # cap at 10 min between retries
)
def send_email_task(self, message_id: str):
    msg = Message.objects.select_related("user").get(pk=message_id)

    # Safety check — suppression list
    if Suppression.objects.filter(user=msg.user, email__iexact=msg.to_email).exists():
        msg.status = "failed"
        msg.last_error = "Recipient suppressed."
        msg.save(update_fields=["status","last_error","updated_at"])
        return

    msg.status = "sending"; msg.attempts += 1
    msg.save(update_fields=["status","attempts","updated_at"])

    client = SESClient()
    aws_id = client.send(
        from_email=msg.from_email, to=msg.to_email,
        subject=msg.subject, html_body=msg.html_body,
    )
    msg.status = "delivered"; msg.message_id = aws_id
    msg.sent_at = timezone.now()
    msg.save(update_fields=["status","message_id","sent_at","updated_at"])
```

---

## 3.2 — Open & Click Tracking

### Files to create / modify

| File | Action |
|------|--------|
| `tracking/views.py` | `open_pixel`, `click_redirect`, `unsubscribe` views |
| `tracking/urls.py` | Routes: `/t/o/<token>/`, `/t/c/<token>/`, `/t/u/<token>/` |
| `services/tracking_service.py` | `record_open()`, `record_click()` — updates DB + fires analytics |
| `templates/tracking/unsubscribed.html` | Confirmation page |

### Security rules for tracking

- Tokens are **base64-encoded** message UUIDs — never expose raw PKs
- Click redirects validate the destination URL against allowed domains
- Open pixel returns a real 1×1 GIF (not a 404) regardless of errors so email clients don't flag it

---

## 3.3 — Webhook Dispatch

### Files to create / modify

| File | Action |
|------|--------|
| `apps/webhooks/models.py` | `Webhook`, `WebhookDelivery` models |
| `services/webhook_service.py` | HMAC-signed POST, retry logic |
| `workers/tasks/webhook_dispatch.py` | Celery task wrapping `webhook_service.send()` |

### HMAC signing (security requirement)

```python
import hmac, hashlib, json, time

def sign_payload(secret: str, body: str) -> str:
    return "sha256=" + hmac.new(
        secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()
```

Users verify this signature on their end to confirm the webhook came from you.

---

---

# PHASE 4 — REST API & Documentation

**Goal:** Versioned, authenticated, throttled REST API with interactive OpenAPI docs.

---

## 4.1 — API Scaffolding

### Files to create / modify

| File | Action |
|------|--------|
| `api/urls.py` | Mount `/v1/` |
| `api/v1/urls.py` | All v1 routes |
| `api/v1/views/send.py` | `POST /v1/send`, `POST /v1/send/bulk` |
| `api/v1/views/messages.py` | `GET /v1/messages`, `GET /v1/messages/<id>` |
| `api/v1/views/domains.py` | Domains CRUD + `/verify` |
| `api/v1/views/templates.py` | Templates CRUD |
| `api/v1/serializers/` | One serializer file per resource |
| `core/pagination/__init__.py` | `StandardPagination(PageNumberPagination)` |
| `core/exceptions/__init__.py` | `custom_exception_handler` — uniform error format |
| `config/urls.py` | Mount `api/` and `web/` and `tracking/` |

### DRF config in `config/settings/base.py`

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.permissions.api_key_auth.APIKeyAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "100/min"},
    "DEFAULT_SCHEMA_CLASS":     "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}
```

---

## 4.2 — OpenAPI / Swagger Docs

### Files to configure

| File | Action |
|------|--------|
| `config/settings/base.py` | `SPECTACULAR_SETTINGS` dict |
| `config/urls.py` | Add `path("api/schema/", include("drf_spectacular.urls"))` |

### `SPECTACULAR_SETTINGS`

```python
SPECTACULAR_SETTINGS = {
    "TITLE":       "Email Delivery Service API",
    "DESCRIPTION": "Send, track, and manage transactional email at scale.",
    "VERSION":     "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },
}
```

### Access docs at

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc:       `http://localhost:8000/api/schema/redoc/`
- Raw schema:  `http://localhost:8000/api/schema/`

---

---

# PHASE 5 — Dashboard & Frontend (React)

**Goal:** Polished SaaS UI connected to the REST API via Axios.

---

## 5.1 — React Project Setup & Routing ✅ (current phase)

> **Why the dev server at `http://localhost:5173` fails:**
>
> The most common reasons and fixes are listed below.

### Troubleshooting `npm run dev` / `http://localhost:5173`

| Symptom | Cause | Fix |
|---------|-------|-----|
| `sh: vite: command not found` | `node_modules` not installed | Run `npm install` inside `frontend/` |
| `Error: Cannot find module` | Dependency missing | `npm install <package-name>` |
| Port 5173 already in use | Another process on that port | `npm run dev -- --port 5174` or kill the process |
| White screen, console 404s | Vite proxy not configured | Add proxy block in `vite.config.js` (see Phase 1.5) |
| `Tailwind classes not applying` | Content paths wrong in config | Update `tailwind.config.js` content array |
| `CORS error` on API calls | Django CORS not set | Add `corsheaders` to Django, set `CORS_ALLOW_ALL_ORIGINS=True` in dev |
| React page blank on route refresh | No server-side fallback | Add `historyApiFallback: true` in Vite config |

### Complete fix sequence

```bash
# 1. Make sure you are IN the frontend folder
cd frontend

# 2. Delete and reinstall node_modules if corrupted
rm -rf node_modules package-lock.json
npm install

# 3. Verify Vite is present
npx vite --version

# 4. Start the dev server
npm run dev

# 5. If port conflict — use a different port
npm run dev -- --port 5174
```

### Updated `vite.config.js` (with historyApiFallback)

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    historyApiFallback: true,   // fixes blank screen on route refresh
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
    },
  },
})
```

---

## 5.2 — Page & Component Structure

### Folder structure inside `frontend/src/`

```
frontend/src/
├── api/
│   ├── client.js          ← Axios instance (Bearer token interceptor)
│   ├── auth.js            ← login(), signup(), logout()
│   ├── messages.js        ← getMessages(), getMessage()
│   ├── domains.js         ← getDomains(), addDomain(), verifyDomain()
│   ├── templates.js       ← CRUD for email templates
│   ├── analytics.js       ← getStats()
│   ├── webhooks.js        ← CRUD for webhooks
│   └── apiKeys.js         ← generate(), revoke()
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx
│   │   ├── TopBar.jsx
│   │   └── Layout.jsx     ← wraps all dashboard pages
│   ├── ui/
│   │   ├── StatCard.jsx
│   │   ├── Badge.jsx      ← status pill (delivered/bounced/etc.)
│   │   ├── Table.jsx
│   │   ├── Modal.jsx
│   │   └── Button.jsx
│   ├── charts/
│   │   ├── VolumeChart.jsx   ← recharts AreaChart
│   │   └── RateChart.jsx     ← open rate / click rate bar chart
│   └── PrivateRoute.jsx
├── pages/
│   ├── Login.jsx
│   ├── Signup.jsx
│   ├── Dashboard.jsx      ← stats + recent messages
│   ├── Messages.jsx       ← list with filters
│   ├── MessageDetail.jsx
│   ├── Domains.jsx
│   ├── DomainDetail.jsx   ← DNS record display + verify button
│   ├── Templates.jsx
│   ├── TemplateEdit.jsx   ← HTML editor (Monaco)
│   ├── Analytics.jsx
│   ├── Webhooks.jsx
│   ├── APIKeys.jsx
│   ├── Suppressions.jsx
│   └── Billing.jsx
├── hooks/
│   ├── useAuth.js         ← reads/writes api_key from localStorage
│   └── useToast.js        ← notification helper
├── context/
│   └── AuthContext.jsx
├── App.jsx
├── main.jsx
└── index.css
```

---

## 5.3 — Dashboard & Analytics

### Files to create

| File | Key implementation detail |
|------|--------------------------|
| `pages/Dashboard.jsx` | Fetches `/api/v1/stats` on mount, renders `VolumeChart` + recent messages table |
| `components/charts/VolumeChart.jsx` | `recharts` `<AreaChart>` — sent / delivered / bounced over 30 days |
| `components/charts/RateChart.jsx` | `recharts` `<BarChart>` — open rate / click rate per day |
| `components/ui/StatCard.jsx` | Reusable card: label + big number + optional delta indicator |

### Install recharts

```bash
cd frontend
npm install recharts
```

---

## 5.4 — Domain Management UI

### Files to create

| File | Key implementation detail |
|------|--------------------------|
| `pages/Domains.jsx` | Lists domains, status badges (verified / pending / failed), "Add Domain" button |
| `pages/DomainDetail.jsx` | Shows SPF / DKIM / DMARC DNS records to copy, "Verify Now" button |
| `api/domains.js` | `verifyDomain(id)` → `GET /api/v1/domains/<id>/verify` → refreshes status |

---

## 5.5 — Template Editor

### Install Monaco (VS Code editor in browser)

```bash
npm install @monaco-editor/react
```

### `pages/TemplateEdit.jsx` — key sections

```jsx
import Editor from '@monaco-editor/react'

<Editor
  height="400px"
  language="html"
  value={htmlBody}
  onChange={setHtmlBody}
  theme="vs-dark"
  options={{ minimap: { enabled: false }, wordWrap: "on" }}
/>
```

---

---

# PHASE 6 — Production Readiness & Docker

**Goal:** Security hardened, monitored, containerised, one-command startup.

---

## 6.1 — Security & Compliance Hardening

### Files to modify

| File | Change |
|------|--------|
| `config/settings/prod.py` | All security headers (see Phase 1.3) |
| `services/email_service.py` | Add `List-Unsubscribe` header, physical address footer |
| `apps/accounts/models.py` | Ensure password hashing via Django's default PBKDF2 |
| `config/urls.py` | Remove debug routes in production |

### Security checklist

- [ ] `DEBUG = False` in production
- [ ] `SECRET_KEY` loaded from environment (never hardcoded)
- [ ] `ALLOWED_HOSTS` is a strict list (no `*`)
- [ ] HTTPS enforced via `SECURE_SSL_REDIRECT = True`
- [ ] HSTS header active with preload
- [ ] `SESSION_COOKIE_SECURE = True` and `CSRF_COOKIE_SECURE = True`
- [ ] API keys stored as SHA-256 hashes only
- [ ] All user passwords hashed by Django (PBKDF2 + SHA256)
- [ ] Rate limiting active per API key
- [ ] CORS origins locked to known frontend domains
- [ ] Admin URL changed from `/admin/` to a random path
- [ ] `django-axes` installed for brute-force login protection

### Change admin URL

```python
# config/urls.py
import os
ADMIN_URL = os.environ.get("ADMIN_URL", "admin")   # set to random string in prod
urlpatterns = [
    path(f"{ADMIN_URL}/", admin.site.urls),
    ...
]
```

---

## 6.2 — Caching & Database Optimisation

### Files to modify

| File | Change |
|------|--------|
| `config/settings/base.py` | Redis cache config |
| `apps/email_messages/models.py` | Add DB indexes on `user_id`, `created_at`, `status` |
| `apps/events/models.py` | Index on `message_id`, `event_type` |
| `services/analytics_service.py` | Cache stats queries in Redis (5 min TTL) |

### Model indexing example

```python
class Message(BaseModel):
    ...
    class Meta:
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["to_email"]),
        ]
```

---

## 6.3 — Monitoring & Logging

### Packages to install

```bash
pip install sentry-sdk
```

### Files to modify

| File | Change |
|------|--------|
| `config/settings/prod.py` | Sentry init, JSON logging config |
| `core/middleware/request_id.py` | Attach `X-Request-ID` to all responses |
| `config/urls.py` | Add `/health/` endpoint |

### `config/settings/prod.py` — structured logging

```python
import sentry_sdk
sentry_sdk.init(dsn=config("SENTRY_DSN", default=""), traces_sample_rate=0.1)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
```

### Health check view

```python
# config/urls.py
from django.http import JsonResponse
urlpatterns += [
    path("health/", lambda r: JsonResponse({"status": "ok"})),
]
```

---

## 6.4 — Docker & docker-compose

### Files to create

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage: build React, collect static, run Gunicorn |
| `docker-compose.yml` | Web + worker + beat + Redis + PostgreSQL |
| `.env.example` | Updated with all prod vars |
| `.dockerignore` | Exclude `.venv`, `node_modules`, `__pycache__`, `.git` |

### `Dockerfile` — multi-stage

```dockerfile
# ── Stage 1: Build React ──────────────────────────────────────────────
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build          # outputs to frontend/dist/

# ── Stage 2: Django + static files ───────────────────────────────────
FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements/prod.txt requirements/prod.txt
RUN pip install --no-cache-dir -r requirements/prod.txt

COPY . .
COPY --from=frontend-build /app/frontend/dist /app/static/frontend

RUN python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### `docker-compose.yml`

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: emailuser
      POSTGRES_PASSWORD: emailpass
      POSTGRES_DB: emailservice
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL","pg_isready -U emailuser"]
      interval: 5s; timeout: 5s; retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD","redis-cli","ping"]
      interval: 5s; timeout: 3s; retries: 5

  web:
    build: .
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db: { condition: service_healthy }
      redis: { condition: service_healthy }
    command: >
      sh -c "python manage.py migrate &&
             gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4"

  worker:
    build: .
    env_file: .env
    command: celery -A config.celery worker --loglevel=info --concurrency=4
    depends_on:
      - db
      - redis

  beat:
    build: .
    env_file: .env
    command: celery -A config.celery beat --loglevel=info
    depends_on:
      - redis

  flower:
    build: .
    env_file: .env
    command: celery -A config.celery flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis

volumes:
  pgdata:
```

### One-command startup

```bash
# Copy and fill in your .env
cp .env.example .env

# Build and start everything
docker-compose up --build

# Access points:
# Django API   → http://localhost:8000
# React UI     → http://localhost:8000/static/frontend/index.html
# Flower tasks → http://localhost:5555
# Admin        → http://localhost:8000/<ADMIN_URL>/
```

---

---

# Summary — What Changed From the Original Workflow

| Original | Updated / Added | Reason |
|----------|----------------|--------|
| CRA (`create-react-app`) | **Vite** | CRA is deprecated; Vite is 10–20× faster |
| `apps/auth/` | `apps/authentication/` | `auth` conflicts with Django's built-in `django.contrib.auth` |
| `apps/messages/` | `apps/email_messages/` | `messages` conflicts with Django's built-in messaging framework |
| `apps/templates/` | `apps/templates_app/` | `templates` is a reserved Django folder name |
| Generic `INSTALLED_APPS` paths | **Full `AppConfig` paths** | Required for `label=` to register correctly (fixes `makemigrations`) |
| `SECRET_KEY = config("SECRET_KEY")` | Added `default=` fallback | Prevents crash on first `runserver` without `.env` |
| No admin URL randomisation | **Random admin URL** | Prevents automated admin scanning attacks |
| No brute-force protection | **`django-axes`** | Locks account after N failed logins |
| SQLite only mentioned | **SQLite dev → PostgreSQL prod** | Explicitly staged with settings split |
| No Windows notes | **`PYTHONIOENCODING=utf-8`** | Fixes `UnicodeEncodeError` on Windows cp1252 terminals |
| Phase 5 had no debug section | **Troubleshooting table for Vite** | Fixes `localhost:5173` not loading |
| No health endpoint | **`/health/` JSON endpoint** | Required for Docker/K8s health checks |
| No logging config | **Structured JSON logging + Sentry** | Production observability |
| No HMAC webhook signing | **SHA-256 HMAC on all webhooks** | Security — allows receivers to verify authenticity |
| No DB index guidance | **Explicit index definitions** | Performance at scale |
