# Django Homepage Feature

## Overview

The civic.band homepage is powered by Django with HTMX for dynamic filtering and Leaflet for interactive mapping.

## Features

- **Search**: Full-text search across municipality name, subdomain, and state
- **Filters**: Filter by state and type (city/county)
- **Sorting**: Sort by pages or last updated
- **Interactive Map**: Leaflet map with marker clustering
- **URL State**: Shareable URLs with filter parameters
- **Progressive Enhancement**: Works without JavaScript

## Architecture

- **Views**: `pages.views.home_view` and `pages.views.sites_search_view`
- **Models**: `pages.models.Site` (read-only from sites.db)
- **Templates**:
  - `templates/pages/home.html` (main page)
  - `templates/pages/_sites_table.html` (HTMX partial)
  - `templates/pages/_map_data.html` (GeoJSON generator)

## URL Parameters

- `?q=<query>` - Search query
- `?state=<state>` - Filter by state
- `?kind=<kind>` - Filter by type (city/county)
- `?sort=<field>` - Sort field (pages/last_updated)

Example: `https://civic.band/?state=CA&kind=city&sort=pages`

## Testing

Run tests: `just test`

Integration tests:
- `tests/test_home_view.py`
- `tests/test_sites_search_view.py`
- `tests/test_site_model.py`

## Deployment

See `docs/deployment/caddyfile-changes.md` for Caddyfile configuration.
