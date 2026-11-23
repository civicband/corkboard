"""Process-wide state for the Open Graph card endpoint.

Datasette's ``--plugins-dir`` loads ``plugins/og_card.py`` by executing the
file as a *new* module (``datasette.utils.module_from_path``), so that module
object is distinct from the ``plugins.og_card`` that Django imports. Module
globals therefore cannot hold state that must be shared: the Datasette route
and the Django view would each get their own cache and their own rate-limit
buckets.

Everything shared lives here instead. This module is imported normally
(``from plugins.og_card_state import ...``), so both copies of the plugin
resolve it through ``sys.modules`` and see the same objects.
"""

import os
import tempfile
import time
from collections import OrderedDict

# Uncached-render guard: N fresh renders per window per client IP.
RENDER_BURST = int(os.getenv("OG_CARD_RENDER_BURST", "10"))
RENDER_WINDOW_SECONDS = float(os.getenv("OG_CARD_RENDER_WINDOW", "60"))

# Rendered cards kept in memory in front of the disk cache (~40KB each).
MEMORY_CACHE_SIZE = int(os.getenv("OG_CARD_MEMORY_CACHE_SIZE", "128"))

DEFAULT_CACHE_DIR = os.path.join(tempfile.gettempdir(), "civicband-og-cards")

# {key: png bytes}, most-recently-used last.
_render_lru: OrderedDict[str, bytes] = OrderedDict()
# {client key: (window_started_at, renders_in_window)}
_render_buckets: dict[str, tuple[float, int]] = {}


def cache_dir() -> str:
    """Directory for rendered cards (``OG_CARD_CACHE_DIR`` overridable)."""
    return os.getenv("OG_CARD_CACHE_DIR", DEFAULT_CACHE_DIR)


def memory_get(key: str) -> bytes | None:
    png = _render_lru.get(key)
    if png is not None:
        _render_lru.move_to_end(key)
    return png


def memory_put(key: str, png: bytes) -> None:
    _render_lru[key] = png
    _render_lru.move_to_end(key)
    while len(_render_lru) > MEMORY_CACHE_SIZE:
        _render_lru.popitem(last=False)


def memory_clear() -> None:
    _render_lru.clear()


def allow_render(client_ip: str) -> bool:
    """Token-bucket guard for *uncached* renders. ``True`` means allowed."""
    now = time.monotonic()
    started, count = _render_buckets.get(client_ip, (now, 0))
    if now - started >= RENDER_WINDOW_SECONDS:
        started, count = now, 0
    if count >= RENDER_BURST:
        _render_buckets[client_ip] = (started, count)
        return False
    _render_buckets[client_ip] = (started, count + 1)
    # Opportunistic cleanup so a long-lived worker cannot grow this dict
    # without bound when it sees many distinct client IPs.
    if len(_render_buckets) > 4096:
        for key, (window_start, _) in list(_render_buckets.items()):
            if now - window_start >= RENDER_WINDOW_SECONDS:
                _render_buckets.pop(key, None)
    return True


def reset() -> None:
    """Clear the memory cache and render-guard buckets (tests)."""
    _render_lru.clear()
    _render_buckets.clear()
