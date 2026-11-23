"""The Open Graph card design - the *only* module that knows what a card
looks like.

Everything about the rendered unfurl image lives here: canvas size, palette,
type scale, where each line of text sits, how the snippet is wrapped, and the
``TEMPLATE_VERSION`` constant that versions the whole design. Route handling,
caching and rate limiting live in ``plugins/og_card.py``; this module has no
knowledge of HTTP.

To change the design, edit this file and bump ``TEMPLATE_VERSION``. That
version is part of the on-disk cache key and of the ``og:image`` URL, so every
page starts pointing at a freshly rendered card and no stale image can be
served (see ``plugins/og_card.py`` for the invalidation story).

Fonts: the container has no system fonts, so the design ships its own
interface font in ``static/fonts`` (Inter, SIL OFL). ``PIL.ImageFont``'s
built-in bitmap font is used as a last-resort fallback so a missing font file
degrades the look of the card but never fails the request.
"""

import functools
import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------------------
# Design constants. Bump TEMPLATE_VERSION whenever anything below changes.
# --------------------------------------------------------------------------
TEMPLATE_VERSION = 1

# 1200x630 is the 1.91:1 shape Twitter/X, Slack, Discord, Facebook and
# LinkedIn all crop to; at exactly this ratio no crawler crops the text.
CARD_WIDTH = 1200
CARD_HEIGHT = 630
CARD_SIZE = (CARD_WIDTH, CARD_HEIGHT)

FONT_DIR = Path(__file__).resolve().parent.parent / "static" / "fonts"
FONT_FILES = {
    "regular": "Inter-Regular.ttf",
    "medium": "Inter-Medium.ttf",
    "bold": "Inter-Bold.ttf",
}

# Palette: CivicBand navy on white paper, with a warm accent bar.
COLOR_BACKGROUND = (255, 255, 255)
COLOR_PANEL = (248, 250, 252)
COLOR_ACCENT = (37, 99, 235)
COLOR_TEXT = (15, 23, 42)
COLOR_MUTED = (100, 116, 139)
COLOR_RULE = (226, 232, 240)

MARGIN_X = 72
MARGIN_TOP = 64
MARGIN_BOTTOM = 56
ACCENT_BAR_WIDTH = 12

TITLE_SIZE = 54
EYEBROW_SIZE = 30
BODY_SIZE = 30
FOOTER_SIZE = 24
TITLE_LINE_HEIGHT = 1.16
BODY_LINE_HEIGHT = 1.42

TITLE_MAX_LINES = 3
BODY_MAX_LINES = 5

# Truncation is done with ``plugins.og_snippet`` so the text on the card and
# the text in ``og:description`` are cleaned identically.
SNIPPET_CHARS = 260


@functools.lru_cache(maxsize=16)
def _load_font(weight: str, size: int):
    """Load a sized font, falling back to Pillow's built-in bitmap font."""
    filename = FONT_FILES.get(weight, FONT_FILES["regular"])
    path = FONT_DIR / filename
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        # Design degrades, request never fails.
        return ImageFont.load_default(size=size)


def _visible_text(value, fallback: str) -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _hard_split(word: str, font, max_width: int) -> list[str]:
    """Break an oversized token into pieces that each fit ``max_width``."""
    pieces: list[str] = []
    rest = word
    while rest:
        cut = len(rest)
        while cut > 1 and font.getlength(rest[:cut]) > max_width:
            cut -= 1
        pieces.append(rest[:cut])
        rest = rest[cut:]
    return pieces


def _wrap(text: str, font, max_width: int, max_lines: int) -> list[str]:
    """Greedy word wrap to ``max_lines`` lines, ellipsizing the last one.

    ``font.getlength`` is used rather than character counts so different
    glyph widths wrap where they look right. A word wider than the card is
    hard-split so it cannot overflow the right margin.
    """
    if not text:
        return []

    lines: list[str] = []
    current = ""
    truncated = False

    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
            if len(lines) >= max_lines:
                truncated = True
                break
        if font.getlength(word) > max_width:
            pieces = _hard_split(word, font, max_width)
            lines.extend(pieces[:-1])
            current = pieces[-1]
            if len(lines) >= max_lines:
                truncated = True
                break
        else:
            current = word

    if current:
        if len(lines) >= max_lines:
            truncated = True
        else:
            lines.append(current)

    lines = lines[:max_lines]
    if not lines:
        return []
    if truncated:
        last = lines[-1]
        while font.getlength(last + "\u2026") > max_width and len(last) > 1:
            last = last[:-1].rstrip()
        lines[-1] = last + "\u2026"
    return lines


