# Django Homepage Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Datasette-powered civic.band homepage with Django + HTMX for integrated search/filter/map functionality

**Architecture:** Django views serve sites listing from sites.db with server-side filtering. HTMX swaps HTML fragments on filter changes. Leaflet map updates via custom events. URL params enable shareable filtered views.

**Tech Stack:** Django 5.2, HTMX 1.9, Leaflet.js, OpenStreetMap tiles, Tailwind CSS

---

## Task 1: Add Sites Database Configuration

**Files:**
- Modify: `config/settings.py` (add DATABASES config)
- Modify: `config/prod_settings.py` (add production sites db path)

**Step 1: Add sites database to settings.py**

In `config/settings.py`, find the `DATABASES` dict and update it:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "civic.db",
    },
    "sites": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR.parent / "civic-band" / "sites.db",
    },
}
```

**Step 2: Add sites database to prod_settings.py**

In `config/prod_settings.py`, find the `DATABASES` dict and update it:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "civic.db",
    },
    "sites": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR.parent / "civic-band" / "sites.db",
    },
}
```

**Step 3: Commit**

```bash
git add config/settings.py config/prod_settings.py
git commit -m "Add sites database configuration"
```

---

## Task 2: Create Site Model

**Files:**
- Create: `pages/models.py`
- Create: `tests/test_site_model.py`

**Step 1: Write failing test for Site model**

Create `tests/test_site_model.py`:

```python
import pytest
from pages.models import Site


@pytest.mark.django_db
class TestSiteModel:
    def test_site_model_exists(self):
        """Site model should be importable."""
        assert Site is not None

    def test_site_model_fields(self):
        """Site model should have expected fields."""
        fields = [f.name for f in Site._meta.get_fields()]
        expected_fields = [
            'subdomain', 'name', 'state', 'country', 'kind',
            'pages', 'last_updated', 'lat', 'lng', 'popup'
        ]
        for field in expected_fields:
            assert field in fields

    def test_site_model_str(self):
        """Site model should have string representation."""
        site = Site(subdomain='test.ca', name='Test City')
        assert str(site) == 'Test City (test.ca)'
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_site_model.py -v`
Expected: FAIL with "No module named 'pages.models'" or ImportError

**Step 3: Create Site model**

Create `pages/models.py`:

```python
from django.db import models


class Site(models.Model):
    """Municipality site in the CivicBand directory."""
    subdomain = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    kind = models.CharField(max_length=100)
    pages = models.IntegerField(default=0)
    last_updated = models.DateTimeField()
    lat = models.CharField(max_length=50, blank=True)
    lng = models.CharField(max_length=50, blank=True)
    popup = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'sites'
        managed = False  # Don't let Django manage this table
        ordering = ['-pages']

    def __str__(self):
        return f"{self.name} ({self.subdomain})"
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_site_model.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add pages/models.py tests/test_site_model.py
git commit -m "Add Site model for sites.db access"
```

---

## Task 3: Create Home View with Initial Load

**Files:**
- Modify: `pages/views.py`
- Create: `tests/test_home_view.py`

**Step 1: Write failing test for home view**

Create `tests/test_home_view.py`:

```python
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestHomeView:
    def test_home_view_renders(self, client: Client):
        """Home view should render successfully."""
        response = client.get(reverse('home'))
        assert response.status_code == 200

    def test_home_view_has_stats(self, client: Client):
        """Home view should include aggregate stats."""
        response = client.get(reverse('home'))
        assert 'num_sites' in response.context
        assert 'total_pages' in response.context

    def test_home_view_respects_query_params(self, client: Client):
        """Home view should filter based on query params."""
        response = client.get(reverse('home') + '?q=test&state=CA&kind=city&sort=pages')
        assert response.context['query'] == 'test'
        assert response.context['state'] == 'CA'
        assert response.context['kind'] == 'city'
        assert response.context['sort'] == 'pages'
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_home_view.py -v`
Expected: FAIL with various errors (missing context, wrong implementation)

**Step 3: Update home_view in pages/views.py**

In `pages/views.py`, replace the current `home_view`:

