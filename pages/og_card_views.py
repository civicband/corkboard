"""Django-hosted Open Graph card endpoint (bare ``civic.band``).

The municipality subdomains render their cards through the Datasette plugin
route (``plugins/og_card.py``, ``/-/og.png``). The homepage search lives on
the bare domain, which Django serves, so it needs a same-origin endpoint.
This view is a thin Django shell over the *same* renderer, cache and guard so
there is exactly one card implementation and one cache:

- URL shape: ``/og-card.png?k=search&m=CivicBand&q=<query>&v=<version>``
- caching: identical disk cache and ``ETag``/``Cache-Control`` policy
- rate limiting: identical per-IP guard for uncached renders
"""

import logging

from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET

from plugins.og_card import (
    CACHE_CONTROL_ERROR,
    CACHE_CONTROL_IMMUTABLE,
    CARD_PARAMS,
    DJANGO_OG_CARD_PATH,
    allow_render,
    card_cache_key,
    client_key,
    read_cached_card,
    render_from_params,
    template_version,
    write_cached_card,
)

logger = logging.getLogger(__name__)

ALLOWED_KINDS = ("row", "search")
RETRY_AFTER_SECONDS = "60"


@require_GET
def og_card_image(request):
    """Serve (and lazily render + cache) a card for the query parameters."""
    params = {name: request.GET.get(name) for name in CARD_PARAMS}
    if (params.get("k") or "row") not in ALLOWED_KINDS:
        return HttpResponse("Unknown card kind", status=404, content_type="text/plain")

    # A stale template version is redirected to the current one, exactly as
    # the Datasette endpoint does, so an old image URL keeps working.
    requested_version = params.get("v")
    if requested_version not in (None, "") and str(
        requested_version
    ) != str(template_version()):
        query = request.GET.copy()
        query["v"] = str(template_version())
        return HttpResponseRedirect(f"{DJANGO_OG_CARD_PATH}?{query.urlencode()}")

    key = card_cache_key(params)

    cached = read_cached_card(key)
    if cached is not None:
        return _png_response(cached, key)

    if not allow_render(client_key(request)):
        response = HttpResponse(
            b"Too many card renders, retry shortly",
            status=429,
            content_type="text/plain",
        )
        response["cache-control"] = CACHE_CONTROL_ERROR
        response["retry-after"] = RETRY_AFTER_SECONDS
        return response

    try:
        png = render_from_params(params)
    except Exception:
        # A broken preview must never look like a broken site.
        logger.exception("Failed to render OG card")
        return HttpResponse(
            "Could not render card", status=500, content_type="text/plain"
        )

    write_cached_card(key, png)
    return _png_response(png, key)


def _png_response(png: bytes, key: str) -> HttpResponse:
    response = HttpResponse(png, content_type="image/png")
    response["cache-control"] = CACHE_CONTROL_IMMUTABLE
    response["etag"] = f'"{key}"'
    return response
