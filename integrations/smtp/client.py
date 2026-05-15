"""
SMTP smart-host integration client.

Used as a fallback / dev alternative to AWS SES.
Reads Django's standard EMAIL_* settings so django.test.utils.override_settings
works out-of-the-box in tests.

Place: integrations/smtp/client.py
"""

import logging
import smtplib
import email.mime.multipart
import email.mime.text

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def send_email(
    *,
    from_email: str,
    from_name: str = "",
    to_email: str,
    subject: str,
    body_html: str = "",
    body_text: str = "",
    reply_to: str = "",
    headers: dict | None = None,
) -> str:
    """
    Send a single email via Django's EMAIL_* SMTP backend.

    Returns a synthetic message ID (SMTP doesn't guarantee one).
    Raises RuntimeError on send failure.
    """
    try:
        from_formatted = f"{from_name} <{from_email}>" if from_name else from_email

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text or " ",   # plain text required
            from_email=from_formatted,
            to=[to_email],
            reply_to=[reply_to] if reply_to else [],
            headers=headers or {},
        )

        if body_html:
            msg.attach_alternative(body_html, "text/html")

        msg.send(fail_silently=False)

        # SMTP doesn't return a message ID from the server — synthesise one
        import uuid
        synthetic_id = f"smtp-{uuid.uuid4()}"
        logger.info("SMTP sent %s → %s", synthetic_id, to_email)
        return synthetic_id

    except Exception as exc:
        logger.error("SMTP send error: %s", exc)
        raise RuntimeError(f"SMTP error: {exc}") from exc