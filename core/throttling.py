"""
Custom DRF throttle classes.

Provides per-API-key rate limiting that reads limits from the APIKey
model itself (rate_limit_per_min / rate_limit_per_hour), falling back
to the global Django settings values.

Place: core/throttling.py
"""

import logging

from django.core.cache import cache
from rest_framework.throttling import BaseThrottle
from rest_framework.exceptions import Throttled

logger = logging.getLogger(__name__)


class _SlidingWindowThrottle(BaseThrottle):
    """
    Sliding-window counter stored in Redis / Django cache.

    Subclass and set:
        scope      – cache key prefix (e.g. "api_min")
        window     – window size in seconds
        unit_label – human-readable unit for error messages
    """

    scope:      str = ""
    window:     int = 60
    unit_label: str = "minute"

    # Global fallback limits (requests per window)
    # Override via REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] in settings.
    default_limit: int = 100

    def get_cache_key(self, request, view) -> str | None:
        """Unique cache key per (api_key OR user) + scope."""
        from apps.authentication.models import APIKey

        if isinstance(request.auth, APIKey):
            ident = f"key:{request.auth.pk}"
        elif request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = f"ip:{self._get_ip(request)}"

        return f"throttle:{self.scope}:{ident}"

    def get_limit(self, request) -> int:
        """
        Per-key override → global setting → hard default.
        """
        from apps.authentication.models import APIKey

        if isinstance(request.auth, APIKey):
            key = request.auth
            per_min  = key.rate_limit_per_min
            per_hour = key.rate_limit_per_hour

            if self.scope == "api_min"  and per_min:
                return per_min
            if self.scope == "api_hour" and per_hour:
                return per_hour

        return self.default_limit

    def allow_request(self, request, view) -> bool:
        self.request = request
        cache_key    = self.get_cache_key(request, view)
        limit        = self.get_limit(request)

        count = cache.get(cache_key, 0)

        if count >= limit:
            self.wait_time = self.window
            logger.warning(
                "Throttle hit: %s (limit=%d/%s)", cache_key, limit, self.unit_label
            )
            return False

        if count == 0:
            cache.set(cache_key, 1, timeout=self.window)
        else:
            cache.incr(cache_key)

        return True

    def wait(self) -> float | None:
        return getattr(self, "wait_time", None)

    @staticmethod
    def _get_ip(request) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")


class PerMinuteThrottle(_SlidingWindowThrottle):
    """100 requests/min by default — overridden per APIKey."""
    scope         = "api_min"
    window        = 60
    unit_label    = "minute"
    default_limit = 100


class PerHourThrottle(_SlidingWindowThrottle):
    """1 000 requests/hour by default — overridden per APIKey."""
    scope         = "api_hour"
    window        = 3_600
    unit_label    = "hour"
    default_limit = 1_000


class SendRateThrottle(_SlidingWindowThrottle):
    """
    Stricter throttle applied only to POST /v1/send and /v1/send/bulk.
    Prevents a single key from flooding the send queue.
    Default: 30 send-requests / minute.
    """
    scope         = "send_min"
    window        = 60
    unit_label    = "minute"
    default_limit = 30


class BurstThrottle(_SlidingWindowThrottle):
    """
    Short burst window (10 requests / 5 seconds) for rapid-fire protection.
    Applied globally via DEFAULT_THROTTLE_CLASSES in settings.
    """
    scope         = "burst"
    window        = 5
    unit_label    = "5 seconds"
    default_limit = 10