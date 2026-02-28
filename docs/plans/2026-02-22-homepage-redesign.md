# Homepage Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign CivicBand homepage with hero section, improved municipality finder with quick-start options, and clear CTAs

**Architecture:** Refactor home.html template into three distinct sections (hero, finder, results). Add geolocation feature using browser API. Use vanilla JS for filter toggles. Maintain existing HTMX functionality for search/filter updates.

**Tech Stack:** Django 5.1, HTMX, Tailwind CSS, Leaflet.js, vanilla JavaScript

---

## Task 1: Create Backup of Current Homepage

**Files:**
- Copy: `templates/pages/home.html` → `templates/pages/home_old.html`

**Step 1: Create backup file**

Run:
```bash
cp templates/pages/home.html templates/pages/home_old.html
```

Expected: File copied successfully

**Step 2: Verify backup exists**

Run:
```bash
ls -la templates/pages/home*.html
```

Expected: Both home.html and home_old.html listed

**Step 3: Commit backup**

```bash
git add templates/pages/home_old.html
git commit -m "chore: backup current homepage before redesign"
```

---

## Task 2: Extract Current Navigation to Partial

**Files:**
- Create: `templates/pages/_navigation.html`
- Modify: `templates/pages/home.html:8-18`

**Step 1: Create navigation partial**

Create `templates/pages/_navigation.html`:

```html
<!-- Navigation -->
<nav class="mb-3 pb-2 border-b border-gray-200">
  <ul class="flex flex-wrap gap-2 text-sm">
    <li><a href="/how.html" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="how">How it works</a></li>
    <li><a href="/why.html" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="why">Why?</a></li>
    <li><a href="/rss.xml" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="rss">RSS Feed</a></li>
    <li><a href="https://github.com/civicband/corkboard" target="_blank" rel="noopener noreferrer" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_nav" data-umami-event-target="github">GitHub <span class="text-xs">↗</span></a></li>
    <li><a rel="me" href="https://sfba.social/@civicband" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_social" data-umami-event-platform="mastodon">Mastodon</a></li>
    <li><a rel="me" href="https://bsky.app/profile/civic.band" class="text-gray-600 hover:text-gray-900 hover:bg-gray-100 px-2 py-0.5 rounded transition" data-umami-event="homepage_social" data-umami-event-platform="bluesky">Bluesky</a></li>
    <li><a href="https://opencollective.com/civicband" class="bg-indigo-500 text-white hover:bg-indigo-600 px-2 py-0.5 rounded font-medium transition" data-umami-event="homepage_support">Support!</a></li>
  </ul>
</nav>
```

**Step 2: Test that file was created**

Run:
```bash
cat templates/pages/_navigation.html | head -5
```

Expected: First 5 lines of navigation HTML displayed

**Step 3: Commit navigation partial**

```bash
git add templates/pages/_navigation.html
git commit -m "refactor: extract navigation to partial template"
```

---

## Task 3: Build Hero Section Structure

**Files:**
- Create: `templates/pages/_hero.html`

**Step 1: Create hero section partial**

Create `templates/pages/_hero.html`:

