"""Text cleaning and trimming for share previews (OG unfurl cards).

OCR output is noisy: it carries hard line breaks at the ends of scanned
lines, hyphenation splits, repeated whitespace, control characters and
stray glyphs that mean nothing to a reader.

The generic parts are handled by the standard library: ``textwrap.shorten``
normalises whitespace and truncates on word boundaries, and ``unicodedata``
identifies control/format characters. Only the OCR-specific line-break
hyphenation and decorative punctuation runs need regular expressions.

This module must not import Django or Datasette so it can be used from
templates, Django views and Datasette routes alike.
"""

import re
import textwrap
import unicodedata

# How long a preview description may be before it is cut. Chosen to fit every
# crawler's truncation point.
DEFAULT_PREVIEW_CHARS = 200

# Page text is capped *before* the regex work so a pathological OCR page
# (or a hostile query string) cannot make cleaning expensive.
MAX_INPUT_CHARS = 4000

# Hard hyphens at a line end are OCR line-split artefacts: "approv-\nal"
# should read "approval", but "well-known" must survive. Requiring whitespace
# before the hyphen distinguishes the two.
_LINE_BREAK_HYPHEN_RE = re.compile(r"(?<=\w)-\s*[\r\n]+\s*(?=[a-z])")

# OCR often leaves runs of punctuation from tables, underlines or stamp
# noise ("..........", "_____", "===="). Collapse those to a single separator
# so they do not eat the description budget.
_NOISE_PUNCT_RE = re.compile(r"([._=~*|·•])\1{2,}")


def _strip_unprintable(text: str) -> str:
    """Replace controls with spaces and drop zero-width formatting marks."""
    out = []
    for char in text:
        if char in "\n\r\t":
            out.append(" ")
            continue
        category = unicodedata.category(char)
        if category == "Cf":
            # Soft hyphens, zero-width spaces/joiners and BOMs are invisible;
            # removing them without a separator keeps words joined.
            continue
        if category.startswith("C"):
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def clean_snippet_text(raw) -> str:
    """Return readable single-line text for a preview."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    # Join line-split hyphens before control characters are normalised so the
    # regex can still see the original line break.
    text = _LINE_BREAK_HYPHEN_RE.sub("", str(raw)[:MAX_INPUT_CHARS])
    text = _strip_unprintable(text)
    text = _NOISE_PUNCT_RE.sub(" ", text)
    return " ".join(text.split())


def trim_to_length(text: str, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Cut ``text`` to at most ``limit`` characters on a word boundary."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text

    shortened = textwrap.shorten(
        text,
        width=limit,
        placeholder="\u2026",
        break_long_words=False,
        break_on_hyphens=False,
    )
    # ``shorten`` returns just the placeholder for a single over-long token;
    # fall back to a hard cut so the preview still carries part of the word.
    if shortened == "\u2026":
        stem = text[: limit - 1].rstrip(" ,;:.-")
        return (stem + "\u2026") if stem else "\u2026"
    if shortened.endswith("\u2026"):
        stem = shortened[:-1].rstrip(" ,;:.-")
        return (stem + "\u2026") if stem else "\u2026"
    return shortened


def preview_text(raw, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Clean then trim in one step - the standard preview description."""
    return trim_to_length(clean_snippet_text(raw), limit)
