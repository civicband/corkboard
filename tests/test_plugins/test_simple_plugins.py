"""
Tests for simpler Datasette plugins.

Tests cover:
- search_highlight.py - Search term highlighting
- robots.py - robots.txt generation
- page_image.py - Image rendering
- date_link.py - Date link generation
- umami.py - Analytics script injection
"""

from unittest.mock import MagicMock

import markupsafe
import pytest

from plugins import date_link, page_image, robots, search_highlight, umami


class TestSearchHighlight:
    """Test search_highlight.py plugin."""

    def test_highlight_exact_match(self):
        """Highlight exact search term match."""
        mock_request = MagicMock()
        mock_request.args.get.return_value = "council"

        result = search_highlight.render_cell(
            row={},
            value="The city council met today",
            column="text",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "<mark>council</mark>" in str(result)

    def test_highlight_case_variations(self):
        """Highlight search term in different cases."""
        mock_request = MagicMock()
        mock_request.args.get.return_value = "Council"

        result = search_highlight.render_cell(
            row={},
            value="The city Council met. COUNCIL approved. council voted.",
            column="text",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "<mark>Council</mark>" in str(result)
        assert "<mark>council</mark>" in str(result)
        assert "<mark>COUNCIL</mark>" in str(result)

    def test_no_highlight_non_text_column(self):
        """Don't highlight non-text columns."""
        mock_request = MagicMock()
        mock_request.args.get.return_value = "council"

        result = search_highlight.render_cell(
            row={},
            value="Some value",
            column="date",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert result is None

    def test_no_highlight_without_search(self):
        """Don't highlight when no search query."""
        mock_request = MagicMock()
        mock_request.args.get.return_value = None

        result = search_highlight.render_cell(
            row={},
            value="The city council met today",
            column="text",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert result is None

    def test_highlight_parameter(self):
        """Use _highlight parameter if _search not present."""
        mock_request = MagicMock()
        mock_request.args.get.side_effect = lambda key: (
            None if key == "_search" else "meeting"
        )

        result = search_highlight.render_cell(
            row={},
            value="The meeting started",
            column="text",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "<mark>meeting</mark>" in str(result)


class TestRobots:
    """Test robots.py plugin."""

    def test_register_routes(self):
        """Register robots.txt route."""
        routes = robots.register_routes()

        assert len(routes) == 1
        assert routes[0][0] == r"^/robots\.txt$"
        assert routes[0][1] == robots.robots_txt

    @pytest.mark.asyncio
    async def test_robots_txt_generation(self):
        """Generate robots.txt with correct disallow rules."""
        mock_datasette = MagicMock()
        mock_datasette.databases = {"meetings": MagicMock(), "_internal": MagicMock()}
        mock_datasette.urls.database.side_effect = lambda db: f"/{db}"

        mock_request = MagicMock()

        response = await robots.robots_txt(mock_datasette, mock_request)

        # Response.body may be str or bytes depending on datasette version
        content = response.body
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        # Should include AI bot user agents
        assert "User-agent: GPTBot" in content
        assert "User-agent: ClaudeBot" in content
        assert "User-agent: Google-Extended" in content

        # Should disallow meetings database but not _internal
        assert "Disallow: /meetings" in content
        assert "Disallow: /_internal" not in content

    @pytest.mark.asyncio
    async def test_robots_txt_multiple_databases(self):
        """Generate robots.txt for multiple databases."""
        mock_datasette = MagicMock()
        mock_datasette.databases = {
            "meetings": MagicMock(),
            "archive": MagicMock(),
            "_internal": MagicMock(),
        }
        mock_datasette.urls.database.side_effect = lambda db: f"/{db}"

        mock_request = MagicMock()

        response = await robots.robots_txt(mock_datasette, mock_request)

        # Response.body may be str or bytes depending on datasette version
        content = response.body
        if isinstance(content, bytes):
            content = content.decode("utf-8")

        # Should disallow both user databases
        assert "Disallow: /meetings" in content
        assert "Disallow: /archive" in content
        assert "Disallow: /_internal" not in content


class TestPageImage:
    """Test page_image.py plugin."""

    def test_render_page_image(self):
        """Render page_image as img tag."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {"subdomain": "alameda.ca"}

        result = page_image.render_cell(
            row={"subdomain": "alameda.ca"},
            value="meetings/2024/page1.jpg",
            column="page_image",
            table="agendas",
            database="meetings",
            datasette=mock_datasette,
        )

        assert isinstance(result, markupsafe.Markup)
        assert (
            '<img src="https://cdn.civic.band/alameda.ca/meetings/2024/page1.jpg?width=800">'
            in str(result)
        )

    def test_render_with_leading_slash(self):
        """Handle value with leading slash."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {"subdomain": "alameda.ca"}

        result = page_image.render_cell(
            row={"subdomain": "alameda.ca"},
            value="/meetings/2024/page1.jpg",
            column="page_image",
            table="agendas",
            database="meetings",
            datasette=mock_datasette,
        )

        assert isinstance(result, markupsafe.Markup)
        # Should not have double slash
        assert "alameda.ca/meetings" in str(result)
        assert "alameda.ca//meetings" not in str(result)

    def test_fallback_to_config_subdomain(self):
        """Use plugin config subdomain when row doesn't have it."""
        mock_datasette = MagicMock()
        mock_datasette.plugin_config.return_value = {"subdomain": "default.subdomain"}

        # Row without subdomain key
        result = page_image.render_cell(
            row={},
            value="page1.jpg",
            column="page_image",
            table="agendas",
            database="meetings",
            datasette=mock_datasette,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "default.subdomain" in str(result)

    def test_no_render_non_page_image_column(self):
        """Don't render non-page_image columns."""
        mock_datasette = MagicMock()

        result = page_image.render_cell(
            row={},
            value="some value",
            column="text",
            table="agendas",
            database="meetings",
            datasette=mock_datasette,
        )

        assert result is None


class TestDateLink:
    """Test date_link.py plugin."""

    def test_render_date_link(self):
        """Render date as filtered link."""
        mock_request = MagicMock()
        mock_request.url = "https://example.com/meetings/agendas/row123"
        mock_request.args = {}

        result = date_link.render_cell(
            row={},
            value="2024-01-15",
            column="date",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "<a href=" in str(result)
        assert "date__exact=2024-01-15" in str(result)
        assert "_sort=meeting" in str(result)

    def test_include_highlight_with_search(self):
        """Include highlight parameter when search present."""
        mock_request = MagicMock()
        mock_request.url = "https://example.com/meetings/agendas"
        mock_request.args = {"_search": "council"}

        result = date_link.render_cell(
            row={},
            value="2024-01-15",
            column="date",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert "_highlight=council" in str(result)

    def test_normalize_path(self):
        """Normalize path to table level."""
        mock_request = MagicMock()
        mock_request.url = "https://example.com/meetings/agendas/row123/extra/parts"
        mock_request.args = {}

        result = date_link.render_cell(
            row={},
            value="2024-01-15",
            column="date",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        # Path should be normalized to /meetings/agendas
        assert "/meetings/agendas/" in str(result)
        assert "/row123" not in str(result)

    def test_replace_upcoming_with_agendas(self):
        """Replace 'upcoming' in path with 'agendas'."""
        mock_request = MagicMock()
        mock_request.url = "https://example.com/meetings/upcoming"
        mock_request.args = {}

        result = date_link.render_cell(
            row={},
            value="2024-01-15",
            column="date",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert "/meetings/agendas/" in str(result)
        assert "/upcoming" not in str(result)

    def test_no_render_non_date_column(self):
        """Don't render non-date columns."""
        mock_request = MagicMock()
        mock_request.url = "https://example.com/meetings/agendas"
        mock_request.args = {}

        result = date_link.render_cell(
            row={},
            value="some value",
            column="text",
            table="agendas",
            database="meetings",
            datasette=None,
            request=mock_request,
        )

        assert result is None


class TestUmami:
    """Test umami.py plugin."""

    def test_extra_body_script(self):
        """Inject Umami analytics script."""
        mock_datasette = MagicMock()

        result = umami.extra_body_script(mock_datasette)

        assert "script" in result
        assert "analytics.civic.band/sunshine" in result["script"]
        assert (
            'data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a"' in result["script"]
        )
        # Auto-track is disabled - we use manual tracking with subdomain
        assert 'data-auto-track="true"' not in result["script"]
        # Should include manual pageview tracking and subdomain logic
        assert "pageview" in result["script"]
        assert "subdomain" in result["script"]