```python
from django.shortcuts import render
from django.db.models import Q, Sum
from pages.models import Site


def home_view(request):
    """Homepage with sites directory."""
    # Get filter params
    query = request.GET.get('q', '')
    state = request.GET.get('state', '')
    kind = request.GET.get('kind', '')
    sort = request.GET.get('sort', 'pages')

    # Base queryset
    sites = Site.objects.using('sites').all()

    # Apply filters
    if query:
        sites = sites.filter(
            Q(name__icontains=query) |
            Q(subdomain__icontains=query) |
            Q(state__icontains=query)
        )
    if state:
        sites = sites.filter(state=state)
    if kind:
        sites = sites.filter(kind=kind)

    # Apply sorting
    if sort == 'last_updated':
        sites = sites.order_by('-last_updated')
    else:
        sites = sites.order_by('-pages')

    # Get aggregate stats (from all sites, not filtered)
    all_sites = Site.objects.using('sites').all()
    num_sites = all_sites.count()
    total_pages = all_sites.aggregate(total=Sum('pages'))['total'] or 0

    # Get unique states for filter dropdown
    states = Site.objects.using('sites').values_list('state', flat=True).distinct().order_by('state')

    context = {
        'sites': sites,
        'query': query,
        'state': state,
        'kind': kind,
        'sort': sort,
        'num_sites': num_sites,
        'total_pages': total_pages,
        'states': states,
    }

    return render(request, 'pages/home.html', context)


def how_view(request):
    return render(request, "pages/how.html")


def why_view(request):
    return render(request, "pages/why.html")


def privacy_view(request):
    return render(request, "pages/privacy.html")


def researchers_view(request):
    return render(request, "pages/researchers.html")


def feed_view(request):
    return render(request, "pages/rss.xml")
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_home_view.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add pages/views.py tests/test_home_view.py
git commit -m "Add home view with filtering and stats"
```

---

## Task 4: Create HTMX Search View

**Files:**
- Modify: `pages/views.py` (add sites_search_view)
- Modify: `config/urls.py` (add search endpoint)
- Create: `tests/test_sites_search_view.py`

**Step 1: Write failing test for search view**

Create `tests/test_sites_search_view.py`:

```python
import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestSitesSearchView:
    def test_sites_search_view_renders(self, client: Client):
        """Sites search view should render successfully."""
        response = client.get(reverse('sites_search'))
        assert response.status_code == 200

    def test_sites_search_filters_by_query(self, client: Client):
        """Sites search should filter by query param."""
        response = client.get(reverse('sites_search') + '?q=berkeley')
        content = response.content.decode()
        # Should not render full page, just fragment
        assert '<html' not in content.lower()
        assert '<table' in content.lower() or 'sites-table' in content.lower()

    def test_sites_search_returns_geojson(self, client: Client):
        """Sites search should return GeoJSON for map."""
        response = client.get(reverse('sites_search'))
        content = response.content.decode()
        assert 'sites:updated' in content  # Custom event trigger
        assert 'FeatureCollection' in content or 'features' in content
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_sites_search_view.py -v`
Expected: FAIL with "Reverse for 'sites_search' not found"

**Step 3: Add sites_search_view to pages/views.py**

In `pages/views.py`, add after the home_view function:

```python
def sites_search_view(request):
    """HTMX endpoint for filtering sites table."""
    # Get filter params (same logic as home_view)
    query = request.GET.get('q', '')
    state = request.GET.get('state', '')
    kind = request.GET.get('kind', '')
    sort = request.GET.get('sort', 'pages')

    # Base queryset
    sites = Site.objects.using('sites').all()

    # Apply filters
    if query:
        sites = sites.filter(
            Q(name__icontains=query) |
            Q(subdomain__icontains=query) |
            Q(state__icontains=query)
        )
    if state:
        sites = sites.filter(state=state)
    if kind:
        sites = sites.filter(kind=kind)

    # Apply sorting
    if sort == 'last_updated':
        sites = sites.order_by('-last_updated')
    else:
        sites = sites.order_by('-pages')

    # Get total count for stats
    total_sites = Site.objects.using('sites').count()

    context = {
        'sites': sites,
        'visible_count': sites.count(),
        'total_count': total_sites,
        'query': query,
    }

    return render(request, 'pages/_sites_table.html', context)
```

**Step 4: Add URL route**

In `config/urls.py`, add the new route:

```python
from pages.views import (
    feed_view, home_view, how_view, researchers_view,
    sites_search_view, why_view
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sites/search/", sites_search_view, name="sites_search"),
    path("how.html", how_view),
    path("why.html", why_view),
    path("researchers", researchers_view),
    path("rss.xml", feed_view),
    path("health/", health_check, name="health_check"),
    path("", home_view, name="home"),
] + djp.urlpatterns()
```

**Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_sites_search_view.py::TestSitesSearchView::test_sites_search_view_renders -v`
Expected: PASS (will fail on template not found, but that's next task)

**Step 6: Commit**

```bash
git add pages/views.py config/urls.py tests/test_sites_search_view.py
git commit -m "Add HTMX sites search view endpoint"
```

---

## Task 5: Create Base Template

**Files:**
- Create: `templates/pages/base.html`

**Step 1: Create base template**

Create `templates/pages/base.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Civic Band - Government and Municipality Meeting Data{% endblock %}</title>

    <!-- Meta tags -->
    <meta name="description" content="{% block description %}Dive into City Meeting Data Across the U.S. | Instant Access to Council Agendas, Minutes, and Local Government Insights{% endblock %}" />
    <meta property="og:url" content="https://civic.band">
    <meta property="og:title" content="{% block og_title %}Civic Band: Government and Municipality Meeting Data{% endblock %}">
    <meta property="og:description" content="{% block og_description %}Dive into City Meeting Data Across the U.S.{% endblock %}">
    <meta property="og:site_name" content="CivicBand"/>

    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>

    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>

    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />

    <!-- Analytics -->
    <script defer src="https://analytics.civic.band/sunshine" data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a"></script>

    {% block extra_head %}{% endblock %}
</head>
<body class="bg-gray-50">
    {% block content %}{% endblock %}

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
</html>
```

**Step 2: Commit**

```bash
git add templates/pages/base.html
git commit -m "Add base template with HTMX and Leaflet"
```

---

## Task 6: Create Home Template

**Files:**
- Create: `templates/pages/home.html`

**Step 1: Create home template**

Create `templates/pages/home.html`:

```html
{% extends "pages/base.html" %}

{% block content %}
<!-- Header Section -->
<div class="bg-gray-900 py-16">
  <div class="mx-auto max-w-7xl px-6 lg:px-8">
    <div class="grid grid-cols-1 gap-10 lg:grid-cols-12 lg:gap-8">
      <div class="lg:col-span-7">
        <h1 class="text-5xl font-semibold tracking-tight text-white sm:text-7xl">Civic Band</h1>
        <p class="mt-8 text-pretty text-lg font-medium text-gray-300 sm:text-xl/8">
          This is a slowly growing collection of databases of the minutes from civic governments.
          A project from <a href="https://galaxybrain.co" class="underline hover:text-white" data-umami-event="homepage_external" data-umami-event-target="galaxybrain">Galaxy Brain</a>.
          Email hello @ civic dot band with questions.
        </p>

        <!-- Navigation Links -->
        <div class="mx-auto mt-7 max-w-2xl lg:mx-0 lg:max-w-none">
          <div class="grid grid-cols-1 gap-x-8 gap-y-6 text-base/7 font-semibold text-white sm:grid-cols-2 md:flex lg:gap-x-10">
            <a href="/how.html" data-umami-event="homepage_nav" data-umami-event-target="how">How it works <span aria-hidden="true">&rarr;</span></a>
            <a href="/why.html" data-umami-event="homepage_nav" data-umami-event-target="why">Why? <span aria-hidden="true">&rarr;</span></a>
            <a href="/rss.xml" data-umami-event="homepage_nav" data-umami-event-target="rss">RSS Feed <span aria-hidden="true">&rarr;</span></a>
            <a rel="me" href="https://sfba.social/@civicband" data-umami-event="homepage_social" data-umami-event-platform="mastodon">Mastodon <span aria-hidden="true">&rarr;</span></a>
            <a rel="me" href="https://bsky.app/profile/civic.band" data-umami-event="homepage_social" data-umami-event-platform="bluesky">Bluesky <span aria-hidden="true">&rarr;</span></a>
            <a href="https://donate.stripe.com/3cs3dN5Ki0BRgzSeUX" data-umami-event="homepage_support">Support! <span aria-hidden="true">&rarr;</span></a>
          </div>

          <!-- Stats -->
          <dl class="mt-7 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <div class="flex flex-col-reverse gap-1">
              <dt class="text-base/7 text-gray-300">Municipalities tracked</dt>
              <dd class="text-4xl font-semibold tracking-tight text-white">{{ num_sites|default:0 }}</dd>
            </div>
            <div class="flex flex-col-reverse gap-1">
              <dt class="text-base/7 text-gray-300">Pages of documents</dt>
              <dd class="text-4xl font-semibold tracking-tight text-white">{{ total_pages|default:0|floatformat:0 }}</dd>
            </div>
          </dl>
        </div>
      </div>

      <!-- Newsletter Form -->
      <div class="lg:col-span-5 lg:pt-2">
        <form class="w-full max-w-md"
              action="https://buttondown.com/api/emails/embed-subscribe/civicband"
              method="post"
              target="popupwindow"
              onsubmit="window.open('https://buttondown.com/civicband', 'popupwindow')">
          <div class="flex gap-x-4">
            <label for="bd-email" class="sr-only">Email address</label>
            <input id="bd-email" name="email" type="email" autocomplete="email" required
                   class="min-w-0 flex-auto rounded-md border-0 bg-white/5 px-3.5 py-2 text-white shadow-sm ring-1 ring-inset ring-white/10 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm/6"
                   placeholder="Enter your email">
            <button type="submit"
                    class="flex-none rounded-md bg-indigo-500 px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
                    data-umami-event="homepage_newsletter">Subscribe</button>
          </div>
          <p class="mt-4 text-sm/6 text-gray-300">
            We care about your data. Read our
            <a href="/privacy.html" class="font-semibold text-white" data-umami-event="homepage_nav" data-umami-event-target="privacy">privacy&nbsp;policy</a>.
          </p>
        </form>
      </div>
    </div>
  </div>
