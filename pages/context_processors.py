"""Template context shared by the bare-domain CivicBand pages.

Includes the canonical permalink for Django pages and the default OG card
image. The Datasette pages get the same values from their own plugins.

Canonical rules:

- The canonical is always absolute and built from ``request.build_absolute_uri``.
- Query strings are dropped (``?q=``, ``?sort=``, ``?page=`` are views of the
  same content, not distinct documents).
- The HTMX-only ``/sites/search/`` endpoint canonicalizes to ``/?<query>``,
  mirroring the redirect ``pages.views.sites_search_view`` issues on direct
  navigation. A POST or HTMX request must never advertise its own URL.

``canonical_url`` is always defined so templates can render unconditionally,
including fragments rendered outside a request (where it is empty).
"""

from urllib.parse import urlencode

from django.urls import reverse

from pages.utils import CANONICAL_QUERY_PARAMS
from plugins.og_meta import global_card_url

# Endpoint that only exists for HTMX; its content lives at "/".
SITES_SEARCH_PATH = reverse("sites_search")

OG_DEFAULT_IMAGE = global_card_url()


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


def og_defaults(request):
    return {"og_default_image": OG_DEFAULT_IMAGE}
