# Template Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor `templates/pages/` so all pages share a navbar and footer via template inheritance, with a unified content page layout.

**Architecture:** Enhance `base.html` with navbar/footer blocks. Create `_content_page.html` as an intermediate template for content pages. Convert standalone pages (how, why, researchers) to extend `_content_page.html`. Homepage overrides the navbar block with its hero section. Delete legacy duplicates.

**Tech Stack:** Django templates, Tailwind CSS (CDN), existing test suite (pytest + pytest-django)

---

### Task 1: Restyle `_navigation.html` as a Standalone Top Bar

The current `_navigation.html` is styled for a dark hero background. It needs to work as a standalone top bar with its own background when used outside the hero.

**Files:**
- Modify: `templates/pages/_navigation.html`

- [ ] **Step 1: Rewrite `_navigation.html` as a standalone nav bar**

Replace the contents of `templates/pages/_navigation.html` with:

```html
<!-- Navigation -->
<nav class="bg-indigo-700 border-b border-indigo-800" aria-label="Main navigation">
  <div class="mx-auto max-w-7xl px-4 py-3 sm:px-6 lg:px-8">
    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
      <a href="/" class="text-white font-bold text-lg mr-4" data-umami-event="nav" data-umami-event-target="home">CivicBand</a>
      <ul class="flex flex-wrap gap-2 text-sm">
        <li><a href="/how.html" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="how">How it works</a></li>
        <li><a href="/why.html" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="why">Why?</a></li>
        <li><a href="/researchers" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="researchers">For Researchers</a></li>
        <li><a href="/rss.xml" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="rss">RSS Feed</a></li>
        <li><a href="https://github.com/civicband" target="_blank" rel="noopener noreferrer" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="github">GitHub <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
        <li><a href="https://sfba.social/@civicband" target="_blank" rel="noopener noreferrer me" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="mastodon">Mastodon <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
        <li><a href="https://bsky.app/profile/civic.band" target="_blank" rel="noopener noreferrer me" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="nav" data-umami-event-target="bluesky">Bluesky <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
        <li><a href="https://opencollective.com/civicband" target="_blank" rel="noopener noreferrer" class="bg-amber-500 text-gray-900 hover:bg-amber-400 px-2 py-0.5 rounded font-medium transition" data-umami-event="nav" data-umami-event-target="donate">Donate! <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
      </ul>
    </div>
  </div>
</nav>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/_navigation.html
git commit -m "Restyle navigation as standalone top bar with indigo background"
```

---

### Task 2: Update `_hero.html` to Inline Its Own Nav Links

The hero currently `{% include %}`s `_navigation.html`, but since we restyled that partial to have its own indigo background wrapper, it will look wrong nested inside the hero's gradient. The hero needs its own inline nav that matches its dark gradient background.

**Files:**
- Modify: `templates/pages/_hero.html`

- [ ] **Step 1: Replace the `{% include %}` with inline nav links**

In `templates/pages/_hero.html`, replace line 6:

```django
    {% include 'pages/_navigation.html' %}
```

with:

```html
    <!-- Navigation (inline for hero context) -->
    <nav class="mb-2 pb-2 border-b border-indigo-500/40" aria-label="Main navigation">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <a href="/" class="text-white font-bold text-lg mr-4">CivicBand</a>
        <ul class="flex flex-wrap gap-2 text-sm">
          <li><a href="/how.html" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="how">How it works</a></li>
          <li><a href="/why.html" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="why">Why?</a></li>
          <li><a href="/researchers" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="researchers">For Researchers</a></li>
          <li><a href="/rss.xml" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="rss">RSS Feed</a></li>
          <li><a href="https://github.com/civicband" target="_blank" rel="noopener noreferrer" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="github">GitHub <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
          <li><a href="https://sfba.social/@civicband" target="_blank" rel="noopener noreferrer me" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_social" data-umami-event-platform="mastodon">Mastodon <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
          <li><a href="https://bsky.app/profile/civic.band" target="_blank" rel="noopener noreferrer me" class="text-white hover:text-white hover:bg-white/10 px-2 py-0.5 rounded transition" data-umami-event="homepage_social" data-umami-event-platform="bluesky">Bluesky <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
          <li><a href="https://opencollective.com/civicband" target="_blank" rel="noopener noreferrer" class="bg-amber-500 text-gray-900 hover:bg-amber-400 px-2 py-0.5 rounded font-medium transition" data-umami-event="homepage_support">Donate! <span class="text-xs" aria-hidden="true">&#8599;</span><span class="sr-only">(opens in new tab)</span></a></li>
        </ul>
      </div>
    </nav>
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py::TestPageViews::test_home_view tests/test_home_view.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/_hero.html
git commit -m "Inline nav links in hero section instead of including standalone nav"
```

