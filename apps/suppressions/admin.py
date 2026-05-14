from django.contrib import admin
from .models import Suppression, UnsubscribeToken


@admin.register(Suppression)
class SuppressionAdmin(admin.ModelAdmin):
    list_display  = ["email", "reason", "user", "source_message_id", "created_at"]
    list_filter   = ["reason"]
    search_fields = ["email", "user__email"]
    readonly_fields = ["id", "email_hash", "created_at", "updated_at"]
    ordering = ["-created_at"]

    actions = ["remove_suppressions"]

    @admin.action(description="Remove selected suppressions (allow sending again)")
    def remove_suppressions(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"{count} suppression(s) removed.")


@admin.register(UnsubscribeToken)
class UnsubscribeTokenAdmin(admin.ModelAdmin):
    list_display  = ["email", "user", "used", "used_at", "created_at"]
    list_filter   = ["used"]
    search_fields = ["email", "user__email"]
    readonly_fields = ["id", "token", "created_at", "used_at"]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False