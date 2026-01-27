import json
import logging
import os
from urllib.parse import parse_qs

import djp
import sqlite_utils
from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Bot protection: max length for text search queries
MAX_QUERY_TEXT_LENGTH = int(os.getenv("MAX_QUERY_TEXT_LENGTH", "500"))
API_SIGNUP_URL = os.getenv("API_SIGNUP_URL", "https://civic.observer/api")

# Patch rich.Console.print_exception to prevent errors in Datasette.
# Datasette's handle_exception calls rich.print_exception() outside of an
# except block, which fails because print_exception() requires sys.exc_info()
# to return an active exception. This patch makes it a safe no-op.
try:
    import rich.console

    def _safe_print_exception(self, *args, **kwargs):
        """No-op replacement for print_exception that won't raise."""
        pass

    rich.console.Console.print_exception = _safe_print_exception
except ImportError:
    pass

from django_plugins.api_key_auth import (
    cap_result_size,
    check_rate_limit,
    extract_api_key,
    is_first_party_request,
    is_internal_service_request,
    is_json_endpoint,
    is_research_tool_request,
    make_401_response,
    make_402_rate_limit_response,
    validate_api_key,
)


@djp.hookimpl
def asgi_wrapper():
    return wrap


def wrap(app):
    async def wrapper(scope, receive, send):
        await datasette_by_subdomain_wrapper(scope, receive, send, app)

    return wrapper


async def send_401_response(send):
    """Send a 401 Unauthorized response."""
    body, headers = make_401_response()

    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": headers,
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


