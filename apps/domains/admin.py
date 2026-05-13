from django.contrib import admin
from .models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = [
        "name", "user", "status",
        "spf_verified", "dkim_verified", "dmarc_verified",
        "created_at", "verified_at",
    ]
    list_filter   = ["status", "spf_verified", "dkim_verified", "dmarc_verified"]
    search_fields = ["name", "user__email"]
    readonly_fields = [
        "id", "dkim_private_key", "dkim_public_key",
        "spf_last_check", "dkim_last_check", "dmarc_last_check",
        "verified_at", "created_at", "updated_at",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("id", "user", "name", "status")}),
        ("SPF",  {"fields": ("spf_verified",  "spf_last_check")}),
        ("DKIM", {"fields": ("dkim_selector", "dkim_verified", "dkim_last_check",
                             "dkim_public_key", "dkim_private_key")}),
        ("DMARC",{"fields": ("dmarc_verified","dmarc_last_check")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "verified_at")}),
    )

    actions = ["trigger_verification"]

    @admin.action(description="Trigger DNS verification for selected domains")
    def trigger_verification(self, request, queryset):
        from services.domain_service import verify_domain
        for domain in queryset:
            verify_domain(domain)
        self.message_user(request, f"Verification triggered for {queryset.count()} domain(s).")