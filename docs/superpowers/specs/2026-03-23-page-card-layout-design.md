# Page Card Layout Design

**Date:** 2026-03-23
**Status:** Approved
**Scope:** Transform meeting minutes and agenda page table views into card-style displays

## Overview

Replace the current table row display for meeting pages (minutes and agendas) with a card-based layout. Each page becomes a card with structured sections for metadata, content (OCR text + image), and extracted data (entities + votes).

## Card Structure

Each card has three rows:

### 1. Metadata Row

**Layout:** Flexbox row with left group and right group

**Left group (separated by `·`):**
- ID (muted grey text)
- Meeting name (bold)
- Date (normal weight)

**Right group:**
- Type badge: "MINUTES" (blue) or "AGENDA" (green) pill
- Page badge: "Page X" grey pill

**Behavior:**
- ID and meeting name both link to the row detail page (provides two click targets for navigation)
- ID link: subtle, muted styling
- Meeting name link: bold, primary link styling
- Bottom border separates from content row

### 2. Content Row

**Layout:** Flexbox row, 60/40 split on desktop

**Left side (60%): OCR Text**
- Displays `text` field content
- Max height ~150px with CSS overflow hidden
- Gradient fade at bottom indicating truncation
- "Show more" link expands to full text
- "Show less" link appears when expanded

**Right side (40%): Page Image**
- Thumbnail display of `page_image`
- Click/tap expands image (inline expand or lightbox)
- Close via click outside or "×" button

### 3. JSON Extraction Row

**Layout:** Flexbox row, 50/50 split

**Left side (50%): Entities**
- Renders `entities_json` using existing `.entity-chip` styles
- Shows persons, organizations, locations as colored chips
- Chips link to filtered search results

**Right side (50%): Votes**
- Renders `votes_json` using existing `.vote-box` styles
- Color-coded by outcome (green passed, yellow contested, red failed)
- Shows motion details and individual votes

**Separator:** Top border separates from content row

## Responsive Behavior

### Desktop (>= 768px)
- Card height: ~300-400px
- Side-by-side layouts for content and JSON rows
- Multiple cards visible on screen

### Mobile (< 768px)
- Single column layout
- Content row: Text full-width, image as small thumbnail (48px) floated right
- Tapping thumbnail expands image inline below text (full-width)
- JSON row: Stacks vertically (entities above votes)

## Visual Styling

Following existing project design system:

**Card container:**
- Background: white
- Border: `1px solid #e1ecf4`
- Border radius: `8px`
- Box shadow on hover (matches `.meeting-item` pattern)
- Margin between cards: `1rem`

**Type badges:**
- Minutes: `#007bff` (blue) background, white text
- Agenda: `#28a745` (green) background, white text
- Border radius: pill shape
- Font size: small, uppercase

**Page badge:**
- Background: `#e9ecef` (light grey)
- Text: `#6c757d` (medium grey)
- Border radius: pill shape

**Text truncation:**
- Gradient fade: transparent to white over bottom 20px
- "Show more" link: `#007bff` blue

## Template Implementation

### File Structure

```
templates/datasette/
├── _page_card.html              # NEW: shared card partial
├── table-meetings-minutes.html  # MODIFY: use cards instead of table
├── table-meetings-agendas.html  # MODIFY or CREATE: use cards
```

### Card Partial (`_page_card.html`)

```html
<article class="page-card" data-type="{{ document_type }}">
  <header class="card-metadata">
    <div class="card-meta-left">
      <a href="{{ row_url }}" class="card-id">ID: {{ row.id }}</a>
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
      <div class="card-text-content">{{ rendered_text }}</div>
      <button class="card-text-toggle" aria-expanded="false">Show more</button>
    </div>
    <div class="card-image">
      {{ rendered_image }}
    </div>
  </div>

  <footer class="card-json">
    <div class="card-entities">{{ rendered_entities }}</div>
    <div class="card-votes">{{ rendered_votes }}</div>
  </footer>
</article>
```

### Table Template Changes

Replace table iteration with card iteration:

```html
<div class="page-cards">
  {% for row in rows %}
    {% include "_page_card.html" with row=row document_type="minutes" %}
  {% endfor %}
</div>
```

## Plugin Integration

Existing Datasette plugins continue to render their columns:

| Plugin | Column | Rendered Output |
|--------|--------|-----------------|
| `page_image.py` | `page_image` | `<img>` tag with CDN URL |
| `json_columns.py` | `entities_json` | Entity chips with search links |
| `json_columns.py` | `votes_json` | Vote boxes with details |
| `date_link.py` | `date` | Linked date text |

The card partial acts as a layout wrapper, positioning the plugin-rendered output within the card structure. No changes to plugin logic required.

## Interactions

### Image Expand
- **Trigger:** Click/tap on thumbnail
- **Desktop:** Inline expand within card or modal lightbox
- **Mobile:** Inline expand below text, full-width
- **Close:** Click outside, "×" button, or Escape key

### Text Expand
- **Trigger:** Click "Show more" link
- **Behavior:** Remove max-height constraint, show full text
- **Toggle:** Link changes to "Show less"
- **Implementation:** CSS + minimal JS, or `<details>` element

### Card Navigation
- **Meeting name:** Links to row detail page
- **Entity chips:** Link to filtered search results
- **ID:** Links to row detail page

## CSS Classes

New classes to add to the stylesheet:

```css
/* Card container */
.page-cards { }
.page-card { }
.page-card:hover { }

/* Metadata row */
.card-metadata { }
.card-meta-left { }
.card-meta-right { }
.card-id { }
.card-meeting { }
.card-date { }
.card-separator { }
.card-type-badge { }
.card-type-minutes { }
.card-type-agenda { }
.card-page-badge { }

/* Content row */
.card-content { }
.card-text { }
.card-text-content { }
.card-text.expanded { }
.card-text-toggle { }
.card-image { }
.card-image.expanded { }

/* JSON row */
.card-json { }
.card-entities { }
.card-votes { }

/* Responsive */
@media (max-width: 767px) {
  .page-card { }
  .card-content { }
  .card-json { }
}
```

## Accessibility

- Semantic HTML: `<article>`, `<header>`, `<footer>`
- ARIA attributes on expand/collapse buttons
- Keyboard navigation for expand interactions
- Focus management when expanding images
- Sufficient color contrast for badges

## Out of Scope

- Changes to detail pages (row view)
- Changes to search result rendering in `search_all.html`
- New filtering or sorting capabilities
- Changes to the underlying data model

## Dependencies

- Existing Datasette plugin system
- Existing CSS design system
- No new external libraries required