async def send_redirect_to_home(send):
    """Send a 302 redirect to civic.band homepage."""
    await send(
        {
            "type": "http.response.start",
            "status": 302,
            "headers": [
                (b"location", b"https://civic.band/"),
                (b"content-type", b"text/plain"),
                (b"content-length", b"0"),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": b"",
        }
    )


async def send_404_response(send):
    """Send a simple 404 Not Found response."""
    body = b"""<!DOCTYPE html>
<html>
<head><title>404 - Page Not Found</title></head>
<body>
<h1>Page not found</h1>
<p>The page you're looking for doesn't exist.</p>
<p><a href="/">Return to homepage</a></p>
</body>
</html>"""
    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


async def send_402_response(send, error_type: str = "query_too_long"):
    """Send a 402 Payment Required response for bot-like queries or rate limiting."""
    if error_type == "rate_limit":
        body, headers = make_402_rate_limit_response()
    else:
        response = {
            "error": "query_too_long",
            "message": "Automated queries require an API key",
            "get_api_key": API_SIGNUP_URL,
        }
        body = json.dumps(response).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
    await send(
        {
            "type": "http.response.start",
            "status": 402,
            "headers": headers,
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


def is_query_too_long(query_string: bytes) -> bool:
    """Check if text search query exceeds maximum allowed length."""
    if not query_string:
        return False

    params = parse_qs(query_string.decode("utf-8", errors="ignore"))

    # Check both 'text' and '_search' parameters
    for param in ("text", "_search"):
        values = params.get(param, [])
        for value in values:
            if len(value) > MAX_QUERY_TEXT_LENGTH:
                return True

    return False


def get_client_ip(scope: dict) -> str:
    """
    Extract client IP address from ASGI scope.

    Checks X-Forwarded-For header first (for proxied requests),
    then falls back to the client address from the scope.

    Args:
        scope: ASGI scope dictionary

    Returns:
        Client IP address string
    """
    headers = scope.get("headers", [])

    # Check X-Forwarded-For header (used by proxies/load balancers)
    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        if name == "x-forwarded-for":
            # X-Forwarded-For can contain multiple IPs; first is the client
            forwarded = header_value.decode("utf-8")
            return forwarded.split(",")[0].strip()

    # Fall back to direct client address
    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"


async def datasette_by_subdomain_wrapper(scope, receive, send, app):
    if scope["type"] == "http":
        headers = scope["headers"]
        for header, value in headers:
            if header.decode("utf-8") == "host":
                host = value.decode("utf-8")
                break
        if host.split(":")[0] in ("localhost", "127.0.0.1", "0.0.0.0"):
            await app(scope, receive, send)
            return  # Early return for localhost to avoid unnecessary processing
        db = sqlite_utils.Database("sites.db")
        parts = host.split(("."))
        subdomain = ".".join(parts[:-2])

        jinja_env = Environment(
            loader=FileSystemLoader("templates/config"),
        )

        subdomain = ".".join(parts[:-2])

        # If no subdomain, fall back to Django app (main site)
        if not subdomain:
            await app(scope, receive, send)
            return

        try:
            site = db["sites"].get(subdomain)
        except Exception:
            site = None

        # Site not found - redirect to homepage
        if site is None:
            logger.warning(
                "Site not found",
                extra={"subdomain": subdomain, "host": host},
            )
            await send_redirect_to_home(send)
            return

        # Bot protection: block overly long text queries
        query_string = scope.get("query_string", b"")
        if is_query_too_long(query_string):
            await send_402_response(send)
            return

        context_blob = {
            "name": site["name"],
            "state": site["state"],
            "subdomain": site["subdomain"],
            "last_updated": site["last_updated"],
        }

        # Tiered JSON access control:
        # | Layer            | Condition                     | Action                    |
        # |------------------|-------------------------------|---------------------------|
        # | First-party      | Matching Referer              | Allow (full access)       |
        # | Internal service | Valid X-Service-Secret        | Allow (full access)       |
        # | Research tools   | UA contains Zotero/etc.       | Allow (full access)       |
        # | Rate limit       | >15 req/min per IP            | 402                       |
        # | API key          | Valid key                     | Allow (unlimited results) |
        # | No API key       | Unauthenticated               | Allow (cap _size at 100)  |
        path = scope.get("path", "")
        should_cap_results = False

        if is_json_endpoint(path):
            # Layers 1-3: Trusted sources get full access without rate limiting
            is_trusted_source = (
                is_first_party_request(headers, subdomain)  # Layer 1: browser AJAX
                or is_internal_service_request(headers)  # Layer 2: civic.observer
                or is_research_tool_request(headers)  # Layer 3: Zotero, etc.
            )

            if not is_trusted_source:
                # Layer 4: Rate limiting for all other JSON requests
                client_ip = get_client_ip(scope)
                if await check_rate_limit(client_ip):
                    logger.warning(
                        "Rate limit exceeded",
                        extra={
                            "subdomain": subdomain,
                            "path": path,
                            "client_ip": client_ip,
                        },
                    )
                    await send_402_response(send, "rate_limit")
                    return

                # Layer 5: Check for API key
                api_key = extract_api_key(headers, query_string)

                if api_key:
                    # Validate key against cache/civic.observer
                    result = await validate_api_key(api_key, subdomain)
                    if not result["valid"]:
                        await send_401_response(send)
                        return
                    # Valid API key - full access, no capping
                else:
                    # Layer 6: No API key - allow but cap results
                    should_cap_results = True

        # Cap result size for unauthenticated requests
        if should_cap_results:
            scope = dict(scope)  # Make a mutable copy
            scope["query_string"] = cap_result_size(query_string)

        metadata = json.loads(
            jinja_env.get_template("metadata.json").render(context=context_blob)
        )

        db_list = [f"../sites/{subdomain}/meetings.db"]

        from datasette.app import Datasette  # noqa: PLC0415

        datasette_instance = Datasette(
            db_list,
            config=metadata,
            plugins_dir="plugins",
            template_dir="templates/datasette",
            settings={
                "force_https_urls": True,
                "default_page_size": 100,
                "sql_time_limit_ms": 3000,
                "num_sql_threads": 5,
                "default_facet_size": 10,
                "facet_time_limit_ms": 100,
                "allow_download": False,
                "allow_csv_stream": False,
            },
        )

        # Compatibility shim for datasette-dashboards 0.8.0 with Datasette 1.0+
        # datasette-dashboards uses the deprecated permission_allowed() method
        # that was removed in Datasette 1.0a20. Add it back as a wrapper.
        async def permission_allowed(actor, action, resource=None, default=False):
            """Compatibility wrapper for the old permission_allowed() API."""
            result = await datasette_instance.allowed(
                actor, action, resource, default=default
            )
            # allowed() returns True/False, permission_allowed() returned True/False/None
            # If default=None, we should return None when permission is denied
            if default is None and not result:
                return None
            return result

        datasette_instance.permission_allowed = permission_allowed

        ds = datasette_instance.app()

        # Import NotFound to catch 404s before they hit Datasette's
        # exception handler (which calls rich.print_exception and fails)
        from datasette.utils.asgi import NotFound  # noqa: PLC0415

        try:
            await ds(scope, receive, send)
            logger.info(
                "Request completed",
                extra={
                    "subdomain": subdomain,
                    "path": path,
                    "method": scope.get("method", "GET"),
                },
            )
        except NotFound:
            # Handle 404s ourselves to avoid rich.print_exception errors
            logger.warning(
                "Page not found",
                extra={
                    "subdomain": subdomain,
                    "path": path,
                    "method": scope.get("method", "GET"),
                },
            )
            await send_404_response(send)
