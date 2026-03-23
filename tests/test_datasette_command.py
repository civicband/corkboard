"""Tests for the datasette management command."""

from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


class TestDatasetteCommandArguments:
    """Test argument parsing and validation."""

    def test_requires_site_or_db(self):
        """Command fails without site or --db argument."""
        with pytest.raises(CommandError, match="must provide"):
            call_command("datasette")

    def test_accepts_site_argument(self):
        """Command accepts a site subdomain as positional argument."""
        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", "test.ca")

    def test_accepts_db_flag(self):
        """Command accepts --db flag for explicit database path."""
        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", db="/path/to/test.db")

    def test_accepts_port_flag(self):
        """Command accepts --port flag."""
        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", db="/path/to/test.db", port=8002)

    def test_default_port_is_8001(self):
        """Default port is 8001."""
        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", db="/path/to/test.db")
            assert start_mock.call_args is not None


class TestDatabasePathResolution:
    """Test database path resolution logic."""

    def test_site_resolves_to_convention_path(self):
        """Site subdomain resolves to ../sites/{subdomain}/meetings.db."""
        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database") as db_mock,
        ):
            mock_db = MagicMock()
            mock_db.__getitem__.return_value.get.return_value = {
                "name": "Alameda",
                "state": "CA",
                "subdomain": "alameda.ca",
                "last_updated": "2026-01-01",
            }
            db_mock.return_value = mock_db

            call_command("datasette", "alameda.ca")

            call_args = start_mock.call_args
            assert call_args[0][0] == "../sites/alameda.ca/meetings.db"

    def test_db_flag_overrides_convention(self):
        """--db flag overrides the convention-based path."""
        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", db="/custom/path/meetings.db")

            call_args = start_mock.call_args
            assert call_args[0][0] == "/custom/path/meetings.db"

    def test_site_with_db_uses_db_path(self):
        """When both site and --db provided, --db takes precedence for path."""
        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database") as db_mock,
        ):
            mock_db = MagicMock()
            mock_db.__getitem__.return_value.get.return_value = {
                "name": "Alameda",
                "state": "CA",
                "subdomain": "alameda.ca",
                "last_updated": "2026-01-01",
            }
            db_mock.return_value = mock_db

            call_command("datasette", "alameda.ca", db="/custom/db.db")

            call_args = start_mock.call_args
            assert call_args[0][0] == "/custom/db.db"

    def test_missing_database_raises_error(self):
        """Error when database file doesn't exist."""
        with (
            patch("os.path.exists", return_value=False),
            pytest.raises(CommandError, match="Database not found"),
        ):
            call_command("datasette", db="/nonexistent/db.db")
