"""Server-rendered replacement for datasette-search-all.

The upstream plugin renders the search page and lets the browser fetch
results from each searchable table over JSON. This plugin instead performs
the search inside the Datasette instance and renders the results server-side:

- ``/-/search`` accepts a POST with a ``q`` form field (GET renders the form).
- Minutes and agendas results are rendered with the existing
  ``_page_card.html`` partial, matching the table views.
- Other searchable tables fall back to a plain ``rows-and-columns`` table.

Result cells are produced by asking Datasette itself for the table JSON with
``_extra=render_cell``, so all of the repo's ``render_cell`` plugins
(search highlighting, page images, JSON entity/vote rendering) apply exactly
as they do on the table pages.
"""

import logging
from urllib.parse import urlencode

import markupsafe
from datasette import Forbidden, hookimpl
from datasette.resources import TableResource
from datasette.utils import PrefixedUrlString
from datasette.utils.asgi import Response

logger = logging.getLogger(__name__)

RESULTS_PER_TABLE = 10
MAX_QUERY_LENGTH = 200

# Tables rendered with the page card partial, mapped to the ``document_type``
# value expected by ``_page_card.html``.
PAGE_CARD_TABLES = {"minutes": "minutes", "agendas": "agenda"}


async def iterate_searchable_tables(datasette, request):
    """Yield (database_name, table_name) for every table with an FTS index.

    Adapted from datasette-search-all (Apache 2.0) since this plugin replaces
    it: hidden tables and FTS shadow tables are skipped, and only tables the
    actor can view are returned.
    """
    for database in datasette.databases.values():
        hidden_tables = set(await database.hidden_table_names())
        for table in await database.table_names():
            if table in hidden_tables or table.endswith("_fts"):
                continue
            if not await database.fts_table(table):
                continue
            try:
                await datasette.ensure_permission(
                    action="view-table",
                    resource=TableResource(database=database.name, table=table),
                    actor=request.actor,
                )
            except Forbidden:
                continue
            yield database.name, table


async def get_searchable_tables(datasette, request):
    return [table async for table in iterate_searchable_tables(datasette, request)]


async def has_searchable_tables(datasette, request):
    async for _ in iterate_searchable_tables(datasette, request):
        return True
    return False


def _build_cell_rows(columns, rows, rendered_rows):
    """Turn raw JSON rows plus render_cell overrides into template cells."""
    cell_rows = []
    for index, row in enumerate(rows):
        rendered = rendered_rows[index] if index < len(rendered_rows) else {}
        cells = []
        for column in columns:
            raw = row.get(column)
            if column in rendered:
                value = markupsafe.Markup(rendered[column])
            elif raw is None or raw == "":
                value = markupsafe.Markup("&nbsp;")
            else:
                value = raw
            cells.append(
                {
                    "column": column,
                    "value": value,
                    "raw": raw,
                    "value_type": "none" if raw is None else type(raw).__name__,
                }
            )
        cell_rows.append(cells)
    return cell_rows


async def search_table(datasette, database, table, query):
    """Search one table and return a template-ready result section."""
    params = [
        ("_search", query),
        ("_size", RESULTS_PER_TABLE),
        ("_shape", "objects"),
        ("_extra", "columns"),
        ("_extra", "render_cell"),
        ("_extra", "count"),
    ]
    url = datasette.urls.table(database, table, format="json")
    target = PrefixedUrlString(f"{url}?{urlencode(params)}")

    result = {
        "database": database,
        "table": table,
        "document_type": PAGE_CARD_TABLES.get(table),
        "count": 0,
        "columns": [],
        "rows": [],
        "search_url": f"{datasette.urls.table(database, table)}?"
        + urlencode({"_search": query}),
        "has_more": False,
        "more_count": 0,
        "error": None,
    }

    try:
        response = await datasette.client.get(target)
    except Exception:
        logger.exception("search-all request failed for %s/%s", database, table)
        result["error"] = "Search failed"
        return result

    if response.status_code != 200:
        logger.warning(
            "search-all got status %s for %s/%s",
            response.status_code,
            database,
            table,
        )
        result["error"] = "Search failed"
        return result

    data = response.json()
    count = data.get("count") or 0
    result["count"] = count
    result["columns"] = data.get("columns") or []
    result["rows"] = _build_cell_rows(
        result["columns"], data.get("rows") or [], data.get("render_cell") or []
    )
    result["has_more"] = count > RESULTS_PER_TABLE
    result["more_count"] = max(count - RESULTS_PER_TABLE, 0)
    return result


async def search_all(datasette, request):
    query = ""
    if request.method == "POST":
        post = await request.post_vars()
        query = (post.get("q") or "").strip()[:MAX_QUERY_LENGTH]

    searchable_tables = await get_searchable_tables(datasette, request)

    results = []
    if query:
        for database, table in searchable_tables:
            results.append(await search_table(datasette, database, table, query))
        total = sum(result["count"] for result in results)
        # Emit a server-side search event. Imported lazily so this plugin still
        # loads without civic_analytics, and never let analytics break search.
        try:
            from plugins.civic_analytics import track_search

            await track_search(
                datasette,
                request,
                query,
                search_type="search_all",
                extra_data={
                    "result_count": total,
                    "tables_searched": len(searchable_tables),
                },
            )
        except ImportError:
            logger.warning("civic_analytics unavailable; skipping search analytics")
        except Exception:
            logger.exception("Failed to track search-all analytics event")

    return Response.html(
        await datasette.render_template(
            "search_all.html",
            {
                "q": query,
                "results": results,
                "searchable_tables": searchable_tables,
            },
            request=request,
        )
    )


@hookimpl
def register_routes():
    return [
        (r"^/-/search$", search_all),
    ]


@hookimpl
def menu_links(datasette, request):
    async def inner():
        if not request:
            return None
        if await has_searchable_tables(datasette, request):
            return [
                {
                    "href": datasette.urls.path("/-/search"),
                    "label": "Search all tables",
                }
            ]

    return inner


@hookimpl
def extra_template_vars(template, datasette, request):
    if template != "index.html":
        return

    async def inner():
        return {"searchable_tables": await get_searchable_tables(datasette, request)}

    return inner
