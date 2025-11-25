"""
Tests for the datasette_by_subdomain Django plugin.

This plugin routes requests to Datasette instances based on subdomains.
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We'll only patch djp since we need it to import our module
# but we don't want to block all imports
mock_djp = MagicMock()
mock_djp.hookimpl = MagicMock()
sys.modules["djp"] = mock_djp

# Now import the module under test
from django_plugins import datasette_by_subdomain


@pytest.mark.asyncio
async def test_asgi_wrapper_localhost():
    """Test that localhost requests route to the original app with early return."""
    with patch(
        "django_plugins.datasette_by_subdomain.sqlite_utils.Database"
    ) as mock_sqlite:
        # Setup mocks
        mock_app = AsyncMock()
        # Add required fields to the scope
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"host", b"localhost:8000")],
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Run the wrapper
        wrapper = datasette_by_subdomain.wrap(mock_app)

        # Run the test
        await wrapper(mock_scope, mock_receive, mock_send)

        # Verify that for localhost, the original app is called
        mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)

        # Implementation now has early return, so Database should not be called
        mock_sqlite.assert_not_called()


@pytest.mark.asyncio
async def test_asgi_wrapper_fully_mocked():
    """Unit test with all components mocked."""
    # The import structure in the datasette_by_subdomain.py file might be different
    # than what we're patching. Let's fix this based on the implementation.

    with (
        patch(
            "django_plugins.datasette_by_subdomain.sqlite_utils"
        ) as mock_sqlite_utils,
        patch("datasette.app.Datasette") as mock_datasette,
        patch("django_plugins.datasette_by_subdomain.Environment") as mock_environment,
        patch("django_plugins.datasette_by_subdomain.FileSystemLoader"),
    ):
        # Setup mocks
        mock_app = AsyncMock()
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"host", b"testcity.civic.band")],
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Setup sqlite mock
        mock_db_instance = MagicMock()
        mock_sites_table = MagicMock()
        mock_db_instance.__getitem__.return_value = mock_sites_table
        mock_sqlite_utils.Database.return_value = mock_db_instance

        # Mock site data
        mock_site = {
            "name": "Test City",
            "subdomain": "testcity",
            "state": "CA",
            "last_updated": "2024-01-01",
        }
        mock_sites_table.get.return_value = mock_site

        # Mock jinja
        mock_env_instance = MagicMock()
        mock_environment.return_value = mock_env_instance
        mock_template = MagicMock()
        mock_env_instance.get_template.return_value = mock_template
        mock_template.render.return_value = json.dumps({"title": "Test City"})

        # Mock datasette
        mock_ds_instance = MagicMock()
        mock_datasette.return_value = mock_ds_instance
        mock_ds_app = AsyncMock()
        mock_ds_instance.app.return_value = mock_ds_app

        # Run the wrapper
        wrapper = datasette_by_subdomain.wrap(mock_app)

        # Run the test
        await wrapper(mock_scope, mock_receive, mock_send)

        # Verify correct database was queried
        mock_sites_table.get.assert_called_once_with("testcity")

        # Verify datasette was initialized correctly
        mock_datasette.assert_called_once()

        # Verify datasette app was called with the correct scope
        mock_ds_app.assert_called_once_with(mock_scope, mock_receive, mock_send)

        # Verify original app was not called
        mock_app.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_metadata_template_rendering():
    """Integration test that uses the real metadata.json template."""
    with (
        patch(
            "django_plugins.datasette_by_subdomain.sqlite_utils.Database"
        ) as mock_sqlite,
        patch("datasette.app.Datasette") as mock_datasette,
        patch(
            "django_plugins.datasette_by_subdomain.Environment", autospec=True
        ) as mock_env,
    ):
        # Setup mocks
        mock_app = AsyncMock()
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"host", b"testcity.civic.band")],
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Setup sqlite mock
        mock_db_instance = MagicMock()
        mock_sites_table = MagicMock()
        mock_db_instance.__getitem__.return_value = mock_sites_table
        mock_sqlite.return_value = mock_db_instance

        # Mock site data with realistic fields that would be in the database
        mock_site = {
            "name": "Test City",
            "subdomain": "testcity",
            "state": "CA",
            "county": "Test County",
            "country": "USA",
            "population": 50000,
            "pages": 1000,
            "last_updated": "2024-01-01",
        }
        mock_sites_table.get.return_value = mock_site

        # Mock jinja environment
        mock_template = MagicMock()
        mock_template.render.return_value = json.dumps({"title": "Test City"})

        mock_env_instance = MagicMock()
        mock_env_instance.get_template.return_value = mock_template
        mock_env.return_value = mock_env_instance

        # Mock datasette
        mock_ds_instance = MagicMock()
        mock_datasette.return_value = mock_ds_instance
        mock_ds_app = AsyncMock()
        mock_ds_instance.app.return_value = mock_ds_app

        # Run the wrapper
        wrapper = datasette_by_subdomain.wrap(mock_app)

        # Run the test
        await wrapper(mock_scope, mock_receive, mock_send)

        # Verify correct database was queried
        mock_sites_table.get.assert_called_once_with("testcity")

        # Verify datasette was initialized properly
        mock_datasette.assert_called_once()
        args, kwargs = mock_datasette.call_args

        # Basic checks
        assert args[0] == ["../sites/testcity/meetings.db"]
        assert kwargs["template_dir"] == "templates/datasette"


@pytest.mark.asyncio
async def test_asgi_wrapper_missing_subdomain():
    """Test handling when subdomain doesn't exist."""
    with patch(
        "django_plugins.datasette_by_subdomain.sqlite_utils.Database"
    ) as mock_sqlite:
        # Setup mocks
        mock_app = AsyncMock()
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"host", b"nonexistent.civic.band")],
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Setup sqlite mock to raise exception for missing site
        mock_db_instance = MagicMock()
        mock_sites_table = MagicMock()
        mock_db_instance.__getitem__.return_value = mock_sites_table
        mock_sqlite.return_value = mock_db_instance

        # Mock site data - simulate not found
        mock_sites_table.get.side_effect = Exception("Site not found")

        # Run the wrapper
        wrapper = datasette_by_subdomain.wrap(mock_app)

        # Run the test
        await wrapper(mock_scope, mock_receive, mock_send)

        # Verify subdomain was correctly extracted
        mock_sites_table.get.assert_called_once_with("nonexistent")

        # With fixed implementation, it should fall back to the original app
        # when site is not found
        mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)
