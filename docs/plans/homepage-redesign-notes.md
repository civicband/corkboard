# Homepage Redesign Notes

## Implementation Date
2026-02-22

## Changes Made

### Structure
- Split homepage into three sections: Hero, Finder, Results
- Extracted partials for better organization:
  - `_navigation.html` - Top nav links
  - `_hero.html` - Hero section with headline, newsletter, CTAs
  - `_finder.html` - Search input, quick-start buttons, filters
  - `_results.html` - Map and table layout
  - `_sites_table_only.html` - Existing table partial (unchanged)
  - `_map_data.html` - Existing map data partial (unchanged)

### New Features
1. **Hero Section**
   - Large headline explaining CivicBand's purpose
   - Expandable "Learn more" details section
   - Newsletter signup form (primary CTA)
   - Secondary CTAs (GitHub, Email)
   - Stats bar showing total pages and municipalities

2. **Municipality Finder**
   - Larger, more prominent search input
   - "Use My Location" button with geolocation API
   - Quick-start buttons for popular municipalities (Oakland, Berkeley, SF, Chicago, NY)
   - Collapsible advanced filters (hidden by default)

3. **Geolocation Feature**
   - Browser Geolocation API integration
   - Calculates nearest municipality using Haversine formula
   - Error handling for permission denial, timeout, etc.

### Technical Details

**JavaScript Functions:**
- `loadMarkers(geojson)` - Loads municipality markers on map
- `findNearestMunicipalities(lat, lng)` - Finds closest municipality to user
- `calculateDistance(lat1, lon1, lat2, lon2)` - Haversine distance formula
- Filter toggle handler
- Quick-start button click handlers
- Clear filters button visibility handler

**Preserved Functionality:**
- HTMX search and filter updates
- URL query parameter support
- Map clustering and interaction
- Existing analytics events

### Content Decisions Made

1. **Hero headline:** "Searchable Civic Meeting Data Across North America"
2. **Quick-start municipalities:** Oakland, Berkeley, San Francisco, Chicago, New York
3. **Geolocation behavior:** Shows single nearest municipality
4. **Learn more content:** Mission statement, use cases, Raft Foundation link

### Browser Compatibility

Tested on:
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)

Geolocation requires HTTPS in production (works on localhost for development).

### Rollback Plan

If issues arise:
1. Old template preserved as `templates/pages/home_old.html`
2. To rollback: Copy `home_old.html` back to `home.html`
3. Run: `git checkout HEAD~1 templates/pages/home.html`

### Future Improvements

Potential enhancements:
- Make quick-start municipalities configurable via Django settings
- Add server-side geolocation endpoint for better accuracy
- Add "Skip to finder" link in hero for returning users
- Add screenshot/preview image in hero section
- Consider A/B testing different headlines
