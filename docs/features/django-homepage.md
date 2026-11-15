# Django Homepage Feature

## Overview

The civic.band homepage is powered by Django with HTMX for dynamic filtering and Leaflet for interactive mapping. It is optimized for getting people to the right municipal site quickly.

## Features

- **Search-first homepage**: Municipality name search, state/province filter, and "Use My Location" are presented before the map.
- **Large interactive map**: Leaflet map with marker clustering and direct links from pins to municipal sites.
- **Compact result cards**: Filtered searches show the top 12 municipalities as direct links, with a link to the full directory.
- **Full directory page**: `/municipalities` provides the complete, paginated, sortable table of municipalities.
- **URL State**: Shareable URLs with filter parameters.
- **Progressive Enhancement**: Search and filtering also work as normal GET forms without JavaScript.

## Architecture

- **Views**:
  - `pages.views.home_view` renders the homepage and returns the `_home_results.html` partial for HTMX requests targeting `#home-results`.
  - `pages.views.municipalities_view` renders `/municipalities` and returns the `_municipalities_table.html` partial for HTMX requests targeting `#municipalities-table-container`.
  - `pages.views.sites_search_view` remains as a compatibility redirect to the homepage.
- **Models**: `pages.models.Site` (read-only from the shared sites database).
- **Templates**:
  - `templates/pages/home.html` (main page)
  - `templates/pages/_hero.html` (compact hero, nav, disclosures)
  - `templates/pages/_finder.html` (search and filters)
  - `templates/pages/_map_section.html` (large map)
  - `templates/pages/_home_results.html` (compact result cards + map data)
  - `templates/pages/_result_card.html` (single municipality card)
  - `templates/pages/municipalities.html` (full directory)
  - `templates/pages/_municipalities_table.html` (paginated table partial)
  - `templates/pages/_map_data.html` (GeoJSON generator)
  - `templates/pages/_nav_social_icons.html` (shared icon-only social links)

## URL Parameters

- `?q=<query>` - Search query
- `?state=<state>` - Filter by state / province
- `?kind=<kind>` - Filter by type (city/county/etc.)
- `?has_finance=1` - Only municipalities with campaign finance data
- `?sort=<field>` - Sort field (pages/updated_at)
- `?page=<n>` - Directory pagination (50 per page)

Examples:
- `https://civic.band/?state=California`
- `https://civic.band/municipalities?q=oakland&page=1`

## Testing

Run tests: `just test`

Relevant tests:
- `tests/test_home_view.py`
- `tests/test_municipalities_view.py`
- `tests/test_pages_views.py`
- `tests/test_site_model.py`

## Deployment

See `docs/deployment/caddyfile-changes.md` for Caddyfile configuration.
