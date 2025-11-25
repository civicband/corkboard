import json

import djp
import sqlite_utils
from jinja2 import Environment, FileSystemLoader


@djp.hookimpl
def asgi_wrapper():
    return wrap


def wrap(app):
    async def wrapper(scope, receive, send):
        await datasette_by_subdomain_wrapper(scope, receive, send, app)

    return wrapper


async def datasette_by_subdomain_wrapper(scope, receive, send, app):
    if scope["type"] == "http":
        headers = scope["headers"]
        for header, value in headers:
            if header.decode("utf-8") == "host":
                host = value.decode("utf-8")
                break
        if host.split(":")[0] in ("localhost", "127.0.0.1", "0.0.0.0"):
            await app(scope, receive, send)
            return  # Early return for localhost to avoid unnecessary processing
        db = sqlite_utils.Database("sites.db")
        parts = host.split(("."))
        subdomain = ".".join(parts[:-2])

        jinja_env = Environment(
            loader=FileSystemLoader("templates/config"),
        )

        subdomain = ".".join(parts[:-2])
        try:
            site = db["sites"].get(subdomain)
        except Exception:
            # Site not found, fall back to Django app
            await app(scope, receive, send)
            return
        context_blob = {
            "name": site["name"],
            "state": site["state"],
            "subdomain": site["subdomain"],
            "last_updated": site["last_updated"],
        }
        metadata = json.loads(
            jinja_env.get_template("metadata.json").render(context=context_blob)
        )

        db_list = [f"../sites/{subdomain}/meetings.db"]

        from datasette.app import Datasette  # noqa: PLC0415

        ds = Datasette(
            db_list,
            config=metadata,
            plugins_dir="plugins",
            template_dir="templates/datasette",
            settings={
                "force_https_urls": True,
                "default_page_size": 100,
                "sql_time_limit_ms": 3000,
                "num_sql_threads": 5,
                "default_facet_size": 10,
                "facet_time_limit_ms": 100,
                "allow_download": "off",
                "allow_csv_stream": "off",
            },
        ).app()
        await ds(scope, receive, send)
