"""Tests for OG unfurl metadata on Datasette row/search/table pages."""

import contextlib
import html
import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from datasette.app import Datasette
from datasette.plugins import pm

from plugins.og_meta import (
    global_card_url,
    municipality_card_url,
    page_scan_url,
    row_title,
    search_title,
)

CARD = "https://cdn.civic.band/alameda.ca/og-card-v1.png"
SCAN = (
    "https://cdn.civic.band/alameda.ca/City%20Council/2024-01-15/1.png"
    "?crop=1200%2C630%2Coffset-y0%2Csafe&width=1200&quality=85"
)


def _create_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for table in ("minutes", "agendas"):
        cur.execute(
            f"""
            CREATE TABLE {table} (
                id TEXT PRIMARY KEY,
                meeting TEXT,
                date TEXT,
                page INTEGER,
                text TEXT,
                page_image TEXT,
                entities_json TEXT,
                votes_json TEXT
            )
            """
        )

    cur.execute(
        "INSERT INTO minutes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "min-001",
            "City Council",
            "2024-01-15",
            1,
            "Meeting called to order at 7:00 PM",
            "/City Council/2024-01-15/1.png",
            None,
            None,
        ),
    )
    cur.execute(
        "INSERT INTO minutes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "min-002",
            "City Council",
            "2024-01-15",
            2,
            "Budget discussion and approval",
            None,
            None,
            None,
        ),
    )
    cur.execute(
        "INSERT INTO agendas VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "agenda-001",
            "Planning Commission",
            "2024-01-16",
            1,
            "Zoning review for downtown",
            "/_agendas/Planning Commission/2024-01-16/1.png",
            None,
            None,
        ),
    )

    for table in ("minutes", "agendas"):
        cur.execute(
            f'CREATE VIRTUAL TABLE {table}_fts USING fts5(text, content="{table}", '
            'content_rowid="rowid")'
        )
        cur.execute(f"INSERT INTO {table}_fts({table}_fts) VALUES('rebuild')")

    conn.commit()
    conn.close()


def _meta(page: str, key: str):
    match = re.search(
        rf'<meta (?:property|name)="{re.escape(key)}" content="([^"]*)"', page
    )
    return html.unescape(match.group(1)) if match else None


@pytest.fixture
async def og_datasette():
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "meetings.db"
    _create_db(db_path)

    root = Path(__file__).parent.parent
    registered_before = set(pm.get_plugins())
    ds = Datasette(
        [str(db_path)],
        template_dir=str(root / "templates" / "datasette"),
        plugins_dir=str(root / "plugins"),
        config={
            "plugins": {
                "corkboard": {
                    "subdomain": "alameda.ca",
                    "site_name": "Alameda",
                    "site_title": "Alameda Civic Data",
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
    if db_path.exists():
        db_path.unlink()
    if temp_dir.exists():
        temp_dir.rmdir()


class TestHelpers:
    def test_municipality_card_url(self):
        assert (
            municipality_card_url("alameda.ca")
            == "https://cdn.civic.band/alameda.ca/og-card-v1.png"
        )

    def test_empty_subdomain_uses_global_card(self):
        assert municipality_card_url("") == global_card_url()

    def test_page_scan_url_encodes_path_and_query(self):
        assert page_scan_url("alameda.ca", "/City Council/2024-01-15/1.png") == SCAN

    def test_page_scan_url_accepts_missing_leading_slash(self):
        assert page_scan_url("alameda.ca", "City Council/1.png").startswith(
            "https://cdn.civic.band/alameda.ca/City%20Council/1.png?"
        )

    def test_page_scan_url_falls_back_without_image(self):
        assert page_scan_url("alameda.ca", None) == CARD
        assert page_scan_url("alameda.ca", "") == CARD

    def test_row_title_omits_missing_parts(self):
        assert (
            row_title("Alameda", "City Council", "2024-01-15", 2)
            == "Alameda \u2014 City Council \u2014 2024-01-15 \u2014 Page 2"
        )
        assert row_title("Alameda", None, None, None) == "Alameda"

    def test_search_title(self):
        assert search_title("budget") == "Search results for \u201cbudget\u201d"
        assert search_title("") == "Search"


class TestRenderedPages:
    async def test_row_with_scan_uses_cdn_image(self, og_datasette):
        response = await og_datasette.client.get("/meetings/minutes/min-001")
        assert response.status_code == 200

        page = response.text
        assert _meta(page, "og:image") == SCAN
        assert _meta(page, "twitter:image") == SCAN
        assert _meta(page, "og:image:width") == "1200"
        assert _meta(page, "og:image:height") == "630"
        assert "City Council" in _meta(page, "og:title")
        assert "Page 1" in _meta(page, "og:title")
        assert _meta(page, "og:description") == "Meeting called to order at 7:00 PM"
        assert (
            _meta(page, "og:url")
            == "https://alameda.ca.civic.band/meetings/minutes/min-001"
        )

    async def test_row_without_scan_uses_card(self, og_datasette):
        response = await og_datasette.client.get("/meetings/minutes/min-002")
        assert response.status_code == 200
        assert _meta(response.text, "og:image") == CARD

    async def test_agenda_row_uses_agenda_scan(self, og_datasette):
        response = await og_datasette.client.get("/meetings/agendas/agenda-001")
        assert response.status_code == 200
        assert _meta(response.text, "og:image").startswith(
            "https://cdn.civic.band/alameda.ca/"
            "_agendas/Planning%20Commission/2024-01-16/1.png?"
        )

    async def test_table_page_uses_card(self, og_datasette):
        response = await og_datasette.client.get("/meetings/minutes")
        assert response.status_code == 200
        assert _meta(response.text, "og:image") == CARD

    async def test_search_page_uses_card_and_query_title(self, og_datasette):
        response = await og_datasette.client.post("/-/search", data={"q": "budget"})
        assert response.status_code == 200
        page = response.text
        assert _meta(page, "og:image") == CARD
        assert _meta(page, "og:title") == "Search results for \u201cbudget\u201d"
