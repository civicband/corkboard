"""
Tests for search_all.py plugin.

Tests cover:
- Menu link generation for searchable tables
- Search all route registration
- Searchable table detection
- Permission checking
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from datasette import Forbidden

from plugins.search_all import (
    extra_template_vars,
    get_searchable_tables,
    has_searchable_tables,
    iterate_searchable_tables,
    menu_links,
    register_routes,
    search_all,
)


class TestMenuLinks:
    """Test menu link generation."""

    @pytest.mark.asyncio
    async def test_with_searchable_tables(self):
        """Show search link when searchable tables exist."""
        mock_datasette = MagicMock()
        mock_datasette.urls.path.return_value = "/-/search"

        mock_request = MagicMock()
        mock_request.actor = None

        # Mock database with searchable tables
        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas"])
        mock_db.fts_table = AsyncMock(return_value="agendas_fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        result_func = menu_links(mock_datasette, mock_request)
        result = await result_func()

        assert result is not None
        assert len(result) == 1
        assert result[0]["label"] == "Search all tables"
        assert result[0]["href"] == "/-/search"

    @pytest.mark.asyncio
    async def test_without_searchable_tables(self):
        """Don't show search link when no searchable tables."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        # Mock database with no FTS tables
        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas"])
        mock_db.fts_table = AsyncMock(return_value=None)  # No FTS

        mock_datasette.databases = {"meetings": mock_db}

        result_func = menu_links(mock_datasette, mock_request)
        result = await result_func()

        assert result is None

    @pytest.mark.asyncio
    async def test_no_request(self):
        """Return None when no request provided."""
        mock_datasette = MagicMock()

        result_func = menu_links(mock_datasette, None)
        result = await result_func()

        assert result is None


class TestRegisterRoutes:
    """Test route registration."""

    def test_registers_search_route(self):
        """Register /-/search route."""
        routes = register_routes()

        assert len(routes) == 1
        assert routes[0][0] == "/-/search"
        assert routes[0][1] == search_all


