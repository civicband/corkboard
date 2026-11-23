"""Tests for the Django-side OG card (bare ``civic.band`` search page).

The homepage is CivicBand's municipality search: a ``?q=`` (optionally
filtered) URL gets an ``og:title``/``og:description``/``og:image`` set from
``pages.context_processors.og_meta`` and the image is served by
``pages/og_card_views.py`` - the same renderer, cache and guard the Datasette
route uses.

The bare homepage (no query) keeps the template's own text and emits no card.
"""

import re
from io import BytesIO

import pytest
from django.test import Client
from django.urls import reverse
from PIL import Image

from plugins import og_card_image

OG_TITLE_RE = re.compile(r'<meta property="og:title" content="([^"]*)">')
OG_DESC_RE = re.compile(r'<meta property="og:description" content="([^"]*)">')
OG_IMAGE_RE = re.compile(r'<meta property="og:image" content="([^"]*)">')
TWITTER_IMAGE_RE = re.compile(r'<meta name="twitter:image" content="([^"]*)">')


def _first(pattern, html):
    match = pattern.search(html)
    return match.group(1) if match else None


@pytest.fixture(autouse=True)
def isolated_card_cache(og_cache_dir):
    """Reuse the shared disk-cache isolation fixture."""


@pytest.mark.django_db
class TestDjangoOgMeta:
    def test_bare_home_has_no_card(self, client: Client):
        html = client.get(reverse("home")).content.decode()
        assert _first(OG_IMAGE_RE, html) is None

    def test_search_emits_card_and_title(self, client: Client):
        html = client.get(reverse("home"), {"q": "alameda"}).content.decode()
        title = _first(OG_TITLE_RE, html)
        assert title == "Municipalities for \u2018alameda\u2019"
        image = _first(OG_IMAGE_RE, html)
        assert image is not None
        assert image.startswith("http://testserver/og-card.png?")
        assert "k=search" in image

    def test_twitter_image_matches_og_image(self, client: Client):
        html = client.get(reverse("home"), {"q": "alameda"}).content.decode()
        assert _first(TWITTER_IMAGE_RE, html) == _first(OG_IMAGE_RE, html)

    def test_filter_only_without_query_has_no_card(self, client: Client):
        """A state filter alone is not a search worth unfurling."""
        html = client.get(reverse("home"), {"state": "CA"}).content.decode()
        assert _first(OG_IMAGE_RE, html) is None

    def test_canonical_is_untouched_by_the_card(self, client: Client):
        html = client.get(reverse("home"), {"q": "alameda"}).content.decode()
        canonical = _first(re.compile(r'<link rel="canonical" href="([^"]*)">'), html)
        og_url = _first(re.compile(r'<meta property="og:url" content="([^"]*)">'), html)
        assert canonical == "http://testserver/"
        assert og_url == canonical

    def test_user_text_is_escaped(self, client: Client):
        html = client.get(reverse("home"), {"q": '"><script>x</script>'}).content
        assert b"<script>x</script>" not in html


@pytest.mark.django_db
class TestDjangoCardEndpoint:
    def _card_url(self, client: Client, query: str) -> str:
        html = client.get(reverse("home"), {"q": query}).content.decode()
        return _first(OG_IMAGE_RE, html)

    def test_search_card_returns_valid_png(self, client: Client):
        url = self._card_url(client, "alameda")
        response = client.get(url)
        assert response.status_code == 200
        assert response["content-type"] == "image/png"
        with Image.open(BytesIO(response.content)) as image:
            assert image.format == "PNG"
            assert image.size == (1200, 630)

    def test_cache_headers_and_stable_etag(self, client: Client):
        url = self._card_url(client, "alameda")
        first = client.get(url)
        second = client.get(url)
        assert first["etag"] == second["etag"]
        assert "immutable" in first["cache-control"]

    def test_row_card_without_text_returns_valid_png(self, client: Client):
        url = (
            f"{reverse('og_card_image')}?k=row&m=Alameda"
            f"&v={og_card_image.TEMPLATE_VERSION}"
        )
        response = client.get(url)
        assert response.status_code == 200
        with Image.open(BytesIO(response.content)) as image:
            assert image.size == (1200, 630)

    def test_unknown_kind_is_404(self, client: Client):
        assert client.get(reverse("og_card_image"), {"k": "poster"}).status_code == 404

    def test_stale_version_redirects(self, client: Client):
        response = client.get(reverse("og_card_image"), {"k": "search", "q": "x", "v": 0})
        assert response.status_code == 302
        assert "v=" in response["location"]

    def test_post_is_not_allowed(self, client: Client):
        assert client.post(reverse("og_card_image"), {"k": "search"}).status_code == 405
