# Page Card Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform meeting minutes and agenda page table views from tabular rows into card-style displays with metadata, content (OCR text + image), and JSON extraction sections.

**Architecture:** Create a shared `_page_card.html` template partial that both minutes and agendas table templates include. Add card CSS to a new stylesheet. Use `<details>` elements for text expand/collapse (no JS required). Image expand uses inline expansion with CSS.

**Tech Stack:** Datasette templates (Jinja2), CSS (custom, following existing design system), minimal JavaScript for image lightbox

**Spec:** `docs/superpowers/specs/2026-03-23-page-card-layout-design.md`

---

## File Structure

```
templates/datasette/
├── _page_card.html                # NEW: shared card partial
├── table-meetings-minutes.html    # NEW: card layout for minutes table
├── table-meetings-agendas.html    # NEW: card layout for agendas table
static/
├── page-card.css                  # NEW: card component styles
```

---

## Task 1: Create Card CSS Stylesheet

**Files:**
- Create: `static/page-card.css`

- [ ] **Step 1: Create the base card container styles**

Create `static/page-card.css` with the card container and metadata row styles:

```css
/* Page Card Component Styles */

/* Card container */
.page-cards {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.page-card {
    background: #ffffff;
    border: 1px solid #e1ecf4;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    overflow: hidden;
    transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.page-card:hover {
    box-shadow: 0 4px 12px rgba(0, 123, 255, 0.15);
    transform: translateY(-1px);
}

/* Metadata row */
.card-metadata {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-bottom: 1px solid #e1ecf4;
    gap: 0.5rem;
}

.card-meta-left {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.95rem;
}

.card-meta-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.card-id {
    color: #6c757d;
    text-decoration: none;
    font-size: 0.85rem;
}

.card-id:hover {
    color: #007bff;
    text-decoration: underline;
}

.card-meeting {
    font-weight: 600;
    color: #1a365d;
    text-decoration: none;
}

.card-meeting:hover {
    color: #007bff;
    text-decoration: underline;
}

.card-date {
    color: #495057;
}

.card-separator {
    color: #adb5bd;
    margin: 0 0.25rem;
}

/* Type badges */
.card-type-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.card-type-minutes {
    background: #007bff;
    color: white;
}

.card-type-agenda {
    background: #28a745;
    color: white;
}

.card-page-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 500;
    background: #e9ecef;
    color: #6c757d;
}
```

- [ ] **Step 2: Add content row styles**

Append content row styles to `static/page-card.css`:

```css
/* Content row */
.card-content {
    display: flex;
    padding: 1rem;
    gap: 1rem;
    border-bottom: 1px solid #f1f3f4;
}

.card-text {
    flex: 0 0 60%;
    min-width: 0;
}

.card-text-content {
    max-height: 150px;
    overflow: hidden;
    position: relative;
    line-height: 1.5;
    color: #333;
}

.card-text-content::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 40px;
    background: linear-gradient(transparent, white);
    pointer-events: none;
}

.card-text details[open] .card-text-content {
    max-height: none;
}

.card-text details[open] .card-text-content::after {
    display: none;
}

.card-text summary {
    cursor: pointer;
    color: #007bff;
    font-size: 0.9rem;
    margin-top: 0.5rem;
    user-select: none;
}

.card-text summary:hover {
    text-decoration: underline;
}

.card-text summary::-webkit-details-marker {
    display: none;
}

.card-text summary::marker {
    display: none;
    content: '';
}

/* Image section */
.card-image {
    flex: 0 0 40%;
    min-width: 0;
}

.card-image img {
    width: 100%;
    height: auto;
    border-radius: 4px;
    cursor: pointer;
    transition: transform 0.2s ease;
}

.card-image img:hover {
    transform: scale(1.02);
}

.card-image.expanded img {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    max-width: 90vw;
    max-height: 90vh;
    width: auto;
    height: auto;
    z-index: 1000;
    border-radius: 8px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.card-image-overlay {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    z-index: 999;
}

.card-image.expanded .card-image-overlay {
    display: block;
}
```

- [ ] **Step 3: Add JSON row and responsive styles**

Append JSON row and responsive styles to `static/page-card.css`:

