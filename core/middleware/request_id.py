"""
Middleware that attaches a unique X-Request-ID to every request/response.
Useful for correlating logs across Django, Celery, and external services.

Place: core/middleware/request_id.py
"""

import uuid


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Honour an incoming header (e.g. from a load balancer) or generate one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id

        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response