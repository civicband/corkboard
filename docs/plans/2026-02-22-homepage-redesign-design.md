# Homepage Redesign Design Document

**Date:** 2026-02-22
**Status:** Approved
**Author:** Brainstorming session with phildini

## Overview

Redesign the CivicBand homepage to better explain what we do, improve municipality discovery, and provide clear calls-to-action for engagement (newsletter, GitHub, email).

## Problem Statement

The current homepage has three main issues:

1. **Too compact/dense** - Users don't understand what CivicBand is before being presented with search functionality
2. **Municipality finder UX** - Search is not prominent enough, lacks "quick start" entry points
3. **Unclear CTAs** - No clear hierarchy for newsletter signup vs. GitHub contribution vs. email contact

## Goals

### Primary
- Explain what CivicBand is and its value proposition before asking users to search
- Make municipality search more prominent and accessible
- Establish clear CTA hierarchy: Newsletter primary, GitHub/email secondary

### Secondary
- Maintain map visibility to show geographic coverage
- Keep existing HTMX functionality for filtering and search
- Preserve URL-based filtering for direct links

## Design Approach

**Selected Approach:** Traditional Hero + Finder

This approach provides:
- Clear hierarchy: explanation → action
- Prominent search with quick-start options
- Newsletter in hero for maximum visibility
- Map remains visible in results view

## Detailed Design

### Section 1: Hero Section

**Purpose:** Explain CivicBand's mission and value before presenting tools

**Visual Structure:**
- Full-width section with light background (bg-gray-50)
- Max-width container (max-w-7xl) for content
- Generous vertical padding for breathing room

**Content Elements:**

1. **Navigation** (keep current)
   - Top nav: How, Why, RSS, GitHub, Mastodon, Bluesky, Support
   - Consider adding "Skip to finder" link for returning users

2. **Headline** (large, bold, prominent)
   - Primary option: "Searchable Civic Meeting Data Across North America"
   - Alternative: "Track What Your Local Government Is Doing"

3. **Brief Explanation** (visible by default, 2-3 sentences)
   - What CivicBand is
   - Core value proposition
   - Who it's for

4. **Expandable "Learn More"** (tiered content approach)
   - Implementation: HTML `<details>` element or Alpine.js toggle
   - Contains:
     - Detailed mission statement
     - Use cases and examples
     - Who runs it (Raft Foundation link)
   - Links to full "How it works" and "Why?" pages

5. **Newsletter Signup Form** (primary CTA, prominent placement)
   - Email input field
   - "Subscribe" button
   - Privacy policy link
   - Success/error message handling
   - Current Buttondown integration maintained

6. **Secondary CTAs** (below newsletter, less prominent)
   - "Contribute on GitHub" button/link
   - "Email us: hello@civic.band" link
   - Visually distinct from primary CTA but accessible

7. **Stats Bar** (bottom of hero or top of next section)
   - "Tracking X pages across Y municipalities"
   - Optionally: "Z municipalities with finance data"

### Section 2: Municipality Finder

**Purpose:** Help users find their municipality quickly and easily

**Visual Structure:**
- Full-width section with distinct background (white or light gray contrast)
- Clear visual separation from hero (border or spacing)
- Padding for breathing room

**Components:**

1. **Section Header**
   - Title: "Find Your Municipality" or "Search Meeting Data"
   - Optional subhead: "Search XXX cities and counties"

2. **Primary Search Input** (large and prominent)
   - Larger text size (text-lg or text-xl)
   - Placeholder: "Search by city, town, or county name..."
   - Search icon for visual clarity
   - Auto-complete/instant search via HTMX (existing behavior)
   - Shows results as you type

3. **Quick-Start Options** (below search box)

   **a) "Use My Location" Button**
   - Requests browser geolocation permission
   - Calculates nearest municipalities using lat/lng from Site model
   - Loads nearby municipalities into results
   - Graceful fallback if permission denied

   **b) Popular/Featured Municipalities** (5-6 buttons)
   - Examples: "San Francisco, CA", "New York, NY", "Chicago, IL"
   - Clicking instantly loads that municipality's data
   - Implementation: Can be static (hardcoded) or dynamic (based on traffic)
   - Consider making configurable via Django settings

4. **Advanced Filters** (collapsible/toggleable, initially hidden)
   - "Show filters" button to reveal panel
   - When expanded:
     - State dropdown
     - Type/kind dropdown
     - "Has finance data" checkbox
   - Same HTMX behavior as current implementation
   - "Clear filters" button when any filters active

**Interaction Flow:**
- **Empty state:** Search box + quick-start buttons only
- **After search/selection:** Results section appears below
- **Filters:** Only visible when user expands filter panel

### Section 3: Map & Results Display

**Purpose:** Show matching municipalities and geographic coverage

**Visual Structure:**
- Appears below finder after user searches/selects
- Responsive two-column grid
- Desktop: 2/3 table, 1/3 map (lg:col-span-2 / lg:col-span-1)
- Mobile: Map first (condensed height), table below

**Components:**

1. **Results Header**
   - Count: "Showing X of Y municipalities"
   - Active filters display (chips/badges)
   - "Clear all" button if filters active

