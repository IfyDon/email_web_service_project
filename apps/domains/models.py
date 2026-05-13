"""
Domain model — represents a verified sending domain.

Each domain stores:
  - Verification status (SPF / DKIM / DMARC checked independently)
  - DKIM private key (RSA, generated on add) + public key (for DNS TXT record)
  - DNS hostnames the user must publish

Place: apps/domains/models.py
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models.base import UUIDModel, TimeStampedModel, OwnedModel


class Domain(UUIDModel, TimeStampedModel, OwnedModel):
    """
    A sending domain registered by a user.

    DNS records (SPF, DKIM, DMARC) must be published by the user
    before the domain is considered fully verified.
    """

    class Status(models.TextChoices):
        PENDING  = "pending",  "Pending"
        VERIFIED = "verified", "Verified"
        FAILED   = "failed",   "Failed"

    # ── Core ──────────────────────────────────────────────────────────────────
    name = models.CharField(
        max_length=253,
        unique=True,
        help_text="Bare domain: example.com (no https://)",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ── SPF ───────────────────────────────────────────────────────────────────
    spf_verified    = models.BooleanField(default=False)
    spf_last_check  = models.DateTimeField(null=True, blank=True)

    # ── DKIM ──────────────────────────────────────────────────────────────────
    # Selector: the DNS sub-hostname, e.g. "mf2024._domainkey.example.com"
    dkim_selector       = models.CharField(max_length=63, default="mf1")
    dkim_private_key    = models.TextField(blank=True, help_text="PEM-encoded RSA private key (never exposed via API)")
    dkim_public_key     = models.TextField(blank=True, help_text="Base64 DER public key – placed in DNS TXT record")
    dkim_verified       = models.BooleanField(default=False)
    dkim_last_check     = models.DateTimeField(null=True, blank=True)

    # ── DMARC ─────────────────────────────────────────────────────────────────
    dmarc_verified   = models.BooleanField(default=False)
    dmarc_last_check = models.DateTimeField(null=True, blank=True)

    # ── Timestamps ─────────────────────────────────────────────────────────────
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = "Domain"
        verbose_name_plural = "Domains"
        ordering            = ["-created_at"]
        indexes             = [
            models.Index(fields=["name"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return self.name

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_verified(self) -> bool:
        return self.status == self.Status.VERIFIED

    @property
    def all_records_verified(self) -> bool:
        return self.spf_verified and self.dkim_verified and self.dmarc_verified

    # ── DNS record helpers (what to show in the dashboard) ───────────────────

    @property
    def spf_record_value(self) -> str:
        """Expected SPF TXT value on the root domain."""
        return "v=spf1 include:spf.mailflow.io ~all"

    @property
    def dkim_record_host(self) -> str:
        """DNS hostname the user must create."""
        return f"{self.dkim_selector}._domainkey.{self.name}"

    @property
    def dkim_record_value(self) -> str:
        """Expected DKIM TXT value (p= is the base64 public key)."""
        pub = self.dkim_public_key.replace("\n", "")
        return f"v=DKIM1; k=rsa; p={pub}"

    @property
    def dmarc_record_host(self) -> str:
        return f"_dmarc.{self.name}"

    @property
    def dmarc_record_value(self) -> str:
        return "v=DMARC1; p=quarantine; rua=mailto:dmarc@mailflow.io"

    def dns_records_to_publish(self) -> list[dict]:
        """Return a list of DNS records the user must publish."""
        return [
            {
                "type":    "TXT",
                "host":    self.name,
                "value":   self.spf_record_value,
                "purpose": "SPF",
                "verified": self.spf_verified,
            },
            {
                "type":    "TXT",
                "host":    self.dkim_record_host,
                "value":   self.dkim_record_value,
                "purpose": "DKIM",
                "verified": self.dkim_verified,
            },
            {
                "type":    "TXT",
                "host":    self.dmarc_record_host,
                "value":   self.dmarc_record_value,
                "purpose": "DMARC",
                "verified": self.dmarc_verified,
            },
        ]

    # ── Status sync ───────────────────────────────────────────────────────────

    def sync_status(self) -> None:
        """
        Recompute overall status from individual record flags and save.
        Call after updating spf_verified / dkim_verified / dmarc_verified.
        """
        if self.all_records_verified:
            self.status      = self.Status.VERIFIED
            self.verified_at = timezone.now()
        elif not any([self.spf_verified, self.dkim_verified, self.dmarc_verified]):
            if self.status != self.Status.PENDING:
                self.status  = self.Status.FAILED
        self.save(update_fields=[
            "status", "verified_at",
            "spf_verified", "spf_last_check",
            "dkim_verified", "dkim_last_check",
            "dmarc_verified", "dmarc_last_check",
        ])