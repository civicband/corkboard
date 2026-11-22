"""
Tests for simpler Datasette plugins.

Tests cover:
- search_highlight.py - Search term highlighting
- robots.py - robots.txt generation
- page_image.py - Image rendering
- date_link.py - Date link generation
- umami.py - Analytics script injection
"""

from unittest.mock import MagicMock, patch

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

        # Should include AI bot user agents in the grouped User-agent line
        user_agent_line = next(
            line for line in content.splitlines() if line.startswith("User-agent:")
        )
        user_agents = {
            agent.strip()
            for agent in user_agent_line.removeprefix("User-agent:").split(",")
        }
        assert {"GPTBot", "ClaudeBot", "Google-Extended"} <= user_agents

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

    @patch.dict("os.environ", {"CDN_URL": "https://cdn.civic.band"})
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

    @patch.dict("os.environ", {"CDN_URL": "https://cdn.civic.band"})
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

    @patch.dict("os.environ", {"CDN_URL": "https://cdn.civic.band"})
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


def _date_link_request(url, search=None):
    request = MagicMock()
    request.url = url
    request.args = {"_search": search} if search else {}
    return request


def _date_link_datasette():
    datasette = MagicMock()
    datasette.urls.table = lambda database, table: f"/{database}/{table}"
    return datasette


def _render_date(
    url,
    value="2024-01-15",
    column="date",
    table="agendas",
    row=None,
    search=None,
    datasette=None,
):
    return date_link.render_cell(
        row={} if row is None else row,
        value=value,
        column=column,
        table=table,
        database="meetings",
        datasette=_date_link_datasette() if datasette is None else datasette,
        request=_date_link_request(url, search=search),
    )


class TestDateLink:
    """Test date_link.py plugin."""

    def test_render_date_link(self):
        """Render date as filtered link for the queried table."""
        result = _render_date(
            "https://example.com/meetings/agendas/City%20Council/2024-01-15"
        )

        assert isinstance(result, markupsafe.Markup)
        assert 'href="/meetings/agendas?date__exact=2024-01-15' in str(result)
        assert "_sort=page" in str(result)

    def test_uses_table_argument_over_path(self):
        """The table Datasette queried wins, even on a row page path."""
        result = _render_date(
            "https://example.com/meetings/agendas/City%20Council/2024-01-15",
            table="minutes",
        )

        assert "/meetings/minutes?" in str(result)
        assert "/meetings/agendas?" not in str(result)

    def test_path_segment_fallback_without_table(self):
        """Fall back to a minutes path segment when table is unavailable."""
        result = _render_date("https://example.com/meetings/minutes", table=None)

        assert "/meetings/minutes?" in str(result)

    def test_no_link_for_upcoming(self):
        """Saved query pages are ambiguous, so no link is emitted."""
        result = _render_date("https://example.com/meetings/upcoming", table=None)

        assert result is None

    def test_no_link_for_database_sql_page(self):
        """Database-level SQL pages are ambiguous, so no link is emitted."""
        result = _render_date(
            "https://example.com/meetings?sql=select+*+from+agendas", table=None
        )

        assert result is None

    def test_no_link_for_unrelated_table(self):
        """Non meeting tables get no link, even with a date column."""
        result = _render_date(
            "https://example.com/finance/contributions", table="contributions"
        )

        assert result is None

    def test_table_segment_below_database(self):
        """Only segments after the database name select the table."""
        result = _render_date("https://example.com/otherdb/minutes/table", table=None)

        assert "/meetings/minutes?" in str(result)

    def test_no_link_for_non_exact_dates(self):
        """Years and free text cannot be filtered exactly, so no link."""
        for value in ("2024", "Jan 15, 2024", "2024-01", ""):
            assert (
                _render_date("https://example.com/meetings/agendas", value=value)
                is None
            )

    def test_no_link_for_none_value(self):
        """Null dates render as plain cells."""
        assert _render_date("https://example.com/meetings/agendas", value=None) is None

    def test_no_link_for_non_date_columns(self):
        """Only date columns are linked."""
        assert (
            _render_date("https://example.com/meetings/agendas", column="text") is None
        )
        assert (
            _render_date("https://example.com/meetings/agendas", column="report_date")
            is None
        )

    def test_isodate_column(self):
        """Minute slugs use isodate; the filter key follows the column."""
        result = _render_date(
            "https://example.com/meetings/minutes", column="isodate", table="minutes"
        )

        assert "isodate__exact=2024-01-15" in str(result)

    def test_include_highlight_with_search(self):
        """Include highlight parameter when search present."""
        result = _render_date("https://example.com/meetings/agendas", search="council")

        assert "_highlight=council" in str(result)
        assert "_search" not in str(result)

    def test_meeting_filter_is_encoded(self):
        """Meeting names are URL encoded, not pasted raw."""
        result = _render_date(
            "https://example.com/meetings/agendas",
            row={"meeting": "City Council & Board"},
        )

        assert "meeting__exact=City+Council+%26+Board" in str(result)
        assert "&Board" not in str(result)

    def test_no_meeting_filter_without_meeting(self):
        """Rows without a meeting column still link by date."""
        result = _render_date("https://example.com/meetings/agendas", row={})

        assert "meeting__exact" not in str(result)
        assert "date__exact=2024-01-15" in str(result)

    def test_value_is_escaped(self):
        """Anchor text is HTML escaped."""
        result = _render_date(
            "https://example.com/meetings/agendas", value="2024-01-15<script>"
        )

        text = str(result)
        assert "<script>" not in text
        assert "2024-01-15&lt;script&gt;" in text

    def test_fallback_without_url_builder(self):
        """A datasette without urls still yields a table-level path."""
        result = _render_date(
            "https://example.com/meetings/agendas", datasette=MagicMock(urls=None)
        )

        assert "/meetings/agendas?" in str(result)


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
