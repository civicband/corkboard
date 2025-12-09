"""
Tests for retrieve_umami_analytics.py script.

Tests cover:
- UmamiClient authentication and API interactions
- AnalyticsDatabase SQLite operations
- Data retrieval and storage
"""

import sqlite3

# We need to handle the import carefully since it's a script
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Mock the script execution to avoid running main
with patch("sys.argv", ["retrieve_umami_analytics.py"]):
    from retrieve_umami_analytics import (
        AnalyticsDatabase,
        UmamiClient,
        generate_summary_report,
        get_stat_value,
    )


class TestUmamiClient:
    """Test UmamiClient class."""

    def test_init(self):
        """Initialize client with credentials."""
        client = UmamiClient(
            url="https://analytics.civic.band",
            username="test_user",
            password="test_pass",
            website_id="test-website-id",
        )

        assert client.url == "https://analytics.civic.band"
        assert client.username == "test_user"
        assert client.password == "test_pass"
        assert client.website_id == "test-website-id"
        assert client.token is None

    def test_init_strips_trailing_slash(self):
        """Strip trailing slash from URL."""
        client = UmamiClient(
            url="https://analytics.civic.band/",
            username="user",
            password="pass",
            website_id="id",
        )

        assert client.url == "https://analytics.civic.band"

    @patch("requests.post")
    def test_authenticate_success(self, mock_post):
        """Successfully authenticate and get token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"token": "test-token-123"}
        mock_post.return_value = mock_response

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="id",
        )

        result = client.authenticate()

        assert result is True
        assert client.token == "test-token-123"

        # Verify API call
        mock_post.assert_called_once_with(
            "https://analytics.civic.band/api/auth/login",
            headers={"Content-Type": "application/json"},
            json={"username": "user", "password": "pass"},
            timeout=10,
        )

    @patch("requests.post")
    def test_authenticate_failure_no_token(self, mock_post):
        """Handle authentication response without token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # No token
        mock_post.return_value = mock_response

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="id",
        )

        result = client.authenticate()

        assert result is False
        assert client.token is None

    @patch("requests.post")
    def test_authenticate_network_error(self, mock_post):
        """Handle network errors during authentication."""
        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="id",
        )

        result = client.authenticate()

        assert result is False
        assert client.token is None

    @patch("requests.post")
    def test_authenticate_http_error(self, mock_post):
        """Handle HTTP errors during authentication."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "401 Unauthorized"
        )
        mock_post.return_value = mock_response

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="id",
        )

        result = client.authenticate()

        assert result is False

    def test_get_headers(self):
        """Get authorization headers."""
        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="id",
        )
        client.token = "test-token-123"

        headers = client._get_headers()

        assert headers == {
            "Authorization": "Bearer test-token-123",
            "Accept": "application/json",
        }

    @patch("requests.get")
    def test_get_website_stats_success(self, mock_get):
        """Get website statistics successfully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pageviews": {"value": 1000},
            "visitors": {"value": 250},
        }
        mock_get.return_value = mock_response

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="test-id",
        )
        client.token = "test-token"

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        stats = client.get_website_stats(start_date, end_date)

        assert stats is not None
        assert stats["pageviews"]["value"] == 1000
        assert stats["visitors"]["value"] == 250

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args

        assert "test-id" in call_args[0][0]
        assert call_args[1]["params"]["startAt"] == int(start_date.timestamp() * 1000)
        assert call_args[1]["params"]["endAt"] == int(end_date.timestamp() * 1000)

    @patch("requests.get")
    def test_get_website_stats_error(self, mock_get):
        """Handle errors when getting website stats."""
        mock_get.side_effect = requests.exceptions.RequestException("API error")

        client = UmamiClient(
            url="https://analytics.civic.band",
            username="user",
            password="pass",
            website_id="test-id",
        )
        client.token = "test-token"

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        stats = client.get_website_stats(start_date, end_date)

        assert stats is None


