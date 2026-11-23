"""Tests for the Django-side canonical link (Phase 1 of the sharing plan).

Rules under test:

- ``templates/pages/base.html`` emits an absolute ``<link rel="canonical">``.
- Query strings are dropped, so filter/sort views canonicalize to the
  underlying page.
- ``og:url`` matches the canonical URL and is well formed.
- The HTMX-only ``/sites/search/`` endpoint canonicalizes to ``/?<query>``
  instead of exposing its own URL, matching the redirect in
  ``sites_search_view``.
"""

import re

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse

from pages.context_processors import canonical_url_for_request

CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]*)">')
OG_URL_RE = re.compile(r'<meta property="og:url" content="([^"]*)">')


def _canonical(html: str) -> str:
    match = CANONICAL_RE.search(html)
    assert match, "no canonical link rendered"
    return match.group(1)


@pytest.mark.django_db
class TestDjangoCanonicalLink:
    def test_home_has_absolute_canonical(self, client: Client):
        response = client.get(reverse("home"))
        assert response.status_code == 200
        canonical = _canonical(response.content.decode())
        assert canonical.startswith("http://testserver/")
        assert "://" in canonical

    def test_home_canonical_drops_query_string(self, client: Client):
        response = client.get(reverse("home") + "?q=test&state=CA&sort=pages")
        canonical = _canonical(response.content.decode())
        assert "?" not in canonical
        assert canonical.endswith("/")

    def test_municipalities_canonical_drops_pagination(self, client: Client):
        response = client.get(reverse("municipalities") + "?page=2")
        canonical = _canonical(response.content.decode())
        assert canonical.endswith("/municipalities")
        assert "page=" not in canonical

    def test_og_url_matches_canonical(self, client: Client):
        response = client.get(reverse("home"))
        html = response.content.decode()
        og_url = OG_URL_RE.search(html)
        assert og_url, "no og:url rendered"
        assert og_url.group(1) == _canonical(html)
        assert "://" in og_url.group(1)

    def test_sites_search_htmx_canonical_hides_endpoint(self, client: Client):
        """HTMX fragment requests must not advertise the /sites/search/ URL."""
        response = client.get(
            reverse("sites_search") + "?q=oak&state=CA", HTTP_HX_REQUEST="true"
        )
        assert response.status_code == 200
        # Fragment does not extend base.html, so no head tags leak at all.
        html = response.content.decode()
        assert 'rel="canonical"' not in html
        assert "og:url" not in html


class TestCanonicalUrlForRequest:
    """Unit tests for the canonical rule function itself."""

    def setup_method(self):
        self.rf = RequestFactory(HTTP_HOST="civic.band")

    def test_root(self):
        assert canonical_url_for_request(self.rf.get("/")) == "http://civic.band/"

    def test_query_string_dropped(self):
        request = self.rf.get("/?q=oakland&sort=pages")
        assert canonical_url_for_request(request) == "http://civic.band/"

    def test_path_preserved(self):
        request = self.rf.get("/why.html?utm_source=x")
        assert canonical_url_for_request(request) == "http://civic.band/why.html"

    def test_sites_search_canonicalizes_to_home(self):
        request = self.rf.get(reverse("sites_search") + "?q=oak&state=CA")
        canonical = canonical_url_for_request(request)
        assert canonical == "http://civic.band/?q=oak&state=CA"
        assert "/sites/search/" not in canonical

    def test_sites_search_post_never_exposes_endpoint(self):
        request = self.rf.post(reverse("sites_search"), {"q": "secret"})
        canonical = canonical_url_for_request(request)
        assert canonical == "http://civic.band/"
        assert "secret" not in canonical
        assert "/sites/search/" not in canonical

    def test_sites_search_drops_unknown_params(self):
        request = self.rf.get(reverse("sites_search") + "?q=oak&utm_source=x")
        assert canonical_url_for_request(request) == "http://civic.band/?q=oak"

    def test_no_request_returns_empty(self):
        assert canonical_url_for_request(None) == ""