---

### Task 3: Create `_footer.html`

**Files:**
- Create: `templates/pages/_footer.html`

- [ ] **Step 1: Create the footer partial**

Create `templates/pages/_footer.html` with:

```html
<!-- Footer -->
<footer class="bg-indigo-900 text-white mt-auto">
  <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">

      <!-- About -->
      <div>
        <h3 class="text-lg font-bold mb-3">
          <a href="/" class="hover:text-indigo-200 transition">CivicBand</a>
        </h3>
        <p class="text-sm text-indigo-200">
          Municipal transparency and civic participation. The largest public collection of civic meeting and election finance data for the US and Canada.
        </p>
        <p class="text-sm text-indigo-300 mt-2">
          A project of the <a href="https://raft.foundation" class="underline hover:text-white transition" data-umami-event="footer_external" data-umami-event-target="raft-foundation">Raft Foundation</a>.
        </p>
      </div>

      <!-- Navigation -->
      <div>
        <h3 class="text-sm font-semibold uppercase tracking-wider text-indigo-300 mb-3">Pages</h3>
        <ul class="space-y-2 text-sm">
          <li><a href="/" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="home">Home</a></li>
          <li><a href="/how.html" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="how">How it works</a></li>
          <li><a href="/why.html" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="why">Why?</a></li>
          <li><a href="/researchers" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="researchers">For Researchers</a></li>
          <li><a href="/map" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="map">Sites Map</a></li>
          <li><a href="/rss.xml" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="rss">RSS Feed</a></li>
        </ul>
      </div>

      <!-- Social & Connect -->
      <div>
        <h3 class="text-sm font-semibold uppercase tracking-wider text-indigo-300 mb-3">Connect</h3>
        <ul class="space-y-2 text-sm">
          <li><a href="https://github.com/civicband" target="_blank" rel="noopener noreferrer" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_social" data-umami-event-target="github">GitHub</a></li>
          <li><a href="https://sfba.social/@civicband" target="_blank" rel="noopener noreferrer me" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_social" data-umami-event-target="mastodon">Mastodon</a></li>
          <li><a href="https://bsky.app/profile/civic.band" target="_blank" rel="noopener noreferrer me" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_social" data-umami-event-target="bluesky">Bluesky</a></li>
          <li><a href="mailto:hello@civic.band" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_social" data-umami-event-target="email">hello@civic.band</a></li>
          <li><a href="https://civic.observer" class="text-indigo-200 hover:text-white transition" data-umami-event="footer_social" data-umami-event-target="civicobserver">CivicObserver</a></li>
        </ul>
      </div>

      <!-- Newsletter -->
      <div>
        <h3 class="text-sm font-semibold uppercase tracking-wider text-indigo-300 mb-3">Stay Updated</h3>
        <p class="text-sm text-indigo-200 mb-3">New municipalities and features. No spam.</p>
        <form action="https://buttondown.com/api/emails/embed-subscribe/civicband"
              method="post"
              target="popupwindow"
              onsubmit="window.open('https://buttondown.com/civicband', 'popupwindow')"
              class="flex flex-col gap-2">
          <label for="bd-email-footer" class="sr-only">Email address</label>
          <input id="bd-email-footer"
                 name="email"
                 type="email"
                 autocomplete="email"
                 required
                 class="px-3 py-1.5 text-sm border border-indigo-400/50 rounded-lg bg-white/90 text-gray-900 focus:ring-2 focus:ring-white focus:border-white placeholder-gray-500"
                 placeholder="your@email.com">
          <button type="submit"
                  class="px-4 py-1.5 bg-amber-500 text-gray-900 rounded-lg hover:bg-amber-400 font-medium text-sm transition shadow-sm"
                  data-umami-event="footer_newsletter">
            Subscribe
          </button>
        </form>
        <div class="mt-3">
          <a href="https://opencollective.com/civicband" target="_blank" rel="noopener noreferrer"
             class="inline-block bg-amber-500 text-gray-900 hover:bg-amber-400 px-3 py-1.5 rounded-lg font-medium text-sm transition"
             data-umami-event="footer_donate">
            Donate!
          </a>
        </div>
      </div>

    </div>

    <!-- Bottom bar -->
    <div class="mt-8 pt-6 border-t border-indigo-700 flex flex-wrap items-center justify-between gap-4 text-sm text-indigo-300">
      <p>&copy; {{ current_year|default:"2026" }} Raft Foundation. All rights reserved.</p>
      <a href="/privacy.html" class="hover:text-white transition" data-umami-event="footer_nav" data-umami-event-target="privacy">Privacy Policy</a>
    </div>
  </div>
</footer>
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/_footer.html
git commit -m "Create standard footer partial with nav, social, newsletter"
```

