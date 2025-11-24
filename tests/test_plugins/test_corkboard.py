"""
Tests for corkboard.py plugin.

Tests cover:
- Template variable injection for different templates
- Recent content data fetching
- Error handling for missing databases/tables
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from plugins.corkboard import extra_template_vars, get_recent_content


class TestExtraTemplateVars:
    """Test template variable injection."""

    def test_non_index_template(self):
        """Return basic vars for non-index templates."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {
            "site_name": "Alameda CA",
            "subdomain": "alameda.ca",
            "site_title": "Alameda Meetings",
            "site_description_html": "<p>Local government meetings</p>",
        }

        mock_request = MagicMock()

        result = extra_template_vars("table.html", mock_datasette, mock_request)

        # Should return dict immediately for non-index templates
        assert isinstance(result, dict)
        assert result["site_name"] == "Alameda CA"
        assert result["subdomain"] == "alameda.ca"
        assert result["site_title"] == "Alameda Meetings"
        assert result["site_description_html"] == "<p>Local government meetings</p>"

    def test_index_template(self):
        """Return async function for index.html."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {
            "site_name": "Alameda CA",
            "subdomain": "alameda.ca",
            "site_title": "Alameda Meetings",
            "site_description_html": "<p>Local government meetings</p>",
        }

        mock_request = MagicMock()

        result = extra_template_vars("index.html", mock_datasette, mock_request)

        # Should return async function for index.html
        assert callable(result)
        assert hasattr(result, "__call__")

    @pytest.mark.asyncio
    async def test_index_template_execution(self):
        """Execute async function for index.html."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {
            "site_name": "Alameda CA",
            "subdomain": "alameda.ca",
            "site_title": "Alameda Meetings",
            "site_description_html": "<p>Local government meetings</p>",
        }

        # Mock database
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.rows = [
            {"meeting": "City Council", "date": "2024-12-01", "pages": 10}
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_datasette.get_database.return_value = mock_db

        mock_request = MagicMock()

        result_func = extra_template_vars("index.html", mock_datasette, mock_request)
        result = await result_func()

        # Should include basic vars
        assert result["site_name"] == "Alameda CA"
        assert result["subdomain"] == "alameda.ca"

        # Should include recent content
        assert "upcoming_agendas" in result
        assert "recent_minutes" in result
        assert "recent_activity" in result


class TestGetRecentContent:
    """Test recent content data fetching."""

    @pytest.mark.asyncio
    async def test_successful_queries(self):
        """Fetch recent content successfully."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()

        # Mock database and query results
        mock_db = MagicMock()

        # Mock upcoming agendas result
        upcoming_result = MagicMock()
        upcoming_result.rows = [
            {"meeting": "City Council", "date": "2024-12-01", "pages": 10},
            {"meeting": "Planning Commission", "date": "2024-12-05", "pages": 5},
        ]

        # Mock recent minutes result
        minutes_result = MagicMock()
        minutes_result.rows = [
            {
                "meeting": "City Council",
                "date": "2024-11-15",
                "pages": 8,
                "preview": "Meeting called to order...",
            }
        ]

        # Mock recent activity result
        activity_result = MagicMock()
        activity_result.rows = [
            {
                "type": "agenda",
                "meeting": "City Council",
                "date": "2024-11-20",
                "pages": 10,
                "preview": "Budget discussion...",
            },
            {
                "type": "minutes",
                "meeting": "City Council",
                "date": "2024-11-15",
                "pages": 8,
                "preview": "Meeting called to order...",
            },
        ]

        # Setup mock to return different results for different queries
        call_count = [0]

        async def mock_execute(sql):
            call_count[0] += 1
            if "upcoming" in sql or call_count[0] == 1:
                return upcoming_result
            elif "recent_minutes" in sql or call_count[0] == 2:
                return minutes_result
            else:
                return activity_result

        mock_db.execute = mock_execute
        mock_datasette.get_database.return_value = mock_db

        result = await get_recent_content(mock_datasette, mock_request)

        # Verify results
        assert len(result["upcoming_agendas"]) == 2
        assert result["upcoming_agendas"][0]["meeting"] == "City Council"
        assert len(result["recent_minutes"]) == 1
        assert len(result["recent_activity"]) == 2

    @pytest.mark.asyncio
    async def test_database_not_found(self):
        """Handle missing database gracefully."""
        mock_datasette = MagicMock()
        mock_datasette.get_database.side_effect = Exception("Database not found")
        mock_request = MagicMock()

        result = await get_recent_content(mock_datasette, mock_request)

        # Should return empty data on error
        assert result["upcoming_agendas"] == []
        assert result["recent_minutes"] == []
        assert result["recent_activity"] == []

    @pytest.mark.asyncio
    async def test_query_execution_error(self):
        """Handle query execution errors gracefully."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Query failed"))
        mock_datasette.get_database.return_value = mock_db

        result = await get_recent_content(mock_datasette, mock_request)

        # Should return empty data on query errors
        assert result["upcoming_agendas"] == []
        assert result["recent_minutes"] == []
        assert result["recent_activity"] == []

    @pytest.mark.asyncio
    async def test_partial_query_success(self):
        """Handle partial query failures gracefully."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()

        # Mock database
        mock_db = MagicMock()

        # First query succeeds
        upcoming_result = MagicMock()
        upcoming_result.rows = [
            {"meeting": "City Council", "date": "2024-12-01", "pages": 10}
        ]

        call_count = [0]

        async def mock_execute(sql):
            call_count[0] += 1
            if call_count[0] == 1:
                return upcoming_result
            else:
                raise Exception("Query failed")

        mock_db.execute = mock_execute
        mock_datasette.get_database.return_value = mock_db

        result = await get_recent_content(mock_datasette, mock_request)

        # First query should succeed, others should be empty
        assert len(result["upcoming_agendas"]) == 1
        assert result["recent_minutes"] == []
        assert result["recent_activity"] == []

    @pytest.mark.asyncio
    async def test_empty_query_results(self):
        """Handle empty query results."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()

        mock_db = MagicMock()
        empty_result = MagicMock()
        empty_result.rows = []
        mock_db.execute = AsyncMock(return_value=empty_result)
        mock_datasette.get_database.return_value = mock_db

        result = await get_recent_content(mock_datasette, mock_request)

        # Should return empty lists when no data found
        assert result["upcoming_agendas"] == []
        assert result["recent_minutes"] == []
        assert result["recent_activity"] == []
