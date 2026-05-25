"""
Structured request/response logging middleware.

Logs every API request as a JSON line containing:
  method, path, status_code, duration_ms, user, request_id, ip, user_agent

Place: core/middleware/logging.py
"""

import json
import logging
import time

logger = logging.getLogger("api.access")


class RequestLoggingMiddleware:
    """
    Structured JSON access log for every request.
    Attach after RequestIDMiddleware so request_id is available.
    """

    # Paths to skip (health check, static files, tracking pixel)
    _SKIP_PREFIXES = ("/static/", "/media/", "/t/o/", "/t/c/", "/__debug__/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip noisy endpoints
        if any(request.path.startswith(p) for p in self._SKIP_PREFIXES):
            return self.get_response(request)

        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.pk)

        log_record = {
            "method":      request.method,
            "path":        request.path,
            "status":      response.status_code,
            "duration_ms": duration_ms,
            "user_id":     user_id,
            "request_id":  getattr(request, "request_id", ""),
            "ip":          self._get_ip(request),
            "user_agent":  request.META.get("HTTP_USER_AGENT", "")[:200],
        }

        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, json.dumps(log_record))

        return response

    @staticmethod
    def _get_ip(request) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "")