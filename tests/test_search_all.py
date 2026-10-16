"""Tests for the server-rendered search-all Datasette plugin.

These build a real Datasette instance (with FTS indexes and the repo's
plugins loaded) and exercise the ``/-/search`` endpoint:

- GET renders the empty search form only (searching is POST-only).
- POST renders server-side results, using the page card partial for
  minutes/agendas and a generic table for everything else.
- The endpoint reports a server-side analytics event for the query.
"""

import contextlib
import sqlite3
import tempfile
from pathlib import Path

import pytest
from datasette.app import Datasette
from datasette.plugins import pm

MINUTES_MATCHING = 12


def _create_meetings_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE minutes (
            id TEXT PRIMARY KEY,
            meeting TEXT,
            date TEXT,
            page INTEGER,
            text TEXT,
            page_image TEXT,
            entities_json TEXT,
            votes_json TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE agendas (
            id TEXT PRIMARY KEY,
            meeting TEXT,
            date TEXT,
            page INTEGER,
            text TEXT,
            page_image TEXT,
            entities_json TEXT,
            votes_json TEXT
        )
    """)

    for i in range(MINUTES_MATCHING):
        cur.execute(
            "INSERT INTO minutes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"min-{i:03d}",
                "City Council",
                "2024-01-15",
                i + 1,
                f"Discussion of the budget item number {i}",
                "https://example.com/image.jpg",
                None,
                None,
            ),
        )

    for i in range(2):
        cur.execute(
            "INSERT INTO agendas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                f"agenda-{i:03d}",
                "Planning Commission",
                "2024-01-16",
                i + 1,
                f"Budget hearing agenda item {i}",
                "https://example.com/image.jpg",
                None,
                None,
            ),
        )

    cur.execute(
        'CREATE VIRTUAL TABLE minutes_fts USING fts5(text, content="minutes", '
        'content_rowid="rowid")'
    )
    cur.execute("INSERT INTO minutes_fts(minutes_fts) VALUES('rebuild')")
    cur.execute(
        'CREATE VIRTUAL TABLE agendas_fts USING fts5(text, content="agendas", '
        'content_rowid="rowid")'
    )
    cur.execute("INSERT INTO agendas_fts(agendas_fts) VALUES('rebuild')")

    conn.commit()
    conn.close()


def _create_finance_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE contributions (
            id TEXT PRIMARY KEY,
            donor TEXT,
            amount REAL
        )
    """)
    cur.execute("INSERT INTO contributions VALUES ('c-001', 'Budget Corp', 500.0)")
    cur.execute(
        "CREATE VIRTUAL TABLE contributions_fts USING fts5(donor, "
        'content="contributions", content_rowid="rowid")'
    )
    cur.execute("INSERT INTO contributions_fts(contributions_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()


@pytest.fixture
async def datasette_with_search():
    temp_dir = Path(tempfile.mkdtemp())
    meetings_db = temp_dir / "meetings.db"
    finance_db = temp_dir / "finance.db"
    _create_meetings_db(meetings_db)
    _create_finance_db(finance_db)

    templates_dir = Path(__file__).parent.parent / "templates" / "datasette"
    plugins_dir = Path(__file__).parent.parent / "plugins"

    # Datasette's plugin manager is process-global, so remember what was
    # registered before this fixture so the plugins_dir modules loaded here do
    # not leak into other test modules.
    registered_before = set(pm.get_plugins())

    ds = Datasette(
        [str(meetings_db), str(finance_db)],
        template_dir=str(templates_dir),
        plugins_dir=str(plugins_dir),
        config={
            "plugins": {
                "corkboard": {
                    "subdomain": "test",
                    "site_name": "Test",
                    "site_title": "Test Civic Data",
                }
            }
        },
    )

    yield ds

    with contextlib.suppress(AttributeError):
        await ds.invoke_shutdown()

    for plugin in set(pm.get_plugins()) - registered_before:
        with contextlib.suppress(Exception):
            pm.unregister(plugin)

    for path in (meetings_db, finance_db):
        if path.exists():
            path.unlink()
    if temp_dir.exists():
        temp_dir.rmdir()


@pytest.mark.asyncio
class TestSearchAllPage:
    async def test_get_renders_empty_form(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.get("/-/search")

        assert response.status_code == 200
        html = response.text
        assert 'method="post"' in html
        assert "Search all tables" in html
        assert '<article class="page-card"' not in html

    async def test_get_with_query_does_not_search(self, datasette_with_search):
        """Searching is POST-only: a GET query string must not render results."""
        ds = datasette_with_search
        response = await ds.client.get("/-/search?q=budget")

        assert response.status_code == 200
        assert '<article class="page-card"' not in response.text

    async def test_post_renders_page_cards_for_minutes(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        assert response.status_code == 200
        html = response.text
        assert 'data-type="minutes"' in html
        assert '<article class="page-card"' in html
        assert "page-card.css" in html

    async def test_post_renders_page_cards_for_agendas(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        html = response.text
        assert 'data-type="agenda"' in html

    async def test_post_highlights_search_term(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        assert "<mark>budget</mark>" in response.text

    async def test_post_date_links_point_to_table_search(self, datasette_with_search):
        """Date links rendered in cards must not carry the internal .json suffix."""
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        html = response.text
        assert "/meetings/minutes/?date__exact=2024-01-15" in html
        assert "minutes.json" not in html

    async def test_post_limits_results_and_links_to_more(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        html = response.text
        assert "more result" in html
        assert "_search=budget" in html

    async def test_post_renders_generic_table_for_non_meeting_table(
        self, datasette_with_search
    ):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "budget"})

        html = response.text
        assert '<table class="rows-and-columns">' in html
        assert "Budget Corp" in html

    async def test_post_no_results(self, datasette_with_search):
        ds = datasette_with_search
        response = await ds.client.post("/-/search", data={"q": "zzznomatch"})

        assert response.status_code == 200
        html = response.text
        assert '<article class="page-card"' not in html
        assert "No results" in html

    async def test_post_tracks_analytics_event(
        self, datasette_with_search, monkeypatch
    ):
        from plugins import civic_analytics

        calls = []

        async def fake_track_search(datasette, request, query_text, **kwargs):
            calls.append((query_text, kwargs))

        monkeypatch.setattr(civic_analytics, "track_search", fake_track_search)

        ds = datasette_with_search
        await ds.client.post("/-/search", data={"q": "budget"})

        assert len(calls) == 1
        query_text, kwargs = calls[0]
        assert query_text == "budget"
        assert kwargs.get("search_type") == "search_all"
