"""Open Graph unfurl cards (sharing plan, Phase 2 workstream 2).

Every document row page and search page advertises a rendered 1200x630 PNG
social card through ``og:image`` / ``twitter:image``. Cards are generated
server-side with Pillow (``plugins/og_card_image.py``) - no third-party
JavaScript, no new tracking, no client-side work.

URL shape
---------
::

    /-/og.png?k=<card kind>&v=<template version>
        &m=<municipality>&b=<body>&d=<date>&p=<page>&s=<snippet>

``k`` is one of ``row`` or ``search``. ``row`` cards use ``m``/``b``/``d``/``p``
plus the page's OCR text in ``s``; ``search`` cards use ``m``, ``q`` (the
query) and ``n`` (the result count). The route lives on every municipality
subdomain (``https://<sub>.civic.band/-/og.png?...``) and, for the bare
``civic.band`` search page, at ``https://civic.band/-/og.png?...``.

Why the card text is in the query string: it lets crawlers and CDNs cache the
image with a plain GET, keeps the endpoint stateless (no session, no cookie),
and means the image always matches the page that was shared even after the
underlying database is rebuilt. The card itself contains only data that is
already public on the page it belongs to.

Caching
-------
Rendered PNGs are cached on disk under ``OG_CARD_CACHE_DIR`` with a key built
from ``card_cache_key()``: a SHA-256 of the *card kind, template version and
all card text*, i.e. effectively the canonical URL plus
``og_card_image.TEMPLATE_VERSION``. The key is stable across restarts and is
part of the response ``ETag``, so:

- bump ``og_card_image.TEMPLATE_VERSION``  -> new key -> new image everywhere;
- the row's OCR text (or meeting, date, page) changing -> new key;
- nothing else invalidates.

Responses carry ``Cache-Control: public, max-age=31536000, immutable`` plus
the ``ETag``, so browsers, crawlers and the CDN serve repeat hits without
touching this process. Only the first request for a given key renders.

The in-memory cache and the render guard live in ``plugins/og_card_state.py``
rather than in this module's globals. Datasette's ``--plugins-dir`` loader
executes this file as a *new* module object (``module_from_path``), so a
second copy of this module exists at runtime; state in module globals would be
split between that copy and the ``plugins.og_card`` Django imports, giving two
caches and two independent rate-limit buckets. ``og_card_state`` is imported
normally by both, so it is genuinely shared.

Abuse guard
-----------
An uncached render is bounded per client IP with a small in-process token
bucket (no Redis dependency, no new infrastructure). Crawlers unfurling many
distinct rows get 429 with ``Retry-After`` instead of pinning every worker on
Pillow; already-cached keys are always served. The bucket is deliberately
per-worker: a shared global limiter here would be a new cross-worker
dependency for a path that is only expensive once per key.
"""

import asyncio
import contextlib
import functools
import hashlib
import logging
import os
import re
import tempfile
from urllib.parse import urlencode

from datasette import hookimpl
from datasette.utils.asgi import Response

from plugins import og_card_image, og_card_state
from plugins.canonical import municipality_host
from plugins.og_snippet import clean_snippet_text, preview_text

logger = logging.getLogger(__name__)

# Public URL of the endpoint. Kept relative so it works on any host the
# municipality is served from (production, previews, localhost).
OG_CARD_PATH = "/-/og.png"

# The Django (bare-domain) equivalent, served by pages/og_card_views.py.
DJANGO_OG_CARD_PATH = "/og-card.png"

KIND_ROW = "row"
KIND_SEARCH = "search"

# Row templates that carry a document page (minutes/agendas). Only these get
# the per-page OG card; every other page keeps the municipality defaults.
ROW_TEMPLATES = ("row-meetings-minutes.html", "row-meetings-agendas.html")

# The server-rendered cross-table search page (plugins/search_all.py).
SEARCH_TEMPLATE = "search_all.html"

# Every query parameter that can influence the rendered image. ``v`` is the
# template version and is part of both the cache key and the URL, so an image
# URL from before a design change can never collide with the new design.
CARD_PARAMS = ("k", "v", "m", "b", "d", "p", "q", "n", "s")

# Card text limits. The template (og_card_image) does its own pixel-based
# wrapping; these only bound how much text the endpoint accepts so a hostile
# query string cannot turn into a large render.
MAX_SNIPPET_PARAM_CHARS = og_card_image.SNIPPET_CHARS
MAX_TITLE_PART_CHARS = 120
MAX_QUERY_PARAM_CHARS = 160