```html
<!-- Hero Section -->
<div class="bg-gray-50 border-b border-gray-200">
  <div class="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">

    {% include 'pages/_navigation.html' %}

    <!-- Headline -->
    <h1 class="text-4xl sm:text-5xl font-bold text-gray-900 mb-4 mt-6">
      Searchable Civic Meeting Data Across North America
    </h1>

    <!-- Brief Explanation -->
    <div class="text-lg text-gray-700 mb-6 max-w-3xl">
      <p class="mb-2">
        CivicBand is the largest collection of searchable civic meeting data in the United States and Canada.
        We make local government more accessible by gathering meeting minutes, agendas, and campaign finance data
        from hundreds of municipalities.
      </p>
    </div>

    <!-- Expandable Learn More -->
    <details class="mb-8 max-w-3xl">
      <summary class="text-indigo-600 hover:text-indigo-800 cursor-pointer font-medium text-base mb-2">
        Learn more about CivicBand
      </summary>
      <div class="mt-3 text-base text-gray-600 space-y-3 pl-4">
        <p>
          Local government decisions affect everything from housing to transportation to schools,
          but finding out what your city council is discussing shouldn't require hours of digging
          through PDFs or attending meetings in person.
        </p>
        <p>
          CivicBand automatically collects, processes, and makes searchable the public records from
          municipal governments across North America. Whether you're a resident keeping tabs on your
          city, a researcher studying local policy, or a journalist investigating a story, we provide
          the tools you need.
        </p>
        <p>
          This is a project from the <a href="https://raft.foundation" class="text-indigo-600 hover:text-indigo-800 underline" data-umami-event="homepage_external" data-umami-event-target="raft-foundation">Raft Foundation</a>,
          a nonprofit working to make government data more accessible.
        </p>
        <p class="pt-2">
          <a href="/how.html" class="text-indigo-600 hover:text-indigo-800 underline">How it works</a> •
          <a href="/why.html" class="text-indigo-600 hover:text-indigo-800 underline ml-2">Why we built this</a>
        </p>
      </div>
    </details>

    <!-- Newsletter Signup (Primary CTA) -->
    <div class="bg-white border border-gray-300 rounded-lg p-6 mb-6 max-w-2xl">
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Stay Updated</h3>
      <p class="text-sm text-gray-600 mb-4">
        Get updates when we add new municipalities and features. No spam, unsubscribe anytime.
      </p>
      <form action="https://buttondown.com/api/emails/embed-subscribe/civicband"
            method="post"
            target="popupwindow"
            onsubmit="window.open('https://buttondown.com/civicband', 'popupwindow')"
            class="flex flex-wrap gap-3 items-center">
        <label for="bd-email" class="sr-only">Email address</label>
        <input id="bd-email"
               name="email"
               type="email"
               autocomplete="email"
               required
               class="flex-1 min-w-[200px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
               placeholder="your@email.com">
        <button type="submit"
                class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition shadow-sm"
                data-umami-event="homepage_newsletter">
          Subscribe
        </button>
      </form>
      <p class="text-xs text-gray-500 mt-3">
        We care about your data. Read our <a href="/privacy.html" class="text-indigo-600 hover:text-indigo-800 underline" data-umami-event="homepage_nav" data-umami-event-target="privacy">privacy policy</a>.
      </p>
    </div>

    <!-- Secondary CTAs -->
    <div class="flex flex-wrap gap-4 text-sm mb-8">
      <a href="https://github.com/civicband/corkboard"
         target="_blank"
         rel="noopener noreferrer"
         class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition"
         data-umami-event="homepage_cta" data-umami-event-target="github">
        <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd" />
        </svg>
        Contribute on GitHub
      </a>
      <a href="mailto:hello@civic.band"
         class="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition"
         data-umami-event="homepage_cta" data-umami-event-target="email">
        <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        Email us: hello@civic.band
      </a>
    </div>

    <!-- Stats Bar -->
    <div class="text-base font-semibold text-gray-700 border-t border-gray-300 pt-6">
      {% load humanize %}
      Tracking {{ total_pages|default:0|intcomma }} pages across {{ num_sites|default:0|intcomma }} municipalities
      {% if finance_sites_count %}
      • {{ finance_sites_count|intcomma }} with campaign finance data
      {% endif %}
    </div>

  </div>
</div>
```

**Step 2: Verify hero template**

Run:
```bash
wc -l templates/pages/_hero.html
```

Expected: Line count displayed (should be ~100+ lines)

**Step 3: Commit hero section**

```bash
git add templates/pages/_hero.html
git commit -m "feat: add hero section with newsletter signup and CTAs"
```

---

## Task 4: Build Municipality Finder Section

**Files:**
- Create: `templates/pages/_finder.html`

**Step 1: Create finder section partial**

Create `templates/pages/_finder.html`:

