"""Text cleaning and trimming for share previews (OG unfurl cards).

OCR output is noisy: it carries hard line breaks at the ends of scanned
lines, hyphenation splits, repeated whitespace, control characters and
stray glyphs that mean nothing to a reader. The same "make this readable,
then cut it to length" behaviour is used for ``og:description`` on row and
search pages.

This module is intentionally dependency-free: it must not import Django or
Datasette so it can be used from templates, Django views and Datasette
routes alike.
"""

import re

# How long a preview description may be before it is cut. Chosen to fit every
# crawler's truncation point.
DEFAULT_PREVIEW_CHARS = 200

# Page text is capped *before* the regex work so a pathological OCR page
# (or a hostile query string) cannot make cleaning expensive.
MAX_INPUT_CHARS = 4000

# Control characters other than whitespace are never meaningful in a
# preview. Keep \t \n \r for the whitespace normalisation step below.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Soft hyphens are invisible; hard hyphens at a line end are OCR line-split
# artefacts: "approv-\nal" should read "approval", but "well-known" must
# survive. Requiring whitespace *before* the hyphen distinguishes the two.
_LINE_BREAK_HYPHEN_RE = re.compile(r"(?<=\w)-\s*[\r\n]+\s*(?=[a-z])")

# Anything that renders as a break in the scan becomes a single space.
_WHITESPACE_RE = re.compile(r"\s+")

# OCR often leaves runs of punctuation from tables, underlines or stamp
# noise ("..........", "_____", "===="). Collapse those to a single separator
# so they do not eat the description budget.
_NOISE_PUNCT_RE = re.compile(r"([._=~*|·•])\1{2,}")

# Characters that are almost always OCR garbage in a human-facing snippet.
_DROP_CHARS = "\u00ad\u200b\u200c\u200d\ufeff"


def clean_snippet_text(raw) -> str:
    """Return readable single-line text for a preview."""
    if raw is None:
        return ""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    text = str(raw)[:MAX_INPUT_CHARS]
    text = _CONTROL_CHARS_RE.sub(" ", text)
    text = _LINE_BREAK_HYPHEN_RE.sub("", text)
    for char in _DROP_CHARS:
        text = text.replace(char, "")
    text = _NOISE_PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def trim_to_length(text: str, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Cut ``text`` to at most ``limit`` characters on a word boundary."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    budget = limit - 1
    if budget <= 0:
        return "\u2026"[:limit]
    cut = text[:budget]
    space = cut.rfind(" ")
    if space >= budget // 2:
        cut = cut[:space]
    return cut.rstrip(" ,;:.-") + "\u2026"


def preview_text(raw, limit: int = DEFAULT_PREVIEW_CHARS) -> str:
    """Clean then trim in one step - the standard preview description."""
    return trim_to_length(clean_snippet_text(raw), limit)