---

### Task 4: Enhance `base.html` with Navbar and Footer Blocks

**Files:**
- Modify: `templates/pages/base.html`

- [ ] **Step 1: Update `base.html` body to include navbar, main wrapper, and footer**

In `templates/pages/base.html`, replace the `<body>` section (from `<body class="bg-gray-50">` through the closing `</body>`) with:

```html
<body class="bg-gray-50 flex flex-col min-h-screen">
    {% block navbar %}
    {% include 'pages/_navigation.html' %}
    {% endblock %}

    <main class="flex-1">
    {% block content %}{% endblock %}
    </main>

    {% block footer %}
    {% include 'pages/_footer.html' %}
    {% endblock %}

    <!-- Leaflet JS -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <!-- Tawk.to Chat -->
    <script type="text/javascript">
    var Tawk_API=Tawk_API||{}, Tawk_LoadStart=new Date();
    (function(){
    var s1=document.createElement("script"),s0=document.getElementsByTagName("script")[0];
    s1.async=true;
    s1.src='https://embed.tawk.to/6941d7e665b580197cc611f4/1jckj6njm';
    s1.charset='UTF-8';
    s1.setAttribute('crossorigin','*');
    s0.parentNode.insertBefore(s1,s0);
    })();
    </script>

    {% block extra_scripts %}{% endblock %}
</body>
```

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `python -m pytest tests/test_pages_views.py -v`
Expected: All tests PASS (home, how, why, feed views still render)

- [ ] **Step 3: Commit**

```bash
git add templates/pages/base.html
git commit -m "Add navbar and footer blocks to base template"
```

---

### Task 5: Update `home.html` to Override Navbar Block with Hero

The homepage should use the hero section (which already includes `_navigation.html` internally) instead of the standalone nav bar.

**Files:**
- Modify: `templates/pages/home.html`

- [ ] **Step 1: Override the navbar block in `home.html`**

Replace the beginning of `templates/pages/home.html` (the `{% block content %}` section) so that the hero is in the navbar block and the rest is in the content block. The full file should be:

