"""
Shared pytest fixtures for CivicBand tests.
"""

import asyncio
import contextlib
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from datasette.app import Datasette


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for pytest-asyncio."""
    return asyncio.get_event_loop_policy()


@pytest.fixture
def temp_db() -> Generator[Path, None, None]:
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create a simple test database with sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sample tables similar to CivicBand structure
    cursor.execute("""
        CREATE TABLE agendas (
            id TEXT PRIMARY KEY,
            meeting TEXT,
            date TEXT,
            page INTEGER,
            text TEXT,
            page_image TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE minutes (
            id TEXT PRIMARY KEY,
            meeting TEXT,
            date TEXT,
            page INTEGER,
            text TEXT,
            page_image TEXT
        )
    """)

    # Insert sample data
    cursor.execute("""
        INSERT INTO agendas VALUES
        ('agenda1', 'City Council', '2024-01-15', 1, 'Meeting called to order', 'page1.jpg'),
        ('agenda2', 'City Council', '2024-01-15', 2, 'Budget discussion', 'page2.jpg'),
        ('agenda3', 'Planning Commission', '2024-01-16', 1, 'Zoning review', 'page1.jpg')
    """)

    cursor.execute("""
        INSERT INTO minutes VALUES
        ('minute1', 'City Council', '2024-01-15', 1, 'Minutes approved', 'page1.jpg'),
        ('minute2', 'City Council', '2024-01-15', 2, 'Vote on budget', 'page2.jpg')
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def datasette_instance(temp_db: Path) -> AsyncGenerator[Datasette, None]:
    """Create a Datasette instance with test database."""
    ds = Datasette(
        [str(temp_db)],
        metadata={
            "databases": {
                temp_db.stem: {
                    "tables": {
                        "agendas": {"title": "Meeting Agendas"},
                        "minutes": {"title": "Meeting Minutes"},
                    }
                }
            }
        },
    )

    yield ds

    await ds.close()


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for API testing."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.fixture
def mock_umami_response():
    """Mock successful Umami API response."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"success": True}
    return response


@pytest.fixture
def asgi_scope():
    """Create a basic ASGI scope for testing."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"host", b"localhost"),
            (b"user-agent", b"TestClient/1.0"),
        ],
        "server": ("localhost", 8000),
        "scheme": "http",
    }


@pytest.fixture
def asgi_receive():
    """Create a basic ASGI receive callable."""

    async def receive():
        return {"type": "http.request", "body": b""}

    return receive


@pytest.fixture
def asgi_send():
    """Create a mock ASGI send callable that records calls."""
    sent_messages = []

    async def send(message):
        sent_messages.append(message)

    send.messages = sent_messages
    return send


@pytest.fixture
def subdomain_scope(asgi_scope):
    """Create ASGI scope with subdomain."""
    scope = asgi_scope.copy()
    scope["headers"] = [
        (b"host", b"alameda.ca.civic.org"),
        (b"user-agent", b"TestClient/1.0"),
    ]
    return scope


@pytest.fixture
def search_scope(subdomain_scope):
    """Create ASGI scope with search query."""
    scope = subdomain_scope.copy()
    scope["path"] = "/meetings/agendas"
    scope["query_string"] = b"_search=council"
    return scope


@pytest.fixture
def sql_scope(subdomain_scope):
    """Create ASGI scope with SQL query."""
    scope = subdomain_scope.copy()
    scope["path"] = "/meetings"
    scope["query_string"] = b"sql=SELECT+*+FROM+agendas&p0=2024-01-15"
    return scope


