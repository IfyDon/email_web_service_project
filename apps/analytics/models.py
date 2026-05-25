"""
Analytics models — pre-aggregated daily stats per user.
Place: apps/analytics/models.py
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from core.models.base import UUIDModel


class DailyStat(UUIDModel):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_stats",
        db_index=True,
    )
    date = models.DateField(db_index=True)
    domain = models.ForeignKey(
        "domains.Domain",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="daily_stats",
    )

    # Counters
    sent         = models.PositiveIntegerField(default=0)
    delivered    = models.PositiveIntegerField(default=0)
    opened       = models.PositiveIntegerField(default=0)
    clicked      = models.PositiveIntegerField(default=0)
    bounced      = models.PositiveIntegerField(default=0)
    complained   = models.PositiveIntegerField(default=0)
    failed       = models.PositiveIntegerField(default=0)
    unsubscribed = models.PositiveIntegerField(default=0)

    # Computed rates
    open_rate      = models.FloatField(default=0.0)
    click_rate     = models.FloatField(default=0.0)
    bounce_rate    = models.FloatField(default=0.0)
    complaint_rate = models.FloatField(default=0.0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Daily Stat"
        verbose_name_plural = "Daily Stats"
        unique_together     = [("user", "domain", "date")]
        ordering            = ["-date"]
        indexes             = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "domain", "date"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.date} | sent={self.sent}"

    def recompute_rates(self) -> None:
        base = self.delivered or self.sent or 1
        self.open_rate      = round(self.opened    / base * 100, 2)
        self.click_rate     = round(self.clicked   / base * 100, 2)
        self.bounce_rate    = round(self.bounced   / (self.sent or 1) * 100, 2)
        self.complaint_rate = round(self.complained / (self.sent or 1) * 100, 2)

    def save(self, *args, **kwargs):
        self.recompute_rates()
        super().save(*args, **kwargs)

    @classmethod
    def increment(cls, user, event_type: str, date=None) -> None:
        today = date or timezone.now().date()
        field_map = {
            "queued":       "sent",
            "delivered":    "delivered",
            "opened":       "opened",
            "clicked":      "clicked",
            "bounced":      "bounced",
            "complained":   "complained",
            "failed":       "failed",
            "unsubscribed": "unsubscribed",
        }
        field = field_map.get(event_type)
        if not field:
            return
        obj, _ = cls.objects.get_or_create(user=user, date=today)
        cls.objects.filter(pk=obj.pk).update(
            **{field: models.F(field) + 1}
        )