class TestSearchAll:
    """Test search_all view function."""

    @pytest.mark.asyncio
    async def test_render_search_page(self):
        """Render search page with searchable tables."""
        mock_datasette = MagicMock()
        mock_datasette.urls.table.side_effect = lambda db, table, format=None: (
            f"/{db}/{table}" if not format else f"/{db}/{table}.{format}"
        )
        mock_datasette.render_template = AsyncMock(return_value="<html>Search Page</html>")

        mock_request = MagicMock()
        mock_request.args.get.return_value = "test query"
        mock_request.actor = None

        # Mock database with searchable tables
        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas", "minutes"])
        mock_db.fts_table = AsyncMock(return_value="fts_table")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        response = await search_all(mock_datasette, mock_request)

        # Verify template was rendered
        mock_datasette.render_template.assert_called_once()
        call_args = mock_datasette.render_template.call_args[0]

        assert call_args[0] == "search_all.html"
        context = call_args[1]

        assert context["q"] == "test query"
        assert "searchable_tables" in context
        assert len(context["searchable_tables"]) == 2
        assert context["searchable_tables"][0]["database"] == "meetings"
        assert context["searchable_tables"][0]["table"] == "agendas"

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Handle empty search query."""
        mock_datasette = MagicMock()
        mock_datasette.urls.table.side_effect = lambda db, table, format=None: f"/{db}/{table}"
        mock_datasette.render_template = AsyncMock(return_value="<html>Search Page</html>")

        mock_request = MagicMock()
        mock_request.args.get.return_value = None
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=[])

        mock_datasette.databases = {"meetings": mock_db}

        response = await search_all(mock_datasette, mock_request)

        call_args = mock_datasette.render_template.call_args[0]
        context = call_args[1]

        assert context["q"] == ""


class TestExtraTemplateVars:
    """Test extra template vars hook."""

    @pytest.mark.asyncio
    async def test_index_template(self):
        """Add searchable tables to index.html."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        # Mock database
        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas"])
        mock_db.fts_table = AsyncMock(return_value="agendas_fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        result_func = extra_template_vars("index.html", mock_datasette, mock_request)
        result = await result_func()

        assert "searchable_tables" in result
        assert len(result["searchable_tables"]) == 1
        assert result["searchable_tables"][0] == ("meetings", "agendas")

    def test_non_index_template(self):
        """Return None for non-index templates."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()

        result = extra_template_vars("table.html", mock_datasette, mock_request)

        assert result is None


class TestIterateSearchableTables:
    """Test searchable table iteration."""

    @pytest.mark.asyncio
    async def test_with_fts_tables(self):
        """Yield tables with FTS enabled."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        # Mock database with FTS tables
        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas", "minutes"])
        mock_db.fts_table = AsyncMock(side_effect=lambda table: f"{table}_fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        tables = []
        async for db, table in iterate_searchable_tables(mock_datasette, mock_request):
            tables.append((db, table))

        assert len(tables) == 2
        assert ("meetings", "agendas") in tables
        assert ("meetings", "minutes") in tables

    @pytest.mark.asyncio
    async def test_skip_hidden_tables(self):
        """Skip hidden tables."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=["hidden_table"])
        mock_db.table_names = AsyncMock(return_value=["agendas", "hidden_table"])
        mock_db.fts_table = AsyncMock(return_value="fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        tables = []
        async for db, table in iterate_searchable_tables(mock_datasette, mock_request):
            tables.append((db, table))

        assert len(tables) == 1
        assert ("meetings", "agendas") in tables
        assert ("meetings", "hidden_table") not in tables

    @pytest.mark.asyncio
    async def test_skip_non_fts_tables(self):
        """Skip tables without FTS."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas", "no_fts_table"])

        # Only agendas has FTS
        async def mock_fts_table(table):
            return "agendas_fts" if table == "agendas" else None

        mock_db.fts_table = mock_fts_table

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        tables = []
        async for db, table in iterate_searchable_tables(mock_datasette, mock_request):
            tables.append((db, table))

        assert len(tables) == 1
        assert ("meetings", "agendas") in tables

    @pytest.mark.asyncio
    async def test_skip_forbidden_tables(self):
        """Skip tables user doesn't have permission to view."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = {"id": "user1"}

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["public_table", "private_table"])
        mock_db.fts_table = AsyncMock(return_value="fts")

        # Forbidden for private_table
        async def mock_ensure_permissions(actor, permissions):
            for perm in permissions:
                if isinstance(perm, tuple) and perm[0] == "view-table":
                    if perm[1][1] == "private_table":
                        raise Forbidden("Access denied")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = mock_ensure_permissions

        tables = []
        async for db, table in iterate_searchable_tables(mock_datasette, mock_request):
            tables.append((db, table))

        assert len(tables) == 1
        assert ("meetings", "public_table") in tables
        assert ("meetings", "private_table") not in tables


class TestHasSearchableTables:
    """Test searchable table detection."""

    @pytest.mark.asyncio
    async def test_with_tables(self):
        """Return True when searchable tables exist."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas"])
        mock_db.fts_table = AsyncMock(return_value="agendas_fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        result = await has_searchable_tables(mock_datasette, mock_request)

        assert result is True

    @pytest.mark.asyncio
    async def test_without_tables(self):
        """Return False when no searchable tables."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas"])
        mock_db.fts_table = AsyncMock(return_value=None)  # No FTS

        mock_datasette.databases = {"meetings": mock_db}

        result = await has_searchable_tables(mock_datasette, mock_request)

        assert result is False


class TestGetSearchableTables:
    """Test getting list of searchable tables."""

    @pytest.mark.asyncio
    async def test_get_all_tables(self):
        """Get all searchable tables as list."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=["agendas", "minutes"])
        mock_db.fts_table = AsyncMock(return_value="fts")

        mock_datasette.databases = {"meetings": mock_db}
        mock_datasette.ensure_permissions = AsyncMock()

        result = await get_searchable_tables(mock_datasette, mock_request)

        assert len(result) == 2
        assert ("meetings", "agendas") in result
        assert ("meetings", "minutes") in result

    @pytest.mark.asyncio
    async def test_empty_list(self):
        """Return empty list when no searchable tables."""
        mock_datasette = MagicMock()
        mock_request = MagicMock()
        mock_request.actor = None

        mock_db = MagicMock()
        mock_db.name = "meetings"
        mock_db.hidden_table_names = AsyncMock(return_value=[])
        mock_db.table_names = AsyncMock(return_value=[])

        mock_datasette.databases = {"meetings": mock_db}

        result = await get_searchable_tables(mock_datasette, mock_request)

        assert result == []
