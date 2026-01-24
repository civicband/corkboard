# Django-Powered Homepage Design

**Date:** 2026-01-24
**Status:** Approved
**Goal:** Replace Datasette-powered civic.band homepage with Django + HTMX for better search/filter/map integration

## Problem Statement

The current civic.band homepage uses Datasette to serve the sites directory. While functional, this approach has limitations:

1. **Map visibility/integration** - The cluster map doesn't update dynamically with search/filter controls
2. **Feature limitations** - Hard to implement real-time filtering and bidirectional map ↔ table synchronization
3. **Template constraints** - Datasette's Jinja templates limit UX possibilities

Since the sites listing is purely for discovery (not API/query usage), we don't need Datasette's power at the root domain. The real value of Datasette is in individual municipality subdomains (berkeley.ca.civic.band, etc.), which remain unchanged.

## Architecture Overview

### Current State
- `civic.band/` → Datasette (ports 40001/40002) serving sites.db
- Caddyfile reverse proxies to these ports
- Individual subdomains → Django ASGI with dynamic Datasette instances

### New State
- `civic.band/` → Django view serving the homepage
- Caddyfile reverse proxies to Django (ports 8000/8001 via anubis)
- Individual subdomains → Same Django ASGI middleware (unchanged)

### Key Changes
- Update Caddyfile to route root domain to Django instead of sites_datasette
- Remove sites_datasette services from docker-compose.yml
- Remove datasette-homepage-table and datasette-cluster-map dependencies
- Remove custom Datasette templates in `templates/sites-database/`

### What Stays Unchanged
- sites.db location (`../civic-band/sites.db`) and structure
- Subdomain routing logic in `datasette_by_subdomain.py`
- All individual municipality Datasette instances
- Existing Django pages (/how.html, /why.html, etc.)
- Blue/green deployment pattern

## Data Layer

### Database Configuration

Add secondary database connection in Django settings:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'civic.db',
    },
    'sites': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent / 'civic-band' / 'sites.db',
    }
}
```

### Site Model

```python
class Site(models.Model):
    subdomain = models.CharField(primary_key=True)
    name = models.CharField()
    state = models.CharField()
    country = models.CharField()
    kind = models.CharField()
    pages = models.IntegerField()
    last_updated = models.DateTimeField()
    lat = models.CharField()
    lng = models.CharField()
    popup = models.JSONField()

    class Meta:
        db_table = 'sites'
        database = 'sites'
        managed = False  # Don't let Django manage this table
```

**Rationale:**
- Read-only access (sites.db managed externally)
- Use Django ORM for filtering/querying
- Leverages Django's query optimization
- Easy to add annotations and aggregations

## Views & URL Structure

### URLs

```python
urlpatterns = [
    path('', home_view, name='home'),
    path('sites/search/', sites_search_view, name='sites_search'),  # HTMX endpoint
    # ... existing pages
]
```

### Main View (home_view)

- Queries all sites from sites.db
- Reads filter params from URL: `?q=<search>&state=<state>&kind=<kind>&sort=<field>`
- Calculates aggregate stats (total sites, total pages)
- Renders full page with table + map
- Defaults to sorting by pages descending

### HTMX Partial View (sites_search_view)

- Accepts same query params as home_view
- Filters sites based on params
- Returns HTML fragment containing:
  - Updated table rows
  - GeoJSON data for map (as `<script>` tag with custom event trigger)
  - Search stats ("Showing X of Y sites")
- No full page layout, just the table body + map data

**Rationale:**
- Initial load sends full page (SEO, no-JS fallback)
- HTMX requests only swap changed parts
- Server controls all filtering logic (scales as data grows)
- Simple to add pagination later if needed

## Templates & Frontend

### Template Structure

```
templates/pages/
  base.html          # Shared layout
  home.html          # Main homepage template
  _sites_table.html  # Partial: table rows (for HTMX swaps)
  _map_data.html     # Partial: GeoJSON + event trigger
