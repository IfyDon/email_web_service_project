# Email Web Service

A production-ready transactional email delivery SaaS built with Django + PostgreSQL.

## Quick Start

```bash
# 1. Activate the virtual environment
#    macOS / Linux
source .venv/bin/activate
#    Windows
.venv\Scripts\activate

# 2. Copy and edit environment variables
cp .env.example .env

# 3. Create the PostgreSQL database (psql)
createdb email_web_service

# 4. Apply migrations
python manage.py migrate --settings=config.settings.dev

# 5. Create a superuser
python manage.py createsuperuser --settings=config.settings.dev

# 6. Run the development server
python manage.py runserver --settings=config.settings.dev

# 7. Start Celery worker (separate terminal)
celery -A config worker -l info
```

## Project Layout

```
email_web_service/
├── config/          Django project settings & Celery
├── apps/            Domain apps (accounts, domains, messages …)
├── api/             DRF REST API (versioned)
├── web/             Dashboard views & forms
├── templates/       HTML templates (Tailwind + HTMX)
├── static/          CSS / JS / images
├── services/        Business-logic layer
├── workers/         Celery tasks
├── integrations/    AWS SES, SMTP, S3
├── tracking/        Open & click pixel endpoints
├── core/            Shared utils, middleware, permissions
└── tests/           unit / integration / e2e
```
