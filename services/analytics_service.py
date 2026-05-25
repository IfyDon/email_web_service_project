"""
Analytics service — aggregation logic for the stats endpoint and dashboard.

Updated for Phase 4.3: adds domain-filtered variants of get_summary
and get_timeline that query raw Message/Event rows when a domain filter
is applied (DailyStat is not bucketed by domain).

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


# ── Unfiltered helpers (use pre-aggregated DailyStat rows) ────────────────────

def get_summary(user, *, date_from: date, date_to: date) -> dict:
    return get_summary_filtered(user, date_from=date_from, date_to=date_to)


def get_timeline(user, *, date_from: date, date_to: date) -> list[dict]:
    return get_timeline_filtered(user, date_from=date_from, date_to=date_to)


# ── Filtered helpers ──────────────────────────────────────────────────────────

def get_summary_filtered(
    user, *, date_from: date, date_to: date, domain: str | None = None
) -> dict:
    """
    Aggregate counters for [date_from, date_to], optionally filtered by domain.

    When domain is None: uses fast pre-aggregated DailyStat rows.
    When domain is set: falls back to counting raw Message / MessageEvent rows.
    """
    if domain:
        return _summary_from_messages(user, date_from=date_from,
                                      date_to=date_to, domain=domain)

    qs  = DailyStat.objects.filter(
        user=user, date__gte=date_from, date__lte=date_to
    )
    agg = qs.aggregate(
        total_sent        = Sum("sent",         default=0),
        total_delivered   = Sum("delivered",    default=0),
        total_opened      = Sum("opened",       default=0),
        total_clicked     = Sum("clicked",      default=0),
        total_bounced     = Sum("bounced",      default=0),
        total_complained  = Sum("complained",   default=0),
        total_failed      = Sum("failed",       default=0),
        total_unsubscribed= Sum("unsubscribed", default=0),
    )
    return _build_summary(agg, date_from, date_to)


def get_timeline_filtered(
    user, *, date_from: date, date_to: date, domain: str | None = None
) -> list[dict]:
    """Per-day breakdown, optionally filtered by domain."""
    if domain:
        return _timeline_from_messages(user, date_from=date_from,
                                       date_to=date_to, domain=domain)

    stat_map: dict[date, DailyStat] = {
        s.date: s
        for s in DailyStat.objects.filter(
            user=user, date__gte=date_from, date__lte=date_to
        )
    }
    return _build_timeline(stat_map, date_from, date_to)


# ── Domain-specific fallbacks (raw DB queries) ────────────────────────────────

def _base_messages(user, date_from: date, date_to: date, domain: str):
    return Message.objects.filter(
        user=user,
        domain__name=domain,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )


def _summary_from_messages(user, *, date_from: date, date_to: date,
                            domain: str) -> dict:
    msgs = _base_messages(user, date_from, date_to, domain)
    sent = msgs.count()

    def _cnt(status: str) -> int:
        return msgs.filter(status=status).count()

    agg = {
        "total_sent":        sent,
        "total_delivered":   _cnt("delivered") + _cnt("opened") + _cnt("clicked"),
        "total_opened":      _cnt("opened") + _cnt("clicked"),
        "total_clicked":     _cnt("clicked"),
        "total_bounced":     _cnt("bounced"),
        "total_complained":  _cnt("complained"),
        "total_failed":      _cnt("failed"),
        "total_unsubscribed": 0,
    }
    return _build_summary(agg, date_from, date_to)


def _timeline_from_messages(user, *, date_from: date, date_to: date,
                             domain: str) -> list[dict]:
    msgs = _base_messages(user, date_from, date_to, domain)
    # Group by date using values()
    from django.db.models.functions import TruncDate
    rows = (
        msgs
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(
            sent      = Count("id"),
            delivered = Count("id", filter=Q(status__in=["delivered","opened","clicked"])),
            opened    = Count("id", filter=Q(status__in=["opened","clicked"])),
            clicked   = Count("id", filter=Q(status="clicked")),
            bounced   = Count("id", filter=Q(status="bounced")),
            complained= Count("id", filter=Q(status="complained")),
            failed    = Count("id", filter=Q(status="failed")),
        )
        .order_by("day")
    )
    stat_map = {row["day"]: row for row in rows}

    timeline = []
    current  = date_from
    while current <= date_to:
        row = stat_map.get(current, {})
        timeline.append({
            "date":       current.isoformat(),
            "sent":       row.get("sent",       0),
            "delivered":  row.get("delivered",  0),
            "opened":     row.get("opened",     0),
            "clicked":    row.get("clicked",    0),
            "bounced":    row.get("bounced",    0),
            "complained": row.get("complained", 0),
            "failed":     row.get("failed",     0),
        })
        current += timedelta(days=1)
    return timeline


# ── Internal builders ─────────────────────────────────────────────────────────

def _build_summary(agg: dict, date_from: date, date_to: date) -> dict:
    sent      = agg.get("total_sent",      0) or 0
    delivered = agg.get("total_delivered", 0) or 0
    base      = delivered or sent or 1
    return {
        "date_from":       date_from.isoformat(),
        "date_to":         date_to.isoformat(),
        "sent":            sent,
        "delivered":       delivered,
        "opened":          agg.get("total_opened",       0) or 0,
        "clicked":         agg.get("total_clicked",      0) or 0,
        "bounced":         agg.get("total_bounced",      0) or 0,
        "complained":      agg.get("total_complained",   0) or 0,
        "failed":          agg.get("total_failed",       0) or 0,
        "unsubscribed":    agg.get("total_unsubscribed", 0) or 0,
        "open_rate":       round((agg.get("total_opened",     0) or 0) / base * 100, 2),
        "click_rate":      round((agg.get("total_clicked",    0) or 0) / base * 100, 2),
        "bounce_rate":     round((agg.get("total_bounced",    0) or 0) / (sent or 1) * 100, 2),
        "complaint_rate":  round((agg.get("total_complained", 0) or 0) / (sent or 1) * 100, 2),
    }


def _build_timeline(stat_map: dict, date_from: date, date_to: date) -> list[dict]:
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


# ── Top domains ───────────────────────────────────────────────────────────────

def get_top_domains(user, *, date_from: date, date_to: date,
                    limit: int = 10) -> list[dict]:
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
    return [{"domain": r["domain__name"], "count": r["count"]} for r in qs]


# ── Nightly rollup (Celery Beat — Phase 6) ────────────────────────────────────

def rebuild_daily(user, target_date: date | None = None) -> DailyStat:
    if target_date is None:
        target_date = (timezone.now() - timedelta(days=1)).date()

    msgs   = Message.objects.filter(user=user, queued_at__date=target_date)
    events = MessageEvent.objects.filter(
        message__user=user, occurred_at__date=target_date
    )

    def _cnt(etype: str) -> int:
        return events.filter(event_type=etype).count()

    stat, _ = DailyStat.objects.update_or_create(
        user=user,
        date=target_date,
        defaults={
            "sent":         msgs.count(),
            "delivered":    _cnt("delivered"),
            "opened":       _cnt("opened"),
            "clicked":      _cnt("clicked"),
            "bounced":      _cnt("bounced"),
            "complained":   _cnt("complained"),
            "failed":       _cnt("failed"),
            "unsubscribed": _cnt("unsubscribed"),
        },
    )
    logger.info("rebuild_daily: %s for %s", user.email, target_date)
    return stat