@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test."""
    # Save original values of test-specific env vars only
    original_umami = os.environ.get("UMAMI_ANALYTICS_ENABLED")

    # Set test defaults
    os.environ["UMAMI_ANALYTICS_ENABLED"] = "false"

    yield

    # Restore original value or remove if it wasn't set
    if original_umami is not None:
        os.environ["UMAMI_ANALYTICS_ENABLED"] = original_umami
    elif "UMAMI_ANALYTICS_ENABLED" in os.environ:
        del os.environ["UMAMI_ANALYTICS_ENABLED"]


@pytest.fixture
def mock_datasette():
    """Create a mock Datasette instance for plugin testing."""
    ds = MagicMock()
    ds.databases = {}
    ds.get_database = MagicMock()
    return ds


@pytest.fixture(scope="function")
def django_db_setup(django_db_setup, django_db_blocker):
    """Set up the sites database for tests."""
    with django_db_blocker.unblock():
        from django.db import connections

        # Get the default database connection
        with connections["default"].cursor() as cursor:
            # Create the sites table matching the Site model schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sites (
                    subdomain TEXT PRIMARY KEY,
                    name TEXT,
                    state TEXT,
                    kind TEXT,
                    scraper TEXT,
                    pages INTEGER,
                    start_year INTEGER,
                    extra TEXT,
                    country TEXT,
                    lat TEXT,
                    lng TEXT,
                    has_finance_data INTEGER DEFAULT 0,
                    current_stage TEXT,
                    started_at TEXT,
                    updated_at TEXT,
                    fetch_total INTEGER DEFAULT 0,
                    fetch_completed INTEGER DEFAULT 0,
                    fetch_failed INTEGER DEFAULT 0,
                    ocr_total INTEGER DEFAULT 0,
                    ocr_completed INTEGER DEFAULT 0,
                    ocr_failed INTEGER DEFAULT 0,
                    compilation_total INTEGER DEFAULT 0,
                    compilation_completed INTEGER DEFAULT 0,
                    compilation_failed INTEGER DEFAULT 0,
                    extraction_total INTEGER DEFAULT 0,
                    extraction_completed INTEGER DEFAULT 0,
                    extraction_failed INTEGER DEFAULT 0,
                    deploy_total INTEGER DEFAULT 0,
                    deploy_completed INTEGER DEFAULT 0,
                    deploy_failed INTEGER DEFAULT 0,
                    coordinator_enqueued INTEGER DEFAULT 0,
                    last_error_stage TEXT,
                    last_error_message TEXT,
                    last_error_at TEXT,
                    status TEXT,
                    extraction_status TEXT DEFAULT 'pending',
                    last_updated TEXT,
                    last_deployed TEXT,
                    last_extracted TEXT
                )
            """)

            # Insert test data
            cursor.execute("""
                INSERT OR REPLACE INTO sites
                (subdomain, name, state, country, kind, pages, lat, lng)
                VALUES
                ('test.ca', 'Test City', 'California', 'USA', 'city', 100, '37.7749', '-122.4194')
            """)

    yield

    # Cleanup
    with django_db_blocker.unblock(), connections["default"].cursor() as cursor:
        cursor.execute("DELETE FROM sites WHERE subdomain = 'test.ca'")


# ---------------------------------------------------------------------------
# OG unfurl card fixtures (sharing plan, Phase 2 workstream 2)
# ---------------------------------------------------------------------------
OG_TEST_SUBDOMAIN = "alameda.ca"
OG_TEST_BASE_URL = f"https://{OG_TEST_SUBDOMAIN}.civic.band"


def create_og_meetings_db(path: Path) -> None:
    """A minutes/agendas database with the rows the card tests need."""
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
            f'CREATE VIRTUAL TABLE {table}_fts USING fts5(text, '
            f'content="{table}", content_rowid="rowid")'
        )
    # OCR text with the noise a preview must not show: a line-break
    # hyphenation, a hard newline and a control character.
    cur.execute(
        "INSERT INTO minutes VALUES "
        "('min-001', 'City Council', '2024-01-15', 1, ?, '', '', NULL)",
        ("The council approv-\ned the budget 5-2.\x01",),
    )
    # A row with no OCR text, no date and no page.
    cur.execute(
        "INSERT INTO minutes VALUES "
        "('min-empty', NULL, NULL, NULL, NULL, '', '', NULL)"
    )
    cur.execute(
        "INSERT INTO agendas VALUES "
        "('agenda-001', 'Planning Commission', '2024-01-16', 1, "
        "'Zoning map update.', '', '', NULL)"
    )
    cur.execute("INSERT INTO minutes_fts(minutes_fts) VALUES('rebuild')")
    cur.execute("INSERT INTO agendas_fts(agendas_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()


@pytest.fixture
def og_cache_dir(tmp_path, monkeypatch):
    """Private card cache per test so hits/misses are deterministic."""
    from plugins import og_card  # noqa: PLC0415

    monkeypatch.setenv("OG_CARD_CACHE_DIR", str(tmp_path / "og-cards"))
    og_card.reset_caches()
    yield tmp_path / "og-cards"
    og_card.reset_caches()


@pytest.fixture
async def og_site(og_cache_dir):
    """A Datasette instance wired exactly like the production wrapper."""
    from datasette import plugins as datasette_plugins  # noqa: PLC0415

    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "meetings.db"
    create_og_meetings_db(db_path)

    repo = Path(__file__).parent.parent
    registered_before = set(datasette_plugins.pm.get_plugins())

    ds = Datasette(
        [str(db_path)],
        template_dir=str(repo / "templates" / "datasette"),
        plugins_dir=str(repo / "plugins"),
        config={
            "plugins": {
                "corkboard": {
                    "subdomain": OG_TEST_SUBDOMAIN,
                    "site_name": "Alameda",
                    "site_title": "Alameda Public Meetings",
                }
            }
        },
    )
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
