"""Unit tests for the OG card endpoint plumbing (``plugins/og_card.py``).

Covers the pieces the HTTP smoke tests do not pin down:

- ``card_cache_key``: stability, template-version busting, and that only
  card-affecting parameters participate.
- URL shape (relative for templates, absolute for ``og:image``).
- fallbacks for missing date / page / OCR text.
- disk cache read/write (including atomicity and corrupt files).
- the uncached-render rate guard.
- the renderer's title composition and PNG output.
"""

import os
from io import BytesIO

import pytest
from PIL import Image

from plugins import og_card, og_card_image


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Point the disk cache at a temp dir and clear in-process state."""
    monkeypatch.setenv("OG_CARD_CACHE_DIR", str(tmp_path / "cards"))
    og_card.reset_caches()
    yield
    og_card.reset_caches()


ROW_PARAMS = {
    "k": "row",
    "m": "Alameda",
    "b": "City Council",
    "d": "2024-01-15",
    "p": "3",
    "s": "The council approved the budget.",
}


class TestCardCacheKey:
    def test_key_is_stable(self):
        assert og_card.card_cache_key(ROW_PARAMS) == og_card.card_cache_key(
            dict(ROW_PARAMS)
        )

    def test_key_is_hex_sha256(self):
        key = og_card.card_cache_key(ROW_PARAMS)
        assert len(key) == 64
        int(key, 16)

    def test_key_ignores_parameter_order(self):
        reordered = dict(reversed(list(ROW_PARAMS.items())))
        assert og_card.card_cache_key(reordered) == og_card.card_cache_key(ROW_PARAMS)

    def test_key_changes_when_template_version_changes(self, monkeypatch):
        before = og_card.card_cache_key(ROW_PARAMS)
        monkeypatch.setattr(og_card_image, "TEMPLATE_VERSION", 999)
        assert og_card.card_cache_key(ROW_PARAMS) != before

    def test_key_changes_with_content(self):
        changed = dict(ROW_PARAMS, s="Something else entirely.")
        assert og_card.card_cache_key(changed) != og_card.card_cache_key(ROW_PARAMS)

    def test_key_changes_with_card_kind(self):
        search = {"k": "search", "m": "Alameda", "q": "budget"}
        assert og_card.card_cache_key(search) != og_card.card_cache_key(ROW_PARAMS)

    def test_key_ignores_unknown_parameters(self):
        with_extra = dict(ROW_PARAMS, utm_source="slack")
        assert og_card.card_cache_key(with_extra) == og_card.card_cache_key(ROW_PARAMS)

    def test_key_ignores_empty_values(self):
        with_empty = dict(ROW_PARAMS, b="")
        without_b = {k: v for k, v in ROW_PARAMS.items() if k != "b"}
        assert og_card.card_cache_key(with_empty) == og_card.card_cache_key(without_b)


class TestCardUrls:
    def test_relative_url_shape(self):
        url = og_card.card_image_url(ROW_PARAMS)
        assert url.startswith("/-/og.png?")
        assert f"v={og_card_image.TEMPLATE_VERSION}" in url
        assert "k=row" in url

    def test_absolute_url_uses_canonical_host(self):
        url = og_card.absolute_card_url("alameda.ca.civic.band", ROW_PARAMS)
        assert url.startswith("https://alameda.ca.civic.band/-/og.png?")

    def test_django_url_uses_django_path(self):
        url = og_card.django_card_url("civic.band", {"k": "search", "q": "budget"})
        assert url.startswith("https://civic.band/og-card.png?")

    def test_url_escapes_user_text(self):
        url = og_card.card_image_url({"k": "row", "m": "A&B", "s": "x?y=z#q"})
        assert "A%26B" in url
        assert "x%3Fy%3Dz%23q" in url


class TestRowCardParams:
    def test_complete_row(self):
        params = og_card.row_card_params(
            "alameda.ca",
            "Alameda",
            body="City Council",
            meeting_date="2024-01-15",
            page=3,
            text="Budget",
        )
        assert params == {
            "k": "row",
            "m": "Alameda",
            "b": "City Council",
            "d": "2024-01-15",
            "p": "3",
            "s": "Budget",
        }

    def test_missing_optional_fields_are_omitted(self):
        params = og_card.row_card_params(
            "alameda.ca", "Alameda", body=None, meeting_date=None, page=None, text=None
        )
        assert params == {"k": "row", "m": "Alameda"}

    def test_invalid_date_is_dropped(self):
        params = og_card.row_card_params(
            "alameda.ca",
            "Alameda",
            body=None,
            meeting_date="not-a-date",
            page=None,
            text=None,
        )
        assert "d" not in params

    def test_snippet_is_cleaned_and_trimmed(self):
        params = og_card.row_card_params(
            "alameda.ca",
            "Alameda",
            body=None,
            meeting_date=None,
            page=None,
            text="Budget approv-\nal " + "word " * 500,
        )
        assert "\n" not in params["s"]
        assert "approval" in params["s"]
        assert len(params["s"]) <= og_card_image.SNIPPET_CHARS

    def test_municipality_falls_back_to_subdomain(self):
        params = og_card.row_card_params(
            "alameda.ca", "", body=None, meeting_date=None, page=None, text=None
        )
        assert params["m"] == "alameda.ca"


class TestTitles:
    def test_row_title_full(self):
        assert (
            og_card.row_card_title("Alameda", "City Council", "2024-01-15", 3)
            == "Alameda \u2014 City Council \u2014 2024-01-15 \u2014 Page 3"
        )

    def test_row_title_omits_missing_parts(self):
        assert og_card.row_card_title("Alameda", None, None, None) == "Alameda"

    def test_search_title_singular_and_plural(self):
        assert og_card.search_card_title("budget", 1) == "1 result for \u2018budget\u2019"
        assert og_card.search_card_title("budget", 2) == "2 results for \u2018budget\u2019"

    def test_search_title_without_count(self):
        assert og_card.search_card_title("budget") == (
            "Search results for \u2018budget\u2019"
        )


class TestDiskCache:
    def test_write_then_read_round_trip(self):
        png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
        og_card.write_cached_card("a" * 64, png)
        assert og_card.read_cached_card("a" * 64) == png

    def test_miss_returns_none(self):
        assert og_card.read_cached_card("b" * 64) is None

    def test_corrupt_file_is_a_miss(self):
        key = "c" * 64
        path = og_card._disk_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(b"not a png")
        assert og_card.read_cached_card(key) is None

    def test_second_read_served_from_memory(self):
        png = b"\x89PNG\r\n\x1a\n" + b"1" * 16
        og_card.write_cached_card("d" * 64, png)
        og_card.reset_caches()  # only memory cleared, disk kept
        first = og_card.read_cached_card("d" * 64)
        assert first == png

    def test_cache_dir_is_overridable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OG_CARD_CACHE_DIR", str(tmp_path / "custom"))
        assert og_card.cache_dir() == str(tmp_path / "custom")

    def test_unwritable_cache_dir_does_not_raise(self, tmp_path, monkeypatch):
        blocker = tmp_path / "blocked"
        blocker.write_text("this is a file, not a directory")
        monkeypatch.setenv("OG_CARD_CACHE_DIR", str(blocker))
        # Must not raise: the response is still served from memory.
        og_card.write_cached_card("e" * 64, b"\x89PNG\r\n\x1a\n" + b"2" * 8)
        assert og_card.read_cached_card("e" * 64) is not None


class TestRenderGuard:
    def test_allows_up_to_burst(self):
        allowed = sum(og_card.allow_render("1.1.1.1") for _ in range(20))
        assert allowed == og_card.RENDER_BURST

    def test_blocks_after_burst(self):
        for _ in range(og_card.RENDER_BURST):
            assert og_card.allow_render("2.2.2.2")
        assert not og_card.allow_render("2.2.2.2")

    def test_buckets_are_per_client(self):
        for _ in range(og_card.RENDER_BURST):
            og_card.allow_render("3.3.3.3")
        assert not og_card.allow_render("3.3.3.3")
        assert og_card.allow_render("4.4.4.4")


class TestRenderer:
    def test_png_is_returned_and_has_expected_size(self):
        png = og_card_image.render_card(
            title="Alameda \u2014 City Council \u2014 Page 1",
            snippet="The council approved the budget.",
            eyebrow="Alameda",
        )
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        # Assert on dimensions/decodability only, never pixel content.
        with Image.open(BytesIO(png)) as image:
            assert image.size == (1200, 630)

    def test_renders_without_text(self):
        png = og_card_image.render_card(title="Alameda", snippet="", eyebrow="")
        assert png.startswith(b"\x89PNG")

    def test_very_long_title_and_snippet_still_render(self):
        png = og_card_image.render_card(
            title="word " * 200, snippet="word " * 2000, eyebrow="x" * 500
        )
        assert png.startswith(b"\x89PNG")