```

### home.html Layout

- Header section (title, stats, newsletter signup)
- Search/filter toolbar
  - Search input (HTMX triggers on input with debounce)
  - State dropdown
  - Kind filters (All/Cities/Counties)
  - Sort buttons (Most pages/Recently updated)
- Two-column layout:
  - Left: Interactive map (Leaflet)
  - Right: Filtered table
- Map and table update together

### HTMX Strategy

```html
<!-- Search input -->
<input
  type="text"
  name="q"
  hx-get="/sites/search/"
  hx-push-url="true"
  hx-trigger="keyup changed delay:300ms"
  hx-target="#sites-table"
  hx-include="[name='state'], [name='kind'], [name='sort']"
/>

<!-- Filters/sort -->
<select
  name="state"
  hx-get="/sites/search/"
  hx-push-url="true"
  hx-target="#sites-table"
  hx-include="[name='q'], [name='kind'], [name='sort']"
/>
```

All controls:
- Update the same target (`#sites-table`)
- Preserve each other's state via URL params
- Push URL changes for shareable links

### Progressive Enhancement

- Without JS: Form submits work as regular GET requests
- With JS: HTMX intercepts and swaps content
- Map hidden/degraded without JS

## Map Implementation

### Libraries

- Leaflet.js (core mapping)
- Leaflet.markercluster (cluster markers when zoomed out)
- OpenStreetMap tiles (free, no API key needed)

### Map Behavior

```javascript
// Initialize map once on page load
const map = L.map('sites-map').setView([39.8283, -98.5795], 4); // Center on US

// Add tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors'
}).addTo(map);

// Marker cluster group
const markers = L.markerClusterGroup();

// Listen for HTMX updates
document.body.addEventListener('sites:updated', (event) => {
  const geojson = event.detail;

  // Clear existing markers
  markers.clearLayers();

  // Add new markers from filtered data
  L.geoJSON(geojson, {
    onEachFeature: (feature, layer) => {
      layer.bindPopup(feature.properties.popup);
      layer.on('click', () => {
        window.location.href = feature.properties.link;
      });
    }
  }).addTo(markers);

  markers.addTo(map);

  // Auto-zoom to show all markers
  if (markers.getLayers().length > 0) {
    map.fitBounds(markers.getBounds(), { padding: [50, 50] });
  }
});
```

### GeoJSON Format

Server generates GeoJSON in `_map_data.html` partial:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [lng, lat]
      },
      "properties": {
        "name": "Berkeley",
        "popup": "<a href='https://berkeley.ca.civic.band'>Berkeley, CA</a>",
        "link": "https://berkeley.ca.civic.band"
      }
    }
  ]
}
```

**Note:** GeoJSON uses `[lng, lat]` order, not `[lat, lng]`

**Rationale:**
- Cluster plugin prevents overwhelming map with 900+ markers
- Auto-zoom keeps filtered results in view
- Server generates GeoJSON (clean separation)
- Click marker → navigate to municipality site

## Styling & UI

### CSS Approach

Continue using Tailwind CSS (already in use via CDN)

### Layout

```html
<!-- Two-column responsive layout -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
  <!-- Map column (left on desktop, top on mobile) -->
  <div class="order-2 lg:order-1">
    <div id="sites-map" class="h-96 lg:h-[600px] rounded-lg shadow-lg"></div>
  </div>

  <!-- Table column (right on desktop, bottom on mobile) -->
  <div class="order-1 lg:order-2">
    <div id="sites-table-container">
      {% include 'pages/_sites_table.html' %}
    </div>
  </div>
