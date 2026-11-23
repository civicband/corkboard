"""End-to-end tests for the canonical permalink and social metadata (Phase 1).

These render real Datasette pages through the same template directory the
embedded Datasette uses (``templates/datasette``) with the repo plugins
loaded, then assert on the emitted head tags:

- ``<link rel="canonical">`` is present and absolute on index, table and row
  pages, and points at the locked permalink shape.
- Filter/sort query strings never appear in the canonical URL.
- The POST-only ``/-/search`` page canonicalizes to the municipality landing
  page, not its own URL.
- ``og:url`` is well formed (contains ``://``) and equals the canonical URL.
- Page cards expose ``id="page-N"`` anchors.

The fixture deliberately builds Datasette with ``plugins_dir`` pointing at
``plugins/`` so the ``canonical_url`` filter is registered exactly as it is in
production (``django_plugins/datasette_by_subdomain._build_datasette``).
"""

import contextlib
import importlib
import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from datasette import plugins as datasette_plugins
from datasette.app import Datasette

SUBDOMAIN = "alameda.ca"
BASE_URL = f"https://{SUBDOMAIN}.civic.band"

CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]*)">')
OG_URL_RE = re.compile(r'<meta property="og:url" content="([^"]*)"/>')


def _create_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    for table in ("minutes", "agendas"):
        cur.execute(f"""
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
        """)
    cur.execute(
        "INSERT INTO minutes VALUES "
        "('min-001', 'City Council', '2024-01-15', 1, 'Budget', '', '', NULL),"
        "('min-002', 'City Council', '2024-01-15', 2, 'More budget', '', '', NULL)"
    )
    cur.execute(
        "INSERT INTO agendas VALUES "
        "('agenda-001', 'Planning Commission', '2024-01-16', 1, 'Zoning', '', '', NULL)"
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


@pytest.fixture
async def canonical_site():
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "meetings.db"
    _create_db(db_path)

    repo = Path(__file__).parent.parent
    registered_before = set(datasette_plugins.pm.get_plugins())

    ds = Datasette(
        [str(db_path)],
        template_dir=str(repo / "templates" / "datasette"),
        plugins_dir=str(repo / "plugins"),
        config={
            "plugins": {
                "corkboard": {
                    "subdomain": SUBDOMAIN,
                    "site_name": "Alameda",
                    "site_title": "Alameda Public Meetings",
                }
            }
        },
    )
    # Startup is what runs ``prepare_jinja2_environment`` and therefore
    # registers the ``canonical_url`` filter, mirroring production where the
    # ASGI app boots before serving requests.
    with contextlib.suppress(Exception):
        await ds.invoke_startup()

    yield ds

    with contextlib.suppress(AttributeError):
        await ds.invoke_shutdown()

    for plugin in set(datasette_plugins.pm.get_plugins()) - registered_before:
        with contextlib.suppress(Exception):
            datasette_plugins.pm.unregister(plugin)

    if db_path.exists():
        db_path.unlink()
    if temp_dir.exists():
        temp_dir.rmdir()


def _canonical(html: str) -> str:
    match = CANONICAL_RE.search(html)
    assert match, f"no canonical link in page: {html[:500]}"
    return match.group(1)


def _og_url(html: str) -> str:
    match = OG_URL_RE.search(html)
    assert match, f"no og:url in page: {html[:500]}"
    return match.group(1)


@pytest.mark.asyncio
class TestCanonicalLink:
    async def test_index_canonical_is_municipality_root(self, canonical_site):
        response = await canonical_site.client.get("/")
        assert response.status_code == 200
        assert _canonical(response.text) == f"{BASE_URL}/"

    async def test_table_page_canonical(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes")
        assert response.status_code == 200
        assert _canonical(response.text) == f"{BASE_URL}/meetings/minutes"

    async def test_row_page_canonical_is_locked_shape(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes/min-001")
        assert response.status_code == 200
        assert _canonical(response.text) == (f"{BASE_URL}/meetings/minutes/min-001")

    async def test_agenda_row_canonical(self, canonical_site):
        response = await canonical_site.client.get("/meetings/agendas/agenda-001")
        assert response.status_code == 200
        assert _canonical(response.text) == (f"{BASE_URL}/meetings/agendas/agenda-001")

    async def test_database_page_canonical(self, canonical_site):
        response = await canonical_site.client.get("/meetings")
        assert response.status_code == 200
        assert _canonical(response.text) == f"{BASE_URL}/meetings"

    async def test_search_filter_query_is_not_canonical(self, canonical_site):
        """A filtered table view canonicalizes to the bare table URL."""
        response = await canonical_site.client.get(
            "/meetings/minutes?_search=budget&_sort=page"
        )
        canonical = _canonical(response.text)
        assert canonical == f"{BASE_URL}/meetings/minutes"
        assert "?" not in canonical

    async def test_canonical_is_absolute(self, canonical_site):
        for path in ("/", "/meetings/minutes", "/meetings/minutes/min-001"):
            response = await canonical_site.client.get(path)
            canonical = _canonical(response.text)
            assert canonical.startswith("https://"), canonical
            assert canonical.count("://") == 1

    async def test_post_search_canonicalizes_to_landing(self, canonical_site):
        """The POST-only search page must not advertise its POST URL."""
        response = await canonical_site.client.post("/-/search", data={"q": "budget"})
        assert response.status_code == 200
        canonical = _canonical(response.text)
        assert canonical == f"{BASE_URL}/"
        assert "/-/search" not in canonical


@pytest.mark.asyncio
class TestOpenGraphUrl:
    async def test_og_url_is_well_formed(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes/min-001")
        og_url = _og_url(response.text)
        assert "://" in og_url
        assert not og_url.startswith("https:" + SUBDOMAIN)

    async def test_og_url_matches_canonical_per_page(self, canonical_site):
        for path in (
            "/",
            "/meetings/minutes",
            "/meetings/minutes/min-001",
        ):
            response = await canonical_site.client.get(path)
            assert _og_url(response.text) == _canonical(response.text)

    async def test_existing_og_tags_preserved(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes/min-001")
        html = response.text
        assert '<meta property="og:title"' in html
        assert '<meta property="og:description"' in html
        assert '<meta property="og:site_name"' in html

    async def test_twitter_url_matches_canonical(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes")
        match = re.search(r'<meta name="twitter:url" content="([^"]*)">', response.text)
        assert match
        assert match.group(1) == _canonical(response.text)


@pytest.mark.asyncio
class TestPageAnchors:
    async def test_table_page_cards_have_page_anchors(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes")
        html = response.text
        assert 'id="page-1"' in html
        assert 'id="page-2"' in html

    async def test_page_anchor_is_on_the_card(self, canonical_site):
        response = await canonical_site.client.get("/meetings/minutes")
        assert re.search(
            r'<article class="page-card" data-type="minutes" id="page-1">',
            response.text,
        )


def test_canonical_plugin_registers_filter():
    """The plugin must expose the filter and the template flag."""
    module = importlib.import_module("plugins.canonical")
    env = _FakeEnv()
    datasette = _FakeDatasette({"subdomain": SUBDOMAIN})
    module.prepare_jinja2_environment(env, datasette)

    assert env.globals["canonical_plugin_enabled"] is True
    assert env.filters["canonical_url"]("meetings", "minutes", "min-001") == (
        f"{BASE_URL}/meetings/minutes/min-001"
    )


class _FakeEnv:
    def __init__(self):
        self.filters = {}
        self.globals = {}


class _FakeDatasette:
    def __init__(self, config):
        self._config = config

    def plugin_config(self, plugin):
        assert plugin == "corkboard"
        return self._config