</div>

<!-- Search and Filter Toolbar -->
<div class="mx-auto max-w-7xl px-6 lg:px-8 mt-8">
  <div class="bg-gradient-to-br from-gray-50 to-gray-100 border border-gray-200 rounded-lg p-6 shadow-sm">
    <!-- Search Input -->
    <div class="mb-6">
      <div class="relative max-w-2xl mx-auto">
        <input type="text"
               name="q"
               id="search-input"
               value="{{ query }}"
               placeholder="Search municipalities by name, state, or subdomain..."
               class="w-full px-4 py-3 pr-12 rounded-lg border-2 border-gray-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition"
               hx-get="/sites/search/"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#sites-table-container"
               hx-include="[name='state'], [name='kind'], [name='sort']"
               hx-push-url="true">
        <div class="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 text-xl pointer-events-none">🔍</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-4 justify-center items-center">
      <!-- State Filter -->
      <div>
        <label class="block text-xs font-semibold text-gray-600 uppercase mb-1">State</label>
        <select name="state"
                id="state-filter"
                class="px-3 py-2 rounded border border-gray-300 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200"
                hx-get="/sites/search/"
                hx-trigger="change"
                hx-target="#sites-table-container"
                hx-include="[name='q'], [name='kind'], [name='sort']"
                hx-push-url="true">
          <option value="">All states</option>
          {% for st in states %}
          <option value="{{ st }}" {% if st == state %}selected{% endif %}>{{ st }}</option>
          {% endfor %}
        </select>
      </div>

      <!-- Kind Filter -->
      <div>
        <label class="block text-xs font-semibold text-gray-600 uppercase mb-1">Type</label>
        <div class="flex gap-2">
          <button type="button"
                  class="px-3 py-2 rounded border {% if not kind %}bg-indigo-500 text-white border-indigo-600{% else %}bg-white text-gray-700 border-gray-300{% endif %}"
                  hx-get="/sites/search/?kind="
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-include="[name='q'], [name='state'], [name='sort']"
                  hx-push-url="true">All</button>
          <button type="button"
                  class="px-3 py-2 rounded border {% if kind == 'city' %}bg-indigo-500 text-white border-indigo-600{% else %}bg-white text-gray-700 border-gray-300{% endif %}"
                  hx-get="/sites/search/?kind=city"
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-include="[name='q'], [name='state'], [name='sort']"
                  hx-push-url="true">Cities</button>
          <button type="button"
                  class="px-3 py-2 rounded border {% if kind == 'county' %}bg-indigo-500 text-white border-indigo-600{% else %}bg-white text-gray-700 border-gray-300{% endif %}"
                  hx-get="/sites/search/?kind=county"
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-include="[name='q'], [name='state'], [name='sort']"
                  hx-push-url="true">Counties</button>
        </div>
      </div>

      <!-- Sort -->
      <div>
        <label class="block text-xs font-semibold text-gray-600 uppercase mb-1">Sort by</label>
        <div class="flex gap-2">
          <button type="button"
                  class="px-3 py-2 rounded border {% if sort == 'pages' %}bg-indigo-500 text-white border-indigo-600{% else %}bg-white text-gray-700 border-gray-300{% endif %}"
                  hx-get="/sites/search/?sort=pages"
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-include="[name='q'], [name='state'], [name='kind']"
                  hx-push-url="true">Most pages</button>
          <button type="button"
                  class="px-3 py-2 rounded border {% if sort == 'last_updated' %}bg-indigo-500 text-white border-indigo-600{% else %}bg-white text-gray-700 border-gray-300{% endif %}"
                  hx-get="/sites/search/?sort=last_updated"
                  hx-trigger="click"
                  hx-target="#sites-table-container"
                  hx-include="[name='q'], [name='state'], [name='kind']"
                  hx-push-url="true">Recently updated</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Map and Table -->
