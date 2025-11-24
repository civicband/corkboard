"""
Shared pytest fixtures for CivicBand tests.
"""

import asyncio
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
                        "agendas": {
                            "title": "Meeting Agendas"
                        },
                        "minutes": {
                            "title": "Meeting Minutes"
                        }
                    }
                }
            }
        }
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
    # Save original env
    original_env = os.environ.copy()

    # Set test defaults
    os.environ["UMAMI_ANALYTICS_ENABLED"] = "false"

    yield

    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_datasette():
    """Create a mock Datasette instance for plugin testing."""
    ds = MagicMock()
    ds.databases = {}
    ds.get_database = MagicMock()
    return ds
