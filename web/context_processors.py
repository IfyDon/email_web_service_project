"""
Template context processors – inject common data into every
Django-rendered dashboard page.

Place: web/context_processors.py
"""


def quota_context(request):
    """
    Injects the authenticated user's quota info into every template.
    Available in templates as {{ quota_used }}, {{ quota_total }}, etc.
    """
    if not request.user.is_authenticated:
        return {}

    user = request.user
    return {
        "quota_total":     user.monthly_quota,
        "quota_used":      user.emails_sent_mtd,
        "quota_remaining": user.quota_remaining,
        "quota_exceeded":  user.quota_exceeded,
        "quota_pct": (
            round(user.emails_sent_mtd / user.monthly_quota * 100, 1)
            if user.monthly_quota > 0 else 0
        ),
    }