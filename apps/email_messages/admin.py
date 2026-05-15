from django.contrib import admin
from .models import Message, MessageAttempt


class MessageAttemptInline(admin.TabularInline):
    model       = MessageAttempt
    extra       = 0
    fields      = ["attempt_no", "success", "error", "attempted_at"]
    readonly_fields = ["attempt_no", "success", "error", "attempted_at"]
    ordering    = ["attempt_no"]
    can_delete  = False


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display  = [
        "id", "user", "from_email", "to_email",
        "subject", "status", "attempt_count",
        "queued_at", "sent_at",
    ]
    list_filter   = ["status"]
    search_fields = ["to_email", "from_email", "subject", "user__email", "esp_message_id"]
    readonly_fields = [
        "id", "user", "esp_message_id", "celery_task_id",
        "queued_at", "sent_at", "delivered_at",
        "created_at", "updated_at",
    ]
    ordering  = ["-created_at"]
    inlines   = [MessageAttemptInline]

    fieldsets = (
        ("Addressing", {"fields": ("user", "from_email", "from_name",
                                   "to_email", "to_name", "reply_to")}),
        ("Content",    {"fields": ("subject", "body_html", "body_text",
                                   "template", "domain")}),
        ("Metadata",   {"fields": ("tags", "metadata")}),
        ("Delivery",   {"fields": ("status", "esp_message_id", "celery_task_id",
                                   "attempt_count", "max_attempts", "next_attempt")}),
        ("Timestamps", {"fields": ("queued_at", "sent_at", "delivered_at",
                                   "created_at", "updated_at")}),
    )

    actions = ["requeue_failed"]

    @admin.action(description="Re-queue selected failed messages")
    def requeue_failed(self, request, queryset):
        failed = queryset.filter(status=Message.Status.FAILED)
        count  = 0
        for msg in failed:
            msg.status        = Message.Status.QUEUED
            msg.attempt_count = 0
            msg.next_attempt  = None
            msg.save(update_fields=["status", "attempt_count", "next_attempt"])
            from workers.tasks.send_email import dispatch_send_task
            dispatch_send_task.apply_async(args=[str(msg.pk)])
            count += 1
        self.message_user(request, f"{count} message(s) re-queued.")


@admin.register(MessageAttempt)
class MessageAttemptAdmin(admin.ModelAdmin):
    list_display  = ["message", "attempt_no", "success", "attempted_at"]
    list_filter   = ["success"]
    search_fields = ["message__id"]
    readonly_fields = [f.name for f in MessageAttempt._meta.get_fields()
                       if hasattr(f, "name")]
    ordering = ["-attempted_at"]

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False