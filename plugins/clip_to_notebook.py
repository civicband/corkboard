"""Plugin to add clip-to-notebook icons to table rows."""

import markupsafe
from datasette import hookimpl


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    """Add a clip icon next to the page column for agendas/minutes tables.

    Note: We use the 'page' column instead of 'id' because Datasette
    renders the primary key column specially (wrapping it in a link) without
    calling render_cell hooks.
    """
    # Only process the page column
    if column != "page":
        return None

    # Only for agendas and minutes tables
    if table not in ("agendas", "minutes"):
        return None

    # Get the row id from the row data
    try:
        row_id = row["id"]
    except (KeyError, TypeError):
        return None

    # Get the subdomain from plugin config
    config = datasette.plugin_config("corkboard") or {}
    subdomain = config.get("subdomain", "")

    # Build the clip URL with UTM tracking
    clip_url = (
        f"https://civic.observer/clip/?id={row_id}&subdomain={subdomain}&table={table}"
        f"&utm_source=civicband&utm_medium=clip&utm_campaign={subdomain}&utm_content=row_icon"
    )

    # Return the page value with a clip icon link
    escaped_value = markupsafe.escape(value)
    return markupsafe.Markup(
        f"{escaped_value} "
        f'<a href="{clip_url}" target="_blank" title="Clip to Notebook" '
        f'class="clip-icon" '
        f'data-umami-event="clip_to_notebook" '
        f'data-umami-event-table="{table}">📋</a>'
    )
