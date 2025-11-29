"""
Tests for civic_analytics.py plugin.

Tests cover:
- UmamiEventTracker event sending and data cleaning
- Subdomain extraction logic
- Path parsing
- ASGI middleware integration for search and SQL tracking
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.civic_analytics import (
    UmamiEventTracker,
    extract_subdomain,
    parse_datasette_path,
)


class TestSubdomainExtraction:
    """Test subdomain extraction logic."""

    def test_single_level_subdomain(self):
        """Extract single-level subdomain."""
        assert extract_subdomain("alameda.civic.org") == "alameda"

    def test_multi_level_subdomain(self):
        """Extract multi-level subdomain."""
        assert extract_subdomain("alameda.ca.civic.org") == "alameda.ca"
        assert (
            extract_subdomain("vancouver.bc.canada.civic.org") == "vancouver.bc.canada"
        )

    def test_no_subdomain(self):
        """Return None when no subdomain present."""
        assert extract_subdomain("civic.org") is None
        assert extract_subdomain("localhost") is None
        assert extract_subdomain("127.0.0.1") is None
        assert extract_subdomain("0.0.0.0") is None

    def test_port_handling(self):
        """Extract subdomain with port in host."""
        assert extract_subdomain("alameda.ca.civic.org:8000") == "alameda.ca"
        assert extract_subdomain("localhost:8000") is None

    def test_empty_host(self):
        """Return None for empty host."""
        assert extract_subdomain("") is None
        assert extract_subdomain(None) is None

    def test_different_base_domains(self):
        """Work with any base domain."""
        assert extract_subdomain("alameda.ca.civic.band") == "alameda.ca"
        assert extract_subdomain("test.example.com") == "test"


class TestPathParsing:
    """Test Datasette path parsing."""

    def test_database_only(self):
        """Parse path with database only."""
        result = parse_datasette_path("/meetings")
        assert result == {"database": "meetings", "table": None}

    def test_database_and_table(self):
        """Parse path with database and table."""
        result = parse_datasette_path("/meetings/agendas")
        assert result == {"database": "meetings", "table": "agendas"}

    def test_empty_path(self):
        """Parse empty path."""
        result = parse_datasette_path("/")
        assert result == {"database": None, "table": None}

    def test_path_with_row_id(self):
        """Parse path with row ID (ignore extra parts)."""
        result = parse_datasette_path("/meetings/agendas/row123")
        assert result == {"database": "meetings", "table": "agendas"}

    def test_no_leading_slash(self):
        """Parse path without leading slash."""
        result = parse_datasette_path("meetings/agendas")
        assert result == {"database": "meetings", "table": "agendas"}


class TestUmamiEventTracker:
    """Test UmamiEventTracker class."""

    def test_init(self):
        """Initialize tracker with URL and website ID."""
        tracker = UmamiEventTracker("https://analytics.civic.band", "test-id")
        assert tracker.url == "https://analytics.civic.band"
        assert tracker.website_id == "test-id"
        assert tracker.endpoint == "https://analytics.civic.band/api/send"

    def test_init_strips_trailing_slash(self):
        """Strip trailing slash from URL."""
        tracker = UmamiEventTracker("https://analytics.civic.band/", "test-id")
        assert tracker.url == "https://analytics.civic.band"

    @pytest.mark.asyncio
    async def test_track_event_disabled(self):
        """Skip tracking when analytics disabled."""
        # Patch module-level constant directly since it's set at import time
        with patch("plugins.civic_analytics.UMAMI_ENABLED", False):
            tracker = UmamiEventTracker("https://test.com", "test-id")

            with patch("httpx.AsyncClient") as mock_client:
                await tracker.track_event(
                    event_name="test", url="/test", hostname="test.civic.band"
                )
                # Should not call httpx when disabled
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_event_success(self):
        """Successfully track event."""
        # Patch module-level constants directly since they're set at import time
        with (
            patch("plugins.civic_analytics.UMAMI_ENABLED", True),
            patch("plugins.civic_analytics.UMAMI_API_KEY", "test-key"),
        ):
            tracker = UmamiEventTracker("https://test.com", "test-id")

            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await tracker.track_event(
                    event_name="search_query",
                    url="/meetings/agendas",
                    title="Search Query - alameda.ca",
                    referrer="https://google.com",
                    hostname="alameda.ca.civic.band",
                    event_data={"query_text": "council", "subdomain": "alameda.ca"},
                )

            # Verify API call was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args

            # Check endpoint
            assert call_args[0][0] == "https://test.com/api/send"

            # Check payload
            payload = call_args[1]["json"]
            assert payload["type"] == "event"
            assert payload["payload"]["name"] == "search_query"
            assert payload["payload"]["hostname"] == "alameda.ca.civic.band"
            assert payload["payload"]["data"]["query_text"] == "council"

            # Check headers
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_track_event_failure(self):
        """Handle tracking failure gracefully."""
        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            from plugins import civic_analytics

            tracker = civic_analytics.UmamiEventTracker("https://test.com", "test-id")

            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch("httpx.AsyncClient", return_value=mock_client):
                # Should not raise exception
                await tracker.track_event(
                    event_name="test", url="/test", hostname="test.civic.band"
                )

    @pytest.mark.asyncio
    async def test_track_event_exception(self):
        """Handle exceptions during tracking."""
        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            from plugins import civic_analytics

            tracker = civic_analytics.UmamiEventTracker("https://test.com", "test-id")

            with patch("httpx.AsyncClient", side_effect=Exception("Network error")):
                # Should not raise exception
                await tracker.track_event(
                    event_name="test", url="/test", hostname="test.civic.band"
                )

    def test_clean_event_data_strings(self):
        """Truncate long strings to 500 characters."""
        tracker = UmamiEventTracker("https://test.com", "test-id")
        data = {"long_string": "a" * 600}
        cleaned = tracker._clean_event_data(data)
        assert len(cleaned["long_string"]) == 500

    def test_clean_event_data_floats(self):
        """Round floats to 4 decimal places."""
        tracker = UmamiEventTracker("https://test.com", "test-id")
        data = {"number": 3.14159265}
        cleaned = tracker._clean_event_data(data)
        assert cleaned["number"] == 3.1416

    def test_clean_event_data_lists(self):
        """Convert lists to comma-separated strings."""
        tracker = UmamiEventTracker("https://test.com", "test-id")
        data = {"tags": ["tag1", "tag2", "tag3"]}
        cleaned = tracker._clean_event_data(data)
        assert cleaned["tags"] == "tag1,tag2,tag3"

    def test_clean_event_data_none_values(self):
        """Skip None values."""
        tracker = UmamiEventTracker("https://test.com", "test-id")
        data = {"key1": "value1", "key2": None, "key3": "value3"}
        cleaned = tracker._clean_event_data(data)
        assert "key2" not in cleaned
        assert len(cleaned) == 2

    def test_clean_event_data_max_properties(self):
        """Limit to 50 properties."""
        tracker = UmamiEventTracker("https://test.com", "test-id")
        data = {f"key{i}": f"value{i}" for i in range(100)}
        cleaned = tracker._clean_event_data(data)
        assert len(cleaned) <= 50


class TestASGIWrapper:
    """Test ASGI middleware integration."""

    @pytest.mark.asyncio
    async def test_non_http_request(self, asgi_receive, asgi_send):
        """Skip non-HTTP requests."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {"type": "websocket"}

        wrapper = asgi_wrapper(None)
        wrapped_app = wrapper(mock_app)

        await wrapped_app(scope, asgi_receive, asgi_send)

        # Should pass through without tracking
        mock_app.assert_called_once_with(scope, asgi_receive, asgi_send)

    @pytest.mark.asyncio
    async def test_localhost_request(self, asgi_receive, asgi_send):
        """Skip localhost requests."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/meetings/agendas",
            "query_string": b"_search=test",
            "headers": [(b"host", b"localhost:8000")],
        }

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient") as mock_client:
                await wrapped_app(scope, asgi_receive, asgi_send)

                # Should not track localhost
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_admin_path_skipped(self, asgi_receive, asgi_send):
        """Skip admin paths."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/-/settings",
            "query_string": b"",
            "headers": [(b"host", b"alameda.ca.civic.org")],
        }

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient") as mock_client:
                await wrapped_app(scope, asgi_receive, asgi_send)
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_static_path_skipped(self, asgi_receive, asgi_send):
        """Skip static paths."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/static/app.css",
            "query_string": b"",
            "headers": [(b"host", b"alameda.ca.civic.org")],
        }

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient") as mock_client:
                await wrapped_app(scope, asgi_receive, asgi_send)
                mock_client.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_query_tracking(self, asgi_receive, asgi_send):
        """Track search query events."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/meetings/agendas",
            "query_string": b"_search=council&_sort=date",
            "headers": [
                (b"host", b"alameda.ca.civic.org"),
                (b"referer", b"https://google.com"),
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await wrapped_app(scope, asgi_receive, asgi_send)

            # Verify event was tracked
            mock_client.post.assert_called_once()
            payload = mock_client.post.call_args[1]["json"]

            assert payload["payload"]["name"] == "search_query"
            assert payload["payload"]["data"]["query_text"] == "council"
            assert payload["payload"]["data"]["subdomain"] == "alameda.ca"
            assert payload["payload"]["data"]["database"] == "meetings"
            assert payload["payload"]["data"]["table"] == "agendas"
            assert payload["payload"]["data"]["sort_column"] == "date"

    @pytest.mark.asyncio
    async def test_sql_query_tracking(self, asgi_receive, asgi_send):
        """Track SQL query events."""
        from plugins.civic_analytics import asgi_wrapper

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/meetings",
            "query_string": b"sql=SELECT+*+FROM+agendas+WHERE+date=%3Ap0&p0=2024-01-15&_size=100",
            "headers": [(b"host", b"alameda.ca.civic.org")],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient", return_value=mock_client):
                await wrapped_app(scope, asgi_receive, asgi_send)

            # Verify event was tracked
            mock_client.post.assert_called_once()
            payload = mock_client.post.call_args[1]["json"]

            assert payload["payload"]["name"] == "sql_query"
            assert "SELECT * FROM agendas" in payload["payload"]["data"]["query_text"]
            assert payload["payload"]["data"]["subdomain"] == "alameda.ca"
            assert payload["payload"]["data"]["database"] == "meetings"
            assert payload["payload"]["data"]["sql_operation"] == "select"
            assert payload["payload"]["data"]["page_size"] == "100"

            # Check SQL params extraction
            sql_params = json.loads(payload["payload"]["data"]["sql_params"])
            assert sql_params["p0"] == "2024-01-15"
            assert payload["payload"]["data"]["param_count"] == 1

    @pytest.mark.asyncio
    async def test_sql_operation_detection(self, asgi_receive, asgi_send):
        """Detect SQL operation types."""
        from plugins.civic_analytics import asgi_wrapper

        test_cases = [
            ("SELECT * FROM agendas", "select"),
            ("INSERT INTO agendas VALUES (1)", "write"),
            ("UPDATE agendas SET date=now()", "write"),
            ("DELETE FROM agendas", "write"),
            ("CREATE TABLE test (id INTEGER)", "ddl"),
            ("DROP TABLE test", "ddl"),
            ("ALTER TABLE test ADD COLUMN name TEXT", "ddl"),
        ]

        for sql, expected_op in test_cases:
            mock_app = AsyncMock()
            scope = {
                "type": "http",
                "path": "/meetings",
                "query_string": f"sql={sql}".encode("utf-8"),
                "headers": [(b"host", b"alameda.ca.civic.org")],
            }

            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
                wrapper = asgi_wrapper(None)
                wrapped_app = wrapper(mock_app)

                with patch("httpx.AsyncClient", return_value=mock_client):
                    await wrapped_app(scope, asgi_receive, asgi_send)

                if expected_op:
                    payload = mock_client.post.call_args[1]["json"]
                    assert payload["payload"]["data"]["sql_operation"] == expected_op


class TestSQLQueryDeduplication:
    """Test SQL query deduplication logic."""

    def test_query_cache_exists(self):
        """SQLQueryCache class should exist."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)
        assert cache is not None

    def test_query_cache_should_track_new_query(self):
        """New queries should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result is True

    def test_query_cache_should_not_track_duplicate(self):
        """Duplicate queries from same IP/subdomain should not be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        # First call - should track
        result1 = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result1 is True

        # Second call - same query, same IP, same subdomain - should not track
        result2 = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result2 is False

    def test_query_cache_different_ip_should_track(self):
        """Same query from different IP should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Different IP - should track
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.2", "alameda.ca")
        assert result is True

    def test_query_cache_different_subdomain_should_track(self):
        """Same query from different subdomain should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Different subdomain - should track
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "oakland.ca")
        assert result is True

    def test_query_cache_normalizes_whitespace(self):
        """Queries should be normalized for comparison."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Same query with different whitespace - should not track
        result = cache.should_track("SELECT  *  FROM  agendas", "192.168.1.1", "alameda.ca")
        assert result is False

    def test_query_cache_normalizes_case(self):
        """Queries should be case-insensitive for comparison."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Same query with different case - should not track
        result = cache.should_track("select * from agendas", "192.168.1.1", "alameda.ca")
        assert result is False

    def test_query_cache_max_size(self):
        """Cache should respect max size with LRU eviction."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=3, ttl_seconds=3600)

        # Add 3 entries
        cache.should_track("query1", "192.168.1.1", "alameda.ca")
        cache.should_track("query2", "192.168.1.1", "alameda.ca")
        cache.should_track("query3", "192.168.1.1", "alameda.ca")

        # Add 4th entry - should evict oldest
        cache.should_track("query4", "192.168.1.1", "alameda.ca")

        # query1 should have been evicted, so it should be tracked again
        result = cache.should_track("query1", "192.168.1.1", "alameda.ca")
        assert result is True

    def test_query_cache_ttl_expiry(self):
        """Entries should expire after TTL."""
        import time
        from plugins.civic_analytics import SQLQueryCache

        cache = SQLQueryCache(max_size=100, ttl_seconds=1)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should track again after expiry
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result is True