2. **Map Column** (right side on desktop)
   - Keep current Leaflet map with marker clustering
   - Sticky positioning on desktop (stays visible while scrolling)
   - Shows all matching results from current filter/search
   - Popup on marker click (current behavior)
   - Height: ~600px desktop, ~300px mobile

3. **Table Column** (left side on desktop)
   - Current table structure:
     - Municipality name (links to subdomain)
     - State
     - Type/Kind
     - Page count
     - Finance badge (if has_finance_data)
   - Sorted by pages descending (current behavior)
   - Responsive: cards on mobile, table on desktop

4. **Empty States**
   - No search yet: Emphasize quick-start options
   - No results: "No municipalities found. Try different search terms or filters."
   - Default map view: Centered on US/Canada

5. **Filter Controls**
   - Moved from always-visible to collapsible panel
   - Toggle button: "Show filters" / "Hide filters"
   - When expanded: state dropdown, kind dropdown, finance checkbox
   - Filters update results via HTMX (preserve existing implementation)

## Technical Implementation

### Django Backend

**Views (`pages/views.py`):**
- `home_view`: No major changes needed
  - Continue providing: sites list, aggregate stats, states/kinds for filters
- `sites_search_view`: No changes needed
  - HTMX endpoint for filtering remains unchanged

**Models:**
- No changes to `Site` model
- Already has lat/lng fields for geolocation feature

### Templates

**Structure:**
- Refactor `templates/pages/home.html` into clear sections:
  1. Hero section (new)
  2. Finder section (refactored search + new quick-start)
  3. Results section (existing map + table, conditional display)

**Partials:**
- Keep `templates/pages/_sites_table_only.html` for HTMX updates
- Consider extracting map template partial if not already separate

### New Features to Build

1. **Geolocation Feature**
   - JavaScript: Browser Geolocation API
   - Calculate nearest municipalities using Site.lat/lng
   - Populate results with nearby sites (top 10-20?)
   - Error handling: permission denied, timeout, unsupported
   - Fallback: Show message, allow manual search

2. **Quick-Start Buttons**
   - Hardcoded or configurable list of 5-6 popular municipalities
   - Could be Django setting: `HOMEPAGE_FEATURED_CITIES`
   - Clicking triggers same HTMX search as typing name
   - Implementation: Each button has data attribute with subdomain/name

3. **Expandable "Learn More"**
   - Option 1: HTML `<details>` element (no JS, accessible)
   - Option 2: Alpine.js or vanilla JS toggle
   - Content: Extended mission text, use cases, links to How/Why pages

4. **Filter Toggle Panel**
   - Collapsible panel (hidden by default)
   - Toggle with Alpine.js or vanilla JS
   - Filters inside keep existing HTMX behavior
   - State persisted in URL params (existing behavior)

### JavaScript Updates

**Existing (preserve):**
- Leaflet map initialization
- HTMX event handlers for map updates
- Clear filters button logic

**New:**
- Geolocation handler for "Use My Location"
- Filter panel show/hide toggle
- Details/accordion for "Learn More" (if not using `<details>`)

### Styling

**Approach:** Use existing Tailwind CSS classes

**Key Styling Considerations:**
- Hero section: Larger text sizes, more vertical padding
- Search input: Prominent sizing (larger than current), clear focus states
- Quick-start buttons: Pill buttons or card-style buttons
- Visual hierarchy: Hero > Finder > Results
- Consistent spacing between sections

### Backwards Compatibility

**Maintain:**
- URL query parameters (`?q=`, `?state=`, `?kind=`, `?has_finance=`)
- Direct links to filtered views
- HTMX partial updates
- Existing HTMX target elements

### Accessibility

**Requirements:**
- Keyboard navigation for all interactive elements
- ARIA labels for search input, filters, buttons
- Focus management for expandable sections
- Geolocation: Clear messaging when permission denied
- Form labels (visible or sr-only as appropriate)
- Adequate color contrast
- Skip links for keyboard users

## Content Decisions Needed

Before implementation, decide on:

1. **Hero headline** - Which option to use?
2. **Brief explanation text** - Specific wording (2-3 sentences)
3. **Expanded "Learn More" content** - What details to include?
4. **Quick-start municipalities** - Which 5-6 to feature?
5. **Geolocation behavior** - How many nearest municipalities to show?

## Success Metrics

Post-launch, track:
- Newsletter signup conversion rate
- Municipality search engagement (% of visitors who search)
- Quick-start button usage vs. manual search
- "Use My Location" adoption rate
- Bounce rate changes
- Time to first interaction

## Migration Strategy

**Approach:** Full replacement, not gradual rollout

1. Implement new template structure
2. Test locally with existing data
3. Deploy to production
4. Monitor analytics for issues
5. Iterate based on user feedback

**Rollback:** Keep old template as `home_old.html` backup for first week

## Open Questions

- Should "Use My Location" be a button or auto-detect on page load?
- How many municipalities should geolocation return (10? 20?)?
- Should quick-start municipalities be configurable or hardcoded?
- Should we add a screenshot/preview image in the hero section?

## Next Steps

1. Create implementation plan (invoke writing-plans skill)
2. Draft specific copy for hero section
3. Select featured municipalities for quick-start
4. Implement in phases:
   - Phase 1: Hero section + basic finder
   - Phase 2: Geolocation feature
   - Phase 3: Polish and analytics