</div>
```

### Key UI Elements

- Search bar: Large, prominent (similar to current Datasette template)
- Filter chips: Active state clearly visible
- Table: Compact, clickable rows
- Loading states: HTMX provides `htmx-request` class automatically
- Mobile-friendly: Map collapses above table on small screens

### Preserve Existing Styles

Reuse good parts from `templates/sites-database/_table-sites-sites.html`:
- Search input styling
- Filter/sort button styles
- Table row hover effects
- Umami analytics event tracking

### Accessibility

- Proper ARIA labels on search/filter controls
- Keyboard navigation for filters
- Loading indicators for screen readers
- Semantic HTML (actual form elements)

## URL State Management

### URL Parameter Schema

```
/?q=berkeley&state=CA&kind=city&sort=pages
/?q=county&kind=county&sort=last_updated
/?state=NY
```

### HTMX Configuration

All filter controls use `hx-push-url="true"` to update browser URL, enabling:
- Direct links to filtered views
- Browser back/forward navigation
- Shareable searches
- Bookmarkable results
- SEO-friendly filtered pages

### View Implementation

Both `home_view` and `sites_search_view` read the same params from `request.GET` and apply identical filtering logic. The home view renders the full page; the search view returns HTML fragments.

## Error Handling & Edge Cases

### Database Connection Issues

```python
try:
    sites = Site.objects.using('sites').all()
except Exception as e:
    logger.error(f"Failed to load sites: {e}")
    return render(request, 'pages/home_error.html')
```

### Empty Search Results

- Show "No municipalities match your search" message
- Suggest clearing filters
- Map shows empty state or zooms to default view

### Missing Coordinates

Skip sites without lat/lng when generating GeoJSON:

```python
features = [
    {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(s.lng), float(s.lat)]},
        "properties": {...}
    }
    for s in sites
    if s.lat and s.lng  # Skip if missing coordinates
]
```

### HTMX Failures

- User can still use browser back/forward
- Form works as regular GET form (progressive enhancement)
- Add `hx-indicator` for loading spinners

### Performance

- Query optimization: `.only('subdomain', 'name', 'state', 'kind', 'pages', 'last_updated', 'lat', 'lng')`
- Cache aggregate stats (total sites, total pages) since they change infrequently
- Consider adding database indexes if queries slow down (limited by read-only DB)

### Edge Cases

- Sites with special characters in name/subdomain (already handled in DB)
- Very long municipality names (CSS truncation with ellipsis)
- Browser without JavaScript support (form submission fallback works)

## Migration & Deployment Strategy

### Phase 1: Build Django Implementation

1. Add sites database config to settings
2. Create Site model in pages app
3. Build new home_view and sites_search_view
4. Create templates with HTMX + Leaflet
5. Test locally (Django dev server already bypasses subdomain routing)

### Phase 2: Update Infrastructure

1. Remove sites_datasette services from docker-compose.yml
2. Update Caddyfile:
   ```
   civic.band {
       import subdomain-log civic.band
       import block_brazilians
       root * static
       route {
           file_server /how.html
           file_server /why.html
           file_server /privacy.html
           file_server /rss.xml
           reverse_proxy * 127.0.0.1:8000 127.0.0.1:8001 {  # Django instead of 40001/40002
               import health-proxy
           }
       }
   }
   ```
3. Remove datasette-homepage-table and datasette-cluster-map from dependencies

### Phase 3: Deploy with Blue/Green

1. Build new Django image with updated code
2. Deploy to green environment
3. Test civic.band routing
4. Flip Caddy to green
5. Monitor for issues
6. Remove blue if successful

### Rollback Plan

- Keep old docker-compose config in git
- Can quickly revert Caddyfile to point back to ports 40001/40002
- Blue/green gives instant rollback if needed

## Benefits

1. **Integrated filtering** - Map and table update together seamlessly
2. **Scales beyond 1000 sites** - Server-side filtering handles growth
3. **Shareable views** - URL params enable direct links to filtered results
4. **Full control** - No Datasette template constraints
5. **Simpler architecture** - One less service to run (sites_datasette)
6. **Progressive enhancement** - Works without JavaScript
7. **Maintains existing value** - Individual municipality Datasette instances unchanged

## Trade-offs

- Adds code to maintain (vs. plugin configuration)
- Requires HTMX learning curve
- Loses Datasette's built-in JSON API for sites listing (acceptable since it's not used)
