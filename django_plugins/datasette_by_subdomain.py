import json
import djp
from jinja2 import Environment, FileSystemLoader, select_autoescape
import sqlite_utils


@djp.hookimpl
def asgi_wrapper():
    return wrap


def wrap(app):
    async def wrapper(scope, receive, send):
        await datasette_hello_world_wrapper(scope, receive, send, app)

    return wrapper


async def datasette_hello_world_wrapper(scope, receive, send, app):
    if scope["type"] == "http":
        headers = scope["headers"]
        for header, value in headers:
            if header.decode("utf-8") == "host":
                host = value.decode("utf-8")
                break
        if host.split(":")[0] in ("localhost", "127.0.0.1", "0.0.0.0"):
            await app(scope, receive, send)
        db = sqlite_utils.Database("sites.db")

        subdomain = ".".join(host.split(".")[:-2])
        try:
            site = db["sites"].get(subdomain)
            from datasette.app import Datasette

            jinja_env = Environment(
                loader=FileSystemLoader("templates/config"),
                autoescape=select_autoescape(),
            )
            metadata = json.loads(
                jinja_env.get_template("metadata.json").render(site=site)
            )
            ds = Datasette(
                [f"/sites/{subdomain}/meetings.db"],
                metadata=metadata,
                plugins_dir="plugins",
                template_dir="templates/datasette",
                settings={
                    "force_https_urls": True,
                    "default_page_size": 100,
                    "sql_time_limit_ms": 3000,
                    "num_sql_threads": 5,
                    "default_facet_size": 10,
                    "facet_time_limit_ms": 100,
                    "allow_downlaod": "off",
                    "allow_csv_stream": "off",
                },
            ).app()
            await ds(scope, receive, send)
        except:
            await app(scope, receive, send)