# Cache/guard state lives in og_card_state so the Datasette plugin copy
# (loaded by ``module_from_path``) and the Django view share one instance.
# See that module's docstring.
MEMORY_CACHE_SIZE = og_card_state.MEMORY_CACHE_SIZE
RENDER_BURST = og_card_state.RENDER_BURST
RENDER_WINDOW_SECONDS = og_card_state.RENDER_WINDOW_SECONDS

# Cache-Control for a card that is addressable by content (immutable: the key
# changes whenever the content or template version changes).
CACHE_CONTROL_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_CONTROL_ERROR = "no-store"

RENDER_RETRY_AFTER = "60"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ALLOWED_KINDS = (KIND_ROW, KIND_SEARCH)


def _clip(value, limit: int) -> str:
    """Strip control/newline noise and bound a single URL parameter."""
    return clean_snippet_text(value)[:limit]


def card_cache_key(params: dict) -> str:
    """Stable SHA-256 key for a card: kind + template version + card text.

    ``params`` is the card query-string mapping (see ``CARD_PARAMS``). Only
    parameters that affect the pixels are included, in a fixed order, so the
    same content always hashes to the same key regardless of URL order or
    unrelated query parameters.
    """
    parts = [f"kind={params.get('k') or KIND_ROW}"]
    for name in CARD_PARAMS:
        if name == "k":
            continue
        value = params.get(name)
        if value in (None, ""):
            continue
        parts.append(f"{name}={clean_snippet_text(value)}")
    material = "\x00".join(parts) + f"\x00v={og_card_image.TEMPLATE_VERSION}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def card_image_url(params: dict) -> str:
    """Relative ``og:image`` URL (no host) for the given card parameters.

    The template version is added here so every consumer - base template,
    row templates, Django views - emits the same versioned URL.
    """
    query = {name: params[name] for name in CARD_PARAMS if params.get(name)}
    query["v"] = str(og_card_image.TEMPLATE_VERSION)
    return f"{OG_CARD_PATH}?{urlencode(query)}"


def absolute_card_url(host: str, params: dict) -> str:
    """Absolute ``og:image`` URL for an explicit host (no trailing slash)."""
    return f"https://{host.rstrip('/')}{card_image_url(params)}"


def django_card_url(host: str, params: dict, scheme: str = "https") -> str:
    """Absolute card URL for the Django host (``<scheme>://<host>/og-card.png``).

    ``scheme`` is taken from the request so development and tests fetch the
    image they actually advertised instead of bouncing to https.
    """
    query = {name: params[name] for name in CARD_PARAMS if params.get(name)}
    query["v"] = str(og_card_image.TEMPLATE_VERSION)
    return f"{scheme}://{host.rstrip('/')}{DJANGO_OG_CARD_PATH}?{urlencode(query)}"


def row_card_params(
    subdomain: str,
    municipality: str,
    *,
    body: str | None,
    meeting_date: str | None,
    page,
    text: str | None,
) -> dict:
    """Card parameters for a document row page.

    Missing date/page/body fall back to empty (the template omits them), and
    a page with no OCR text still yields a valid card. ``subdomain`` is the
    fallback display name when the municipality name is unknown.
    """
    params = {
        "k": KIND_ROW,
        "m": _clip(municipality or subdomain, MAX_TITLE_PART_CHARS),
    }
    if body:
        params["b"] = _clip(body, MAX_TITLE_PART_CHARS)
    if meeting_date and _DATE_RE.match(str(meeting_date)):
        params["d"] = str(meeting_date)
    if page not in (None, ""):
        params["p"] = str(page)[:8]
    snippet = preview_text(text or "", og_card_image.SNIPPET_CHARS)
    if snippet:
        params["s"] = snippet
    return params


def search_card_params(
    municipality: str, query: str, result_count=None
) -> dict:
    """Card parameters for the ``<N> results for '<query>'`` search card."""
    params = {
        "k": KIND_SEARCH,
        "m": _clip(municipality, MAX_TITLE_PART_CHARS),
        "q": _clip(query, MAX_QUERY_PARAM_CHARS),
    }
    if result_count is not None:
        params["n"] = str(int(result_count))
    return params


