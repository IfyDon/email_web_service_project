from django.contrib import admin
from .models import MessageEvent, ClickToken, OpenToken


@admin.register(MessageEvent)
class MessageEventAdmin(admin.ModelAdmin):
    list_display  = [
        "event_type", "message", "occurred_at",
        "ip_address", "clicked_url",
    ]
    list_filter   = ["event_type"]
    search_fields = ["message__id", "ip_address"]
    readonly_fields = [f.name for f in MessageEvent._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-occurred_at"]

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(ClickToken)
class ClickTokenAdmin(admin.ModelAdmin):
    list_display  = ["token", "message", "original_url", "click_count", "last_clicked"]
    search_fields = ["token", "message__id"]
    readonly_fields = [f.name for f in ClickToken._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-created_at"]

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(OpenToken)
class OpenTokenAdmin(admin.ModelAdmin):
    list_display  = ["token", "message", "open_count", "first_opened", "last_opened"]
    search_fields = ["token", "message__id"]
    readonly_fields = [f.name for f in OpenToken._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-created_at"]

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False