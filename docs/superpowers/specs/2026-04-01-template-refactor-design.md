# Template Refactor: Consistent Styling with Template Inheritance

## Goal

Refactor `templates/pages/` so all pages share a navbar and footer via template inheritance, with consistent styling for content pages.

## Current State

- `base.html` provides HTML boilerplate, Tailwind, HTMX, Leaflet, analytics, and Tawk.to
- `home.html` and `map.html` extend `base.html`
- `how.html`, `why.html`, `researchers.html` are standalone (full HTML, duplicated boilerplate)
- `index.html` is a near-duplicate of `home.html`; `home_old.html` is legacy
- Navigation only exists on the homepage (via `_hero.html` → `_navigation.html`)
- No footer template exists; Tawk.to chat widget is duplicated inline across pages

## Template Hierarchy

```
base.html (enhanced — navbar, footer, all shared assets)
├── home.html (extends base, overrides navbar block with full hero)
├── map.html (extends base, custom content)
└── _content_page.html (extends base, unified content page layout)
    ├── how.html
    ├── why.html
    └── researchers.html
```

## Changes

### 1. Enhanced `base.html`

Add navbar and footer around the content block:

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

  <!-- existing leaflet JS, tawk.to, extra_scripts -->
</body>
```

The `{% block navbar %}` allows `home.html` to override the entire navbar area with its hero section (which already includes navigation internally).

### 2. Restyle `_navigation.html` for Standalone Use

Currently styled for dark indigo hero background (white text). Needs to work as a standalone top bar on non-hero pages.

New approach: wrap in an indigo background strip (`bg-indigo-700`) with padding, so it's visually consistent with the hero branding but works independently. Add the CivicBand logo/name as a home link.

On the homepage, the entire `{% block navbar %}` is overridden by the hero, so this standalone version is never shown there.

### 3. New `_footer.html`

Standard footer with indigo background matching the navbar branding. Contains:

- CivicBand logo/site name (links home)
- Navigation links: How it works, Why, For Researchers, RSS Feed
- Social links: GitHub, Mastodon, Bluesky
- Newsletter signup (Buttondown form, reused from hero)
- Donate link (OpenCollective)
- Copyright line (Raft Foundation)
- Privacy policy link

### 4. New `_content_page.html` Intermediate Template

Extends `base.html`. Provides the unified content page layout:

```django
{% extends "pages/base.html" %}

{% block content %}
<div class="bg-white px-6 py-16 lg:px-8">
  <div class="mx-auto max-w-3xl text-base/7 text-gray-700">
    <h1 class="text-pretty text-4xl font-semibold tracking-tight text-gray-900 sm:text-5xl">
      {% block page_title %}{% endblock %}
    </h1>
    {% block page_subtitle %}<!-- optional intro paragraph, e.g. <p class="mt-6 text-xl/8">...</p> -->{% endblock %}
    <div class="mt-10 max-w-2xl">
      {% block page_content %}{% endblock %}
    </div>
  </div>
</div>
{% endblock %}
```

Content pages become minimal — just extend `_content_page.html` and fill in blocks:
- `{% block title %}` (HTML title, from base.html)
- `{% block description %}` (meta description, from base.html)
- `{% block page_title %}` (visible H1)
- `{% block page_subtitle %}` (optional intro paragraph)
- `{% block page_content %}` (main body content)

### 5. Content Page Conversions

Each of `how.html`, `why.html`, `researchers.html`:

- Change from standalone HTML to `{% extends "pages/_content_page.html" %}`
- Move content into `{% block page_content %}`
- Remove duplicated boilerplate (DOCTYPE, head, analytics, Tawk.to)
- Remove "< Back" links (navbar now provides navigation)
- Set appropriate `{% block title %}` and `{% block description %}`

### 6. `home.html` Changes

- Override `{% block navbar %}` with the full hero section (`{% include 'pages/_hero.html' %}`)
- The hero already includes `_navigation.html` internally, so navigation is preserved
- Standard footer appears below the homepage content (inherited from base.html)

### 7. `map.html` Changes

- Gets navbar and footer automatically from base.html (currently has neither)
- No other changes needed

### 8. Cleanup

- Delete `index.html` (duplicate of `home.html`)
- Delete `home_old.html` (legacy)
- Verify no views/URLs reference the deleted templates

## Files Modified

| File | Action |
|------|--------|
| `templates/pages/base.html` | Add navbar block, footer block, flex layout |
| `templates/pages/_navigation.html` | Restyle as standalone top bar with indigo background |
| `templates/pages/_footer.html` | **New** — standard footer partial |
| `templates/pages/_content_page.html` | **New** — intermediate template for content pages |
| `templates/pages/home.html` | Override navbar block with hero include |
| `templates/pages/map.html` | No changes (inherits navbar/footer automatically) |
| `templates/pages/how.html` | Convert to extend `_content_page.html` |
| `templates/pages/why.html` | Convert to extend `_content_page.html` |
| `templates/pages/researchers.html` | Convert to extend `_content_page.html` |
| `templates/pages/index.html` | **Delete** |
| `templates/pages/home_old.html` | **Delete** |

## Out of Scope

- Changing the homepage layout or hero section content
- Modifying the search/filter/map functionality
- CSS framework changes (staying with Tailwind CDN)
- Adding new pages