```django
{% extends "pages/base.html" %}

{% block navbar %}
{% include 'pages/_hero.html' %}
{% endblock %}

{% block content %}
{% include 'pages/_finder.html' %}
{% include 'pages/_results.html' %}
{% endblock %}

{% block extra_scripts %}
<script>
(function() {
  // ===== MAP INITIALIZATION =====
  let map, markers;

  try {
    map = L.map('sites-map').setView([39.8283, -98.5795], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);

    markers = L.markerClusterGroup({
      maxClusterRadius: 20,
      disableClusteringAtZoom: 8,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true
    });
    markers.addTo(map);
  } catch (error) {
    console.error('Failed to initialize map:', error);
  }

  // ===== MAP DATA LOADING =====
  function loadMarkers(geojson) {
    if (!map || !markers) {
      console.warn('Map not initialized, cannot load markers');
      return;
    }

    try {
      markers.clearLayers();

      if (!geojson || !geojson.features || !Array.isArray(geojson.features)) {
        console.warn('Invalid geojson data');
        map.setView([39.8283, -98.5795], 5);
        return;
      }

      if (geojson.features.length === 0) {
        map.setView([39.8283, -98.5795], 5);
        return;
      }

      L.geoJSON(geojson, {
        onEachFeature: function(feature, layer) {
          if (feature.properties && feature.properties.popup) {
            layer.bindPopup(feature.properties.popup);
          }
        }
      }).addTo(markers);

      if (markers.getLayers().length > 0) {
        map.fitBounds(markers.getBounds(), { padding: [50, 50] });
      }
    } catch (error) {
      console.error('Failed to load markers:', error);
      try {
        map.setView([39.8283, -98.5795], 5);
      } catch (e) {
        console.error('Failed to reset map view:', e);
      }
    }
  }

  // Listen for HTMX updates
  document.body.addEventListener('sites:updated', function(event) {
    loadMarkers(event.detail);
  });

  // Load initial data
  setTimeout(function() {
    if (window.sitesGeoJSON) {
      loadMarkers(window.sitesGeoJSON);
    }
  }, 100);

  // ===== FILTER TOGGLE =====
  const toggleBtn = document.getElementById('toggle-filters-btn');
  const filtersPanel = document.getElementById('advanced-filters');
  const showText = toggleBtn.querySelector('.show-text');
  const hideText = toggleBtn.querySelector('.hide-text');

  toggleBtn.addEventListener('click', function() {
    const isHidden = filtersPanel.classList.contains('hidden');

    if (isHidden) {
      filtersPanel.classList.remove('hidden');
      toggleBtn.setAttribute('aria-expanded', 'true');
      showText.classList.add('hidden');
      hideText.classList.remove('hidden');
    } else {
      filtersPanel.classList.add('hidden');
      toggleBtn.setAttribute('aria-expanded', 'false');
      showText.classList.remove('hidden');
      hideText.classList.add('hidden');
    }
  });

  // ===== CLEAR FILTERS BUTTON VISIBILITY =====
  const clearBtn = document.getElementById('clear-filters-btn');
  const searchInput = document.getElementById('search-input');
  const stateFilter = document.getElementById('state-filter');
  const kindFilter = document.getElementById('kind-filter');
  const financeFilter = document.getElementById('finance-filter');

  function updateClearButton() {
    const hasFilters = searchInput.value || stateFilter.value || kindFilter.value || financeFilter.checked;
    clearBtn.style.display = hasFilters ? 'inline-block' : 'none';
  }

  searchInput.addEventListener('input', updateClearButton);
  stateFilter.addEventListener('change', updateClearButton);
  kindFilter.addEventListener('change', updateClearButton);
  financeFilter.addEventListener('change', updateClearButton);
  document.body.addEventListener('htmx:afterSwap', updateClearButton);

  // ===== QUICK-START BUTTONS =====
  const quickStartButtons = document.querySelectorAll('.quick-start-btn');

  quickStartButtons.forEach(function(button) {
    button.addEventListener('click', function() {
      const searchTerm = this.getAttribute('data-search');
      searchInput.value = searchTerm;

      // Trigger HTMX request
      htmx.trigger(searchInput, 'keyup');

      // Scroll to results
      setTimeout(function() {
        document.getElementById('sites-table-container').scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 300);
    });
  });

  // ===== GEOLOCATION =====
  const useLocationBtn = document.getElementById('use-location-btn');

  useLocationBtn.addEventListener('click', function() {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser');
      return;
    }

    // Show loading state
    useLocationBtn.disabled = true;
    useLocationBtn.innerHTML = `
      <svg class="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      Finding your location...
    `;

    navigator.geolocation.getCurrentPosition(
      function(position) {
        const userLat = position.coords.latitude;
        const userLng = position.coords.longitude;

        findNearestMunicipalities(userLat, userLng);
      },
      function(error) {
        console.error('Geolocation error:', error);
        let message = 'Unable to get your location. ';

        switch(error.code) {
          case error.PERMISSION_DENIED:
            message += 'Please allow location access and try again.';
            break;
          case error.POSITION_UNAVAILABLE:
            message += 'Location information is unavailable.';
            break;
          case error.TIMEOUT:
            message += 'Location request timed out.';
            break;
          default:
            message += 'An unknown error occurred.';
        }

        alert(message);
        resetLocationButton();
      },
      {
        timeout: 10000,
        maximumAge: 60000
      }
    );
  });

  function findNearestMunicipalities(userLat, userLng) {
    if (!window.sitesGeoJSON || !window.sitesGeoJSON.features) {
      alert('Unable to find nearby municipalities. Please try searching manually.');
      resetLocationButton();
      return;
    }

    const sitesWithDistance = window.sitesGeoJSON.features
      .filter(f => f.geometry && f.geometry.coordinates)
      .map(function(feature) {
        const [lng, lat] = feature.geometry.coordinates;
        const distance = calculateDistance(userLat, userLng, lat, lng);
        return {
          name: feature.properties.name,
          distance: distance
        };
      })
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 1);

    if (sitesWithDistance.length > 0) {
      const nearest = sitesWithDistance[0];
      searchInput.value = nearest.name;
      htmx.trigger(searchInput, 'keyup');

      setTimeout(function() {
        document.getElementById('sites-table-container').scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }, 300);
    } else {
      alert('No municipalities found near your location. Try searching manually.');
    }

    resetLocationButton();
  }

  function calculateDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  }

  function resetLocationButton() {
    useLocationBtn.disabled = false;
    useLocationBtn.innerHTML = `
      <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      Use My Location
    `;
  }

})();
</script>
{% endblock %}
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py::TestPageViews::test_home_view tests/test_pages_views.py::TestPageViews::test_home_view_integration tests/test_home_view.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/home.html
git commit -m "Move hero section to navbar block in homepage template"
```

