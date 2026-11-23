"""Tests for the canonical permalink helpers (Phase 1 of the sharing plan).

The helpers are plain functions so the canonical-path decisions can be
asserted directly, without rendering a page:

- row pages -> ``/<db>/<table>/<id>`` (the locked public permalink)
- table pages -> ``/<db>/<table>`` (query strings dropped)
- ``/-/search`` -> municipality landing page (it is POST-only)
"""

from plugins.canonical import (
    canonical_path,
    canonical_url,
    make_canonical_url,
    municipality_host,
    page_anchor,
)


class TestCanonicalPath:
    def test_row_path(self):
        assert canonical_path("meetings", "minutes", "min-001") == (
            "/meetings/minutes/min-001"
        )

    def test_table_path_ignores_row_id_placeholder(self):
        assert canonical_path("meetings", "minutes", None) == "/meetings/minutes"

    def test_table_path_with_empty_row_id(self):
        assert canonical_path("meetings", "minutes", "") == "/meetings/minutes"

    def test_database_path(self):
        assert canonical_path("meetings") == "/meetings"

    def test_landing_page_path(self):
        assert canonical_path() == "/"

    def test_does_not_leak_query_strings(self):
        # The helper only takes path components; there is no way to smuggle a
        # search/sort/filter query string into the canonical URL.
        assert "?" not in canonical_path("meetings", "minutes", "min-001")


class TestCanonicalUrl:
    def test_row_url_is_absolute_and_https(self):
        url = canonical_url("alameda.ca", "meetings", "minutes", "min-001")
        assert url == "https://alameda.ca.civic.band/meetings/minutes/min-001"
        assert url.startswith("https://")

    def test_table_url_has_no_query_string(self):
        url = canonical_url("alameda.ca", "meetings", "minutes")
        assert url == "https://alameda.ca.civic.band/meetings/minutes"
        assert "?" not in url

    def test_landing_page_url(self):
        assert canonical_url("alameda.ca") == "https://alameda.ca.civic.band/"

    def test_uses_canonical_host_not_triangle_host(self):
        # Preview/alternate root domains still canonicalize to civic.band.
        url = canonical_url("alameda.ca", "meetings", "minutes", "min-001")
        assert ".edgecompute.app" not in url
        assert url == "https://alameda.ca.civic.band/meetings/minutes/min-001"

    def test_single_label_subdomain(self):
        assert municipality_host("berkeley") == "berkeley.civic.band"
        assert canonical_url("berkeley") == "https://berkeley.civic.band/"


class TestPageAnchor:
    def test_anchor_for_known_page(self):
        assert page_anchor(3) == "page-3"

    def test_anchor_for_string_page(self):
        assert page_anchor("12") == "page-12"

    def test_no_anchor_without_page(self):
        assert page_anchor(None) == ""
        assert page_anchor("") == ""


class TestCanonicalFilter:
    def test_filter_binds_subdomain(self):
        filter_fn = make_canonical_url("alameda.ca")
        assert filter_fn("meetings", "minutes", "min-001") == (
            "https://alameda.ca.civic.band/meetings/minutes/min-001"
        )

    def test_filter_without_arguments_is_landing_page(self):
        filter_fn = make_canonical_url("alameda.ca")
        assert filter_fn() == "https://alameda.ca.civic.band/"