def search_card_title(query: str, result_count=None) -> str:
    """``<N> results for '<query>'`` (or ``Search results for '<query>'``)."""
    query = _clip(query, MAX_QUERY_PARAM_CHARS)
    if result_count is None:
        return f"Search results for \u2018{query}\u2019"
    noun = "result" if int(result_count) == 1 else "results"
    return f"{int(result_count):,} {noun} for \u2018{query}\u2019"


def row_card_title(
    municipality: str | None,
    body: str | None,
    meeting_date: str | None,
    page,
) -> str:
    """Row card title, also used for ``og:title``."""
    return og_card_image.card_title(municipality, body, meeting_date, page)


def municipality_search_card(host: str, query: str, scheme: str = "https") -> dict:
    """``og_*`` values for the Django homepage's municipality search.

    The Django surface searches *municipalities*, not document pages (Phase 6
    of the plan covers document search there), so the card says
    "Municipalities for '<query>'" rather than claiming document results.
    The image is served by Django (``pages/og_card_views.py``), not the
    Datasette route, because the bare domain is not a municipality site.
    """
    title = f"Municipalities for \u2018{_clip(query, MAX_QUERY_PARAM_CHARS)}\u2019"
    params = {
        "k": KIND_SEARCH,
        "m": "CivicBand",
        "q": _clip(query, MAX_QUERY_PARAM_CHARS),
    }
    return {
        "og_title": title,
        "og_description": f"{title} \u00b7 CivicBand",
        "og_image": django_card_url(host, params, scheme=scheme),
    }


def cache_dir() -> str:
    """Directory for rendered cards (``OG_CARD_CACHE_DIR`` overridable)."""
    return og_card_state.cache_dir()


def reset_caches() -> None:
    """Clear the memory cache and render-guard buckets (tests, config reload)."""
    og_card_state.reset()


def allow_render(client_ip: str) -> bool:
    """Token-bucket guard for *uncached* renders. ``True`` means allowed."""
    return og_card_state.allow_render(client_ip)


def _disk_path(key: str) -> str:
    directory = cache_dir()
    return os.path.join(directory, key[:2], f"{key}.png")


def read_cached_card(key: str) -> bytes | None:
    """Memory then disk lookup. Corrupt/partial files are treated as misses."""
    cached = og_card_state.memory_get(key)
    if cached is not None:
        return cached
    path = _disk_path(key)
    try:
        with open(path, "rb") as fh:
            png = fh.read()
    except OSError:
        return None
    if not png.startswith(b"\x89PNG"):
        return None
    og_card_state.memory_put(key, png)
    return png


def write_cached_card(key: str, png: bytes) -> None:
    """Write the PNG atomically so concurrent readers never see half a file.

    A read-only, full or misconfigured cache directory must not fail the
    request: the memory cache and the response headers still carry the card,
    so failures are logged and swallowed.
    """
    path = _disk_path(key)
    tmp_path = None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        with os.fdopen(fd, "wb") as fh:
            fh.write(png)
        os.replace(tmp_path, path)
    except OSError:
        logger.warning("Could not write OG card cache file %s", path, exc_info=True)
        if tmp_path is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
        og_card_state.memory_put(key, png)
        return
    og_card_state.memory_put(key, png)


def render_from_params(params: dict) -> bytes:
    """Draw the card described by card parameters (never raises for bad data)."""
    kind = params.get("k") or KIND_ROW
    municipality = _clip(params.get("m"), MAX_TITLE_PART_CHARS) or "CivicBand"
    if kind == KIND_SEARCH:
        title = search_card_title(params.get("q") or "", params.get("n"))
        snippet = ""
    else:
        title = row_card_title(
            municipality,
            _clip(params.get("b"), MAX_TITLE_PART_CHARS),
            params.get("d"),
            _clip(params.get("p"), 8),
        )
        snippet = preview_text(
            params.get("s") or "", og_card_image.SNIPPET_CHARS
        )
    return og_card_image.render_card(
        title=title,
        snippet=snippet,
        eyebrow=municipality,
        footer="CivicBand \u00b7 civic.band",
    )


def client_key(request) -> str:
    """Client identity for the render guard (Datasette or Django request)."""
    # Django's HttpRequest: META carries the proxied IP.
    meta = getattr(request, "META", None)
    if isinstance(meta, dict):
        forwarded = meta.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return meta.get("REMOTE_ADDR") or "unknown"

    headers = getattr(request, "headers", {}) or {}
    forwarded = headers.get("x-forwarded-for") if hasattr(headers, "get") else None
    if forwarded:
        return forwarded.split(",")[0].strip()
    scope = getattr(request, "scope", None) or {}
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