---

### Task 6: Update `map.html` to Remove Inline Nav (Gets Navbar from Base)

The map page has its own inline navigation bar. Since it now inherits the shared navbar from `base.html`, we remove the inline nav. However, the map page needs special handling: it's a full-screen layout, so it should hide the footer and use the full viewport height.

**Files:**
- Modify: `templates/pages/map.html`

- [ ] **Step 1: Update `map.html` to remove inline nav and override footer**

Replace the `{% block content %}` section in `templates/pages/map.html`. Remove the inline header/nav (the `<div class="bg-white border-b-2 ...">` block) and override the footer block to hide it on the full-screen map. The full `{% block content %}` becomes:

```django
{% block footer %}{% endblock %}

{% block content %}
<!-- Full-page map layout -->
<div class="relative flex flex-col" style="height: calc(100vh - 52px);">
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
</div>
{% endblock %}
```

Note: The `style="height: calc(100vh - 52px);"` accounts for the navbar height. The `{% block footer %}{% endblock %}` empty override hides the footer on the map page. The `{% block extra_head %}` and `{% block extra_scripts %}` blocks remain unchanged.

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/map.html
git commit -m "Remove inline nav from map page, use shared navbar from base"
```

---

### Task 7: Create `_content_page.html` Intermediate Template

**Files:**
- Create: `templates/pages/_content_page.html`

- [ ] **Step 1: Create the content page template**

Create `templates/pages/_content_page.html` with:

```django
{% extends "pages/base.html" %}

{% block content %}
<div class="bg-white px-6 py-16 lg:px-8">
  <div class="mx-auto max-w-3xl text-base/7 text-gray-700">
    <h1 class="mt-2 text-pretty text-4xl font-semibold tracking-tight text-gray-900 sm:text-5xl">
      {% block page_title %}{% endblock %}
    </h1>
    {% block page_subtitle %}{% endblock %}
    <div class="mt-10 max-w-2xl">
      {% block page_content %}{% endblock %}
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/pages/_content_page.html
git commit -m "Create content page intermediate template"
```

---

### Task 8: Convert `how.html` to Use Template Inheritance

**Files:**
- Modify: `templates/pages/how.html`

- [ ] **Step 1: Rewrite `how.html` to extend `_content_page.html`**

Replace the entire contents of `templates/pages/how.html` with:

```django
{% extends "pages/_content_page.html" %}

{% block title %}How It Works - Civic Band{% endblock %}
{% block description %}How CivicBand collects, processes, and makes searchable public records from municipal governments{% endblock %}

{% block page_title %}How CivicBand makes this all happen{% endblock %}

{% block page_subtitle %}
<p class="mt-6 text-xl/8">CivicBand is a collection of sites for querying and exploring municipal and civic data.
  Each site is its own Datasette instance, with both in-house and third-party plugins.</p>
{% endblock %}