```html
<!-- Municipality Finder Section -->
<div class="bg-white border-b border-gray-200">
  <div class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">

    <!-- Section Header -->
    <div class="text-center mb-6">
      <h2 class="text-3xl font-bold text-gray-900 mb-2">Find Your Municipality</h2>
      <p class="text-gray-600">Search {{ num_sites|default:0 }} cities and counties</p>
    </div>

    <!-- Primary Search Input -->
    <div class="max-w-3xl mx-auto mb-6">
      <div class="relative">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input type="text"
               name="q"
               id="search-input"
               value="{{ query }}"
               placeholder="Search by city, town, or county name..."
               class="block w-full pl-12 pr-4 py-4 text-lg border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
               hx-get="/sites/search/"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#sites-table-container"
               hx-include="[name='state'], [name='kind'], [name='sort'], [name='has_finance']"
               hx-push-url="true"
               aria-label="Search municipalities">
      </div>
    </div>

    <!-- Quick-Start Options -->
    <div class="max-w-3xl mx-auto mb-8">
      <div class="text-center mb-4">
        <button type="button"
                id="use-location-btn"
                class="inline-flex items-center px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition shadow-sm"
                data-umami-event="homepage_geolocation">
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Use My Location
        </button>
      </div>

      <div class="text-center text-sm text-gray-500 mb-3">Or try these popular municipalities:</div>

      <div class="flex flex-wrap justify-center gap-2">
        <button type="button"
                class="quick-start-btn px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition"
                data-search="Oakland, CA"
                data-umami-event="homepage_quickstart" data-umami-event-city="oakland">
          Oakland, CA
        </button>
        <button type="button"
                class="quick-start-btn px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition"
                data-search="Berkeley, CA"
                data-umami-event="homepage_quickstart" data-umami-event-city="berkeley">
          Berkeley, CA
        </button>
        <button type="button"
                class="quick-start-btn px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition"
                data-search="San Francisco, CA"
                data-umami-event="homepage_quickstart" data-umami-event-city="sanfrancisco">
          San Francisco, CA
        </button>
        <button type="button"
                class="quick-start-btn px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition"
                data-search="Chicago, IL"
                data-umami-event="homepage_quickstart" data-umami-event-city="chicago">
          Chicago, IL
        </button>
        <button type="button"
                class="quick-start-btn px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full text-sm font-medium transition"
                data-search="New York, NY"
                data-umami-event="homepage_quickstart" data-umami-event-city="newyork">
          New York, NY
        </button>
      </div>
    </div>

    <!-- Advanced Filters (Collapsible) -->
    <div class="max-w-3xl mx-auto">
      <div class="text-center mb-3">
        <button type="button"
                id="toggle-filters-btn"
                class="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                aria-expanded="false"
                aria-controls="advanced-filters">
          <span class="show-text">Show advanced filters</span>
          <span class="hide-text hidden">Hide advanced filters</span>
        </button>
      </div>

      <div id="advanced-filters" class="hidden">
        <div class="flex flex-wrap gap-3 items-center justify-center p-4 bg-gray-50 rounded-lg border border-gray-200">

          <!-- State Filter -->
          <div>
            <label for="state-filter" class="sr-only">Filter by state</label>
            <select name="state"
                    id="state-filter"
                    class="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    hx-get="/sites/search/"
                    hx-trigger="change"
                    hx-target="#sites-table-container"
                    hx-include="[name='q'], [name='kind'], [name='sort'], [name='has_finance']"
                    hx-push-url="true">
              <option value="">All states</option>
              {% for st in states %}
              <option value="{{ st }}" {% if st == state %}selected{% endif %}>{{ st }}</option>
              {% endfor %}
            </select>
          </div>

          <!-- Type Filter -->
          <div>
            <label for="kind-filter" class="sr-only">Filter by type</label>
            <select name="kind"
                    id="kind-filter"
                    class="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    hx-get="/sites/search/"
                    hx-trigger="change"
                    hx-target="#sites-table-container"
                    hx-include="[name='q'], [name='state'], [name='sort'], [name='has_finance']"
                    hx-push-url="true">
              <option value="">All types</option>
              {% for k in kinds %}
              <option value="{{ k }}" {% if k == kind %}selected{% endif %}>{{ k|title }}</option>
              {% endfor %}
            </select>
          </div>

          <!-- Finance Filter Checkbox -->
          <div>
            <label class="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white cursor-pointer hover:bg-gray-50 transition">
              <input type="checkbox"
                     name="has_finance"
                     id="finance-filter"
                     value="1"
                     {% if has_finance %}checked{% endif %}
                     hx-get="/sites/search/"
                     hx-trigger="change"
                     hx-target="#sites-table-container"
                     hx-include="[name='q'], [name='state'], [name='kind'], [name='sort']"
                     hx-push-url="true"
                     class="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500">
              <span>Has finance data ({{ finance_sites_count }})</span>
            </label>
          </div>

          <!-- Clear Filters Button -->
          <button type="button"
                  id="clear-filters-btn"
                  class="px-4 py-2 text-sm rounded-lg bg-red-100 text-red-700 hover:bg-red-200 border border-red-300 transition"
                  style="display: {% if query or state or kind or has_finance %}inline-block{% else %}none{% endif %};"
                  onclick="document.getElementById('search-input').value=''; document.getElementById('state-filter').value=''; document.getElementById('kind-filter').value=''; document.getElementById('finance-filter').checked=false; this.style.display='none';"
                  hx-get="/sites/search/"
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-push-url="true">
            Clear all filters
          </button>

        </div>
      </div>
    </div>

  </div>
</div>
```

