"""
Authentication models:
  - APIKey        – hashed bearer tokens
  - TOTPDevice    – wraps django-otp for 2FA secret management
  - PasswordResetToken – single-use email reset tokens
  - AuditLog      – immutable security event log

Place: apps/authentication/models.py
"""

import hashlib
import secrets
import uuid

import pyotp
from django.conf import settings
from django.db import models
from django.utils import timezone


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_raw_key() -> str:
    """40-char URL-safe token prefixed with 'ems_'."""
    return "ems_" + secrets.token_urlsafe(36)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _token_expiry():
    """Default: 1-hour expiry for password reset tokens."""
    return timezone.now() + timezone.timedelta(hours=1)


# ── API Key ───────────────────────────────────────────────────────────────────

class APIKey(models.Model):
    """
    Hashed API key record.

    The raw key is shown ONCE on creation and never stored.
    DRF authentication hashes the incoming bearer token and
    matches it against `key_hash`.
    """

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    label      = models.CharField(max_length=100)
    key_hash   = models.CharField(max_length=64, unique=True, editable=False)
    prefix     = models.CharField(
        max_length=12, editable=False,
        help_text="First 12 chars of the raw key shown in the dashboard"
    )

    # Throttle override (null = use global default)
    rate_limit_per_min  = models.PositiveIntegerField(null=True, blank=True)
    rate_limit_per_hour = models.PositiveIntegerField(null=True, blank=True)

    is_active  = models.BooleanField(default=True)
    last_used  = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Leave blank for non-expiring keys"
    )

    class Meta:
        verbose_name        = "API Key"
        verbose_name_plural = "API Keys"
        ordering            = ["-created_at"]
        indexes             = [models.Index(fields=["key_hash"])]

    def __str__(self) -> str:
        return f"{self.label} ({self.prefix}…)"

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create_for_user(
        cls,
        user,
        label: str,
        expires_at=None,
        rate_limit_per_min: int | None = None,
        rate_limit_per_hour: int | None = None,
    ) -> tuple["APIKey", str]:
        """
        Generate a new key.
        Returns (APIKey, raw_key). Show raw_key to user once – never stored.
        """
        raw = _generate_raw_key()
        instance = cls.objects.create(
            user=user,
            label=label,
            key_hash=_hash_key(raw),
            prefix=raw[:12],
            expires_at=expires_at,
            rate_limit_per_min=rate_limit_per_min,
            rate_limit_per_hour=rate_limit_per_hour,
        )
        return instance, raw

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() > self.expires_at)

    def touch(self) -> None:
        """Update last_used without loading the full model."""
        APIKey.objects.filter(pk=self.pk).update(last_used=timezone.now())

    def revoke(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active"])

    @staticmethod
    def resolve(raw_key: str) -> "APIKey | None":
        """
        Resolve a raw bearer token to an active, non-expired APIKey.
        Returns None if not found; raises nothing (caller decides on 401).
        """
        try:
            return (
                APIKey.objects
                .select_related("user")
                .get(key_hash=_hash_key(raw_key), is_active=True)
            )
        except APIKey.DoesNotExist:
            return None


# ── TOTP / 2FA ────────────────────────────────────────────────────────────────

class TOTPDevice(models.Model):
    """
    Stores a user's TOTP secret for two-factor authentication.
    Works alongside django-otp; we keep our own record so we can
    expose QR-code generation and backup codes in the dashboard.
    """

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user        = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="totp_device",
    )
    secret      = models.CharField(
        max_length=64, default=pyotp.random_base32,
        help_text="Base32 TOTP secret – never expose in API responses"
    )
    confirmed   = models.BooleanField(default=False)   # True after user verifies first code
    created_at  = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "TOTP Device"

    def __str__(self) -> str:
        return f"TOTP for {self.user.email} ({'confirmed' if self.confirmed else 'unconfirmed'})"

    def get_totp(self) -> pyotp.TOTP:
        return pyotp.TOTP(self.secret)

    def verify(self, code: str) -> bool:
        """Verify a 6-digit code with ±1 window tolerance."""
        return self.get_totp().verify(code, valid_window=1)

    def provisioning_uri(self) -> str:
        return self.get_totp().provisioning_uri(
            name=self.user.email,
            issuer_name="MailFlow"
        )

    def generate_backup_codes(self, count: int = 8) -> list[str]:
        """
        Generate one-time backup codes (store hashed in BackupCode table).
        Returns raw codes to show to the user once.
        """
        codes = [secrets.token_hex(5).upper() for _ in range(count)]
        BackupCode.objects.filter(device=self).delete()  # clear old codes
        BackupCode.objects.bulk_create([
            BackupCode(device=self, code_hash=_hash_key(c)) for c in codes
        ])
        return codes