```css
/* JSON row */
.card-json {
    display: flex;
    padding: 1rem;
    gap: 1rem;
    background: #fafbfc;
}

.card-entities {
    flex: 1;
    min-width: 0;
}

.card-votes {
    flex: 1;
    min-width: 0;
}

.card-json-empty {
    color: #6c757d;
    font-style: italic;
    font-size: 0.9rem;
}

/* Responsive styles */
@media (max-width: 767px) {
    .card-metadata {
        flex-direction: column;
        align-items: flex-start;
    }

    .card-meta-right {
        margin-top: 0.5rem;
    }

    .card-content {
        flex-direction: column;
    }

    .card-text {
        flex: none;
        width: 100%;
        order: 1;
    }

    .card-image {
        flex: none;
        width: 48px;
        float: right;
        margin-left: 1rem;
        margin-bottom: 0.5rem;
        order: 0;
    }

    .card-image img {
        width: 48px;
        height: auto;
    }

    .card-json {
        flex-direction: column;
    }

    .card-entities,
    .card-votes {
        flex: none;
        width: 100%;
    }
}
```

- [ ] **Step 4: Verify CSS file exists and is valid**

Run: `ls -la static/page-card.css && head -50 static/page-card.css`

Expected: File exists with card container styles at the top

- [ ] **Step 5: Commit CSS**

```bash
git add static/page-card.css
git commit -m "feat: add page card component CSS styles

Implements card layout for meeting pages with:
- Metadata row with badges
- Content row with text truncation and image
- JSON row for entities and votes
- Responsive mobile layout"
```

---

## Task 2: Create Card Partial Template

**Files:**
- Create: `templates/datasette/_page_card.html`

- [ ] **Step 1: Create the card partial template**

Create `templates/datasette/_page_card.html`:

```html
{# Page Card Partial Template
   Variables expected:
   - row: dict with id, meeting, date, page, text, page_image, entities_json, votes_json
   - document_type: "minutes" or "agenda"
   - database: database name
   - table: table name
   - datasette: datasette instance
   - request: request object
#}
{% set row_url = "/" ~ database ~ "/" ~ table ~ "/" ~ (row.id|urlencode) %}

<article class="page-card" data-type="{{ document_type }}">
  <header class="card-metadata">
    <div class="card-meta-left">
      <a href="{{ row_url }}" class="card-id">ID: {{ row.id[:12] }}{% if row.id|length > 12 %}...{% endif %}</a>
      <span class="card-separator">·</span>
      <a href="{{ row_url }}" class="card-meeting">{{ row.meeting }}</a>
      <span class="card-separator">·</span>
      <span class="card-date">{{ row.date }}</span>
    </div>
    <div class="card-meta-right">
      <span class="card-type-badge card-type-{{ document_type }}">{{ document_type|upper }}</span>
      <span class="card-page-badge">Page {{ row.page }}</span>
    </div>
  </header>

  <div class="card-content">
    <div class="card-text">
      <details>
        <div class="card-text-content">{{ row.text or "" }}</div>
        <summary>Show more</summary>
      </details>
    </div>
    <div class="card-image" onclick="this.classList.toggle('expanded')">
      <div class="card-image-overlay" onclick="event.stopPropagation(); this.parentElement.classList.remove('expanded')"></div>
      {{ render_cell(row.page_image, row, "page_image", table, database, datasette, request)|safe }}
    </div>
  </div>

  <footer class="card-json">
    <div class="card-entities">
      {% if row.entities_json %}
        {{ render_cell(row.entities_json, row, "entities_json", table, database, datasette, request)|safe }}
      {% else %}
        <span class="card-json-empty">No entities extracted</span>
      {% endif %}
    </div>
    <div class="card-votes">
      {% if row.votes_json %}
        {{ render_cell(row.votes_json, row, "votes_json", table, database, datasette, request)|safe }}
      {% else %}
        <span class="card-json-empty">No votes recorded</span>
      {% endif %}
    </div>
  </footer>
</article>
```

- [ ] **Step 2: Verify template exists**

Run: `ls -la templates/datasette/_page_card.html`

Expected: File exists

- [ ] **Step 3: Commit partial template**

```bash
git add templates/datasette/_page_card.html
git commit -m "feat: add page card partial template

Shared template for rendering meeting pages as cards with:
- Metadata row with ID, meeting name, date, type badge, page number
- Content row with expandable text and clickable image
- JSON row with entities and votes"
```

---

## Task 3: Create Minutes Table Template

**Files:**
- Create: `templates/datasette/table-meetings-minutes.html`
- Reference: `templates/datasette/base.html`

