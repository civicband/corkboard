from urllib.parse import urlencode

import markupsafe
from datasette import hookimpl

DATE_COLUMNS = {"date", "isodate"}
LINKABLE_TABLES = ("agendas", "minutes")


def _is_iso_date(value):
    # Only exact dates can be filtered on; years, ranges, and datetimes get no
    # link so we never emit a filter that returns nothing.
    date_part = str(value)[:10]
    if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
        return False
    return (date_part[:4] + date_part[5:7] + date_part[8:10]).isdigit()


def _link_target(table, path):
    # The table argument is the table Datasette actually queried, so it is the
    # strongest signal. Fall back to a path segment for views that do not pass
    # one. Anything else is ambiguous: return None rather than guess.
    if table in LINKABLE_TABLES:
        return table
    # First path segment is the database; only look at what follows so a
    # database named "minutes" cannot masquerade as a table.
    for segment in [segment for segment in path.split("/") if segment][1:]:
        if segment in LINKABLE_TABLES:
            return segment
    return None


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    if column not in DATE_COLUMNS or not database:
        return None
    if value is None or value == "" or not _is_iso_date(value):
        return None
    path = getattr(request, "url", "").split("?", 1)[0]
    target = _link_target(table, path)
    if target is None:
        return None

    params = {f"{column}__exact": value, "_sort": "page"}
    try:
        meeting = row["meeting"]
    except (KeyError, IndexError, TypeError):
        meeting = None
    if meeting:
        params["meeting__exact"] = meeting
    query = getattr(request, "args", {}) or {}
    if query.get("_search"):
        params["_highlight"] = query["_search"]

    try:
        base = datasette.urls.table(database, target)
    except (AttributeError, KeyError):
        base = f"/{database}/{target}"
    href = f"{base}?{urlencode(params)}"
    return markupsafe.Markup(
        f'<a href="{markupsafe.escape(href)}">{markupsafe.escape(value)}</a>'
    )