**Step 2: Verify finder template**

Run:
```bash
wc -l templates/pages/_finder.html
```

Expected: Line count displayed (should be ~150+ lines)

**Step 3: Commit finder section**

```bash
git add templates/pages/_finder.html
git commit -m "feat: add municipality finder with quick-start buttons and collapsible filters"
```

---

## Task 5: Build Results Section Structure

**Files:**
- Create: `templates/pages/_results.html`

**Step 1: Create results section partial**

Create `templates/pages/_results.html`:

```html
<!-- Results Section -->
<div class="bg-gray-50 py-8">
  <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">

    <!-- Results Header -->
    <div class="mb-4 flex flex-wrap items-center justify-between gap-2">
      <div class="text-sm text-gray-600">
        Showing <span class="font-semibold">{{ visible_count }}</span> of <span class="font-semibold">{{ total_count }}</span> municipalities
      </div>
    </div>

    <!-- Two-Column Layout: Table + Map -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Table Column (2/3 width on desktop) -->
      <div class="lg:col-span-2 order-2 lg:order-1">
        <div id="sites-table-container">
          {% include 'pages/_sites_table_only.html' %}
        </div>
      </div>

      <!-- Map Column (1/3 width on desktop, sticky) -->
      <div class="lg:col-span-1 order-1 lg:order-2">
        <div id="sites-map" class="h-80 lg:h-[600px] rounded-lg border-2 border-gray-300 lg:sticky lg:top-4 shadow-sm"></div>
      </div>

    </div>
  </div>
</div>
```

**Step 2: Verify results template**

Run:
```bash
cat templates/pages/_results.html | head -10
```

Expected: First 10 lines displayed

**Step 3: Commit results section**

```bash
git add templates/pages/_results.html
git commit -m "feat: add results section with map and table layout"
```

---

## Task 6: Refactor Main Homepage Template

**Files:**
- Modify: `templates/pages/home.html` (replace entire content)

**Step 1: Replace home.html with new structure**

Replace entire content of `templates/pages/home.html`:

```html
{% extends "pages/base.html" %}

{% block content %}

{% include 'pages/_hero.html' %}

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
        map.setView([39.8283, -98.5795], 4);
        return;
      }

      if (geojson.features.length === 0) {
        map.setView([39.8283, -98.5795], 4);
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
        map.setView([39.8283, -98.5795], 4);
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

        // Find nearest municipalities (this is a simple implementation)
        // In production, you might want a backend endpoint for this
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
    // Get all sites with coordinates from the current page data
    if (!window.sitesGeoJSON || !window.sitesGeoJSON.features) {
      alert('Unable to find nearby municipalities. Please try searching manually.');
      resetLocationButton();
      return;
    }

    // Calculate distances
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
      .slice(0, 1); // Get closest municipality

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
    // Haversine formula for distance between two points
    const R = 6371; // Earth's radius in km
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

**Step 2: Verify template structure**

Run:
```bash
grep -c "{% include" templates/pages/home.html
```

Expected: 3 (three include statements)

**Step 3: Commit refactored homepage**

```bash
git add templates/pages/home.html
git commit -m "refactor: restructure homepage with hero, finder, and results sections"
```

---

## Task 7: Test Homepage Locally

**Files:**
- Test: All homepage functionality

**Step 1: Start development server**

Run:
```bash
just serve
```

Expected: Server starts on port 8000

**Step 2: Open homepage in browser**

Navigate to: `http://localhost:8000/`

