"""
Tests for page card template functionality.

This test module verifies that the page card layout renders correctly
for both minutes and agendas tables, including:
- Card layout structure
- Metadata display
- Content sections
- JSON data sections
- CSS loading
"""

import contextlib
import sqlite3
import tempfile
from pathlib import Path

import pytest
from datasette.app import Datasette


@pytest.fixture
async def datasette_with_meetings():
    """Create a Datasette instance with meeting data."""
    # Create a temporary directory for the database
    temp_dir = Path(tempfile.mkdtemp())
    # Name the database "meetings" to match the template naming convention
    db_path = temp_dir / "meetings.db"

    # Create test database with sample meeting data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create minutes table
    cursor.execute("""
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

    # Create agendas table
    cursor.execute("""
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

    # Insert test minutes data
    cursor.execute("""
        INSERT INTO minutes VALUES
        (
            'min-001',
            'City Council',
            '2024-01-15',
            1,
            'Meeting called to order at 7:00 PM',
            'https://example.com/image1.jpg',
            '["Entity1", "Entity2"]',
            '{"resolution": "001", "result": "passed"}'
        ),
        (
            'min-002',
            'City Council',
            '2024-01-15',
            2,
            'Budget discussion and approval',
            'https://example.com/image2.jpg',
            '["Budget", "Finance"]',
            '{"resolution": "002", "result": "passed"}'
        )
    """)

    # Insert test agendas data
    cursor.execute("""
        INSERT INTO agendas VALUES
        (
            'agenda-001',
            'Planning Commission',
            '2024-01-16',
            1,
            'Zoning review for downtown area',
            'https://example.com/image3.jpg',
            '["Zoning", "Downtown"]',
            NULL
        )
    """)

    conn.commit()
    conn.close()

    # Create Datasette instance with templates directory
    # Point to the datasette subdirectory where the custom templates live
    templates_dir = Path(__file__).parent.parent / "templates" / "datasette"
    ds = Datasette(
        [str(db_path)],
        template_dir=str(templates_dir),
        metadata={
            "databases": {
                "meetings": {
                    "tables": {
                        "minutes": {"title": "Meeting Minutes"},
                        "agendas": {"title": "Meeting Agendas"},
                    }
                }
            }
        },
    )

    yield ds

    # Cleanup datasette instance
    with contextlib.suppress(AttributeError):
        await ds.invoke_shutdown()

    # Cleanup database file and temp directory
    if db_path.exists():
        db_path.unlink()
    if temp_dir.exists():
        temp_dir.rmdir()


@pytest.mark.asyncio
class TestPageCardTemplate:
    """Test page card template rendering."""

    async def test_minutes_table_uses_card_layout(self, datasette_with_meetings):
        """Minutes table should use card layout with page-cards container."""
        ds = datasette_with_meetings

        # Request the minutes table page (database is named "meetings")
        response = await ds.client.get("/meetings/minutes")

        assert response.status_code == 200

        # Check for page-cards container
        html = response.text
        assert '<div class="page-cards">' in html, "Should have .page-cards container"

    async def test_agendas_table_uses_card_layout(self, datasette_with_meetings):
        """Agendas table should use card layout with page-cards container."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/agendas")

        assert response.status_code == 200

        html = response.text
        assert '<div class="page-cards">' in html, "Should have .page-cards container"

    async def test_minutes_cards_have_articles(self, datasette_with_meetings):
        """Each minute should render as an article.page-card element."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text
        # Count page-card article occurrences
        card_count = html.count('<article class="page-card"')
        assert card_count > 0, "Should have at least one page-card article"
        assert card_count == 2, "Should have two minute cards"

    async def test_agenda_cards_have_articles(self, datasette_with_meetings):
        """Each agenda should render as an article.page-card element."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/agendas")

        html = response.text
        # Count page-card article occurrences
        card_count = html.count('<article class="page-card"')
        assert card_count > 0, "Should have at least one page-card article"
        assert card_count == 1, "Should have one agenda card"

    async def test_card_has_metadata_row(self, datasette_with_meetings):
        """Card should have metadata row with ID, meeting, date."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Check for metadata header
        assert (
            '<header class="card-metadata">' in html
        ), "Card should have .card-metadata header"

        # Check for ID link
        assert 'class="card-id"' in html, "Should have card ID link"
        assert "ID:" in html, "Should display ID label"

        # Check for meeting link
        assert 'class="card-meeting"' in html, "Should have meeting link"

        # Check for date
        assert 'class="card-date"' in html, "Should have date span"

    async def test_card_has_badges(self, datasette_with_meetings):
        """Card metadata should have document type and page badges."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Check for type badge
        assert 'class="card-type-badge' in html, "Should have type badge"

        # Check for page badge
        assert 'class="card-page-badge"' in html, "Should have page badge"
        assert "Page" in html, "Should display page number"

    async def test_card_has_content_row(self, datasette_with_meetings):
        """Card should have content row with text and image."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Check for content div
        assert (
            '<div class="card-content">' in html
        ), "Card should have .card-content div"

        # Check for text section with toggle button
        assert '<div class="card-text">' in html, "Should have .card-text section"
        assert '<div class="card-text-content">' in html, "Should have text content"
        assert "card-text-toggle" in html, "Should have text toggle button"

        # Check for image section
        assert '<div class="card-image"' in html, "Should have .card-image section"

    async def test_card_has_json_row(self, datasette_with_meetings):
        """Card should have footer with entities and votes sections."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Check for footer
        assert (
            '<footer class="card-json">' in html
        ), "Card should have .card-json footer"

        # Check for entities section
        assert (
            '<div class="card-entities">' in html
        ), "Should have .card-entities section"

        # Check for votes section
        assert '<div class="card-votes">' in html, "Should have .card-votes section"

    async def test_page_card_css_is_loaded(self, datasette_with_meetings):
        """Page card CSS should be loaded in the page head."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Look for page-card.css reference
        assert "page-card.css" in html, "Should include page-card.css stylesheet"

    async def test_minutes_card_type_attribute(self, datasette_with_meetings):
        """Minutes cards should have data-type='minutes' attribute."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text
        assert (
            'data-type="minutes"' in html
        ), "Minutes card should have data-type='minutes'"

    async def test_agenda_card_type_attribute(self, datasette_with_meetings):
        """Agenda cards should have data-type='agenda' attribute."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/agendas")

        html = response.text
        assert (
            'data-type="agenda"' in html
        ), "Agenda card should have data-type='agenda'"

    async def test_card_id_links_to_row(self, datasette_with_meetings):
        """Card ID and meeting should link to the row detail page."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text

        # Check that links to row details exist
        assert "href=" in html, "Should have links"
        assert "min-001" in html, "Should reference the row ID"
        assert 'class="card-id"' in html, "Should have ID link with card-id class"
        assert (
            'class="card-meeting"' in html
        ), "Should have meeting link with card-meeting class"

    async def test_minutes_page_title(self, datasette_with_meetings):
        """Minutes table page should have 'Meeting Minutes' heading."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/minutes")

        html = response.text
        assert "<h1" in html, "Should have h1 heading"
        assert "Meeting Minutes" in html, "Should say 'Meeting Minutes'"

    async def test_agendas_page_title(self, datasette_with_meetings):
        """Agendas table page should have 'Meeting Agendas' heading."""
        ds = datasette_with_meetings

        response = await ds.client.get("/meetings/agendas")

        html = response.text
        assert "<h1" in html, "Should have h1 heading"
        assert "Meeting Agendas" in html, "Should say 'Meeting Agendas'"
