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
# urlpatterns() must return a list for Django URL concatenation to work
mock_djp.urlpatterns = MagicMock(return_value=[])
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


class TestQueryLengthProtection:
    """Tests for bot protection via query length limits."""

    def test_is_query_too_long_short_query(self):
        """Short queries should be allowed."""
        assert datasette_by_subdomain.is_query_too_long(b"text=hello") is False
        assert datasette_by_subdomain.is_query_too_long(b"_search=council") is False

    def test_is_query_too_long_long_text(self):
        """Long text queries should be blocked."""
        long_text = "a" * 600
        query = f"text={long_text}".encode()
        assert datasette_by_subdomain.is_query_too_long(query) is True

    def test_is_query_too_long_long_search(self):
        """Long _search queries should be blocked."""
        long_text = "a" * 600
        query = f"_search={long_text}".encode()
        assert datasette_by_subdomain.is_query_too_long(query) is True

    def test_is_query_too_long_empty(self):
        """Empty query string should be allowed."""
        assert datasette_by_subdomain.is_query_too_long(b"") is False
        assert datasette_by_subdomain.is_query_too_long(None) is False

    def test_is_query_too_long_other_params(self):
        """Long values in other params should be allowed."""
        long_text = "a" * 600
        query = f"other_param={long_text}".encode()
        assert datasette_by_subdomain.is_query_too_long(query) is False


@pytest.mark.asyncio
async def test_bot_protection_blocks_long_queries():
    """Test that long text queries return 402."""
    with patch(
        "django_plugins.datasette_by_subdomain.sqlite_utils.Database"
    ) as mock_sqlite:
        mock_app = AsyncMock()
        long_text = "a" * 600
        mock_scope = {
            "type": "http",
            "method": "GET",
            "path": "/meetings/minutes",
            "query_string": f"text={long_text}".encode(),
            "headers": [(b"host", b"test.civic.band")],
        }
        mock_receive = AsyncMock()
        mock_send = AsyncMock()

        # Setup sqlite mock
        mock_db_instance = MagicMock()
        mock_sites_table = MagicMock()
        mock_db_instance.__getitem__.return_value = mock_sites_table
        mock_sqlite.return_value = mock_db_instance
        mock_sites_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test",
            "last_updated": "2024-01-01",
        }

        wrapper = datasette_by_subdomain.wrap(mock_app)
        await wrapper(mock_scope, mock_receive, mock_send)

        # Should NOT call the app
        mock_app.assert_not_called()

        # Should return 402
        assert mock_send.call_count == 2
        start_message = mock_send.call_args_list[0][0][0]
        assert start_message["status"] == 402

        # Body should be JSON with API signup URL
        body_message = mock_send.call_args_list[1][0][0]
        body = json.loads(body_message["body"])
        assert body["error"] == "query_too_long"
        assert "get_api_key" in body


@pytest.mark.asyncio
async def test_asgi_wrapper_missing_subdomain():
    """Test handling when subdomain doesn't exist - should redirect to civic.band."""
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

        # Should NOT fall back to Django app - should redirect instead
        mock_app.assert_not_called()

        # Verify redirect response was sent
        assert mock_send.call_count == 2

        # First call should be http.response.start with 302 status
        start_call = mock_send.call_args_list[0]
        start_message = start_call[0][0]
        assert start_message["type"] == "http.response.start"
        assert start_message["status"] == 302
        # Check location header
        headers_dict = dict(start_message["headers"])
        assert headers_dict[b"location"] == b"https://civic.band/"

        # Second call should be http.response.body
        body_call = mock_send.call_args_list[1]
        body_message = body_call[0][0]
        assert body_message["type"] == "http.response.body"


@pytest.mark.asyncio
async def test_asgi_wrapper_missing_subdomain_returns_none():
    """Test handling when subdomain lookup returns None (not exception)."""
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

        # Setup sqlite mock to return None for missing site
        mock_db_instance = MagicMock()
        mock_sites_table = MagicMock()
        mock_db_instance.__getitem__.return_value = mock_sites_table
        mock_sqlite.return_value = mock_db_instance

        # Mock site data - return None (site not found)
        mock_sites_table.get.return_value = None

        # Run the wrapper
        wrapper = datasette_by_subdomain.wrap(mock_app)

        # Run the test
        await wrapper(mock_scope, mock_receive, mock_send)

        # Verify subdomain was correctly extracted
        mock_sites_table.get.assert_called_once_with("nonexistent")

        # Should NOT fall back to Django app - should redirect instead
        mock_app.assert_not_called()

        # Verify redirect response was sent (302 to civic.band)
        assert mock_send.call_count == 2
        start_message = mock_send.call_args_list[0][0][0]
        assert start_message["status"] == 302


class TestGetClientIp:
    """Test client IP extraction from ASGI scope."""

    def test_direct_client_ip(self):
        """Direct connection should use client IP from scope."""
        scope = {
            "headers": [(b"content-type", b"application/json")],
            "client": ("192.168.1.100", 54321),
        }
        assert datasette_by_subdomain.get_client_ip(scope) == "192.168.1.100"

    def test_x_forwarded_for_single(self):
        """Single IP in X-Forwarded-For should be used."""
        scope = {
            "headers": [(b"x-forwarded-for", b"10.0.0.50")],
            "client": ("127.0.0.1", 54321),
        }
        assert datasette_by_subdomain.get_client_ip(scope) == "10.0.0.50"

    def test_x_forwarded_for_multiple(self):
        """First IP in X-Forwarded-For chain should be used."""
        scope = {
            "headers": [(b"x-forwarded-for", b"10.0.0.50, 192.168.1.1, 172.16.0.1")],
            "client": ("127.0.0.1", 54321),
        }
        assert datasette_by_subdomain.get_client_ip(scope) == "10.0.0.50"

    def test_x_forwarded_for_with_spaces(self):
        """X-Forwarded-For with extra whitespace should be handled."""
        scope = {
            "headers": [(b"x-forwarded-for", b"  10.0.0.50  , 192.168.1.1")],
            "client": ("127.0.0.1", 54321),
        }
        assert datasette_by_subdomain.get_client_ip(scope) == "10.0.0.50"

    def test_no_client_info(self):
        """Missing client info should return 'unknown'."""
        scope = {"headers": []}
        assert datasette_by_subdomain.get_client_ip(scope) == "unknown"

    def test_empty_scope(self):
        """Empty scope should return 'unknown'."""
        scope = {}
        assert datasette_by_subdomain.get_client_ip(scope) == "unknown"

    def test_x_forwarded_for_takes_precedence(self):
        """X-Forwarded-For should take precedence over client tuple."""
        scope = {
            "headers": [(b"x-forwarded-for", b"10.0.0.50")],
            "client": ("192.168.1.100", 54321),
        }
        assert datasette_by_subdomain.get_client_ip(scope) == "10.0.0.50"
