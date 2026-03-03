# Live Deploy Monitor on Map Page

## Overview

A mode on the map page where, for logged-in users only, the map dynamically shows site details whenever a deployment event is detected. Includes a rolling deploy log sidebar.

## Backend

### Polling Endpoint

**`GET /api/recent-deploys/?since=<timestamp>`** (login required)

- Accepts a `since` ISO timestamp query parameter
- Returns sites where `current_stage = 'deploy'` and `updated_at > since`
- Returns 403 for anonymous users
- Response format:

```json
[
  {
    "subdomain": "berkeley.ca",
    "name": "Berkeley",
    "state": "CA",
    "lat": 37.87,
    "lng": -122.27,
    "deploy_completed": 44058,
    "updated_at": "2026-03-02T14:30:00Z"
  }
]
```

## Frontend

All frontend features are auth-gated via `{% if user.is_authenticated %}` — anonymous users see the normal static map with zero extra JS or network requests.

### Polling & State

- Polls `/api/recent-deploys/?since=<lastPollTime>` every 10 seconds
- `lastPollTime` initialized to page load time, updated after each poll
- Every site in the response is a new deploy event — no client-side diffing needed

### Popup Behavior

When a deploy event arrives:

1. Find the marker on the map by matching `subdomain` to the GeoJSON feature
2. Pan the map to center on that marker (smooth animation)
3. Open a Leaflet popup with site details: name, state, kind, deploy timestamp
4. Apply a glow/pulse CSS animation on the popup as visual flourish
5. After 5 seconds, auto-close the popup with a fade-out transition

Multiple deploys in a single poll response are queued and shown sequentially (5 seconds each).

### Deploy Log Sidebar

- Right-side panel, visible only for authenticated users
- Starts empty with a "Deploy Log" heading
- Each entry: site name, state, relative timestamp ("just now", "2m ago")
- New entries prepend to the top (newest first)
- Scrollable if the list grows long
- Clicking an entry pans the map to that site and opens its popup
- Subtle slide-in/fade-in animation for new entries
- Styled with existing Tailwind CSS patterns

## Error Handling & Edge Cases

- **Network errors:** Skip silently, retry on next 10-second cycle
- **Session expiry (403):** Stop polling entirely, no redirect or disruptive UI
- **Empty response:** No-op
- **Tab not visible:** Log events to sidebar only, skip popup animations. No replay queue when returning to tab.

## Technology

- Leaflet popups and map panning (already in use)
- CSS animations for glow/pulse and fade-out
- Tailwind CSS for sidebar styling
- Vanilla JS polling (no new libraries)
- Django `@login_required` view returning JSON

## Non-Goals

- No WebSocket or SSE infrastructure
- No persistence of deploy log across page reloads
- No deploy history beyond the current session
- No notifications for non-deploy pipeline stage changes
