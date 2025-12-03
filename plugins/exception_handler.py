"""Custom exception handler to prevent rich.print_exception errors.

Datasette's default handle_exception hook calls rich.print_exception()
when rich is available, but this fails in Docker environments because
print_exception() requires being called inside an except block.

This plugin uses @hookimpl(tryfirst=True) to run BEFORE the default
handler, returning a Response to prevent the default handler from
executing at all.
"""

from datasette import Response, hookimpl
from datasette.utils.asgi import Base400


@hookimpl(tryfirst=True)
def handle_exception(datasette, request, exception):
    """Handle all exceptions before the default handler runs.

    By using tryfirst=True, this runs before Datasette's built-in
    handler which calls rich.print_exception().
    """

    async def inner():
        # Determine status code
        if isinstance(exception, Base400):
            status = exception.status
            message = exception.args[0] if exception.args else "Error"
        else:
            status = 500
            message = str(exception)

        # For JSON requests, return JSON error
        if request.path.split("?")[0].endswith(".json"):
            return Response.json(
                {"ok": False, "error": message, "status": status},
                status=status,
            )

        # For HTML requests, render error template
        templates = [f"{status}.html", "error.html"]
        try:
            environment = datasette.get_jinja_environment(request)
            template = environment.select_template(templates)
            return Response.html(
                await template.render_async(
                    {
                        "ok": False,
                        "error": message,
                        "status": status,
                        "title": f"Error {status}",
                        "urls": datasette.urls,
                        "app_css_hash": datasette.app_css_hash(),
                        "menu_links": lambda: [],
                    }
                ),
                status=status,
            )
        except Exception:
            # Fallback if template rendering fails
            return Response.html(
                f"""<!DOCTYPE html>
<html>
<head><title>Error {status}</title></head>
<body>
<h1>Error {status}</h1>
<p>{message}</p>
<p><a href="/">Return to homepage</a></p>
</body>
</html>""",
                status=status,
            )

    return inner
