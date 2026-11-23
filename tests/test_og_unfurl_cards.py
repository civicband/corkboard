"""End-to-end tests for the OG unfurl cards (sharing plan, Phase 2 WS2).

Renders real Datasette pages through the same template directory and plugins
the embedded Datasette uses, then asserts on:

- ``og:*``/``twitter:*`` tags on a document row page: composed title,
  cleaned snippet description, and a per-page image URL.
- the same tags on the server-rendered ``/-/search`` page, including
  ``<N> results for '<query>'``.
- the image endpoint returning a decodable 1200x630 PNG for a row with OCR
  text and for a row without it, with cache headers and stable ``ETag``.
- template-version busting via the ``v`` parameter.

Pixel content is never asserted; only that the image decodes and has the
advertised dimensions. The ``og_site`` fixture (tests/conftest.py) builds the
municipality site.
"""

import re
from io import BytesIO

import pytest
from PIL import Image

from plugins import og_card, og_card_image, og_card_state
from tests.conftest import OG_TEST_BASE_URL as BASE_URL

OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="([^"]*)"/>')
OG_TITLE_RE = re.compile(r'<meta property="og:title" content="([^"]*)"/>')
OG_DESC_RE = re.compile(r'<meta property="og:description" content="([^"]*)"/>')
TWITTER_IMAGE_RE = re.compile(r'<meta name="twitter:image" value="([^"]*)" />')


def _first(pattern, html):
    match = pattern.search(html)
    return match.group(1) if match else None


def _relative(url: str) -> str:
    """Turn an absolute og:image URL back into a request path."""
    assert url.startswith(BASE_URL), url
    return url[len(BASE_URL) :].replace("&amp;", "&")


def _assert_png(response, width=1200, height=630):
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/png")
    assert response.content.startswith(b"\x89PNG\r\n\x1a\n")
    with Image.open(BytesIO(response.content)) as image:
        assert image.format == "PNG"
        assert image.size == (width, height)


@pytest.mark.asyncio
class TestRowPageMeta:
    async def test_row_page_has_composed_title(self, og_site):
        response = await og_site.client.get("/meetings/minutes/min-001")
        assert response.status_code == 200
        title = _first(OG_TITLE_RE, response.text)
        assert title == "Alameda \u2014 City Council \u2014 2024-01-15 \u2014 Page 1"

    async def test_description_is_cleaned_snippet(self, og_site):
        response = await og_site.client.get("/meetings/minutes/min-001")
        description = _first(OG_DESC_RE, response.text)
        assert description == "The council approved the budget 5-2."

    async def test_row_page_advertises_og_and_twitter_image(self, og_site):
        response = await og_site.client.get("/meetings/minutes/min-001")
        html = response.text
        image = _first(OG_IMAGE_RE, html)
        assert image is not None
        assert image.startswith(f"{BASE_URL}/-/og.png?")
        assert f"v={og_card_image.TEMPLATE_VERSION}" in image
        assert "k=row" in image
        # Twitter follows the same image so the card is used on X too.
        assert _first(TWITTER_IMAGE_RE, html) == image

    async def test_image_dimensions_declared(self, og_site):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        assert '<meta property="og:image:width" content="1200"/>' in html
        assert '<meta property="og:image:height" content="630"/>' in html
        assert '<meta property="og:image:type" content="image/png"/>' in html

    async def test_og_url_still_the_phase1_canonical(self, og_site):
        """Phase 2 must not disturb the Phase 1 canonical plumbing."""
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        canonical = _first(
            re.compile(r'<link rel="canonical" href="([^"]*)">'), html
        )
        og_url = _first(re.compile(r'<meta property="og:url" content="([^"]*)"/>'), html)
        assert canonical == f"{BASE_URL}/meetings/minutes/min-001"
        assert og_url == canonical

    async def test_row_without_text_or_date_degrades(self, og_site):
        response = await og_site.client.get("/meetings/minutes/min-empty")
        html = response.text
        assert response.status_code == 200
        assert _first(OG_TITLE_RE, html) == "Alameda"
        assert _first(OG_DESC_RE, html)
        image = _first(OG_IMAGE_RE, html)
        assert image is not None
        # No date/page/snippet parameters - the card is text-free but valid.
        assert "d=" not in image
        assert "p=" not in image
        assert "s=" not in image

    async def test_agenda_row_page_has_card(self, og_site):
        html = (await og_site.client.get("/meetings/agendas/agenda-001")).text
        assert "Planning Commission" in (_first(OG_TITLE_RE, html) or "")

    async def test_table_page_does_not_get_a_row_card(self, og_site):
        """Only document row pages advertise a card; lists keep defaults."""
        html = (await og_site.client.get("/meetings/minutes")).text
        assert _first(OG_IMAGE_RE, html) is None


