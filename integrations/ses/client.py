"""
AWS SES integration client.

Wraps boto3 SES send_raw_email / send_email so the rest of the
codebase never imports boto3 directly.

Place: integrations/ses/client.py
"""

import logging
import email as email_lib
import email.mime.multipart
import email.mime.text
import email.mime.base
from email import encoders

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return a boto3 SES client using settings credentials."""
    return boto3.client(
        "ses",
        region_name=getattr(settings, "AWS_SES_REGION", "eu-west-1"),
        aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
        aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
    )


def send_email(
    *,
    from_email: str,
    from_name: str = "",
    to_email: str,
    to_name: str = "",
    subject: str,
    body_html: str = "",
    body_text: str = "",
    reply_to: str = "",
    headers: dict | None = None,
    attachments: list | None = None,
) -> str:
    """
    Send a single email via AWS SES send_raw_email.

    Returns the SES MessageId string on success.
    Raises RuntimeError on SES / boto3 errors (caller handles retry).

    `headers` is a dict of extra headers e.g.:
        {
            "List-Unsubscribe": "<https://…>, <mailto:…>",
            "X-Mailer": "MailFlow/1.0",
        }
    """
    msg = _build_mime(
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        reply_to=reply_to,
        extra_headers=headers or {},
        attachments=attachments or [],
    )

    raw_bytes = msg.as_bytes()

    try:
        client = _get_client()
        response = client.send_raw_email(
            Source=_format_address(from_name, from_email),
            Destinations=[_format_address(to_name, to_email)],
            RawMessage={"Data": raw_bytes},
        )
        message_id = response["MessageId"]
        logger.info("SES accepted message %s → %s", message_id, to_email)
        return message_id

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_msg  = exc.response["Error"]["Message"]
        logger.error("SES ClientError [%s]: %s", error_code, error_msg)
        raise RuntimeError(f"SES error {error_code}: {error_msg}") from exc

    except BotoCoreError as exc:
        logger.error("SES BotoCoreError: %s", exc)
        raise RuntimeError(f"SES transport error: {exc}") from exc


# ── MIME builder ──────────────────────────────────────────────────────────────

def _format_address(name: str, email: str) -> str:
    if name:
        return f"{name} <{email}>"
    return email


def _build_mime(
    *,
    from_email: str,
    from_name: str,
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
    body_text: str,
    reply_to: str,
    extra_headers: dict,
    attachments: list,
) -> email.mime.multipart.MIMEMultipart:
    """Construct a MIME multipart/alternative message."""

    # Outer wrapper (needed for attachments; harmless when none)
    outer = email.mime.multipart.MIMEMultipart("mixed")
    outer["From"]    = _format_address(from_name, from_email)
    outer["To"]      = _format_address(to_name, to_email)
    outer["Subject"] = subject

    if reply_to:
        outer["Reply-To"] = reply_to

    for key, value in extra_headers.items():
        outer[key] = value

    # Multipart/alternative for text + html
    alt = email.mime.multipart.MIMEMultipart("alternative")

    if body_text:
        alt.attach(email.mime.text.MIMEText(body_text, "plain", "utf-8"))

    if body_html:
        alt.attach(email.mime.text.MIMEText(body_html, "html", "utf-8"))

    outer.attach(alt)

    # Attachments
    for attachment in attachments:
        # attachment = {"filename": "file.pdf", "content": bytes, "mimetype": "application/pdf"}
        part = email.mime.base.MIMEBase(*attachment["mimetype"].split("/"))
        part.set_payload(attachment["content"])
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment["filename"],
        )
        outer.attach(part)

    return outer