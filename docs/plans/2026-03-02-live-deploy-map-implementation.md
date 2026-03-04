# Live Deploy Monitor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a live deploy monitor to the map page that shows popups and a sidebar log when sites deploy, for authenticated users only.

**Architecture:** A Django JSON endpoint returns recently-deployed sites filtered by timestamp. The map page JS polls this endpoint every 10 seconds (auth-gated). On new deploys, Leaflet popups appear with animations and entries are added to a sidebar log.

**Tech Stack:** Django views + JsonResponse, Leaflet.js popups, Tailwind CSS, vanilla JS polling.

---

### Task 1: Backend — Recent Deploys Endpoint

**Files:**
- Test: `tests/test_recent_deploys.py`
- Modify: `pages/views.py`
- Modify: `config/urls.py`

**Step 1: Write the failing tests**

```python
"""Tests for the recent deploys API endpoint."""

import json
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone


class TestRecentDeploys:
    """Test /api/recent-deploys/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def authenticated_client(self):
        user = User.objects.create_user(username="testuser", password="testpass")
        client = Client()
        client.login(username="testuser", password="testpass")
        return client

    @pytest.mark.django_db
    def test_anonymous_returns_403(self, client):
        """Anonymous users get 403."""
        response = client.get("/api/recent-deploys/")
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_authenticated_returns_200(self, authenticated_client):
        """Authenticated users get 200 with JSON array."""
        since = timezone.now().isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert isinstance(data, list)

    @pytest.mark.django_db
    def test_missing_since_uses_now(self, authenticated_client):
        """Missing since param defaults to now (returns empty)."""
        response = authenticated_client.get("/api/recent-deploys/")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == []

    @pytest.mark.django_db
    def test_returns_recent_deploys(self, authenticated_client):
        """Returns sites with deploy stage updated after since."""
        from pages.models import Site

        now = timezone.now()
        # Create a site with a recent deploy
        Site.objects.create(
            subdomain="test.ca",
            name="Test City",
            state="CA",
            lat="37.0",
            lng="-122.0",
            current_stage="deploy",
            deploy_completed=5,
            updated_at=now,
        )
        # Create a site that is NOT deploying
        Site.objects.create(
            subdomain="old.ca",
            name="Old City",
            state="CA",
            lat="38.0",
            lng="-121.0",
            current_stage="fetch",
            updated_at=now,
        )

        since = (now - timedelta(minutes=1)).isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        data = json.loads(response.content)

        assert len(data) == 1
        assert data[0]["subdomain"] == "test.ca"
        assert data[0]["name"] == "Test City"
        assert data[0]["state"] == "CA"
        assert data[0]["lat"] == "37.0"
        assert data[0]["lng"] == "-122.0"
        assert data[0]["deploy_completed"] == 5
        assert "updated_at" in data[0]

    @pytest.mark.django_db
    def test_excludes_old_deploys(self, authenticated_client):
        """Sites updated before since are excluded."""
        from pages.models import Site

        old_time = timezone.now() - timedelta(hours=1)
        Site.objects.create(
            subdomain="old-deploy.ca",
            name="Old Deploy",
            state="CA",
            lat="37.0",
            lng="-122.0",
            current_stage="deploy",
            deploy_completed=3,
            updated_at=old_time,
        )

        since = timezone.now().isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        data = json.loads(response.content)
        assert data == []
```

**Step 2: Run tests to verify they fail**

Run: `just test-file tests/test_recent_deploys.py`
Expected: FAIL — `recent_deploys_view` doesn't exist, URL not found.

**Step 3: Write the view**

Add to `pages/views.py`:

```python
import json
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def recent_deploys_view(request):
    """API endpoint returning recently deployed sites.

    Query params:
        since: ISO timestamp — only return sites updated after this time.
               Defaults to now (returns empty).

    Returns 403 for anonymous users.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=403)

    since_param = request.GET.get("since")
    if since_param:
        since = parse_datetime(since_param)
        if since is None:
            since = timezone.now()
    else:
        since = timezone.now()

    sites = Site.objects.filter(
        current_stage="deploy",
        updated_at__gt=since,
        lat__isnull=False,
        lng__isnull=False,
    )

    data = [
        {
            "subdomain": site.subdomain,
            "name": site.name,
            "state": site.state,
            "lat": site.lat,
            "lng": site.lng,
            "deploy_completed": site.deploy_completed,
            "updated_at": site.updated_at.isoformat() if site.updated_at else None,
        }
        for site in sites
    ]

    return JsonResponse(data, safe=False)
```

**Step 4: Add the URL**

In `config/urls.py`, add the import and URL:

```python
from pages.views import (
    ...
    recent_deploys_view,
)

urlpatterns = [
    ...
    path("api/recent-deploys/", recent_deploys_view, name="recent_deploys"),
    ...
]
```

**Step 5: Run tests to verify they pass**

Run: `just test-file tests/test_recent_deploys.py`
Expected: All 5 tests PASS.

**Step 6: Commit**

```bash
git add tests/test_recent_deploys.py pages/views.py config/urls.py
git commit -m "Add /api/recent-deploys/ endpoint for live deploy monitor"
```

