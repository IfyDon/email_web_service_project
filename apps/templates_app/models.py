"""
Email template models.

EmailTemplate  – the user-created template (HTML + plain text + metadata).
TemplateVersion – immutable version history; every save creates a new version.

Place: apps/templates_app/models.py
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models.base import UUIDModel, TimeStampedModel, OwnedModel


class EmailTemplate(UUIDModel, TimeStampedModel, OwnedModel):
    """
    A reusable email template owned by a user.

    Supports:
      - Raw HTML body (Jinja2 variables: {{ first_name }}, etc.)
      - Plain-text fallback body
      - MJML source (optional) – compiled to HTML on save
      - Version history via TemplateVersion
    """

    class BodyType(models.TextChoices):
        HTML  = "html",  "HTML"
        MJML  = "mjml",  "MJML"
        TEXT  = "text",  "Plain Text"

    # ── Identity ───────────────────────────────────────────────────────────────
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    slug        = models.SlugField(
        max_length=200,
        help_text="Machine-readable identifier for use in the API (e.g. 'welcome-email')",
        blank=True,
    )

    # ── Content ───────────────────────────────────────────────────────────────
    subject      = models.CharField(
        max_length=998,
        help_text="Email subject line. Supports Jinja2 variables: {{ first_name }}",
    )
    body_type    = models.CharField(
        max_length=5, choices=BodyType.choices, default=BodyType.HTML
    )
    body_html    = models.TextField(
        blank=True,
        help_text="HTML body. Use Jinja2 syntax for dynamic content.",
    )
    body_mjml    = models.TextField(
        blank=True,
        help_text="MJML source. Compiled to body_html automatically on save.",
    )
    body_text    = models.TextField(
        blank=True,
        help_text="Plain-text fallback. Auto-generated from HTML if left blank.",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────
    is_active       = models.BooleanField(default=True)
    current_version = models.PositiveIntegerField(default=1)

    # Variables declared by the template author for documentation
    # e.g. {"first_name": "Recipient first name", "action_url": "CTA button link"}
    variable_schema = models.JSONField(
        default=dict, blank=True,
        help_text="Declared template variables and their descriptions.",
    )

    class Meta:
        verbose_name        = "Email Template"
        verbose_name_plural = "Email Templates"
        ordering            = ["-created_at"]
        # A user cannot have two templates with the same slug
        unique_together     = [("user", "slug")]
        indexes             = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} (v{self.current_version})"

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)[:200]
        super().save(*args, **kwargs)

    # ── Version helpers ───────────────────────────────────────────────────────

    def snapshot(self) -> "TemplateVersion":
        """
        Save the current body as a new immutable TemplateVersion.
        Called by the service layer before each update.
        """
        return TemplateVersion.objects.create(
            template=self,
            version_number=self.current_version,
            subject=self.subject,
            body_html=self.body_html,
            body_text=self.body_text,
            body_mjml=self.body_mjml,
        )

    def restore_version(self, version_number: int) -> None:
        """Roll the template back to a specific version."""
        version = self.versions.get(version_number=version_number)
        self.subject   = version.subject
        self.body_html = version.body_html
        self.body_text = version.body_text
        self.body_mjml = version.body_mjml
        self.save()


class TemplateVersion(models.Model):
    """
    Immutable snapshot of an EmailTemplate at a given point in time.
    Created automatically before each update via EmailTemplate.snapshot().
    """

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template        = models.ForeignKey(
        EmailTemplate, on_delete=models.CASCADE, related_name="versions"
    )
    version_number  = models.PositiveIntegerField()
    subject         = models.CharField(max_length=998)
    body_html       = models.TextField(blank=True)
    body_text       = models.TextField(blank=True)
    body_mjml       = models.TextField(blank=True)
    created_at      = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name        = "Template Version"
        verbose_name_plural = "Template Versions"
        ordering            = ["-version_number"]
        unique_together     = [("template", "version_number")]

    def __str__(self) -> str:
        return f"{self.template.name} v{self.version_number}"