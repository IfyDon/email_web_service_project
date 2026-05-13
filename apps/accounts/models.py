"""
Custom User model + Team model.

Place: apps/accounts/models.py
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


# ── Manager ───────────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None, **extra):
        if not email:
            raise ValueError("Email address is required.")
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff",     True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_verified",  True)
        return self.create_user(email, password, **extra)


# ── User ──────────────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):
    """
    Central user record – identified by email, no username.
    Inherited by all other models via settings.AUTH_USER_MODEL.
    """

    class Role(models.TextChoices):
        OWNER  = "owner",  "Owner"
        ADMIN  = "admin",  "Admin"
        MEMBER = "member", "Member"

    # ── Fields ────────────────────────────────────────────────────────────────
    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email     = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    role      = models.CharField(
        max_length=10, choices=Role.choices, default=Role.MEMBER
    )

    # Status
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)   # email confirmed

    # 2FA
    otp_enabled = models.BooleanField(default=False)

    # Quota (emails per month)
    monthly_quota   = models.PositiveIntegerField(default=10_000)
    emails_sent_mtd = models.PositiveIntegerField(default=0)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login  = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name        = "User"
        verbose_name_plural = "Users"
        ordering            = ["-date_joined"]
        indexes             = [models.Index(fields=["email"])]

    def __str__(self) -> str:
        return self.email

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def quota_remaining(self) -> int:
        return max(0, self.monthly_quota - self.emails_sent_mtd)

    @property
    def quota_exceeded(self) -> bool:
        return self.emails_sent_mtd >= self.monthly_quota

    def increment_sent(self, count: int = 1) -> None:
        """Thread-safe counter increment via UPDATE … SET emails_sent_mtd = emails_sent_mtd + n."""
        User.objects.filter(pk=self.pk).update(
            emails_sent_mtd=models.F("emails_sent_mtd") + count
        )
        self.refresh_from_db(fields=["emails_sent_mtd"])


# ── Team (optional multi-user workspace) ─────────────────────────────────────

class Team(models.Model):
    """
    A workspace that groups multiple users under one billing/sending account.
    Phase 2.1 scaffolds the model; full team invitations come in a later phase.
    """

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name       = models.CharField(max_length=100)
    owner      = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_teams"
    )
    members    = models.ManyToManyField(User, through="TeamMembership", related_name="teams")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name        = "Team"
        verbose_name_plural = "Teams"

    def __str__(self) -> str:
        return self.name


class TeamMembership(models.Model):
    """Through table for Team ↔ User with a role column."""

    class Role(models.TextChoices):
        OWNER  = "owner",  "Owner"
        ADMIN  = "admin",  "Admin"
        MEMBER = "member", "Member"

    team   = models.ForeignKey(Team, on_delete=models.CASCADE)
    user   = models.ForeignKey(User, on_delete=models.CASCADE)
    role   = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("team", "user")]

    def __str__(self) -> str:
        return f"{self.user.email} in {self.team.name} ({self.role})"
    

"""
Verify this line exists in config/settings/base.py:

    AUTH_USER_MODEL = "accounts.User"

The value must use the APP LABEL (defined in AppConfig.label),
NOT the Python module path.

  ✅  AUTH_USER_MODEL = "accounts.User"          ← correct (label = "accounts")
  ❌  AUTH_USER_MODEL = "apps.accounts.User"     ← wrong (module path, not label)
  ❌  AUTH_USER_MODEL = "apps_accounts.User"     ← wrong

Also verify SITE_ID = 1 is present (required by allauth).
"""