{% block page_content %}
<p>The way we get data from municipality websites and into our system follows a pretty standard Extract,
  Transform, Load pattern. Effectively, we pull extract data (in the form of PDFs) out of websites, OCR that
  into text, load that text into a SQLite DB, and deploy the DB with Datasette to the production server. Let's
  talk about that process in more detail, by going through a hypothetical, say "Getting the data for Alameda,
  CA" </p>
<ul class="list-disc mt-8 max-w-xl space-y-8 text-gray-600">
  <li class="gap-x-3">
    Start by looking at the Alameda, CA city government website, and figure out if there's some system they're
    using to store all meeting minutes.
  </li>
  <li class="gap-x-3">
    There is! I'm not going to name it here, because while this data is public data, the systems that cities
    contract with to run it aren't. They could make my life way more difficult if they chose. They could also
    make
    my life easier! If you run one of these systems, email hello@civic.band.
  </li>
  <li class="gap-x-3">
    Fetch all the PFDs, store them in folders organized by "pdfs/MeetingName/Date", eg
    "pdfs/CityCouncil/2020-04-20.pdf". We do this so we the directory structure itself is metadata that we can
    use
    in later processing.
  </li>
  <li class="gap-x-3">
    Run all the PDFs through a program that splits each PDF into a folder of images by page number, eg
    "images/CityCouncil/2020-04-20/1.png". We do this so that the OCR jobs can be parallelized easier, and it
    matches how the data is eventually stored.
  </li>
  <li class="gap-x-3">
    Upload the images to a CDN, so that it can be displayed alongside the text result.
  </li>
  <li class="gap-x-3">
    Run Tesseract on all the page images, saving the output as text files, eg "txt/CityCouncil/2020-04-20/1.txt"
  </li>
  <li class="gap-x-3">
    Load all the text files as rows into a SQLite DB, with search turned on.
  </li>
  <li class="gap-x-3">
    Deploy that DB to a docker container running Datasette on the production server.
  </li>
</ul>
<p class="mt-8">Each of these steps represents many hours of work and trial and error, not to mention the
  scrapers I have written for various storage systems. I may eventuall open-source parts of this, but am pretty
  unlikely to open-source the whole thing. That said, if you want to work on this, or work on the data, please
  reach out to hello@civic.band.</p>
{% endblock %}
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py::TestPageViews::test_how_view tests/test_pages_views.py::TestPageViews::test_how_view_integration -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/how.html
git commit -m "Convert how.html to use content page template inheritance"
```

---

### Task 9: Convert `why.html` to Use Template Inheritance

**Files:**
- Modify: `templates/pages/why.html`

- [ ] **Step 1: Rewrite `why.html` to extend `_content_page.html`**

Replace the entire contents of `templates/pages/why.html` with:

```django
{% extends "pages/_content_page.html" %}

{% block title %}Why? - Civic Band{% endblock %}
{% block description %}Why CivicBand exists - municipal transparency and civic participation{% endblock %}

{% block page_title %}Why?{% endblock %}

{% block page_subtitle %}
<p class="mt-6 text-xl/8">So, why do we do all this? Why does CivicBand exist?</p>
{% endblock %}

{% block page_content %}
<p>This project started because I wanted to know more about what was going on in my hometown of Alameda,
    CA. Specifically, I wanted to be able to look up the voting records of elected officials, and was
    mad that I couldn't do that easily. Even with Alameda using a central management platform for
    hosting
    all the PDFs, searching in them was hard, if not impossible.</p>
<p class="mt-8">Around that time, Simon Willison was writing about how he was OCR'ing PDFs right into
    Datasette, and I realized this was the perfect fit for what I was trying to do. I modified his
    techniques to run totally locally, because AWS is expensive, and I was off to the races.</p>
<p class="mt-8">The question isn't "why did I start?", it's "why didn't I stop?". Why do we now track
    149 different municipal bodies, with more being added every week? It's actually pretty simple: The
    biggest impact most of us can have is locally, and in order to make that impact you need to know how
    and where to show up.</p>
<p class="mt-8">Do you care about rent control? Do you know when upcoming City Council meetings or
    Planning Board meetings are talking about that? Do you know how the current City Council has voted
    on it in the past? CivicBand gives you that, for every place we track, for ideally any issue you
    care about.</p>
