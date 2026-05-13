"""
Web dashboard views for account management:
  - Profile settings
  - Password change
  - API key list / create / revoke
  - 2FA setup / verify / disable
  - Billing (stub)

Place: web/views/account.py
"""

import io
import base64
import qrcode

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.http import HttpRequest, HttpResponse

from apps.authentication.models import APIKey, AuditLog, TOTPDevice
from web.forms.auth_forms import (
    APIKeyCreateForm,
    ProfileUpdateForm,
    ChangePasswordForm,
    TOTPVerifyForm,
)


# ── Profile & Password ────────────────────────────────────────────────────────

def account_settings(request: HttpRequest) -> HttpResponse:
    profile_form  = ProfileUpdateForm(instance=request.user)
    password_form = ChangePasswordForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            profile_form = ProfileUpdateForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profile updated.")
                return redirect("web:account")

        elif action == "change_password":
            password_form = ChangePasswordForm(request.POST)
            if password_form.is_valid():
                cd = password_form.cleaned_data
                if not request.user.check_password(cd["current_password"]):
                    password_form.add_error("current_password", "Incorrect password.")
                else:
                    request.user.set_password(cd["new_password"])
                    request.user.save(update_fields=["password"])
                    update_session_auth_hash(request, request.user)  # keep session alive
                    AuditLog.record(AuditLog.Action.PASSWORD_RESET,
                                    user=request.user, request=request)
                    messages.success(request, "Password changed successfully.")
                    return redirect("web:account")

    return render(request, "dashboard/account.html", {
        "page_title":   "Account Settings",
        "profile_form": profile_form,
        "password_form": password_form,
    })


# ── API Keys ──────────────────────────────────────────────────────────────────

def api_keys(request: HttpRequest) -> HttpResponse:
    keys = APIKey.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "dashboard/api_keys.html", {
        "page_title": "API Keys",
        "api_keys":   keys,
    })


def api_key_create(request: HttpRequest) -> HttpResponse:
    form = APIKeyCreateForm()

    if request.method == "POST":
        form = APIKeyCreateForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            api_key, raw_key = APIKey.create_for_user(
                user=request.user,
                label=cd["label"],
                expires_at=cd.get("expires_at"),
            )
            AuditLog.record(AuditLog.Action.API_KEY_CREATED,
                            user=request.user, request=request, label=api_key.label)
            # raw_key shown once; store in session for the next page
            request.session["new_api_key_raw"] = raw_key
            request.session["new_api_key_id"]  = str(api_key.pk)
            return redirect("web:api-key-reveal")

    return render(request, "dashboard/api_key_new.html", {
        "page_title": "New API Key",
        "form": form,
    })


def api_key_reveal(request: HttpRequest) -> HttpResponse:
    """Show the raw key ONCE, then clear it from the session."""
    raw_key = request.session.pop("new_api_key_raw", None)
    key_id  = request.session.pop("new_api_key_id",  None)

    if not raw_key:
        messages.warning(request, "No key to display. Create a new key below.")
        return redirect("web:api-keys")

    api_key = get_object_or_404(APIKey, pk=key_id, user=request.user)
    return render(request, "dashboard/api_key_created.html", {
        "page_title": "Save Your API Key",
        "api_key":    api_key,
        "raw_key":    raw_key,
    })


@require_POST
def api_key_revoke(request: HttpRequest, pk) -> HttpResponse:
    key = get_object_or_404(APIKey, pk=pk, user=request.user)
    key.revoke()
    AuditLog.record(AuditLog.Action.API_KEY_REVOKED,
                    user=request.user, request=request, label=key.label)
    messages.success(request, f"API key '{key.label}' revoked.")
    return redirect("web:api-keys")


# ── 2FA ───────────────────────────────────────────────────────────────────────

def two_fa_setup(request: HttpRequest) -> HttpResponse:
    """GET – show QR code. POST – verify first code and enable 2FA."""
    device, _ = TOTPDevice.objects.get_or_create(user=request.user)
    form       = TOTPVerifyForm()
    error      = None

    if request.method == "POST":
        form = TOTPVerifyForm(request.POST)
        if form.is_valid():
            if device.verify(form.cleaned_data["code"]):
                device.confirmed = True
                device.save(update_fields=["confirmed"])
                request.user.otp_enabled = True
                request.user.save(update_fields=["otp_enabled"])
                AuditLog.record(AuditLog.Action.TWO_FA_ENABLED,
                                user=request.user, request=request)
                backup_codes = device.generate_backup_codes()
                request.session["backup_codes"] = backup_codes
                return redirect("web:2fa-backup-codes")
            else:
                error = "Invalid code. Please try again."

    # Build QR code as base64 PNG
    uri = device.provisioning_uri()
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    return render(request, "dashboard/2fa_setup.html", {
        "page_title": "Enable Two-Factor Authentication",
        "qr_data_url": qr_data_url,
        "secret": device.secret,
        "form":   form,
        "error":  error,
    })


def two_fa_backup_codes(request: HttpRequest) -> HttpResponse:
    """Display newly generated backup codes once."""
    codes = request.session.pop("backup_codes", [])
    if not codes:
        return redirect("web:account")
    return render(request, "dashboard/2fa_backup_codes.html", {
        "page_title": "Save Your Backup Codes",
        "codes": codes,
    })


@require_POST
def two_fa_disable(request: HttpRequest) -> HttpResponse:
    password = request.POST.get("password", "")
    if not request.user.check_password(password):
        messages.error(request, "Incorrect password.")
        return redirect("web:account")

    try:
        request.user.totp_device.delete()
    except TOTPDevice.DoesNotExist:
        pass

    request.user.otp_enabled = False
    request.user.save(update_fields=["otp_enabled"])
    AuditLog.record(AuditLog.Action.TWO_FA_DISABLED,
                    user=request.user, request=request)
    messages.success(request, "Two-factor authentication has been disabled.")
    return redirect("web:account")


# ── Billing (stub) ────────────────────────────────────────────────────────────

def billing(request: HttpRequest) -> HttpResponse:
    return render(request, "dashboard/billing.html", {
        "page_title": "Billing",
        "user": request.user,
    })