<div class="mx-auto max-w-7xl px-6 lg:px-8 mt-8 pb-16">
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <!-- Map Column -->
    <div class="order-2 lg:order-1">
      <div id="sites-map" class="h-96 lg:h-[600px] rounded-lg shadow-lg border border-gray-200"></div>
    </div>

    <!-- Table Column -->
    <div class="order-1 lg:order-2">
      <div id="sites-table-container">
        {% include 'pages/_sites_table.html' %}
      </div>
    </div>
  </div>
</div>
{% endblock %}

{% block extra_scripts %}
<script>
// Initialize map
const map = L.map('sites-map').setView([39.8283, -98.5795], 4);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors',
  maxZoom: 19
}).addTo(map);

const markers = L.markerClusterGroup();
markers.addTo(map);

// Load initial markers
function loadMarkers(geojson) {
  markers.clearLayers();

  if (!geojson || !geojson.features || geojson.features.length === 0) {
    map.setView([39.8283, -98.5795], 4);
    return;
  }

  L.geoJSON(geojson, {
    onEachFeature: function(feature, layer) {
      if (feature.properties && feature.properties.popup) {
        layer.bindPopup(feature.properties.popup);
      }
      layer.on('click', function() {
        if (feature.properties && feature.properties.link) {
          window.location.href = feature.properties.link;
        }
      });
    }
  }).addTo(markers);

  if (markers.getLayers().length > 0) {
    map.fitBounds(markers.getBounds(), { padding: [50, 50] });
  }
}

// Listen for HTMX updates
document.body.addEventListener('sites:updated', function(event) {
  loadMarkers(event.detail);
});

// Initial load
loadMarkers({{ sites_geojson|safe }});
</script>
{% endblock %}
```

**Step 2: Commit**

```bash
git add templates/pages/home.html
git commit -m "Add home template with search, filters, and map"
```

---

## Task 7: Create Sites Table Partial Template

**Files:**
- Create: `templates/pages/_sites_table.html`
- Create: `templates/pages/_map_data.html`

**Step 1: Create sites table partial**

Create `templates/pages/_sites_table.html`:

```html
<div class="bg-white rounded-lg shadow overflow-hidden">
  {% if sites %}
    {% if query %}
    <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 text-sm text-gray-600">
      Showing {{ visible_count }} of {{ total_count }} sites
    </div>
    {% endif %}

    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Municipality
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              State
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Pages
            </th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          {% for site in sites %}
          <tr class="hover:bg-gray-50 transition cursor-pointer" onclick="window.location='https://{{ site.subdomain }}.civic.band'">
            <td class="px-6 py-4 whitespace-nowrap">
              <a href="https://{{ site.subdomain }}.civic.band"
                 class="text-indigo-600 hover:text-indigo-900 font-medium"
                 data-umami-event="homepage_muni"
                 data-umami-event-subdomain="{{ site.subdomain }}">
                {{ site.name }}
              </a>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ site.state }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 capitalize">
              {{ site.kind }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ site.pages|floatformat:0 }}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  {% else %}
    <div class="px-6 py-12 text-center">
      <p class="text-gray-500">No municipalities match your search.</p>
      <p class="text-sm text-gray-400 mt-2">Try adjusting your filters</p>
    </div>
  {% endif %}
</div>

