"""Open Graph metadata helpers for Datasette row/search pages.

No images are rendered here. Row pages point at the page scan that already
exists on the CDN; everything else uses a static per-municipality card that
the site builder uploads at deploy time.
"""

import os
from urllib.parse import quote, urlencode

from datasette import hookimpl

from plugins.og_snippet import preview_text

CDN_URL = os.getenv("CDN_URL", "https://cdn.civic.band").rstrip("/")

# Must match plugins/og_card_image.py in the civic-band builder.
OG_CARD_VERSION = 1

# Fastly Image Optimizer transform for a page scan: a top-aligned 1200x630
# crop. Bump only if the design/ratio changes.
SCAN_CROP = "1200,630,offset-y0,safe"
SCAN_WIDTH = 1200
SCAN_QUALITY = 85


def global_card_url() -> str:
    return f"{CDN_URL}/og/civicband-v{OG_CARD_VERSION}.png"


def municipality_card_url(subdomain) -> str:
    """Static fallback card uploaded by the builder for this municipality."""
    if not subdomain:
        return global_card_url()
    sub = quote(str(subdomain).strip(), safe=".-")
    return f"{CDN_URL}/{sub}/og-card-v{OG_CARD_VERSION}.png"


def page_scan_url(subdomain, page_image) -> str:
    """CDN URL for a row's page scan, cropped and resized by the CDN.

    Falls back to the municipality card when a row has no ``page_image``.
    """
    if not page_image:
        return municipality_card_url(subdomain)
    if not subdomain:
        return global_card_url()
    path = str(page_image).strip()
    if not path.startswith("/"):
        path = f"/{path}"
    sub = quote(str(subdomain or "").strip(), safe=".-")
    encoded_path = quote(path, safe="/")
    query = urlencode({"crop": SCAN_CROP, "width": SCAN_WIDTH, "quality": SCAN_QUALITY})
    return f"{CDN_URL}/{sub}{encoded_path}?{query}"


def row_title(municipality, body, meeting_date, page) -> str:
    """``<Municipality> — <Body> — <Date> — Page <n>`` with missing parts omitted."""
    parts = [
        municipality or "CivicBand",
        body,
        meeting_date,
        f"Page {page}" if page not in (None, "") else "",
    ]
    cleaned = [str(part).strip() for part in parts if part not in (None, "")]
    return " \u2014 ".join(part for part in cleaned if part)


def search_title(query) -> str:
    q = (query or "").strip()
    return f"Search results for \u201c{q}\u201d" if q else "Search"


@hookimpl
def prepare_jinja2_environment(env, datasette):
    config = datasette.plugin_config("corkboard") or {}
    subdomain = config.get("subdomain") or ""

    env.filters["og_scan_url"] = lambda value: page_scan_url(subdomain, value)
    env.filters["og_preview"] = preview_text
    env.globals["og_default_image"] = municipality_card_url(subdomain)
    env.globals["og_row_title"] = row_title
    env.globals["og_search_title"] = search_title
