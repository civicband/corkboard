import markupsafe
from datasette import hookimpl


@hookimpl
def render_cell(row, value, column, table, database, datasette):
    # Render {"href": "...", "label": "..."} as link
    if not column == "page_image":
        return None
    subdomain = datasette.plugin_config("umami").get("subdomain")
    if not value.startswith("/"):
        value = f"/{value}"
    return markupsafe.Markup(
        f'<img src="https://cdn.civic.band/{subdomain}{value}?width=800">'
    )
