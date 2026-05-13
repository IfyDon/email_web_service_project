# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY . .
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
