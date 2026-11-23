"""Unit tests for the OG preview text cleaning and trimming helpers.

These cover ``plugins/og_snippet.py``, which is shared by the meta tags, the
image card and the endpoint so OCR noise never reaches a preview.
"""

import pytest

from plugins.og_snippet import (
    DEFAULT_PREVIEW_CHARS,
    clean_snippet_text,
    preview_text,
    trim_to_length,
)


class TestCleanSnippetText:
    def test_none_and_empty(self):
        assert clean_snippet_text(None) == ""
        assert clean_snippet_text("") == ""

    def test_collapses_newlines_and_runs_of_whitespace(self):
        assert clean_snippet_text("The  council\n voted\t5-2.") == (
            "The council voted 5-2."
        )

    def test_rejoins_line_break_hyphenation(self):
        """OCR splits words at line ends: approv-\\nal -> approval."""
        assert clean_snippet_text("budget approv-\nal passed") == (
            "budget approval passed"
        )

    def test_keeps_real_hyphenated_words(self):
        assert clean_snippet_text("a well-known budget item") == (
            "a well-known budget item"
        )

    def test_removes_control_characters(self):
        assert clean_snippet_text("Budget\x00\x07 item\ttwo") == "Budget item two"

    def test_drops_zero_width_and_soft_hyphens(self):
        assert clean_snippet_text("bud\u00adget\u200b") == "budget"

    def test_collapses_decorative_punctuation_runs(self):
        assert clean_snippet_text("Votes .......... 5-2") == "Votes 5-2"

    def test_accepts_bytes(self):
        assert clean_snippet_text(b"Budget item") == "Budget item"

    def test_accepts_non_string(self):
        assert clean_snippet_text(42) == "42"

    def test_caps_pathological_input(self):
        result = clean_snippet_text("word " * 100_000)
        assert len(result) <= 4000 + 1


class TestTrimToLength:
    def test_short_text_unchanged(self):
        assert trim_to_length("Short text", 40) == "Short text"

    def test_trims_on_word_boundary(self):
        result = trim_to_length("The council voted on the budget", 20)
        assert result.endswith("\u2026")
        assert result == "The council voted\u2026"

    def test_result_never_exceeds_limit(self):
        text = "alpha beta gamma delta epsilon zeta eta theta"
        for limit in range(5, 50):
            assert len(trim_to_length(text, limit)) <= limit

    def test_single_long_word_is_hard_cut(self):
        result = trim_to_length("A" * 100, 20)
        assert len(result) <= 20
        assert result.endswith("\u2026")

    def test_zero_or_negative_limit(self):
        assert trim_to_length("abc", 0) == ""
        assert trim_to_length("abc", -1) == ""


class TestPreviewText:
    def test_cleans_then_trims(self):
        raw = "The council\napprov-\ned the  budget. " + "More text here. " * 40
        result = preview_text(raw, DEFAULT_PREVIEW_CHARS)
        assert len(result) <= DEFAULT_PREVIEW_CHARS
        assert "\n" not in result
        assert result.startswith("The council approved the budget.")

    def test_empty_input(self):
        assert preview_text(None) == ""
        assert preview_text("") == ""

    @pytest.mark.parametrize("noise", ["....", "____", "====", "~~~~"])
    def test_noise_only_input_becomes_empty(self, noise):
        assert preview_text(noise) == ""
