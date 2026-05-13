"""
DRF authentication class that resolves a raw Bearer token
to an APIKey → User pair.

Place: core/authentication.py
"""

import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.authentication.models import APIKey


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class APIKeyAuthentication(BaseAuthentication):
    """
    Authorization: Bearer ems_<token>

    Flow:
      1. Extract raw key from Authorization header.
      2. Delegate resolution + validation to APIKey.resolve().
      3. Enforce per-key rate limits (if set) via Redis cache.
      4. Touch last_used timestamp.
      5. Return (user, api_key).
    """

    keyword = "Bearer"

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith(f"{self.keyword} "):
            return None  # pass to next authenticator

        raw_key = auth[len(self.keyword) + 1:].strip()
        if not raw_key:
            return None

        api_key = APIKey.resolve(raw_key)

        if api_key is None:
            raise AuthenticationFailed("Invalid API key.")

        if api_key.is_expired:
            raise AuthenticationFailed("API key has expired.")

        if not api_key.user.is_active:
            raise AuthenticationFailed("User account is disabled.")

        self._check_rate_limit(api_key)
        api_key.touch()

        return (api_key.user, api_key)

    def authenticate_header(self, request):
        return self.keyword

    # ── Rate limiting ─────────────────────────────────────────────────────────

    def _check_rate_limit(self, api_key: APIKey) -> None:
        """
        Lightweight sliding-window counter stored in Redis.
        Checks per-minute then per-hour limits if configured on the key.
        """
        if api_key.rate_limit_per_min:
            self._enforce(
                key=f"rl:min:{api_key.pk}",
                limit=api_key.rate_limit_per_min,
                window=60,
                unit="minute",
            )

        if api_key.rate_limit_per_hour:
            self._enforce(
                key=f"rl:hr:{api_key.pk}",
                limit=api_key.rate_limit_per_hour,
                window=3600,
                unit="hour",
            )

    @staticmethod
    def _enforce(key: str, limit: int, window: int, unit: str) -> None:
        count = cache.get(key, 0)
        if count >= limit:
            raise Throttled(
                detail=f"Rate limit exceeded: {limit} requests per {unit}.",
                wait=window,
            )
        # Increment; set TTL only on first request in the window
        pipe = cache.get_many([key])
        if key not in pipe:
            cache.set(key, 1, timeout=window)
        else:
            cache.incr(key)