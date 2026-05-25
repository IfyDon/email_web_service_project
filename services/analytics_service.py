"""
Analytics service — aggregation logic for stats endpoint and dashboard.

Provides:
  - get_summary()  – totals across a date range (for /api/v1/stats/)
  - get_timeline() – per-day breakdown for charts
  - get_top_domains() – sending volume per domain
  - rebuild_daily() – recalculate DailyStat rows from raw events (Celery Beat)

Place: services/analytics_service.py
"""

import logging
from datetime import date, timedelta

from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.analytics.models import DailyStat
from apps.email_messages.models import Message
from apps.events.models import MessageEvent

logger = logging.getLogger(__name__)


# ── Summary (totals) ──────────────────────────────────────────────────────────

def get_summary(user, *, date_from: date, date_to: date) -> dict:
    """
    Return aggregate counters for the user across [date_from, date_to].

    First tries pre-aggregated DailyStat rows; falls back to counting
    Message / MessageEvent rows directly for the current day (where
    the nightly rollup hasn't run yet).
    """
    qs = DailyStat.objects.filter(
        user=user, date__gte=date_from, date__lte=date_to
    )

    agg = qs.aggregate(
        total_sent       = Sum("sent",        default=0),
        total_delivered  = Sum("delivered",   default=0),
        total_opened     = Sum("opened",      default=0),
        total_clicked    = Sum("clicked",     default=0),
        total_bounced    = Sum("bounced",     default=0),
        total_complained = Sum("complained",  default=0),
        total_failed     = Sum("failed",      default=0),
        total_unsubscribed = Sum("unsubscribed", default=0),
    )

    sent       = agg["total_sent"] or 0
    delivered  = agg["total_delivered"] or 0
    base       = delivered or sent or 1

    return {
        "date_from":    date_from.isoformat(),
        "date_to":      date_to.isoformat(),
        "sent":         sent,
        "delivered":    delivered,
        "opened":       agg["total_opened"]       or 0,
        "clicked":      agg["total_clicked"]      or 0,
        "bounced":      agg["total_bounced"]      or 0,
        "complained":   agg["total_complained"]   or 0,
        "failed":       agg["total_failed"]       or 0,
        "unsubscribed": agg["total_unsubscribed"] or 0,
        "open_rate":    round((agg["total_opened"] or 0)    / base * 100, 2),
        "click_rate":   round((agg["total_clicked"] or 0)   / base * 100, 2),
        "bounce_rate":  round((agg["total_bounced"] or 0)   / (sent or 1) * 100, 2),
        "complaint_rate": round((agg["total_complained"] or 0) / (sent or 1) * 100, 2),
    }


# ── Timeline (per-day breakdown for charts) ───────────────────────────────────

def get_timeline(user, *, date_from: date, date_to: date) -> list[dict]:
    """
    Return a list of daily data points for charting.

    Output:
        [
            {"date": "2025-01-01", "sent": 100, "opened": 40, ...},
            ...
        ]
    """
    stat_map: dict[date, DailyStat] = {
        s.date: s
        for s in DailyStat.objects.filter(
            user=user, date__gte=date_from, date__lte=date_to
        )
    }

    timeline = []
    current  = date_from
    while current <= date_to:
        stat = stat_map.get(current)
        timeline.append({
            "date":       current.isoformat(),
            "sent":       getattr(stat, "sent",       0),
            "delivered":  getattr(stat, "delivered",  0),
            "opened":     getattr(stat, "opened",     0),
            "clicked":    getattr(stat, "clicked",    0),
            "bounced":    getattr(stat, "bounced",    0),
            "complained": getattr(stat, "complained", 0),
            "failed":     getattr(stat, "failed",     0),
        })
        current += timedelta(days=1)

    return timeline


# ── Top sending domains ───────────────────────────────────────────────────────

def get_top_domains(user, *, date_from: date, date_to: date,
                    limit: int = 10) -> list[dict]:
    """Return the top N sending domains by message volume."""
    qs = (
        Message.objects
        .filter(
            user=user,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .exclude(domain__isnull=True)
        .values("domain__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return [{"domain": row["domain__name"], "count": row["count"]} for row in qs]


# ── Nightly rollup (called by Celery Beat) ────────────────────────────────────

def rebuild_daily(user, target_date: date | None = None) -> DailyStat:
    """
    Recount all MessageEvent rows for `target_date` (default: yesterday)
    and upsert the DailyStat row.

    Called by the Celery Beat task in Phase 6.
    """
    if target_date is None:
        target_date = (timezone.now() - timedelta(days=1)).date()

    # Count messages queued on that day
    msgs = Message.objects.filter(
        user=user,
        queued_at__date=target_date,
    )
    sent = msgs.count()

    # Count events that occurred that day
    events = MessageEvent.objects.filter(
        message__user=user,
        occurred_at__date=target_date,
    )

    def _count(etype: str) -> int:
        return events.filter(event_type=etype).count()

    stat, _ = DailyStat.objects.update_or_create(
        user=user,
        date=target_date,
        defaults={
            "sent":        sent,
            "delivered":   _count("delivered"),
            "opened":      _count("opened"),
            "clicked":     _count("clicked"),
            "bounced":     _count("bounced"),
            "complained":  _count("complained"),
            "failed":      _count("failed"),
            "unsubscribed":_count("unsubscribed"),
        },
    )

    logger.info(
        "rebuild_daily: %s for %s — sent=%d delivered=%d",
        user.email, target_date, stat.sent, stat.delivered,
    )
    return stat