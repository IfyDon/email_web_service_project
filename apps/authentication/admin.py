from django.contrib import admin
from .models import APIKey, AuditLog, TOTPDevice, BackupCode, PasswordResetToken


# ── API Key ───────────────────────────────────────────────────────────────────

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display    = ["label", "prefix", "user", "is_active",
                       "rate_limit_per_min", "last_used", "created_at", "expires_at"]
    list_filter     = ["is_active"]
    search_fields   = ["label", "user__email", "prefix"]
    readonly_fields = ["id", "key_hash", "prefix", "created_at", "last_used"]
    ordering        = ["-created_at"]

    def has_add_permission(self, request):
        return False   # must go through APIKey.create_for_user()


# ── TOTP Device ───────────────────────────────────────────────────────────────

class BackupCodeInline(admin.TabularInline):
    model   = BackupCode
    extra   = 0
    fields  = ["code_hash", "used", "used_at"]
    readonly_fields = ["code_hash", "used_at"]


@admin.register(TOTPDevice)
class TOTPDeviceAdmin(admin.ModelAdmin):
    list_display  = ["user", "confirmed", "created_at"]
    list_filter   = ["confirmed"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "secret", "created_at"]
    inlines = [BackupCodeInline]

    def has_add_permission(self, request):
        return False


# ── Password Reset Token ──────────────────────────────────────────────────────

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display  = ["user", "used", "created_at", "expires_at"]
    list_filter   = ["used"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "token_hash", "created_at"]


# ── Audit Log ─────────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ["action", "user", "ip_address", "created_at"]
    list_filter   = ["action"]
    search_fields = ["user__email", "ip_address"]
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False