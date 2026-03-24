"""Django management command to run Datasette for local development."""

import os

import sqlite_utils
from django.core.management.base import BaseCommand, CommandError


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

    def handle(self, **options):
        site = options.get("site")
        db_path = options.get("db")
        port = options.get("port")

        if not site and not db_path:
            raise CommandError("You must provide either a site subdomain or --db path.")

        resolved_db = db_path if db_path else f"../sites/{site}/meetings.db"

        if not os.path.exists(resolved_db):
            raise CommandError(f"Database not found: {resolved_db}")

        # Build metadata context
        if site:
            context = self.get_site_context(site)
        else:
            context = self.get_placeholder_context()

        self.start_server(resolved_db, site, port, context)

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

    def start_server(self, db_path, site, port, context):
        """Start the Datasette server. Stubbed for testing."""
        pass