Manual test checklist:
- [ ] Hero section displays with headline
- [ ] Newsletter signup form is visible
- [ ] Secondary CTAs (GitHub, Email) are visible
- [ ] "Learn more" details expands/collapses
- [ ] Search input is large and prominent
- [ ] Quick-start buttons are visible
- [ ] "Show advanced filters" toggles filter panel
- [ ] Map displays correctly
- [ ] Table displays municipalities

**Step 3: Test search functionality**

Manual tests:
1. Type in search box → Results should filter via HTMX
2. Click quick-start button → Search should populate and filter
3. Toggle advanced filters → Panel should show/hide
4. Change state filter → Results should update
5. Check "Has finance data" → Results should filter

**Step 4: Test geolocation (if on HTTPS or localhost)**

Manual test:
1. Click "Use My Location"
2. Accept browser permission
3. Verify nearest municipality appears in search

**Step 5: Document any issues**

Create note file if issues found:
```bash
touch docs/homepage-test-issues.md
```

---

## Task 8: Responsive Design Testing

**Files:**
- Test: Responsive behavior across screen sizes

**Step 1: Test mobile viewport (375px)**

Browser DevTools: Set viewport to iPhone SE (375px width)

Manual test checklist:
- [ ] Hero section is readable
- [ ] Newsletter form stacks vertically
- [ ] Search input is full width
- [ ] Quick-start buttons wrap appropriately
- [ ] Map appears above table
- [ ] Table displays correctly (or switches to cards if implemented)

**Step 2: Test tablet viewport (768px)**

Browser DevTools: Set viewport to iPad (768px width)

Manual test checklist:
- [ ] Layout transitions smoothly
- [ ] Two-column layout begins to appear
- [ ] All interactive elements are accessible

**Step 3: Test desktop viewport (1280px+)**

Browser DevTools: Set viewport to 1280px or wider

Manual test checklist:
- [ ] Hero section has good max-width
- [ ] Map is sticky on scroll
- [ ] Two-column layout (2/3 table, 1/3 map) works
- [ ] Filters panel displays properly

---

## Task 9: Accessibility Audit

**Files:**
- Test: Keyboard navigation and screen reader support

**Step 1: Test keyboard navigation**

Manual tests:
1. Tab through all interactive elements
2. Verify focus indicators are visible
3. Test Enter key on buttons
4. Test Space key on buttons
5. Verify skip link works (if implemented)

**Step 2: Test ARIA attributes**

Run in browser console:
```javascript
// Check for missing alt text
document.querySelectorAll('img:not([alt])').length

// Check for missing labels
document.querySelectorAll('input:not([aria-label]):not([id])').length
```

Expected: Both should return 0

**Step 3: Test with screen reader (optional)**

If available, test with:
- VoiceOver (macOS): Cmd+F5
- NVDA (Windows)
- Browser's built-in reader

Verify:
- [ ] Form labels are announced
- [ ] Button purposes are clear
- [ ] Expandable sections announce state

---

## Task 10: Performance Check

**Files:**
- Test: Page load performance

**Step 1: Run Lighthouse audit**

Browser DevTools → Lighthouse:
- Categories: Performance, Accessibility, Best Practices
- Device: Mobile and Desktop

Run audit and check scores.

**Step 2: Check network requests**

Browser DevTools → Network tab:
1. Reload page
2. Check total requests
3. Check total transfer size
4. Verify no failed requests

**Step 3: Test HTMX interactions**

Monitor Network tab while:
1. Typing in search
2. Changing filters
3. Clicking quick-start buttons

Verify only necessary requests are made.

---

## Task 11: Update Documentation

**Files:**
- Create: `docs/homepage-redesign-notes.md`

**Step 1: Create documentation file**

Create `docs/homepage-redesign-notes.md`:

```markdown
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
```

**Step 2: Commit documentation**

```bash
git add docs/homepage-redesign-notes.md
git commit -m "docs: add homepage redesign implementation notes"
```

---

## Task 12: Final Commit and Testing

**Files:**
- All modified files

**Step 1: Run linting and formatting**

Run:
```bash
just lint-fix
just format
```

Expected: All files formatted correctly

**Step 2: Run test suite**

Run:
```bash
just test
```

Expected: All tests pass

**Step 3: Final visual check**

Open `http://localhost:8000/` and do final review:
1. Hero section looks professional
2. Finder is intuitive and accessible
3. Results display properly
4. No console errors
5. All links work
6. Analytics events fire correctly (check browser console for umami events)