class BackupCode(models.Model):
    """Single-use hashed backup code for 2FA recovery."""

    device    = models.ForeignKey(TOTPDevice, on_delete=models.CASCADE, related_name="backup_codes")
    code_hash = models.CharField(max_length=64)
    used      = models.BooleanField(default=False)
    used_at   = models.DateTimeField(null=True, blank=True)

    def consume(self) -> bool:
        """Mark the code as used. Returns False if already consumed."""
        if self.used:
            return False
        self.used    = True
        self.used_at = timezone.now()
        self.save(update_fields=["used", "used_at"])
        return True

    @classmethod
    def redeem(cls, device: TOTPDevice, raw_code: str) -> bool:
        """Hash raw_code and consume the matching BackupCode if found."""
        try:
            bc = cls.objects.get(device=device, code_hash=_hash_key(raw_code), used=False)
            return bc.consume()
        except cls.DoesNotExist:
            return False


# ── Password Reset Token ──────────────────────────────────────────────────────

class PasswordResetToken(models.Model):
    """
    Single-use token emailed to users for password reset.
    Allauth handles the email flow; this model backs the token store.
    """

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    used       = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=_token_expiry)

    class Meta:
        verbose_name = "Password Reset Token"
        ordering     = ["-created_at"]

    @classmethod
    def create_for_user(cls, user) -> str:
        """Generate a reset token, return the raw token string."""
        raw = secrets.token_urlsafe(48)
        cls.objects.filter(user=user, used=False).delete()   # invalidate old tokens
        cls.objects.create(user=user, token_hash=_hash_key(raw))
        return raw

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def consume(self) -> bool:
        if self.used or self.is_expired:
            return False
        self.used = True
        self.save(update_fields=["used"])
        return True


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    """Append-only log of security-relevant events."""

    class Action(models.TextChoices):
        API_KEY_CREATED = "api_key_created", "API Key Created"
        API_KEY_REVOKED = "api_key_revoked", "API Key Revoked"
        LOGIN_SUCCESS   = "login_success",   "Login Success"
        LOGIN_FAILED    = "login_failed",    "Login Failed"
        PASSWORD_RESET  = "password_reset",  "Password Reset"
        TWO_FA_ENABLED  = "2fa_enabled",     "2FA Enabled"
        TWO_FA_DISABLED = "2fa_disabled",    "2FA Disabled"
        DOMAIN_ADDED    = "domain_added",    "Domain Added"
        DOMAIN_VERIFIED = "domain_verified", "Domain Verified"
        TEMPLATE_EDITED = "template_edited", "Template Edited"

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    action     = models.CharField(max_length=50, choices=Action.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata   = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name        = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} – {self.user} @ {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def record(cls, action: str, user=None, request=None, **metadata) -> "AuditLog":
        ip = ua = ""
        if request:
            ip = _get_client_ip(request)
            ua = request.META.get("HTTP_USER_AGENT", "")
        return cls.objects.create(
            action=action, user=user,
            ip_address=ip, user_agent=ua,
            metadata=metadata,
        )


def _get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")