<p class="mt-8">CivicBand a tool for activists, and journalists, and NGOs, and
    non-profits, and really any organization that cares about regional issues to know what's going on
    and hold elected officials accountable. We're just getting started, and if this is interesting to
    you reach out to hello@civic.band.</p>
{% endblock %}
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py::TestPageViews::test_why_view tests/test_pages_views.py::TestPageViews::test_why_view_integration -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/why.html
git commit -m "Convert why.html to use content page template inheritance"
```

---

### Task 10: Convert `researchers.html` to Use Template Inheritance

**Files:**
- Modify: `templates/pages/researchers.html`

- [ ] **Step 1: Rewrite `researchers.html` to extend `_content_page.html`**

Replace the entire contents of `templates/pages/researchers.html` with:

```django
{% extends "pages/_content_page.html" %}

{% block title %}For Researchers - Civic Band{% endblock %}
{% block description %}CivicBand for researchers and academics - citation formats, Zotero integration, and research tools{% endblock %}

{% block page_title %}CivicBand for Researchers{% endblock %}

{% block page_subtitle %}
<p class="mt-6 text-xl/8">CivicBand provides free access to searchable municipal meeting records. Here's how to integrate CivicBand into your research workflow.</p>
{% endblock %}

{% block page_content %}
<h2 class="text-2xl font-bold tracking-tight text-gray-900">Citing CivicBand Records</h2>
<p class="mt-4">Each record page includes a "Cite this page" section with a pre-formatted citation. Records include Dublin Core metadata for automated citation tools.</p>

<h3 class="mt-8 text-lg font-semibold text-gray-900">Citation Examples</h3>
<p class="mt-2 text-sm text-gray-500">For a City Council Minutes page from Alameda, CA dated January 15, 2024:</p>

<div class="mt-4 space-y-4">
  <div class="bg-gray-50 p-4 rounded-lg">
    <p class="font-semibold text-sm text-gray-900">Chicago (Notes-Bibliography)</p>
    <p class="mt-2 text-sm font-mono text-gray-600">City of Alameda. "City Council Minutes." January 15, 2024, page 3. CivicBand Archive. Accessed [date]. https://alameda.ca.civic.band/meetings/minutes/[id]</p>
  </div>

  <div class="bg-gray-50 p-4 rounded-lg">
    <p class="font-semibold text-sm text-gray-900">APA (7th Edition)</p>
    <p class="mt-2 text-sm font-mono text-gray-600">City of Alameda. (2024, January 15). City council minutes (p. 3). CivicBand Archive. https://alameda.ca.civic.band/meetings/minutes/[id]</p>
  </div>

  <div class="bg-gray-50 p-4 rounded-lg">
    <p class="font-semibold text-sm text-gray-900">MLA (9th Edition)</p>
    <p class="mt-2 text-sm font-mono text-gray-600">City of Alameda. "City Council Minutes." 15 Jan. 2024, p. 3. <em>CivicBand Archive</em>, alameda.ca.civic.band/meetings/minutes/[id]. Accessed [date].</p>
  </div>
</div>

<h2 class="mt-12 text-2xl font-bold tracking-tight text-gray-900">Browser Search Integration</h2>
<p class="mt-4">Each CivicBand site supports <a href="https://developer.mozilla.org/en-US/docs/Web/OpenSearch" class="text-indigo-600 hover:text-indigo-500">OpenSearch</a>, allowing you to add it as a search engine in your browser.</p>

<div class="mt-4 bg-gray-50 p-4 rounded-lg">
  <p class="font-semibold text-sm text-gray-900">To add a CivicBand site as a search engine:</p>
  <ol class="mt-2 text-sm text-gray-600 list-decimal list-inside space-y-1">
    <li>Visit any CivicBand site (e.g., <a href="https://alameda.ca.civic.band" class="text-indigo-600 hover:text-indigo-500">alameda.ca.civic.band</a>)</li>
    <li>In Firefox: Right-click the address bar and select "Add Search Engine"</li>
    <li>In Chrome: The site will appear in Settings &gt; Search engine &gt; Manage search engines</li>
  </ol>
</div>

<h2 class="mt-12 text-2xl font-bold tracking-tight text-gray-900">Zotero Integration</h2>
<p class="mt-4">CivicBand works with <a href="https://www.zotero.org/" class="text-indigo-600 hover:text-indigo-500">Zotero</a>, the free reference management tool popular with researchers.</p>

