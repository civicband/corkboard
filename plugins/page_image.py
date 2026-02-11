import markupsafe
from datasette import hookimpl
import os


@hookimpl
def render_cell(row, value, column, table, database, datasette):
    # Render {"href": "...", "label": "..."} as link
    if column != "page_image":
        return None
    try:
        subdomain = row["subdomain"]
    except (KeyError, IndexError):
        subdomain = datasette.plugin_config("corkboard").get("subdomain")
    if not value.startswith("/"):
        value = f"/{value}"

    url = os.getenv("CDN_URL", "https://cdn.civic.band")
    return markupsafe.Markup(f'<img src="{url}/{subdomain}{value}?width=800">')