def template_version() -> int:
    """The running card design version (part of every URL and cache key)."""
    return og_card_image.TEMPLATE_VERSION


def _png_response(png: bytes, key: str) -> Response:
    etag = f'"{key}"'
    return Response(
        body=png,
        status=200,
        content_type="image/png",
        headers={
            "cache-control": CACHE_CONTROL_IMMUTABLE,
            "etag": etag,
            "content-length": str(len(png)),
        },
    )


async def og_card(request):
    """Serve (and lazily render + cache) the card for the request parameters."""
    params = {name: request.args.get(name) for name in CARD_PARAMS}
    kind = params.get("k") or KIND_ROW
    if kind not in _ALLOWED_KINDS:
        return Response.text("Unknown card kind", status=404)

    # A card whose version is not the running template version would be
    # rendered with the wrong design; send the client to the current URL.
    requested_version = params.get("v")
    if requested_version not in (None, "") and str(
        requested_version
    ) != str(og_card_image.TEMPLATE_VERSION):
        query = {name: value for name, value in params.items() if value}
        query["v"] = str(og_card_image.TEMPLATE_VERSION)
        location = f"{OG_CARD_PATH}?{urlencode(query)}"
        return Response(
            body=b"",
            status=302,
            headers={"location": location, "cache-control": "no-cache"},
        )

    key = card_cache_key(params)

    cached = read_cached_card(key)
    if cached is not None:
        return _png_response(cached, key)

    if not allow_render(client_key(request)):
        logger.info("OG card render rate limit hit")
        return Response(
            body=b"Too many card renders, retry shortly",
            status=429,
            content_type="text/plain",
            headers={
                "cache-control": CACHE_CONTROL_ERROR,
                "retry-after": RENDER_RETRY_AFTER,
            },
        )

    try:
        # Pillow is CPU-bound: keep it off the event loop so one uncached card
        # cannot stall every other request handled by this worker.
        png = await asyncio.to_thread(render_from_params, params)
    except Exception:
        logger.exception("Failed to render OG card")
        return Response.text("Could not render card", status=500)

    write_cached_card(key, png)
    return _png_response(png, key)


def row_card_meta(
    municipality: str,
    *,
    body: str | None,
    meeting_date: str | None,
    page,
    text: str | None,
    host: str,
) -> dict:
    """``og:*`` values for a document row page.

    One dict consumed by ``base.html`` (title/description/image) so the
    headline, description and rendered card can never disagree. ``og:url``
    is not here: Phase 1's canonical plumbing owns it.
    """
    params = row_card_params(
        municipality,
        municipality,
        body=body,
        meeting_date=meeting_date,
        page=page,
        text=text,
    )
    title = row_card_title(municipality, body, meeting_date, page)
    description = preview_text(text or "", og_card_image.SNIPPET_CHARS)
    return {
        "og_title": title,
        "og_description": description or f"{title} \u2013 CivicBand meeting record",
        "og_image": absolute_card_url(host, params),
    }


@hookimpl
def register_routes():
    return [(r"^/-/og\.png$", og_card)]


@hookimpl
def prepare_jinja2_environment(env, datasette):
    """Make the card helpers available to templates.

    Templates extend ``default:row.html`` and cannot easily thread values
    from a row template up into ``base.html``'s head, so ``og_image``,
    ``og_title`` and ``og_description`` are ``block``-able template
    variables set by the row templates, and the filter builds the URL.
    """
    subdomain = (datasette.plugin_config("corkboard") or {}).get("subdomain") or ""
    host = municipality_host(subdomain)
    env.filters["og_image_url"] = lambda params: absolute_card_url(host, params)
    env.globals["row_card_meta"] = functools.partial(row_card_meta, host=host)
    env.globals["og_card_enabled"] = True
    env.globals["og_card_path"] = OG_CARD_PATH


def _template_name(template) -> str:
    """Basename of a template name.

    Datasette passes ``template.name``, which is the path relative to the
    template directory (``templates/datasette/search_all.html`` when served
    through the Corkboard wrapper, plain ``search_all.html`` otherwise).
    Normalising here keeps the hook stable either way.
    """
    return str(template or "").replace("\\", "/").rsplit("/", 1)[-1]


