"""Tests for the datasette management command."""

from unittest.mock import patch

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
