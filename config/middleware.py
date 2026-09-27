"""Structured request logging for the corkboard Django app.

Emits one JSON access record per request on the ``corkboard.access`` logger.
"""

import logging
import time

logger = logging.getLogger("corkboard.access")


def _client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


class RequestLogMiddleware:
    """Log a structured access record for every Django-processed request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 3)
        user = getattr(request, "user", None)
        logger.info(
            "request completed",
            extra={
                "request_method": request.method,
                "request_path": request.get_full_path(),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_agent": request.headers.get("User-Agent", ""),
                "remote_addr": _client_ip(request),
                "request_host": request.get_host(),
                "referer": request.headers.get("Referer", ""),
                "request_content_type": request.content_type or "",
                "request_content_length": request.headers.get("Content-Length", ""),
                "response_content_length": response.get("Content-Length", ""),
                "hx_request": bool(request.headers.get("HX-Request")),
                "user_id": (
                    user.pk if user is not None and user.is_authenticated else None
                ),
                "scheme": request.scheme,
            },
        )
        return response