- [ ] **Step 1: Create the minutes table template**

Create `templates/datasette/table-meetings-minutes.html`:

```html
{% extends "base.html" %}

{% block title %}{{ table }} - {{ database }}{% endblock %}

{% block extra_head %}
<link rel="stylesheet" href="{{ urls.static_plugins('corkboard', 'page-card.css') }}">
{% endblock %}

{% block content %}
<div class="page-container" style="max-width: 1200px; margin: 0 auto; padding: 1rem;">
    <div class="page-header" style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 1.75rem; font-weight: 600; color: #1a365d; margin: 0;">
            Meeting Minutes
        </h1>
        {% if filtered_table_rows_count is defined %}
        <p style="color: #6c757d; margin-top: 0.5rem;">
            {{ "{:,}".format(filtered_table_rows_count) }} page{% if filtered_table_rows_count != 1 %}s{% endif %}
            {% if request.args.get('meeting__exact') %}
            for {{ request.args.get('meeting__exact') }}
            {% endif %}
            {% if request.args.get('date__exact') %}
            on {{ request.args.get('date__exact') }}
            {% endif %}
        </p>
        {% endif %}
    </div>

    {% if display_rows %}
    <div class="page-cards">
        {% for row in display_rows %}
            {% with document_type="minutes" %}
                {% include "_page_card.html" %}
            {% endwith %}
        {% endfor %}
    </div>

    {% if next_url %}
    <div style="text-align: center; margin-top: 1.5rem;">
        <a href="{{ next_url }}" style="display: inline-block; padding: 0.75rem 1.5rem; background: #007bff; color: white; text-decoration: none; border-radius: 6px; font-weight: 500;">
            Load more
        </a>
    </div>
    {% endif %}
    {% else %}
    <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 1.5rem; text-align: center; color: #856404;">
        <p>No minutes found matching your criteria.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Verify template exists**

Run: `ls -la templates/datasette/table-meetings-minutes.html`

Expected: File exists

- [ ] **Step 3: Commit minutes template**

```bash
git add templates/datasette/table-meetings-minutes.html
git commit -m "feat: add card-based minutes table template

Replaces default table view with card layout for minutes pages"
```

---

## Task 4: Create Agendas Table Template

**Files:**
- Create: `templates/datasette/table-meetings-agendas.html`

- [ ] **Step 1: Create the agendas table template**

Create `templates/datasette/table-meetings-agendas.html`:

```html
{% extends "base.html" %}

{% block title %}{{ table }} - {{ database }}{% endblock %}

{% block extra_head %}
<link rel="stylesheet" href="{{ urls.static_plugins('corkboard', 'page-card.css') }}">
{% endblock %}

{% block content %}
<div class="page-container" style="max-width: 1200px; margin: 0 auto; padding: 1rem;">
    <div class="page-header" style="margin-bottom: 1.5rem;">
        <h1 style="font-size: 1.75rem; font-weight: 600; color: #1a365d; margin: 0;">
            Meeting Agendas
        </h1>
        {% if filtered_table_rows_count is defined %}
        <p style="color: #6c757d; margin-top: 0.5rem;">
            {{ "{:,}".format(filtered_table_rows_count) }} page{% if filtered_table_rows_count != 1 %}s{% endif %}
            {% if request.args.get('meeting__exact') %}
            for {{ request.args.get('meeting__exact') }}
            {% endif %}
            {% if request.args.get('date__exact') %}
            on {{ request.args.get('date__exact') }}
            {% endif %}
        </p>
        {% endif %}
    </div>

    {% if display_rows %}
    <div class="page-cards">
        {% for row in display_rows %}
            {% with document_type="agenda" %}
                {% include "_page_card.html" %}
            {% endwith %}
        {% endfor %}
    </div>

    {% if next_url %}
    <div style="text-align: center; margin-top: 1.5rem;">
        <a href="{{ next_url }}" style="display: inline-block; padding: 0.75rem 1.5rem; background: #007bff; color: white; text-decoration: none; border-radius: 6px; font-weight: 500;">
            Load more
        </a>
    </div>
    {% endif %}
    {% else %}
    <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 1.5rem; text-align: center; color: #856404;">
        <p>No agendas found matching your criteria.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 2: Verify template exists**

Run: `ls -la templates/datasette/table-meetings-agendas.html`

Expected: File exists