def card_title(
    municipality: str | None,
    body: str | None,
    meeting_date: str | None,
    page,
) -> str:
    """``<Municipality> - <Body> - <Meeting date> - Page <n>``.

    Missing parts are omitted rather than rendered as "None"/"" so a card for
    a row without a date or page still reads as a sentence.
    """
    parts = [
        _visible_text(municipality, "CivicBand"),
        _visible_text(body, ""),
        _visible_text(meeting_date, ""),
        f"Page {page}" if page not in (None, "") else "",
    ]
    return " \u2014 ".join(part for part in parts if part)


def render_card(
    *,
    title: str,
    snippet: str = "",
    eyebrow: str = "",
    footer: str = "CivicBand \u00b7 civic.band",
    version: int = TEMPLATE_VERSION,
) -> bytes:
    """Render the card and return PNG bytes.

    ``title`` is expected to already be the composed title (see
    ``card_title``); ``snippet`` should come from ``og_snippet.preview_text``
    so it is cleaned and trimmed. All inputs are treated as untrusted strings.
    """
    del version  # Callers pick the version; the drawing itself needs only text.

    image = Image.new("RGB", CARD_SIZE, COLOR_BACKGROUND)
    draw = ImageDraw.Draw(image)
    fonts = {weight: _load_font(weight, size) for weight, size in _font_sizes()}

    content_left = MARGIN_X + ACCENT_BAR_WIDTH + 32
    content_width = CARD_WIDTH - content_left - MARGIN_X

    # Left accent bar: the single brand mark, cheap to draw, no assets.
    draw.rectangle(
        [(MARGIN_X, MARGIN_TOP), (MARGIN_X + ACCENT_BAR_WIDTH, CARD_HEIGHT - 120)],
        fill=COLOR_ACCENT,
    )

    y = MARGIN_TOP

    eyebrow_text = _visible_text(eyebrow, "")
    if eyebrow_text:
        draw.text(
            (content_left, y),
            eyebrow_text.upper(),
            font=fonts["eyebrow"],
            fill=COLOR_ACCENT,
        )
        y += int(EYEBROW_SIZE * 1.5)

    title_lines = _wrap(
        _visible_text(title, "CivicBand"),
        fonts["title"],
        content_width,
        TITLE_MAX_LINES,
    )
    for line in title_lines:
        draw.text((content_left, y), line, font=fonts["title"], fill=COLOR_TEXT)
        y += int(TITLE_SIZE * TITLE_LINE_HEIGHT)

    y += 20
    draw.line(
        [(content_left, y), (CARD_WIDTH - MARGIN_X, y)],
        fill=COLOR_RULE,
        width=2,
    )
    y += 28

    snippet_text = _visible_text(snippet, "")
    if snippet_text:
        body_lines = _wrap(
            snippet_text, fonts["body"], content_width, BODY_MAX_LINES
        )
        for line in body_lines:
            draw.text((content_left, y), line, font=fonts["body"], fill=COLOR_MUTED)
            y += int(BODY_SIZE * BODY_LINE_HEIGHT)

    # Footer pinned to the bottom edge, independent of content height.
    footer_text = _visible_text(footer, "CivicBand")
    draw.text(
        (content_left, CARD_HEIGHT - MARGIN_BOTTOM),
        footer_text,
        font=fonts["footer"],
        fill=COLOR_MUTED,
    )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _font_sizes() -> list[tuple[str, int]]:
    return [
        ("title", TITLE_SIZE),
        ("eyebrow", EYEBROW_SIZE),
        ("body", BODY_SIZE),
        ("footer", FOOTER_SIZE),
    ]
