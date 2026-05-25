from django.contrib import admin
from .models import DailyStat


@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = [
        "user", "date", "sent", "delivered", "opened", "clicked",
        "bounced", "complained", "open_rate", "click_rate",
    ]
    list_filter  = ["date"]
    search_fields= ["user__email"]
    readonly_fields = [
        "id", "open_rate", "click_rate",
        "bounce_rate", "complaint_rate", "updated_at",
    ]
    ordering = ["-date", "user"]

    actions = ["rebuild_stats"]

    @admin.action(description="Rebuild DailyStat from raw events")
    def rebuild_stats(self, request, queryset):
        from services.analytics_service import rebuild_daily
        count = 0
        for stat in queryset:
            rebuild_daily(user=stat.user, target_date=stat.date)
            count += 1
        self.message_user(request, f"Rebuilt {count} stat row(s).")