@hookimpl
def extra_template_vars(template, datasette, request):
    """Provide ``og_title``/``og_description``/``og_image`` for row + search.

    A child row template cannot pass values into ``base.html``'s head (Jinja
    compiles the parent's blocks independently), so the row is looked up
    here instead. Only row templates and the search page are requested, and
    any failure leaves the base template's municipality defaults in place
    rather than breaking the page.
    """
    if request is None:
        return None
    name = _template_name(template)
    if name in ROW_TEMPLATES:
        return _row_template_vars(datasette, request)
    if name == SEARCH_TEMPLATE:
        return _search_template_vars(datasette, request)
    return None


def _row_template_vars(datasette, request):
    """Async closure returning the row page's OG vars.

    Returned directly from ``extra_template_vars`` - Datasette asserts the
    hook returns a callable, not a coroutine, so the await happens inside.
    """

    async def inner():
        try:
            try:
                resolved = await datasette.resolve_row(request)
            except Exception:
                # Not a real row (404, bad pk path): keep base defaults.
                logger.debug("Could not resolve row for OG card", exc_info=True)
                return {}
            row = resolved.row
            config = datasette.plugin_config("corkboard") or {}
            host = municipality_host(config.get("subdomain") or "")
            return row_card_meta(
                config.get("site_name") or config.get("subdomain") or "CivicBand",
                body=_row_value(row, "meeting"),
                meeting_date=_row_value(row, "date"),
                page=_row_value(row, "page"),
                text=_row_value(row, "text"),
                host=host,
            )
        except Exception:
            # A preview must never be able to break a page: any unexpected
            # failure leaves the base template's municipality defaults.
            logger.warning("Falling back to default OG tags", exc_info=True)
            return {}

    return inner


def _search_template_vars(datasette, request):
    """Async closure returning the search page's OG vars."""

    async def inner():
        try:
            config = datasette.plugin_config("corkboard") or {}
            host = municipality_host(config.get("subdomain") or "")
            municipality = (
                config.get("site_name") or config.get("subdomain") or "CivicBand"
            )
            query = await _search_query(request)
            if not query:
                # No query: the page is the search form, not a result set.
                return {}
            count = None
            try:
                # Same totals the page shows, from the same plugin, so the
                # card and the page cannot disagree.
                totals = await _search_totals(datasette, request, query)
                count = sum(totals.values())
            except Exception:
                logger.debug("Could not count search results", exc_info=True)
            title = search_card_title(query, count)
            params = search_card_params(municipality, query, count)
            return {
                "og_title": title,
                "og_description": f"{title} \u00b7 {municipality} on CivicBand",
                "og_image": absolute_card_url(host, params),
            }
        except Exception:
            logger.warning("Falling back to default search OG tags", exc_info=True)
            return {}

    return inner


async def _search_query(request) -> str:
    """The search terms for ``/-/search``.

    The page is POST-only: the terms are a form field in the request body,
    not a query-string parameter. A GET can still carry ``?q=`` (form
    pre-fill and crawler probes), so both are checked.

    Never re-reads the POST body here: ``plugins/search_all.py`` has already
    consumed it by the time templates render, and a second read blocks
    waiting for an ASGI message that will never arrive. The view passes the
    parsed query through the template context instead.
    """
    query = (request.args.get("q") or "").strip()
    if query:
        return query
    return (getattr(request, "_corkboard_search_q", None) or "").strip()


async def remember_search_query(request) -> None:
    """Parse the POST body once and stash the query for later hooks.

    Called by the search view before rendering; ``extra_template_vars``
    runs during that same render.
    """
    if request.method != "POST":
        return
    try:
        post = await request.post_vars()
    except Exception:
        return
    request._corkboard_search_q = (post.get("q") or "").strip()


async def _search_totals(datasette, request, query) -> dict:
    """Per-table result counts for ``query`` (``{}`` if unavailable)."""
    from plugins.search_all import (  # noqa: PLC0415 - avoid import cycle
        get_searchable_tables,
        search_table,
    )

    tables = await get_searchable_tables(datasette, request)
    totals = {}
    for database, table in tables:
        result = await search_table(datasette, database, table, query)
        totals[f"{database}/{table}"] = result.get("count") or 0
    return totals


def _row_value(row, column: str):
    """Read a column from a sqlite3.Row, dict or Mapping-like row.

    ``sqlite3.Row`` supports ``row[column]`` but not ``.get()``, so a missing
    column raises rather than returning None.
    """
    try:
        return row[column]
    except (KeyError, IndexError, TypeError):
        return None
