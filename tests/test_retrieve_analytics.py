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
    from retrieve_umami_analytics import AnalyticsDatabase, UmamiClient


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

    def test_save_events(self, temp_db_path):
        """Save events to database."""
        db = AnalyticsDatabase(str(temp_db_path))

        events = [
            {
                "event_name": "search_query",
                "url": "/meetings/agendas",
                "hostname": "alameda.ca.civic.band",
                "data": {"query_text": "council", "subdomain": "alameda.ca"},
                "created_at": "2024-01-15T10:00:00Z",
            },
            {
                "event_name": "sql_query",
                "url": "/meetings",
                "hostname": "vancouver.bc.civic.band",
                "data": {
                    "query_text": "SELECT * FROM agendas",
                    "subdomain": "vancouver.bc",
                },
                "created_at": "2024-01-15T11:00:00Z",
            },
        ]

        db.save_events(events)

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

    def test_save_website_stats(self, temp_db_path):
        """Save website statistics to database."""
        db = AnalyticsDatabase(str(temp_db_path))

        stats = {
            "pageviews": {"value": 1000},
            "visitors": {"value": 250},
            "visits": {"value": 500},
            "bounces": {"value": 100},
        }

        db.save_website_stats(stats, "2024-01-01", "2024-01-31")

        # Verify stats were saved
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM website_stats")
        count = cursor.fetchone()[0]

        assert count == 1

        # Verify stats data
        cursor.execute("SELECT pageviews, visitors, visits, bounces FROM website_stats")
        row = cursor.fetchone()

        assert row[0] == 1000  # pageviews
        assert row[1] == 250  # visitors
        assert row[2] == 500  # visits
        assert row[3] == 100  # bounces

        conn.close()

    def test_get_event_summary(self, temp_db_path):
        """Get summary of events."""
        db = AnalyticsDatabase(str(temp_db_path))

        # Insert test events
        events = [
            {
                "event_name": "search_query",
                "url": "/meetings/agendas",
                "hostname": "alameda.ca.civic.band",
                "data": {"subdomain": "alameda.ca"},
                "created_at": "2024-01-15T10:00:00Z",
            },
            {
                "event_name": "search_query",
                "url": "/meetings/minutes",
                "hostname": "alameda.ca.civic.band",
                "data": {"subdomain": "alameda.ca"},
                "created_at": "2024-01-15T11:00:00Z",
            },
            {
                "event_name": "sql_query",
                "url": "/meetings",
                "hostname": "vancouver.bc.civic.band",
                "data": {"subdomain": "vancouver.bc"},
                "created_at": "2024-01-15T12:00:00Z",
            },
        ]

        db.save_events(events)

        summary = db.get_event_summary()

        assert summary is not None
        assert summary["total_events"] == 3
        assert "event_types" in summary
        assert "search_query" in str(summary["event_types"])

    def test_empty_database(self, temp_db_path):
        """Handle empty database gracefully."""
        db = AnalyticsDatabase(str(temp_db_path))

        summary = db.get_event_summary()

        assert summary["total_events"] == 0
