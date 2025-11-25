
import markupsafe
from datasette import hookimpl


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    if column != "text":
        return None
    search_query = request.args.get("_search")
    if not search_query:
        search_query = request.args.get("_highlight")
    if search_query:
        marked_text = value.replace(search_query, f"<mark>{search_query}</mark>")
        if search_query != search_query.lower():
            marked_text = marked_text.replace(
                search_query.lower(), f"<mark>{search_query.lower()}</mark>"
            )
        if search_query != search_query.upper():
            marked_text = marked_text.replace(
                search_query.upper(), f"<mark>{search_query.upper()}</mark>"
            )
        return markupsafe.Markup(marked_text)
    return None