---

### Task 2: Frontend — Add Subdomain to GeoJSON Properties

The frontend needs `subdomain` in each GeoJSON feature to match poll results to markers.

**Files:**
- Modify: `templates/pages/_map_data.html`

**Step 1: Update GeoJSON template**

In `templates/pages/_map_data.html`, add `subdomain` to the properties object:

```javascript
"properties": {
    "subdomain": "{{ site.subdomain|escapejs }}",
    "name": "{{ site.name|escapejs }}",
    "state": "{{ site.state }}",
    "popup": "<a href='https://{{ site.subdomain }}.civic.band'>{{ site.name|escapejs }}, {{ site.state }}</a>",
    "link": "https://{{ site.subdomain }}.civic.band"
}
```

**Step 2: Verify map still works**

Run: `just test`
Expected: All existing tests pass. Manual check: `just serve`, visit `/map`.

**Step 3: Commit**

```bash
git add templates/pages/_map_data.html
git commit -m "Add subdomain property to map GeoJSON features"
```

---

### Task 3: Frontend — Deploy Log Sidebar HTML + CSS

**Files:**
- Modify: `templates/pages/map.html`

**Step 1: Add sidebar and CSS to map template**

In `templates/pages/map.html`, modify the layout to include a sidebar for authenticated users. Replace the `<!-- Full-page map -->` section:

```html
<!-- Full-page map with optional sidebar -->
<div class="flex-1 relative flex">
  <div id="full-map" class="{% if user.is_authenticated %}flex-1{% else %}absolute inset-0{% endif %}"></div>

  {% if user.is_authenticated %}
  <!-- Deploy log sidebar -->
  <div id="deploy-sidebar" class="w-72 bg-white border-l border-gray-200 flex flex-col overflow-hidden">
    <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
      <h2 class="text-sm font-semibold text-gray-700">Deploy Log</h2>
    </div>
    <div id="deploy-log" class="flex-1 overflow-y-auto">
      <p id="deploy-log-empty" class="px-4 py-8 text-sm text-gray-400 text-center">
        Watching for deploys...
      </p>
    </div>
  </div>
  {% endif %}
</div>
```

Add CSS for animations in `{% block extra_head %}`:

```html
{% block extra_head %}
{% if user.is_authenticated %}
<style>
  /* Deploy popup glow animation */
  .deploy-popup .leaflet-popup-content-wrapper {
    animation: deploy-glow 1s ease-in-out 2;
    box-shadow: 0 0 15px rgba(99, 102, 241, 0.6);
  }
  @keyframes deploy-glow {
    0%, 100% { box-shadow: 0 0 5px rgba(99, 102, 241, 0.3); }
    50% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.8); }
  }
  /* Popup fade-out */
  .deploy-popup-fading {
    opacity: 0;
    transition: opacity 0.5s ease-out;
  }
  /* Sidebar entry slide-in */
  .deploy-entry {
    animation: slide-in 0.3s ease-out;
  }
  @keyframes slide-in {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
</style>
{% endif %}
{% endblock %}
```

**Step 2: Verify map still renders**

Run: `just test`
Expected: All tests pass.

**Step 3: Commit**

```bash
git add templates/pages/map.html
git commit -m "Add deploy log sidebar and animation CSS for authenticated users"
```

---

### Task 4: Frontend — Polling and Popup Logic

**Files:**
- Modify: `templates/pages/map.html` (inside `{% block extra_scripts %}`)

**Step 1: Add the deploy monitor script**

After the existing map initialization script in `{% block extra_scripts %}`, add inside `{% if user.is_authenticated %}`:

