"""
DRF serializers for authentication flows:
  - User registration & profile
  - API key CRUD
  - 2FA setup / verify
  - Password reset

Place: apps/authentication/serializers.py
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import APIKey, TOTPDevice

User = get_user_model()


# ── User ──────────────────────────────────────────────────────────────────────

class UserRegistrationSerializer(serializers.ModelSerializer):
    """POST /api/v1/auth/signup"""

    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model  = User
        fields = ["email", "full_name", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """GET/PATCH /api/v1/auth/me"""

    quota_remaining = serializers.ReadOnlyField()
    quota_exceeded  = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = [
            "id", "email", "full_name", "role",
            "is_verified", "otp_enabled",
            "monthly_quota", "emails_sent_mtd",
            "quota_remaining", "quota_exceeded",
            "date_joined",
        ]
        read_only_fields = [
            "id", "email", "role", "is_verified",
            "otp_enabled", "monthly_quota",
            "emails_sent_mtd", "date_joined",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """POST /api/v1/auth/change-password"""

    current_password = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, validators=[validate_password])
    new_password2    = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """POST /api/v1/auth/password-reset/request"""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """POST /api/v1/auth/password-reset/confirm"""
    token        = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])


# ── API Key ───────────────────────────────────────────────────────────────────

class APIKeySerializer(serializers.ModelSerializer):
    """Read-only representation of an API key (safe to return in list view)."""

    class Meta:
        model  = APIKey
        fields = [
            "id", "label", "prefix",
            "rate_limit_per_min", "rate_limit_per_hour",
            "is_active", "last_used", "created_at", "expires_at",
        ]
        read_only_fields = fields


class APIKeyCreateSerializer(serializers.ModelSerializer):
    """POST /api/v1/auth/api-keys – accepts label + optional expiry."""

    class Meta:
        model  = APIKey
        fields = ["label", "expires_at", "rate_limit_per_min", "rate_limit_per_hour"]
        extra_kwargs = {
            "expires_at":          {"required": False, "allow_null": True},
            "rate_limit_per_min":  {"required": False, "allow_null": True},
            "rate_limit_per_hour": {"required": False, "allow_null": True},
        }

    def create(self, validated_data):
        user = self.context["request"].user
        api_key, raw_key = APIKey.create_for_user(user=user, **validated_data)
        # Temporarily attach raw key so the view can return it once
        api_key._raw_key = raw_key
        return api_key


class APIKeyCreatedSerializer(serializers.ModelSerializer):
    """
    Response serializer used ONLY on initial creation.
    Includes the raw key (shown once, then gone).
    """
    key = serializers.SerializerMethodField()

    class Meta:
        model  = APIKey
        fields = ["id", "label", "key", "prefix", "created_at", "expires_at"]

    def get_key(self, obj) -> str:
        return getattr(obj, "_raw_key", "")


# ── 2FA ───────────────────────────────────────────────────────────────────────

class TOTPSetupSerializer(serializers.Serializer):
    """
    GET /api/v1/auth/2fa/setup
    Returns the provisioning URI + QR code data URL.
    No input fields needed.
    """
    provisioning_uri = serializers.CharField(read_only=True)
    qr_code_url      = serializers.CharField(read_only=True)
    secret           = serializers.CharField(read_only=True)


class TOTPVerifySerializer(serializers.Serializer):
    """POST /api/v1/auth/2fa/verify  – confirm setup with first valid code."""
    code = serializers.CharField(max_length=6, min_length=6)


class TOTPDisableSerializer(serializers.Serializer):
    """POST /api/v1/auth/2fa/disable – require password confirmation."""
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Incorrect password.")
        return value


class BackupCodeSerializer(serializers.Serializer):
    """Response for newly generated backup codes."""
    codes = serializers.ListField(child=serializers.CharField())