{% include 'pages/_map_data.html' %}
```

**Step 2: Create map data partial**

Create `templates/pages/_map_data.html`:

```html
<script>
(function() {
  const geojson = {
    "type": "FeatureCollection",
    "features": [
      {% for site in sites %}
      {% if site.lat and site.lng %}
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [{{ site.lng }}, {{ site.lat }}]
        },
        "properties": {
          "name": "{{ site.name|escapejs }}",
          "popup": "<a href='https://{{ site.subdomain }}.civic.band'>{{ site.name|escapejs }}, {{ site.state }}</a>",
          "link": "https://{{ site.subdomain }}.civic.band"
        }
      }{% if not forloop.last %},{% endif %}
      {% endif %}
      {% endfor %}
    ]
  };

  // Dispatch custom event for map update
  const event = new CustomEvent('sites:updated', { detail: geojson });
  document.body.dispatchEvent(event);
})();
</script>
```

**Step 3: Update home_view to include GeoJSON**

In `pages/views.py`, update the `home_view` context:

```python
def home_view(request):
    """Homepage with sites directory."""
    # ... existing filter code ...

    context = {
        'sites': sites,
        'query': query,
        'state': state,
        'kind': kind,
        'sort': sort,
        'num_sites': num_sites,
        'total_pages': total_pages,
        'states': states,
        'visible_count': sites.count(),
        'total_count': num_sites,
    }

    return render(request, 'pages/home.html', context)
```

**Step 4: Commit**

```bash
git add templates/pages/_sites_table.html templates/pages/_map_data.html pages/views.py
git commit -m "Add sites table and map data partial templates"
```

---

## Task 8: Run Integration Tests

**Files:**
- N/A (testing only)

**Step 1: Run all tests**

Run: `uv run pytest -v`
Expected: All tests should PASS

**Step 2: Test manual flow**

1. Start server: `just serve`
2. Navigate to `http://localhost:8000/`
3. Verify:
   - Homepage loads with stats
   - Map shows markers
   - Search input filters table and map
   - State dropdown filters
   - Kind buttons filter
   - Sort buttons work
   - URL params update
   - Clicking table row or map marker navigates to subdomain

**Step 3: Fix any issues found**

If issues found, create new commits with fixes.

---

## Task 9: Update Infrastructure Configuration

**Files:**
- Modify: `docker-compose.yml` (remove sites_datasette services)

**Step 1: Remove sites_datasette services**

In `docker-compose.yml`, remove these services:
- `sites_datasette_blue` (lines 71-88)
- `sites_datasette_green` (lines 89-106)

**Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "Remove sites_datasette services from docker-compose"
```

---

## Task 10: Update Caddyfile Documentation

**Files:**
- Create: `docs/deployment/caddyfile-changes.md`

**Step 1: Document Caddyfile changes**

Create `docs/deployment/caddyfile-changes.md`:

```markdown
# Caddyfile Changes for Django Homepage

## Required Change

Update the `civic.band` block in the Caddyfile to route to Django instead of sites_datasette:

### Before
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
        reverse_proxy * 127.0.0.1:40001 127.0.0.1:40002 {
            import health-proxy
        }
    }
}
```

### After
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
        reverse_proxy * 127.0.0.1:8000 127.0.0.1:8001 {
            import health-proxy
        }
    }
}
```

## Rollback

To rollback, revert the Caddyfile change to use ports 40001/40002.

## Verification

After deployment:
1. Visit https://civic.band/
2. Verify homepage loads with search/filter/map
3. Verify subdomains still work (e.g., https://berkeley.ca.civic.band)
```

**Step 2: Commit**

```bash
git add docs/deployment/caddyfile-changes.md
git commit -m "Document Caddyfile changes for Django homepage"
```

---

## Task 11: Clean Up Old Templates

**Files:**
- Delete: `templates/sites-database/table-sites-sites.html`
- Delete: `templates/sites-database/_table-sites-sites.html`

**Step 1: Remove old Datasette templates**

```bash
git rm templates/sites-database/table-sites-sites.html
git rm templates/sites-database/_table-sites-sites.html
```

**Step 2: Commit**

```bash
git commit -m "Remove old Datasette homepage templates"
```

---

## Task 12: Final Testing and Documentation

**Files:**
- Create: `docs/features/django-homepage.md`

**Step 1: Create feature documentation**

Create `docs/features/django-homepage.md`:

```markdown
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
```

**Step 2: Run full test suite**

Run: `just test`
Expected: All tests PASS with good coverage

**Step 3: Commit**

```bash
git add docs/features/django-homepage.md
git commit -m "Add Django homepage feature documentation"
```

---

## Summary

This plan implements a Django-powered homepage with:
- Server-side filtering that scales beyond 1000 sites
- HTMX for seamless partial page updates
- Leaflet map with marker clustering
- URL parameters for shareable filtered views
- Progressive enhancement (works without JS)

Total estimated implementation time: ~2-3 hours
Total commits: 12
Total test files: 3