<h3 class="mt-6 text-lg font-semibold text-gray-900">Automatic Metadata Detection</h3>
<p class="mt-2">CivicBand pages include Dublin Core metadata that Zotero can automatically detect. When viewing a record page, the Zotero browser connector will recognize it as a citable source.</p>

<h3 class="mt-6 text-lg font-semibold text-gray-900">Adding as a Locate Engine</h3>
<p class="mt-2">You can add CivicBand sites as Zotero "Locate" engines for quick lookups. Add the following to your <code class="text-sm bg-gray-100 px-1 py-0.5 rounded">engines.json</code> file in your Zotero data directory:</p>

<div class="mt-4 bg-gray-900 p-4 rounded-lg overflow-x-auto">
  <pre class="text-sm text-gray-100"><code>{
"name": "Alameda CA CivicBand",
"alias": "Alameda Civic",
"description": "Search Alameda CA meeting records",
"_urlTemplate": "https://alameda.ca.civic.band/meetings?_search={z:title}",
"hidden": false
}</code></pre>
</div>

<p class="mt-4 text-sm text-gray-500">Replace "alameda.ca" with the subdomain for your municipality of interest. Find all available sites at <a href="https://civic.band" class="text-indigo-600 hover:text-indigo-500">civic.band</a>.</p>

<h2 class="mt-12 text-2xl font-bold tracking-tight text-gray-900">Data Access</h2>
<p class="mt-4">All CivicBand data is accessible via JSON API. Append <code class="text-sm bg-gray-100 px-1 py-0.5 rounded">.json</code> to any page URL to get machine-readable data.</p>

<div class="mt-4 bg-gray-50 p-4 rounded-lg">
  <p class="font-semibold text-sm text-gray-900">Example API URLs:</p>
  <ul class="mt-2 text-sm text-gray-600 space-y-1 font-mono">
    <li>Table data: <code>https://alameda.ca.civic.band/meetings/minutes.json</code></li>
    <li>Search results: <code>https://alameda.ca.civic.band/meetings/minutes.json?_search=budget</code></li>
    <li>Single record: <code>https://alameda.ca.civic.band/meetings/minutes/[id].json</code></li>
  </ul>
</div>

<p class="mt-4 text-sm text-gray-500">For high-volume API access or cross-domain search capabilities, contact us about <a href="https://civic.observer" class="text-indigo-600 hover:text-indigo-500">CivicObserver</a> research accounts.</p>

<h2 class="mt-12 text-2xl font-bold tracking-tight text-gray-900">Questions?</h2>
<p class="mt-4">For research inquiries, data access questions, or collaboration opportunities, contact us at <a href="mailto:hello@civic.band" class="text-indigo-600 hover:text-indigo-500">hello@civic.band</a>.</p>
{% endblock %}
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/test_pages_views.py -v`
Expected: All PASS

- [ ] **Step 3: Commit**

```bash
git add templates/pages/researchers.html
git commit -m "Convert researchers.html to use content page template inheritance"
```

---

### Task 11: Delete Legacy Templates

**Files:**
- Delete: `templates/pages/index.html`
- Delete: `templates/pages/home_old.html`

- [ ] **Step 1: Verify no views reference these templates**

The `index.html` in `plugins/corkboard.py` refers to Datasette's built-in `index.html`, not `templates/pages/index.html`. No Django view references either file. Safe to delete.

- [ ] **Step 2: Delete the files**

```bash
git rm templates/pages/index.html templates/pages/home_old.html
```

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git commit -m "Remove legacy index.html and home_old.html templates"
```

---

### Task 12: Final Verification

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Start the dev server and manually verify pages**

Run: `python manage.py runserver`

Verify each URL loads with navbar and footer:
- `http://localhost:8000/` — homepage with hero (not standalone nav) + footer
- `http://localhost:8000/how.html` — standalone nav + content + footer
- `http://localhost:8000/why.html` — standalone nav + content + footer
- `http://localhost:8000/researchers` — standalone nav + content + footer
- `http://localhost:8000/map` — standalone nav + map (no footer, full height)

- [ ] **Step 3: Commit any final fixes if needed**
