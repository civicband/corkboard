# This is from https://github.com/simonw/datasette-search-all because we need
# more adjustments than easily fit in a PR.

import json

from datasette import hookimpl
from datasette.utils.asgi import Response


@hookimpl
def menu_links(datasette, request):
    async def inner():
        if not request:
            return None
        if await has_searchable_tables(datasette, request):
            return [
                {"href": datasette.urls.path("/-/search"), "label": "Search all tables"}
            ]

    return inner


async def search_all(datasette, request):
    searchable_tables = list(await get_searchable_tables(datasette, request))
    tables = [
        {
            "database": database,
            "table": table,
            "url": datasette.urls.table(database, table),
            "url_json": datasette.urls.table(database, table, format="json"),
        }
        for database, table in searchable_tables
    ]

    async def metadata():
        return await datasette.get_instance_metadata()

    return Response.html(
        await datasette.render_template(
            "search_all.html",
            {
                "q": request.args.get("q") or "",
                "metadata": metadata(),
                "searchable_tables": tables,
                "searchable_tables_json": json.dumps(tables, indent=4),
            },
            request=request,
        )
    )


@hookimpl
def extra_template_vars(template, datasette, request):
    if template != "index.html":
        return

    # Add list of searchable tables
    async def inner():
        searchable_tables = list(await get_searchable_tables(datasette, request))
        return {"searchable_tables": searchable_tables}

    return inner


@hookimpl
def register_routes():
    return [
        ("/-/search", search_all),
    ]


from datasette import Forbidden


async def iterate_searchable_tables(datasette, request):
    for db_name, database in datasette.databases.items():
        hidden_tables = set(await database.hidden_table_names())
        for table in await database.table_names():
            if table in hidden_tables:
                continue
            fts_table = await database.fts_table(table)
            if fts_table:
                # Check user has permission to view that table
                try:
                    await datasette.ensure_permissions(
                        request.actor,
                        [
                            ("view-table", (database.name, table)),
                            ("view-database", database.name),
                            "view-instance",
                        ],
                    )
                    yield (db_name, table)
                except Forbidden:
                    pass


async def has_searchable_tables(datasette, request):
    # Return True on the first table we find
    async for _ in iterate_searchable_tables(datasette, request):
        return True
    return False


async def get_searchable_tables(datasette, request):
    tables = []
    async for table in iterate_searchable_tables(datasette, request):
        tables.append(table)
    return tables
