"""
drf-spectacular preprocessing and postprocessing hooks.

Registered in SPECTACULAR_SETTINGS["PREPROCESSING_HOOKS"] and
SPECTACULAR_SETTINGS["POSTPROCESSING_HOOKS"].

Place: api/schema_hooks.py
"""

import logging

logger = logging.getLogger(__name__)


# ── Preprocessing ─────────────────────────────────────────────────────────────

def preprocess_exclude_schema_endpoints(endpoints, **kwargs):
    """
    Strip internal / non-public endpoints from the generated schema.

    Excludes:
      - Django admin endpoints  (/admin/…)
      - Debug toolbar           (/__debug__/…)
      - Allauth internal views  (/accounts/…) — these are web views, not API
    """
    EXCLUDED_PREFIXES = ("/admin/", "/__debug__/", "/accounts/")

    return [
        (path, path_regex, method, callback)
        for (path, path_regex, method, callback) in endpoints
        if not any(path.startswith(p) for p in EXCLUDED_PREFIXES)
    ]


# ── Postprocessing ────────────────────────────────────────────────────────────

def postprocess_add_examples(result, generator, request, public, **kwargs):
    """
    Inject hand-crafted request/response examples into the schema.

    Adding examples via postprocessing keeps the view code clean and
    avoids cluttering @extend_schema decorators.
    """
    paths = result.get("paths", {})

    # ── POST /api/v1/send ─────────────────────────────────────────────────────
    _add_example(
        paths, "/api/v1/send", "post", "requestBody",
        name="TransactionalEmail",
        summary="Transactional email with HTML body",
        value={
            "to_email":   "alice@example.com",
            "to_name":    "Alice Smith",
            "from_email": "noreply@yourdomain.com",
            "from_name":  "Acme Corp",
            "subject":    "Your order has shipped!",
            "body_html":  "<h1>It's on its way!</h1><p>Your order #1234 is en route.</p>",
            "body_text":  "It's on its way! Your order #1234 is en route.",
            "tags":       ["transactional", "shipping"],
            "metadata":   {"order_id": "1234"},
        },
    )

    _add_example(
        paths, "/api/v1/send", "post", "requestBody",
        name="TemplatedEmail",
        summary="Send using a saved template",
        value={
            "to_email":          "bob@example.com",
            "template_id":       "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "template_context":  {"first_name": "Bob", "action_url": "https://app.example.com"},
        },
    )

    # ── POST /api/v1/send/bulk ────────────────────────────────────────────────
    _add_example(
        paths, "/api/v1/send/bulk", "post", "requestBody",
        name="BulkSend",
        summary="Personalised bulk send to three recipients",
        value={
            "template_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "from_email":  "noreply@yourdomain.com",
            "recipients": [
                {"to_email": "a@example.com", "context": {"first_name": "Alice"}},
                {"to_email": "b@example.com", "context": {"first_name": "Bob"}},
                {"to_email": "c@example.com", "context": {"first_name": "Carol"}},
            ],
        },
    )

    # ── POST /api/v1/domains/ ─────────────────────────────────────────────────
    _add_example(
        paths, "/api/v1/domains/", "post", "requestBody",
        name="AddDomain",
        summary="Register a sending domain",
        value={"name": "mail.yourdomain.com"},
    )

    # ── POST /api/v1/auth/api-keys/ ───────────────────────────────────────────
    _add_example(
        paths, "/api/v1/auth/api-keys/", "post", "requestBody",
        name="CreateAPIKey",
        summary="Create a production API key (non-expiring)",
        value={"label": "Production"},
    )

    return result


# ── Internal helper ───────────────────────────────────────────────────────────

def _add_example(paths: dict, path: str, method: str,
                 location: str, *, name: str, summary: str, value: dict) -> None:
    """
    Safely inject an example into a schema path → method → location block.
    Silently skips if the path / method is not in the schema.
    """
    operation = paths.get(path, {}).get(method, {})
    if not operation:
        return

    target = operation.get(location, {})
    content = target.get("content", {})
    json_block = content.get("application/json", {})

    examples = json_block.setdefault("examples", {})
    examples[name] = {"summary": summary, "value": value}