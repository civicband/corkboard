"""Context processor providing the canonical URL for the main Django site.

Phase 1 of the sharing plan: every page advertises one canonical permalink.
Rules:

- The canonical is always absolute and built from ``request.build_absolute_uri``.
- Query strings are dropped (``?q=``, ``?sort=``, ``?page=`` are views of the
  same content, not distinct documents).
- The HTMX-only ``/sites/search/`` endpoint canonicalizes to ``/?<query>``,
  mirroring the redirect ``pages.views.sites_search_view`` issues on direct
  navigation. A POST or HTMX request must never advertise its own URL.

``canonical_url`` is always defined so templates can render unconditionally,
including fragments rendered outside a request (where it is empty).

Phase 2 (sharing plan, workstream 2) adds ``og_*`` values for the Django
search page - the homepage with query/filter parameters, which is where
``/sites/search/`` redirects. It gets a rendered unfurl card from
``plugins/og_card.py``, the same endpoint the municipality subdomains use.
Every other Django page leaves the template's ``og_title``/
``og_description`` blocks in charge and emits no card.
"""

from urllib.parse import urlencode

from django.urls import reverse

from pages.utils import CANONICAL_QUERY_PARAMS

# Endpoint that only exists for HTMX; its content lives at "/".
SITES_SEARCH_PATH = reverse("sites_search")


def canonical_url_for_request(request) -> str:
    """Return the absolute canonical URL for a Django request."""
    if request is None:
        return ""

    if request.path == SITES_SEARCH_PATH:
        params = {
            key: request.GET.get(key)
            for key in CANONICAL_QUERY_PARAMS
            if request.GET.get(key)
        }
        query = urlencode(params)
        return request.build_absolute_uri("/" + (f"?{query}" if query else ""))

    return request.build_absolute_uri(request.path)


def canonical(request):
    return {"canonical_url": canonical_url_for_request(request)}


def og_meta(request):
    """``og_*`` values for a filtered homepage (the Django search page).

    Returns ``{}`` for every other page, including a bare homepage: the
    default card says nothing about a search that was not performed.
    """
    if request is None:
        return {}
    query = (request.GET.get("q") or "").strip()
    if not query:
        return {}

    # Imported lazily: plugins/ imports Datasette, which the plain Django
    # surface does not otherwise load. Keeping it here bounds that to the one
    # page that needs a card.
    from plugins.og_card import municipality_search_card  # noqa: PLC0415

    return municipality_search_card(
        request.get_host(), query, scheme=request.scheme or "https"
    )
