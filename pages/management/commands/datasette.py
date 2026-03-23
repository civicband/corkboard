"""Django management command to run Datasette for local development."""

import os

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

        self.start_server(resolved_db, site, port)

    def start_server(self, db_path, site, port):
        """Start the Datasette server. Stubbed for testing."""
        pass