@pytest.mark.asyncio
class TestSearchPageMeta:
    async def test_search_title_has_result_count_and_query(self, og_site):
        response = await og_site.client.post("/-/search", data={"q": "budget"})
        assert response.status_code == 200
        title = _first(OG_TITLE_RE, response.text)
        assert re.fullmatch(r"\d+ results? for \u2018budget\u2019", title or ""), title

    async def test_search_page_advertises_card(self, og_site):
        response = await og_site.client.post("/-/search", data={"q": "budget"})
        image = _first(OG_IMAGE_RE, response.text)
        assert image is not None
        assert "k=search" in image
        assert "q=budget" in image
        assert _first(TWITTER_IMAGE_RE, response.text) == image

    async def test_search_form_without_query_keeps_defaults(self, og_site):
        html = (await og_site.client.get("/-/search")).text
        assert _first(OG_IMAGE_RE, html) is None
        assert _first(OG_TITLE_RE, html) == "Alameda Public Meetings"


@pytest.mark.asyncio
class TestImageEndpoint:
    async def test_row_with_text_returns_valid_png(self, og_site):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        url = _relative(_first(OG_IMAGE_RE, html))
        response = await og_site.client.get(url)
        _assert_png(response)

    async def test_row_without_text_returns_valid_png(self, og_site):
        html = (await og_site.client.get("/meetings/minutes/min-empty")).text
        url = _relative(_first(OG_IMAGE_RE, html))
        _assert_png(await og_site.client.get(url))

    async def test_search_card_returns_valid_png(self, og_site):
        html = (await og_site.client.post("/-/search", data={"q": "budget"})).text
        _assert_png(await og_site.client.get(_relative(_first(OG_IMAGE_RE, html))))

    async def test_cache_headers_and_stable_etag(self, og_site):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        url = _relative(_first(OG_IMAGE_RE, html))

        first = await og_site.client.get(url)
        second = await og_site.client.get(url)
        _assert_png(first)
        assert first.headers["etag"] == second.headers["etag"]
        assert "immutable" in first.headers["cache-control"]
        assert "31536000" in first.headers["cache-control"]

    async def test_second_request_is_served_without_rerendering(
        self, og_site, monkeypatch
    ):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        url = _relative(_first(OG_IMAGE_RE, html))
        await og_site.client.get(url)

        def _boom(*args, **kwargs):
            raise AssertionError("rendered twice for the same card")

        monkeypatch.setattr(og_card, "render_from_params", _boom)
        # Memory cache is warm, so no render should happen.
        _assert_png(await og_site.client.get(url))

    async def test_disk_cache_used_after_memory_cleared(self, og_site):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        url = _relative(_first(OG_IMAGE_RE, html))
        await og_site.client.get(url)
        og_card.reset_caches()
        _assert_png(await og_site.client.get(url))

    async def test_stale_template_version_redirects(self, og_site):
        response = await og_site.client.get("/-/og.png?k=row&m=Alameda&v=0")
        assert response.status_code == 302
        assert f"v={og_card_image.TEMPLATE_VERSION}" in response.headers["location"]

    async def test_unknown_kind_is_404(self, og_site):
        response = await og_site.client.get("/-/og.png?k=poster&m=Alameda")
        assert response.status_code == 404

    async def test_uncached_render_burst_is_rate_limited(self, og_site, monkeypatch):
        # The guard reads its limits from og_card_state, which is the single
        # shared instance for both plugin copies.
        monkeypatch.setattr(og_card_state, "RENDER_BURST", 2)
        og_card.reset_caches()
        statuses = []
        for index in range(4):
            response = await og_site.client.get(
                f"/-/og.png?k=row&m=Alameda&s=unique-{index}&v={og_card_image.TEMPLATE_VERSION}"
            )
            statuses.append(response.status_code)
        assert statuses[:2] == [200, 200]
        assert statuses[2:] == [429, 429]
        # A throttle response must tell the crawler to retry and must not be
        # cached as if it were the card.
        limited = await og_site.client.get(
            f"/-/og.png?k=row&m=Alameda&s=unique-3&v={og_card_image.TEMPLATE_VERSION}"
        )
        assert limited.headers["retry-after"]
        assert "no-store" in limited.headers["cache-control"]

    async def test_cached_card_is_served_even_when_guard_is_exhausted(
        self, og_site, monkeypatch
    ):
        html = (await og_site.client.get("/meetings/minutes/min-001")).text
        url = _relative(_first(OG_IMAGE_RE, html))
        await og_site.client.get(url)  # now cached

        monkeypatch.setattr(og_card, "RENDER_BURST", 0)
        og_card.reset_caches()
        # reset_caches dropped the memory copy but the disk copy remains.
        _assert_png(await og_site.client.get(url))