class TestAnalyticsDatabase:
    """Test AnalyticsDatabase class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        yield db_path

        # Cleanup
        if db_path.exists():
            db_path.unlink()

    def test_init_creates_database(self, temp_db_path):
        """Initialize database and create schema."""
        AnalyticsDatabase(str(temp_db_path))

        assert temp_db_path.exists()

        # Verify schema
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check events table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        )
        assert cursor.fetchone() is not None

        # Check website_stats table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='website_stats'"
        )
        assert cursor.fetchone() is not None

        conn.close()

    def test_insert_events(self, temp_db_path):
        """Insert events to database."""
        db = AnalyticsDatabase(str(temp_db_path))

        # Events use the structure expected by insert_events
        events = [
            {
                "name": "search_query",
                "url": "/meetings/agendas",
                "hostname": "alameda.ca.civic.band",
                "data": {"query_text": "council", "subdomain": "alameda.ca"},
                "timestamp": "2024-01-15T10:00:00Z",
            },
            {
                "name": "sql_query",
                "url": "/meetings",
                "hostname": "vancouver.bc.civic.band",
                "data": {
                    "query_text": "SELECT * FROM agendas",
                    "subdomain": "vancouver.bc",
                },
                "timestamp": "2024-01-15T11:00:00Z",
            },
        ]

        db.insert_events(events)

        # Verify events were saved
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]

        assert count == 2

        # Verify event data
        cursor.execute(
            "SELECT event_name, event_url, event_data FROM events ORDER BY event_name"
        )
        rows = cursor.fetchall()

        assert rows[0][0] == "search_query"
        assert rows[0][1] == "/meetings/agendas"
        assert "council" in rows[0][2]

        assert rows[1][0] == "sql_query"
        assert "SELECT * FROM agendas" in rows[1][2]

        conn.close()

    def test_insert_website_stats(self, temp_db_path):
        """Insert website statistics to database (new flat format)."""
        db = AnalyticsDatabase(str(temp_db_path))

        # New Umami API format returns flat integers
        stats = {
            "pageviews": 1000,
            "visitors": 250,
            "visits": 500,
            "bounces": 100,
            "totaltime": 50000,
        }

        # insert_website_stats expects datetime objects
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        db.insert_website_stats(start_date, end_date, stats)

        # Verify stats were saved
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM website_stats")
        count = cursor.fetchone()[0]

        assert count == 1

        # Verify stats data - note: visitors column is 'unique_visitors' in schema
        cursor.execute(
            "SELECT pageviews, unique_visitors, visits, bounces FROM website_stats"
        )
        row = cursor.fetchone()

        assert row[0] == 1000  # pageviews
        assert row[1] == 250  # unique_visitors (from 'visitors' in stats)
        assert row[2] == 500  # visits
        assert row[3] == 100  # bounces

        conn.close()

    def test_insert_website_stats_legacy_format(self, temp_db_path):
        """Insert website statistics with legacy nested format."""
        db = AnalyticsDatabase(str(temp_db_path))

        # Legacy Umami API format with nested {"value": X} objects
        stats = {
            "pageviews": {"value": 2000},
            "visitors": {"value": 500},
            "visits": {"value": 800},
            "bounces": {"value": 200},
            "totaltime": {"value": 100000},
        }

        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 2, 28)

        db.insert_website_stats(start_date, end_date, stats)

        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT pageviews, unique_visitors, visits, bounces FROM website_stats"
        )
        row = cursor.fetchone()

        assert row[0] == 2000  # pageviews
        assert row[1] == 500  # unique_visitors
        assert row[2] == 800  # visits
        assert row[3] == 200  # bounces

        conn.close()

    def test_insert_multiple_events(self, temp_db_path):
        """Insert multiple events and verify counts."""
        db = AnalyticsDatabase(str(temp_db_path))

        # Insert test events using correct structure
        events = [
            {
                "name": "search_query",
                "url": "/meetings/agendas",
                "hostname": "alameda.ca.civic.band",
                "data": {"subdomain": "alameda.ca"},
                "timestamp": "2024-01-15T10:00:00Z",
            },
            {
                "name": "search_query",
                "url": "/meetings/minutes",
                "hostname": "alameda.ca.civic.band",
                "data": {"subdomain": "alameda.ca"},
                "timestamp": "2024-01-15T11:00:00Z",
            },
            {
                "name": "sql_query",
                "url": "/meetings",
                "hostname": "vancouver.bc.civic.band",
                "data": {"subdomain": "vancouver.bc"},
                "timestamp": "2024-01-15T12:00:00Z",
            },
        ]

        db.insert_events(events)

        # Verify event counts by querying directly
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM events")
        total = cursor.fetchone()[0]
        assert total == 3

        cursor.execute(
            "SELECT event_name, COUNT(*) FROM events GROUP BY event_name ORDER BY event_name"
        )
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "search_query"
        assert rows[0][1] == 2
        assert rows[1][0] == "sql_query"
        assert rows[1][1] == 1

        conn.close()

    def test_empty_database(self, temp_db_path):
        """Handle empty database gracefully."""
        # Initialize database to create schema
        AnalyticsDatabase(str(temp_db_path))

        # Verify tables exist but are empty
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM events")
        assert cursor.fetchone()[0] == 0

        cursor.execute("SELECT COUNT(*) FROM website_stats")
        assert cursor.fetchone()[0] == 0

        conn.close()

    def test_context_manager(self, temp_db_path):
        """Database supports context manager protocol."""
        with AnalyticsDatabase(str(temp_db_path)) as db:
            stats = {"pageviews": 100, "visitors": 50}
            db.insert_website_stats(datetime(2024, 1, 1), datetime(2024, 1, 31), stats)

        # Connection should be closed after context
        assert db.conn is None or not db.conn

        # Data should still be persisted
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM website_stats")
        assert cursor.fetchone()[0] == 1
        conn.close()

    def test_context_manager_closes_on_exception(self, temp_db_path):
        """Context manager closes connection even on exception."""
        try:
            with AnalyticsDatabase(str(temp_db_path)) as db:
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Connection should be closed
        assert db.conn is None or not db.conn

    def test_consistent_retrieved_at_timestamp(self, temp_db_path):
        """All inserts in a session use the same timestamp."""
        db = AnalyticsDatabase(str(temp_db_path))

        events = [
            {"name": "event1", "url": "/", "hostname": "test.com", "data": {}},
            {"name": "event2", "url": "/", "hostname": "test.com", "data": {}},
        ]
        db.insert_events(events)

        stats = {"pageviews": 100}
        db.insert_website_stats(datetime(2024, 1, 1), datetime(2024, 1, 31), stats)

        # All records should have the same retrieved_at
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT retrieved_at FROM events")
        event_timestamps = cursor.fetchall()
        assert len(event_timestamps) == 1

        cursor.execute("SELECT retrieved_at FROM website_stats")
        stats_timestamp = cursor.fetchone()[0]

        # All timestamps should match
        assert event_timestamps[0][0] == stats_timestamp

        conn.close()
        db.close()

    def test_duplicate_stats_replaced(self, temp_db_path):
        """Duplicate stats for same date range are replaced, not duplicated."""
        db = AnalyticsDatabase(str(temp_db_path))

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # Insert first stats
        stats1 = {"pageviews": 100, "visitors": 50}
        db.insert_website_stats(start_date, end_date, stats1)

        # Insert updated stats for same date range
        stats2 = {"pageviews": 200, "visitors": 100}
        db.insert_website_stats(start_date, end_date, stats2)

        # Should only have one record with updated values
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM website_stats")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT pageviews, unique_visitors FROM website_stats")
        row = cursor.fetchone()
        assert row[0] == 200  # Updated value
        assert row[1] == 100  # Updated value

        conn.close()
        db.close()

    def test_duplicate_url_metrics_replaced(self, temp_db_path):
        """Duplicate URL metrics for same date range are replaced."""
        db = AnalyticsDatabase(str(temp_db_path))

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # Insert first metrics
        metrics1 = [{"x": "/page1", "y": 100}]
        db.insert_metrics(start_date, end_date, metrics1, "url")

        # Insert updated metrics for same date range and URL
        metrics2 = [{"x": "/page1", "y": 200}]
        db.insert_metrics(start_date, end_date, metrics2, "url")

        # Should only have one record with updated value
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM url_metrics")
        assert cursor.fetchone()[0] == 1

        cursor.execute("SELECT visits FROM url_metrics")
        assert cursor.fetchone()[0] == 200

        conn.close()
        db.close()

    def test_insert_metrics_invalid_type_raises(self, temp_db_path):
        """Invalid metric type raises ValueError."""
        db = AnalyticsDatabase(str(temp_db_path))

        metrics = [{"x": "/page1", "y": 100}]

        with pytest.raises(ValueError) as exc_info:
            db.insert_metrics(
                datetime(2024, 1, 1), datetime(2024, 1, 31), metrics, "invalid"
            )

        assert "Invalid metric_type" in str(exc_info.value)
        db.close()


class TestGetStatValue:
    """Test get_stat_value helper function."""

    def test_new_format_integer(self):
        """Handle new API format with direct integers."""
        stats = {"pageviews": 1000, "visitors": 250}
        assert get_stat_value(stats, "pageviews") == 1000
        assert get_stat_value(stats, "visitors") == 250

    def test_legacy_format_nested(self):
        """Handle legacy API format with nested value objects."""
        stats = {"pageviews": {"value": 2000}, "visitors": {"value": 500}}
        assert get_stat_value(stats, "pageviews") == 2000
        assert get_stat_value(stats, "visitors") == 500

    def test_missing_key_returns_zero(self):
        """Missing key returns 0."""
        stats = {"pageviews": 1000}
        assert get_stat_value(stats, "visitors") == 0

    def test_invalid_type_returns_zero(self):
        """Non-integer, non-dict value returns 0."""
        stats = {"pageviews": "invalid"}
        assert get_stat_value(stats, "pageviews") == 0

    def test_empty_stats(self):
        """Empty stats dict returns 0 for any key."""
        stats = {}
        assert get_stat_value(stats, "pageviews") == 0


class TestGenerateSummaryReport:
    """Test generate_summary_report function."""

    def test_new_api_format(self):
        """Generate report with new API format stats."""
        stats = {
            "pageviews": 1000,
            "visitors": 250,
            "visits": 500,
            "bounces": 100,
            "totaltime": 50000,
        }
        events = []
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        report = generate_summary_report(stats, events, start_date, end_date)

        assert report["overview"]["pageviews"] == 1000
        assert report["overview"]["unique_visitors"] == 250
        assert report["overview"]["visits"] == 500
        assert report["overview"]["bounce_rate"] == 100
        assert report["overview"]["total_time_seconds"] == 50000

    def test_legacy_api_format(self):
        """Generate report with legacy API format stats."""
        stats = {
            "pageviews": {"value": 2000},
            "visitors": {"value": 500},
            "visits": {"value": 800},
            "bounces": {"value": 200},
            "totaltime": {"value": 100000},
        }
        events = []
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        report = generate_summary_report(stats, events, start_date, end_date)

        assert report["overview"]["pageviews"] == 2000
        assert report["overview"]["unique_visitors"] == 500

    def test_event_counting(self):
        """Report correctly counts events by type."""
        stats = {"pageviews": 100}
        events = [
            {"name": "search_query", "data": {"subdomain": "alameda.ca"}},
            {"name": "search_query", "data": {"subdomain": "alameda.ca"}},
            {"name": "sql_query", "data": {"subdomain": "vancouver.bc"}},
        ]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        report = generate_summary_report(stats, events, start_date, end_date)

        assert report["events"]["total_events"] == 3
        assert report["events"]["event_breakdown"]["search_query"] == 2
        assert report["events"]["event_breakdown"]["sql_query"] == 1

    def test_municipality_counting(self):
        """Report correctly counts events by municipality."""
        stats = {"pageviews": 100}
        events = [
            {"name": "search", "data": {"subdomain": "alameda.ca"}},
            {"name": "search", "data": {"subdomain": "alameda.ca"}},
            {"name": "search", "data": {"subdomain": "vancouver.bc"}},
        ]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        report = generate_summary_report(stats, events, start_date, end_date)

        assert report["municipalities"]["total_municipalities"] == 2
        assert report["municipalities"]["municipality_breakdown"]["alameda.ca"] == 2
        assert report["municipalities"]["municipality_breakdown"]["vancouver.bc"] == 1

    def test_empty_stats(self):
        """Handle empty stats gracefully."""
        stats = {}
        events = []
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        report = generate_summary_report(stats, events, start_date, end_date)

        assert report["overview"]["pageviews"] == 0
        assert report["overview"]["unique_visitors"] == 0
        assert report["events"]["total_events"] == 0
