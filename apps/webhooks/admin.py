
from django.contrib import admin
from .models import Webhook, WebhookDelivery


class WebhookDeliveryInline(admin.TabularInline):
    model        = WebhookDelivery
    extra        = 0
    fields       = ["event_type", "attempt_no", "status", "http_status",
                    "duration_ms", "attempted_at"]
    readonly_fields = ["event_type", "attempt_no", "status", "http_status",
                       "duration_ms", "attempted_at"]
    ordering     = ["-attempted_at"]
    can_delete   = False
    max_num      = 20


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display  = [
        "label", "user", "url", "is_active",
        "total_deliveries", "failed_deliveries", "last_triggered",
    ]
    list_filter   = ["is_active"]
    search_fields = ["label", "url", "user__email"]
    readonly_fields = [
        "id", "secret", "total_deliveries", "failed_deliveries",
        "last_triggered", "created_at", "updated_at",
    ]
    inlines     = [WebhookDeliveryInline]
    ordering    = ["-created_at"]

    fieldsets = (
        (None,       {"fields": ("id", "user", "label", "url", "is_active")}),
        ("Security", {"fields": ("secret",)}),
        ("Events",   {"fields": ("event_types",)}),
        ("Stats",    {"fields": ("total_deliveries", "failed_deliveries", "last_triggered")}),
        ("Timestamps",{"fields": ("created_at", "updated_at")}),
    )

    actions = ["disable_webhooks", "enable_webhooks"]

    @admin.action(description="Disable selected webhooks")
    def disable_webhooks(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Enable selected webhooks")
    def enable_webhooks(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display  = [
        "webhook", "event_type", "attempt_no",
        "status", "http_status", "duration_ms", "attempted_at",
    ]
    list_filter   = ["status", "event_type"]
    search_fields = ["webhook__label", "webhook__url"]
    readonly_fields = [f.name for f in WebhookDelivery._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-attempted_at"]

    def has_add_permission(self, request):         return False
    def has_change_permission(self, request, obj=None): return False