**Step 4: Create summary commit**

```bash
git add -A
git commit -m "feat: complete homepage redesign with hero, improved finder, and geolocation

- Add hero section with mission statement and newsletter signup
- Improve municipality finder with prominent search and quick-start buttons
- Add geolocation feature to find nearest municipalities
- Move advanced filters to collapsible panel
- Maintain existing HTMX functionality and URL parameter support
- Preserve map and table display with improved layout
- Add comprehensive documentation

Closes #[issue-number]"
```

---

## Task 13: Create Pull Request (if on feature branch)

**Files:**
- N/A (Git operation)

**Step 1: Push changes to remote**

Run:
```bash
git push origin homepage-ux-improvements
```

Expected: Branch pushed successfully

**Step 2: Create pull request**

Run:
```bash
gh pr create --title "Homepage Redesign: Hero Section, Improved Finder, and Geolocation" --body "$(cat <<'EOF'
## Summary

Complete redesign of the CivicBand homepage to better explain our mission, improve municipality discovery, and provide clear calls-to-action.

### Changes

**Hero Section:**
- Large headline explaining CivicBand's purpose
- Expandable "Learn More" section with mission details
- Newsletter signup form as primary CTA
- Secondary CTAs for GitHub and email contact
- Stats bar showing coverage

**Municipality Finder:**
- Larger, more prominent search input
- "Use My Location" button with geolocation
- Quick-start buttons for popular municipalities
- Collapsible advanced filters (hidden by default)

**Results Display:**
- Improved layout with sticky map
- Clear result counts
- Maintained HTMX functionality

**New Features:**
- Browser Geolocation API integration
- Haversine distance calculation for nearest municipality
- Responsive design across all screen sizes
- Accessibility improvements

### Testing Checklist

- [x] All interactive elements work (search, filters, buttons)
- [x] HTMX updates function correctly
- [x] Map displays and updates properly
- [x] Geolocation feature works
- [x] Responsive design tested (mobile, tablet, desktop)
- [x] Keyboard navigation works
- [x] No console errors
- [x] Linting and formatting pass
- [x] All tests pass

### Documentation

- Design doc: `docs/plans/2026-02-22-homepage-redesign-design.md`
- Implementation notes: `docs/homepage-redesign-notes.md`
- Backup template: `templates/pages/home_old.html`

### Screenshots

[Add screenshots of before/after if desired]

EOF
)"
```

**Step 3: Verify PR created**

Run:
```bash
gh pr view
```

Expected: PR details displayed

---

## Completion Checklist

Before considering this implementation complete, verify:

- [ ] All template files created and structured properly
- [ ] Homepage displays hero, finder, and results sections
- [ ] Newsletter signup form works
- [ ] Search functionality works via HTMX
- [ ] Quick-start buttons populate search
- [ ] Geolocation feature finds nearest municipality
- [ ] Advanced filters toggle and work correctly
- [ ] Map displays and updates correctly
- [ ] Table displays municipalities
- [ ] Responsive design works on mobile, tablet, desktop
- [ ] Keyboard navigation works throughout
- [ ] No console errors
- [ ] HTMX requests work as expected
- [ ] URL parameters preserved
- [ ] Analytics events fire correctly
- [ ] Code is linted and formatted
- [ ] Tests pass
- [ ] Documentation written
- [ ] Backup template saved
- [ ] Changes committed with clear messages
- [ ] Pull request created (if applicable)

---

## Notes for Implementer

**Testing Geolocation:**
- Geolocation only works on HTTPS or localhost
- In development, use `http://localhost:8000/`
- In production, ensure site is served over HTTPS
- Browser will prompt for permission on first use

**Quick-Start Municipalities:**
- Current selection: Oakland, Berkeley, SF, Chicago, NY
- These can be changed in `_finder.html`
- Consider making configurable via Django settings in future

**Performance:**
- Geolocation distance calculation runs in browser
- For better performance with many municipalities, consider server-side endpoint
- Current implementation filters from existing page data

**Browser Support:**
- Geolocation API supported in all modern browsers
- Fallback messages for unsupported browsers
- `<details>` element supported in all modern browsers (no JS required)

**Accessibility:**
- All interactive elements have keyboard support
- ARIA labels added where needed
- Focus indicators visible
- Screen reader compatible
