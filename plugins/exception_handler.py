"""Custom exception handler to suppress noisy rich output for 404s.

When rich is installed (e.g., via logfire), Datasette's default exception
handler prints full tracebacks to the console for ALL exceptions, including
routine 404s from bot scanners. This creates excessive noise in logs.

This plugin intercepts NotFound exceptions and returns a clean 404 response
without the rich debug output, while letting actual errors (500s) through
to be properly logged.
"""

from datasette import Response, hookimpl
from datasette.utils.asgi import NotFound


@hookimpl
def handle_exception(datasette, request, exception):
    """Handle exceptions, suppressing rich output for 404s."""
    # Only intercept NotFound (404) exceptions
    if isinstance(exception, NotFound):

        async def inner():
            # Return a simple 404 response
            return Response.html(
                await datasette.render_template(
                    "404.html",
                    {
                        "error": "Page not found",
                        "status": 404,
                        "title": "Page not found",
                    },
                    request=request,
                ),
                status=404,
            )

        return inner

    # Let other exceptions (500s, etc.) fall through to default handler
    # which will log them properly via Sentry
    return None