- [ ] **Step 3: Commit agendas template**

```bash
git add templates/datasette/table-meetings-agendas.html
git commit -m "feat: add card-based agendas table template

Replaces default table view with card layout for agenda pages"
```

---

## Task 5: Register Static Files with Datasette

**Files:**
- Modify: `plugins/__init__.py` (or create static plugin registration)
- Check: `pyproject.toml` or `setup.py` for static file configuration

- [ ] **Step 1: Check current static file configuration**

Run: `grep -r "static" plugins/*.py | head -20`

Expected: See how static files are currently registered (if at all)

- [ ] **Step 2: Check if there's a datasette metadata or config file**

Run: `ls -la *.yaml *.yml metadata.json 2>/dev/null || echo "No config files found"`

Run: `grep -r "static_plugins\|extra_css" . --include="*.py" --include="*.yaml" --include="*.yml" | head -10`

Expected: Understand how to register the CSS file

- [ ] **Step 3: Add static file registration if needed**

If static files aren't already registered for the `corkboard` plugin, create or modify the appropriate configuration. The exact approach depends on what Step 1-2 reveal.

Option A: If using `datasette-plugin` pattern, add to plugin:
```python
@hookimpl
def extra_css_urls():
    return ["/static/page-card.css"]
```

Option B: If using metadata.yaml:
```yaml
extra_css_urls:
  - /static/page-card.css
```

- [ ] **Step 4: Verify static file is accessible**

Run: `python -c "from pathlib import Path; print(Path('static/page-card.css').exists())"`

Expected: `True`

- [ ] **Step 5: Commit any configuration changes**

```bash
git add -A
git commit -m "feat: register page-card.css with Datasette

Ensures card styles are loaded for table templates"
```

---

## Task 6: Fix Template Variable Access

**Files:**
- Modify: `templates/datasette/_page_card.html`

The `render_cell` function in Datasette plugins receives parameters differently than template filters. We need to check how to properly call the render_cell hooks from templates.

- [ ] **Step 1: Check how existing templates render cells**

Run: `grep -r "render_cell\|display_column" templates/datasette/*.html`

Expected: See how other templates handle cell rendering

- [ ] **Step 2: Check Datasette's table.html for reference**

Run: `python -c "import datasette; from pathlib import Path; p = Path(datasette.__file__).parent / 'templates' / 'table.html'; print(p.read_text()[:2000] if p.exists() else 'not found')"`

Expected: See how default table template renders cells

- [ ] **Step 3: Update card partial to use correct cell rendering**

Based on findings, update `_page_card.html` to use the correct method for rendering cells. Datasette templates typically use `{{ row["column_name"] }}` directly and plugins intercept via hooks.

The plugins we have (`page_image.py`, `json_columns.py`) use `render_cell` hookimpl which Datasette calls automatically. We may need to mark columns or use a different approach.

Update the template based on findings from Steps 1-2.

- [ ] **Step 4: Commit template fixes**

```bash
git add templates/datasette/_page_card.html
git commit -m "fix: correct cell rendering in card template

Use proper Datasette cell rendering approach"
```

---

## Task 7: Manual Testing

**Files:**
- No file changes

- [ ] **Step 1: Start the development server**

Run: `python manage.py runserver` or the appropriate command for this project

Expected: Server starts without errors

- [ ] **Step 2: Navigate to minutes table**

Open browser to: `/meetings/minutes`

Expected: Cards display instead of table rows. Check:
- Metadata row shows ID, meeting, date, badges
- Content row shows text (truncated) and image
- JSON row shows entities and votes
- Mobile responsive layout works

- [ ] **Step 3: Navigate to agendas table**

Open browser to: `/meetings/agendas`

Expected: Same card layout with green "AGENDA" badge

- [ ] **Step 4: Test interactions**

Test:
- Click "Show more" to expand text
- Click image to expand/lightbox
- Click ID or meeting name to go to detail page
- Click entity chips to search
- Test on mobile viewport

- [ ] **Step 5: Document any issues found**

If issues found, note them for fixing before final commit.

---

## Task 8: Write Tests

**Files:**
- Create: `tests/test_page_card_template.py`

- [ ] **Step 1: Create template test file**

Create `tests/test_page_card_template.py`:

