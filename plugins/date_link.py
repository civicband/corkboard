import markupsafe
from urllib.parse import urlparse, parse_qs
from datasette import hookimpl


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    if not column == "date":
        return None
    parts = urlparse(request.url)
    path = parts.path
    if "agendas" not in path or "minutes" not in path:
        path = parts.path.replace("upcoming", "agendas")
    url = f"{path}/?date__exact={value}&_sort=page"
    if "_search" in request.args:
        url += f"&_highlight={request.args['_search']}"
    return markupsafe.Markup(f"<a href='{url}'>{value}</a>")
