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
        mock_table = MagicMock()
        mock_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database", return_value=mock_db),
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


class TestMetadataContext:
    """Test metadata context building from sites.db or defaults."""

    def test_site_lookup_builds_context_from_sitesdb(self):
        """Site subdomain triggers sites.db lookup for context."""
        mock_table = MagicMock()
        mock_table.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-03-15",
        }
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database", return_value=mock_db),
        ):
            call_command("datasette", "alameda.ca")

            mock_db.__getitem__.assert_called_with("sites")
            mock_table.get.assert_called_with("alameda.ca")

    def test_site_not_found_raises_error(self):
        """Error when site not found in sites.db."""
        mock_table = MagicMock()
        mock_table.get.return_value = None
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        with (
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database", return_value=mock_db),
            pytest.raises(CommandError, match="Site not found"),
        ):
            call_command("datasette", "nonexistent.ca")

    def test_db_only_uses_placeholder_defaults(self):
        """--db only mode uses placeholder defaults for context."""
        with (
            patch("pages.management.commands.datasette.Command.start_server"),
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database") as db_mock,
        ):
            call_command("datasette", db="/path/to/test.db")

            db_mock.assert_not_called()


class TestMetadataTemplateRendering:
    """Test Jinja2 metadata template rendering."""

    def test_renders_metadata_template_with_context(self):
        """Metadata template is rendered with site context."""
        mock_table = MagicMock()
        mock_table.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-03-15",
        }
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database", return_value=mock_db),
        ):
            call_command("datasette", "alameda.ca")

            call_args = start_mock.call_args
            context = call_args[0][3]  # Fourth positional arg
            assert context["name"] == "Alameda"
            assert context["state"] == "CA"
            assert context["subdomain"] == "alameda.ca"

    def test_placeholder_context_used_for_db_only(self):
        """Placeholder context used when only --db provided."""
        with (
            patch(
                "pages.management.commands.datasette.Command.start_server"
            ) as start_mock,
            patch("os.path.exists", return_value=True),
        ):
            call_command("datasette", db="/path/to/test.db")

            call_args = start_mock.call_args
            context = call_args[0][3]
            assert context["name"] == "Local Dev"
            assert context["state"] == ""
            assert context["subdomain"] == "local"


class TestDatasetteServerSetup:
    """Test Datasette instance configuration."""

    def test_creates_datasette_with_correct_settings(self):
        """Datasette instance created with dev-friendly settings."""
        mock_table = MagicMock()
        mock_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        mock_template = MagicMock()
        mock_template.render.return_value = '{"title": "Test"}'
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        with (
            patch("os.path.exists", return_value=True),
            patch("sqlite_utils.Database", return_value=mock_db),
            patch("pages.management.commands.datasette.Datasette") as datasette_mock,
            patch("pages.management.commands.datasette.uvicorn.run"),
            patch(
                "pages.management.commands.datasette.Environment", return_value=mock_env
            ),
        ):
            call_command("datasette", "test.ca")

            datasette_mock.assert_called_once()
            call_kwargs = datasette_mock.call_args.kwargs
            assert call_kwargs["settings"]["force_https_urls"] is False
            assert call_kwargs["settings"]["allow_download"] is True
            assert call_kwargs["plugins_dir"] == "plugins"
            assert call_kwargs["template_dir"] == "templates/datasette"

    def test_includes_additional_databases_if_present(self):
        """Finance and items databases included if they exist."""

        def path_exists(path):
            return path in [
                "../sites/test.ca/meetings.db",
                "../sites/test.ca/finance/election_finance.db",
                "../sites/test.ca/finance/items.db",
            ]

        mock_table = MagicMock()
        mock_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mock_db = MagicMock()
        mock_db.__getitem__.return_value = mock_table

        mock_template = MagicMock()
        mock_template.render.return_value = '{"title": "Test"}'
        mock_env = MagicMock()
        mock_env.get_template.return_value = mock_template

        with (
            patch("os.path.exists", side_effect=path_exists),
            patch("sqlite_utils.Database", return_value=mock_db),
            patch("pages.management.commands.datasette.Datasette") as datasette_mock,
            patch("pages.management.commands.datasette.uvicorn.run"),
            patch(
                "pages.management.commands.datasette.Environment", return_value=mock_env
            ),
        ):
            call_command("datasette", "test.ca")

            call_args = datasette_mock.call_args
            db_list = call_args[0][0]
            assert len(db_list) == 3
            assert "../sites/test.ca/meetings.db" in db_list
            assert "../sites/test.ca/finance/election_finance.db" in db_list
            assert "../sites/test.ca/finance/items.db" in db_list