```javascript
{% if user.is_authenticated %}
<script>
(function() {
  const POLL_INTERVAL = 10000; // 10 seconds
  const POPUP_DURATION = 5000; // 5 seconds
  const FADE_DURATION = 500;   // 0.5 seconds

  let lastPollTime = new Date().toISOString();
  let popupQueue = [];
  let isShowingPopup = false;
  let pollTimer = null;

  // Reference to the map — access from the outer IIFE's closure
  // We need to wait for the map to be ready
  function getMap() {
    const container = document.getElementById('full-map');
    if (container && container._leaflet_id) {
      // Leaflet stores map reference; access via L.Map instances
      // We'll use a different approach: store map ref globally in the map init script
      return window._civicMap;
    }
    return null;
  }

  // Build a GeoJSON layer index by subdomain for fast lookups
  function getMarkerBySubdomain(subdomain) {
    if (!window._civicMarkers) return null;
    let found = null;
    window._civicMarkers.eachLayer(function(layer) {
      if (layer.eachLayer) {
        layer.eachLayer(function(marker) {
          if (marker.feature &&
              marker.feature.properties &&
              marker.feature.properties.subdomain === subdomain) {
            found = marker;
          }
        });
      }
    });
    return found;
  }

  // Add entry to sidebar
  function addSidebarEntry(deploy) {
    const log = document.getElementById('deploy-log');
    const empty = document.getElementById('deploy-log-empty');
    if (empty) empty.remove();

    const entry = document.createElement('div');
    entry.className = 'deploy-entry px-4 py-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition';
    entry.innerHTML = `
      <div class="text-sm font-medium text-gray-900">${deploy.name}</div>
      <div class="text-xs text-gray-500">${deploy.state} · just now</div>
    `;
    entry.dataset.lat = deploy.lat;
    entry.dataset.lng = deploy.lng;
    entry.dataset.subdomain = deploy.subdomain;
    entry.addEventListener('click', function() {
      const map = getMap();
      if (map) {
        map.flyTo([parseFloat(deploy.lat), parseFloat(deploy.lng)], 12);
        const marker = getMarkerBySubdomain(deploy.subdomain);
        if (marker) {
          marker.openPopup();
        }
      }
    });

    // Prepend (newest first)
    log.insertBefore(entry, log.firstChild);
  }

  // Show deploy popup on map
  function showDeployPopup(deploy) {
    const map = getMap();
    if (!map) { processQueue(); return; }

    // If tab is hidden, skip popup, just log to sidebar
    if (document.hidden) {
      addSidebarEntry(deploy);
      processQueue();
      return;
    }

    isShowingPopup = true;
    addSidebarEntry(deploy);

    const lat = parseFloat(deploy.lat);
    const lng = parseFloat(deploy.lng);

    map.flyTo([lat, lng], 10, { duration: 1 });

    // Open popup after pan completes
    setTimeout(function() {
      const popup = L.popup({
        className: 'deploy-popup',
        closeOnClick: false,
        autoClose: false,
      })
        .setLatLng([lat, lng])
        .setContent(`
          <div class="p-1">
            <div style="font-weight:600;font-size:14px;">${deploy.name}</div>
            <div style="color:#6b7280;font-size:12px;">${deploy.state}</div>
            <div style="margin-top:4px;font-size:11px;color:#6366f1;font-weight:500;">
              Deployed
            </div>
          </div>
        `)
        .openOn(map);

      // Fade and close after 5 seconds
      setTimeout(function() {
        const el = popup.getElement();
        if (el) el.classList.add('deploy-popup-fading');
        setTimeout(function() {
          map.closePopup(popup);
          isShowingPopup = false;
          processQueue();
        }, FADE_DURATION);
      }, POPUP_DURATION);
    }, 1000); // Wait for flyTo animation
  }

  // Process popup queue sequentially
  function processQueue() {
    if (popupQueue.length === 0) {
      isShowingPopup = false;
      return;
    }
    const next = popupQueue.shift();
    showDeployPopup(next);
  }

  // Poll for recent deploys
  async function poll() {
    try {
      const url = `/api/recent-deploys/?since=${encodeURIComponent(lastPollTime)}`;
      const response = await fetch(url);

      if (response.status === 403) {
        // Session expired — stop polling
        if (pollTimer) clearInterval(pollTimer);
        return;
      }

      if (!response.ok) return; // Skip this cycle

      const deploys = await response.json();
      lastPollTime = new Date().toISOString();

      if (deploys.length === 0) return;

      // Queue all new deploys
      for (const deploy of deploys) {
        popupQueue.push(deploy);
      }

      if (!isShowingPopup) {
        processQueue();
      }
    } catch (e) {
      // Network error — skip silently, retry next cycle
    }
  }

  // Start polling
  pollTimer = setInterval(poll, POLL_INTERVAL);
})();
</script>
{% endif %}
```

**Step 2: Expose map and markers as globals**

In the existing map initialization script in `map.html`, add after `markers.addTo(map);`:

```javascript
// Expose for deploy monitor
window._civicMap = map;
window._civicMarkers = markers;
```

**Step 3: Run full test suite**

Run: `just test`
Expected: All tests pass.

**Step 4: Commit**

```bash
git add templates/pages/map.html
git commit -m "Add polling, popup, and sidebar logic for live deploy monitor"
```

---

### Task 5: Manual Integration Testing

**Step 1: Create a test deploy in the database**

Using Django shell to simulate a deploy event:

```bash
just shell
```

```python
from django.utils import timezone
from pages.models import Site

# Pick a site with coordinates and simulate a deploy
site = Site.objects.filter(lat__isnull=False).first()
print(f"Testing with: {site.name} ({site.subdomain})")
# Note its current deploy_completed count, then update:
Site.objects.filter(subdomain=site.subdomain).update(
    current_stage='deploy',
    deploy_completed=site.deploy_completed + 1,
    updated_at=timezone.now(),
)
```

**Step 2: Test in browser**

1. Run `just serve`
2. Log in at `/admin/login/`
3. Visit `/map`
4. Verify: within 10 seconds, the map pans to the test site, a glowing popup appears, and a sidebar entry is added
5. Verify: popup fades after 5 seconds
6. Verify: clicking the sidebar entry pans back to the site
7. Log out and visit `/map` — verify no sidebar, no polling (check Network tab)

**Step 3: Reset test data**

```python
Site.objects.filter(subdomain=site.subdomain).update(
    current_stage='',
    deploy_completed=site.deploy_completed,
)
```

**Step 4: Final commit (if any tweaks needed)**

```bash
git add -A && git commit -m "Finalize live deploy monitor"
```
