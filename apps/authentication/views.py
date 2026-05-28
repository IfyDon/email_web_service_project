"""
DRF API views for authentication & API key management.

Endpoints (all under /api/v1/auth/):
  POST   signup
  POST   login
  POST   logout
  GET    me
  PATCH  me
  POST   change-password
  POST   password-reset/request
  POST   password-reset/confirm
  GET    api-keys
  POST   api-keys
  DELETE api-keys/<pk>/
  GET    2fa/setup
  POST   2fa/verify
  POST   2fa/disable
  GET    2fa/backup-codes   (regenerate)

Place: apps/authentication/views.py
"""

import io
import qrcode
import qrcode.image.svg
import base64

from django.contrib.auth import get_user_model, authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from .models import APIKey, AuditLog, TOTPDevice, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer,
    UserProfileSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    APIKeySerializer,
    APIKeyCreateSerializer,
    APIKeyCreatedSerializer,
    TOTPSetupSerializer,
    TOTPVerifySerializer,
    TOTPDisableSerializer,
    BackupCodeSerializer,
)

User = get_user_model()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _qr_data_url(uri: str) -> str:
    """Return a base64 PNG data URL for the given provisioning URI."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"


# ── Signup ────────────────────────────────────────────────────────────────────

class SignupView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = UserRegistrationSerializer

    @extend_schema(request=UserRegistrationSerializer,
                   responses={201: UserProfileSerializer})
    def post(self, request):
        ser = UserRegistrationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        AuditLog.record(AuditLog.Action.LOGIN_SUCCESS, user=user, request=request)
        return Response(
            UserProfileSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


# ── Login / Logout ────────────────────────────────────────────────────────────

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request={"application/json": {"type": "object",
                 "properties": {"email": {"type": "string"}, "password": {"type": "string"}}}},
        responses={200: UserProfileSerializer},
    )
    def post(self, request):
        email    = request.data.get("email", "")
        password = request.data.get("password", "")
        user     = authenticate(request, username=identifier, password=password)


        if user is None:
            AuditLog.record(AuditLog.Action.LOGIN_FAILED, request=request,
                            email=email)
            return Response(
                {"error": {"code": "invalid_credentials",
                           "message": "Invalid email or password."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"error": {"code": "account_disabled",
                           "message": "This account has been disabled."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        # If 2FA is enabled, return a challenge token instead of logging in
        if user.otp_enabled:
            request.session["pending_2fa_user_id"] = str(user.pk)
            return Response(
                {"requires_2fa": True},
                status=status.HTTP_200_OK,
            )

        login(request, user)
        AuditLog.record(AuditLog.Action.LOGIN_SUCCESS, user=user, request=request)
        return Response(UserProfileSerializer(user).data)


class TwoFALoginView(APIView):
    """
    Second step of login when 2FA is active.
    POST { "code": "123456" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user_id = request.session.get("pending_2fa_user_id")
        if not user_id:
            return Response(
                {"error": {"code": "no_pending_login",
                           "message": "No pending 2FA challenge."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get("code", "")
        device = getattr(user, "totp_device", None)

        if device and device.confirmed and device.verify(code):
            del request.session["pending_2fa_user_id"]
            login(request, user)
            AuditLog.record(AuditLog.Action.LOGIN_SUCCESS, user=user, request=request)
            return Response(UserProfileSerializer(user).data)

        return Response(
            {"error": {"code": "invalid_otp", "message": "Invalid or expired OTP code."}},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."}, status=status.HTTP_200_OK)


# ── Profile ───────────────────────────────────────────────────────────────────

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        ser = UserProfileSerializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# ── Password ──────────────────────────────────────────────────────────────────

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        AuditLog.record(AuditLog.Action.PASSWORD_RESET, user=request.user, request=request)
        return Response({"detail": "Password updated."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        email = ser.validated_data["email"]
        try:
            user  = User.objects.get(email=email, is_active=True)
            token = PasswordResetToken.create_for_user(user)
            reset_url = f"{request.scheme}://{request.get_host()}/accounts/password-reset/confirm/?token={token}"
            send_mail(
                subject="Reset your MailFlow password",
                message=f"Use this link to reset your password (expires in 1 hour):\n{reset_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=True,
            )
        except User.DoesNotExist:
            pass  # Silent – don't reveal whether email exists

        return Response({"detail": "If that email exists, a reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from apps.authentication.models import _hash_key
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        raw_token    = ser.validated_data["token"]
        new_password = ser.validated_data["new_password"]

        try:
            record = PasswordResetToken.objects.select_related("user").get(
                token_hash=_hash_key(raw_token)
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"error": {"code": "invalid_token", "message": "Token is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not record.consume():
            return Response(
                {"error": {"code": "invalid_token", "message": "Token is invalid or has expired."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record.user.set_password(new_password)
        record.user.save(update_fields=["password"])
        return Response({"detail": "Password has been reset."})


# ── API Key management ────────────────────────────────────────────────────────

class APIKeyListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all API keys for the current user."""
        keys = APIKey.objects.filter(user=request.user)
        return Response(APIKeySerializer(keys, many=True).data)

    def post(self, request):
        """Create a new API key – returns the raw key once."""
        ser = APIKeyCreateSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        api_key = ser.save()
        AuditLog.record(AuditLog.Action.API_KEY_CREATED, user=request.user,
                        request=request, label=api_key.label)
        return Response(
            APIKeyCreatedSerializer(api_key).data,
            status=status.HTTP_201_CREATED,
        )


class APIKeyDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_key(self, request, pk):
        return get_object_or_404(APIKey, pk=pk, user=request.user)

    def get(self, request, pk):
        return Response(APIKeySerializer(self._get_key(request, pk)).data)

    def delete(self, request, pk):
        """Revoke (soft-delete) an API key."""
        key = self._get_key(request, pk)
        key.revoke()
        AuditLog.record(AuditLog.Action.API_KEY_REVOKED, user=request.user,
                        request=request, label=key.label)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── 2FA setup ─────────────────────────────────────────────────────────────────

class TwoFASetupView(APIView):
    """
    GET  – generate (or return existing) TOTP secret + QR code.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        device, _ = TOTPDevice.objects.get_or_create(user=request.user)
        uri       = device.provisioning_uri()
        return Response({
            "provisioning_uri": uri,
            "qr_code_url":      _qr_data_url(uri),
            "secret":           device.secret,   # shown once for manual entry
        })


class TwoFAVerifyView(APIView):
    """
    POST { "code": "123456" } – confirm setup; marks device confirmed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TOTPVerifySerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            device = request.user.totp_device
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": {"code": "no_device", "message": "Run GET /2fa/setup first."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not device.verify(ser.validated_data["code"]):
            return Response(
                {"error": {"code": "invalid_otp", "message": "Invalid OTP code."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.confirmed = True
        device.save(update_fields=["confirmed"])
        request.user.otp_enabled = True
        request.user.save(update_fields=["otp_enabled"])

        AuditLog.record(AuditLog.Action.TWO_FA_ENABLED, user=request.user, request=request)

        backup_codes = device.generate_backup_codes()
        return Response({
            "detail": "2FA enabled.",
            "backup_codes": backup_codes,   # shown once
        }, status=status.HTTP_200_OK)


class TwoFADisableView(APIView):
    """
    POST { "password": "…" } – disable 2FA after password confirmation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = TOTPDisableSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)

        try:
            device = request.user.totp_device
            device.delete()
        except TOTPDevice.DoesNotExist:
            pass

        request.user.otp_enabled = False
        request.user.save(update_fields=["otp_enabled"])
        AuditLog.record(AuditLog.Action.TWO_FA_DISABLED, user=request.user, request=request)
        return Response({"detail": "2FA has been disabled."})


class BackupCodeRegenerateView(APIView):
    """
    GET – regenerate 8 new backup codes (invalidates old ones).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            device = request.user.totp_device
        except TOTPDevice.DoesNotExist:
            return Response(
                {"error": {"code": "no_device", "message": "2FA is not enabled."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        codes = device.generate_backup_codes()
        return Response(BackupCodeSerializer({"codes": codes}).data)