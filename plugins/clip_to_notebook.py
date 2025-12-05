"""Plugin to add clip-to-notebook icons to table rows."""

import markupsafe
from datasette import hookimpl


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    """Add a clip icon next to the id column for agendas/minutes tables."""
    # Only process the id column (primary key for these tables)
    if column != "id":
        return None

    # Only for agendas and minutes tables
    if table not in ("agendas", "minutes"):
        return None

    # Get the subdomain from plugin config
    subdomain = datasette.plugin_config("corkboard", {}).get("subdomain", "")

    # Build the clip URL with UTM tracking
    clip_url = (
        f"https://civic.observer/clip/?id={value}&subdomain={subdomain}&table={table}"
        f"&utm_source=civicband&utm_medium=clip&utm_campaign={subdomain}&utm_content=row_icon"
    )

    # Return the rowid value with a clip icon link
    return markupsafe.Markup(
        f"{value} "
        f'<a href="{clip_url}" target="_blank" title="Clip to Notebook" '
        f'class="clip-icon" '
        f'data-umami-event="clip_to_notebook" '
        f'data-umami-event-table="{table}">📋</a>'
    )
