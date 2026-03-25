"""Django management command to run Datasette for local development."""

import json
import os

import sqlite_utils
import uvicorn
from datasette.app import Datasette
from django.core.management.base import BaseCommand, CommandError
from jinja2 import Environment, FileSystemLoader


class Command(BaseCommand):
    """Start a standalone Datasette server for local template testing."""

    help = "Start Datasette for local development without subdomain configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "site",
            nargs="?",
            help="Site subdomain (e.g., alameda.ca). Used to find database and metadata.",
        )
        parser.add_argument(
            "--db",
            dest="db",
            help="Explicit database path. Overrides site-based path.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run Datasette on (default: 8001).",
        )
        parser.add_argument(
            "--base-url",
            dest="base_url",
            default="/",
            help="Base URL path (e.g., /proxy/8001/ for VS Code tunnels).",
        )

    def handle(self, **options):
        site = options.get("site")
        db_path = options.get("db")
        port = options.get("port")
        base_url = options.get("base_url")

        if not site and not db_path:
            raise CommandError("You must provide either a site subdomain or --db path.")

        resolved_db = db_path if db_path else f"../sites/{site}/meetings.db"

        if not os.path.exists(resolved_db):
            raise CommandError(f"Database not found: {resolved_db}")

        if site:
            context = self.get_site_context(site)
        else:
            context = self.get_placeholder_context()

        self.start_server(resolved_db, site, port, context, base_url)

    def get_site_context(self, subdomain):
        """Look up site in sites.db and return context dict."""
        db = sqlite_utils.Database("sites.db")
        site = db["sites"].get(subdomain)

        if site is None:
            raise CommandError(
                f"Site not found: {subdomain}. "
                "Run with --db to use a database without site metadata."
            )

        return {
            "name": site["name"],
            "state": site["state"],
            "subdomain": site["subdomain"],
            "last_updated": site["last_updated"],
        }

    def get_placeholder_context(self):
        """Return placeholder defaults for --db only mode."""
        return {
            "name": "Local Dev",
            "state": "",
            "subdomain": "local",
            "last_updated": "",
        }

    def start_server(self, db_path, site, port, context, base_url="/"):
        """Start the Datasette server."""
        db_list = [db_path]

        if site:
            finance_db = f"../sites/{site}/finance/election_finance.db"
            if os.path.exists(finance_db):
                db_list.append(finance_db)

            items_db = f"../sites/{site}/finance/items.db"
            if os.path.exists(items_db):
                db_list.append(items_db)

        jinja_env = Environment(loader=FileSystemLoader("templates/config"))
        template = jinja_env.get_template("metadata.json")
        metadata = json.loads(template.render(context=context))

        datasette_instance = Datasette(
            db_list,
            config=metadata,
            plugins_dir="plugins",
            template_dir="templates/datasette",
            static_mounts=[("-/static-plugins/corkboard", "plugins/static")],
            settings={
                "base_url": base_url,
                "force_https_urls": False,
                "default_page_size": 100,
                "sql_time_limit_ms": 3000,
                "num_sql_threads": 5,
                "default_facet_size": 10,
                "facet_time_limit_ms": 100,
                "allow_download": True,
                "allow_csv_stream": True,
                "truncate_cells_html": 0,
            },
        )

        site_name = context.get("name", "Local Dev")
        self.stdout.write(f"Starting Datasette for {site_name}")
        self.stdout.write(f"Database: {db_path}")
        self.stdout.write(f"Metadata: {site_name} Civic Data")
        self.stdout.write("")
        self.stdout.write(f"Running at http://localhost:{port}/")
        self.stdout.write("Press Ctrl+C to stop.")

        # Use lifespan="on" to trigger Datasette's startup hooks
        uvicorn.run(
            datasette_instance.app(),
            host="127.0.0.1",
            port=port,
            log_level="info",
            lifespan="on",
        )