```python
"""Tests for page card template rendering."""

import pytest
from bs4 import BeautifulSoup


@pytest.mark.asyncio
async def test_minutes_table_uses_card_layout(ds_client):
    """Minutes table should render with card layout."""
    response = await ds_client.get("/meetings/minutes")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, "html.parser")

    # Should have page-cards container
    cards_container = soup.find("div", class_="page-cards")
    assert cards_container is not None, "Expected .page-cards container"

    # Should have at least one card
    cards = soup.find_all("article", class_="page-card")
    assert len(cards) > 0, "Expected at least one .page-card"


@pytest.mark.asyncio
async def test_agendas_table_uses_card_layout(ds_client):
    """Agendas table should render with card layout."""
    response = await ds_client.get("/meetings/agendas")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, "html.parser")

    cards_container = soup.find("div", class_="page-cards")
    assert cards_container is not None, "Expected .page-cards container"


@pytest.mark.asyncio
async def test_card_has_metadata_row(ds_client):
    """Card should have metadata row with ID, meeting, date, badges."""
    response = await ds_client.get("/meetings/minutes")
    soup = BeautifulSoup(response.text, "html.parser")

    card = soup.find("article", class_="page-card")
    if card:
        metadata = card.find("header", class_="card-metadata")
        assert metadata is not None, "Card should have .card-metadata header"

        # Check for ID link
        id_link = metadata.find("a", class_="card-id")
        assert id_link is not None, "Should have .card-id link"

        # Check for meeting link
        meeting_link = metadata.find("a", class_="card-meeting")
        assert meeting_link is not None, "Should have .card-meeting link"

        # Check for type badge
        type_badge = metadata.find("span", class_="card-type-badge")
        assert type_badge is not None, "Should have .card-type-badge"
        assert "MINUTES" in type_badge.text.upper()


@pytest.mark.asyncio
async def test_card_has_content_row(ds_client):
    """Card should have content row with text and image."""
    response = await ds_client.get("/meetings/minutes")
    soup = BeautifulSoup(response.text, "html.parser")

    card = soup.find("article", class_="page-card")
    if card:
        content = card.find("div", class_="card-content")
        assert content is not None, "Card should have .card-content"

        text_section = content.find("div", class_="card-text")
        assert text_section is not None, "Should have .card-text"

        image_section = content.find("div", class_="card-image")
        assert image_section is not None, "Should have .card-image"


@pytest.mark.asyncio
async def test_card_has_json_row(ds_client):
    """Card should have JSON row with entities and votes."""
    response = await ds_client.get("/meetings/minutes")
    soup = BeautifulSoup(response.text, "html.parser")

    card = soup.find("article", class_="page-card")
    if card:
        json_row = card.find("footer", class_="card-json")
        assert json_row is not None, "Card should have .card-json footer"

        entities = json_row.find("div", class_="card-entities")
        assert entities is not None, "Should have .card-entities"

        votes = json_row.find("div", class_="card-votes")
        assert votes is not None, "Should have .card-votes"


@pytest.mark.asyncio
async def test_page_card_css_loaded(ds_client):
    """Page card CSS should be loaded."""
    response = await ds_client.get("/meetings/minutes")
    soup = BeautifulSoup(response.text, "html.parser")

    # Check for CSS link
    css_links = soup.find_all("link", rel="stylesheet")
    css_hrefs = [link.get("href", "") for link in css_links]

    has_card_css = any("page-card" in href for href in css_hrefs)
    assert has_card_css, f"Expected page-card.css to be loaded. Found: {css_hrefs}"
```

- [ ] **Step 2: Run tests**

Run: `pytest tests/test_page_card_template.py -v`

Expected: All tests pass

- [ ] **Step 3: Commit tests**

```bash
git add tests/test_page_card_template.py
git commit -m "test: add page card template tests

Verifies card layout renders correctly for minutes and agendas"
```

---

## Task 9: Final Review and Cleanup

**Files:**
- Review all changed files

- [ ] **Step 1: Run full test suite**

Run: `pytest`

Expected: All tests pass

- [ ] **Step 2: Check for any lint issues**

Run: `ruff check .`

Expected: No new errors

- [ ] **Step 3: Review all changes**

Run: `git log --oneline -10`
Run: `git diff main --stat`

Expected: Clean history with descriptive commits

- [ ] **Step 4: Create summary commit if needed**

If everything looks good, no additional commit needed. Otherwise:

```bash
git add -A
git commit -m "chore: cleanup page card implementation"
```
