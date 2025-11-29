# Analytics Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add subdomain property to all client-side events and add deduplication to server-side SQL query tracking.

**Architecture:** Modify the Umami plugin to inject JavaScript that manually tracks pageviews with subdomain and patches `umami.track` for custom events. Add an in-memory LRU cache to civic_analytics.py to deduplicate SQL queries per IP/subdomain/query.

**Tech Stack:** Python, Datasette plugins, JavaScript

---

## Task 1: Add Tests for Umami Plugin Subdomain Tracking

**Files:**
- Create: `tests/test_plugins/test_umami.py`

**Step 1: Write the failing tests**

```python
"""
Tests for umami.py plugin.

Tests cover:
- Script injection without auto-track
- Subdomain extraction JavaScript
- Manual pageview tracking
- umami.track patching for custom events
"""

import pytest
from plugins.umami import extra_body_script


class TestUmamiPlugin:
    """Test Umami plugin script injection."""

    def test_script_does_not_have_auto_track(self):
        """Script should not have data-auto-track attribute."""
        result = extra_body_script(None)
        script = result["script"]
        assert "data-auto-track" not in script

    def test_script_includes_umami_loader(self):
        """Script should include Umami script loader."""
        result = extra_body_script(None)
        script = result["script"]
        assert "https://analytics.civic.band/sunshine" in script
        assert "6250918b-6a0c-4c05-a6cb-ec8f86349e1a" in script

    def test_script_extracts_subdomain(self):
        """Script should extract subdomain from hostname."""
        result = extra_body_script(None)
        script = result["script"]
        # Should have subdomain extraction logic
        assert "hostname" in script.lower() or "subdomain" in script.lower()

    def test_script_tracks_pageview_with_subdomain(self):
        """Script should track pageview with subdomain property."""
        result = extra_body_script(None)
        script = result["script"]
        # Should call umami.track for pageview
        assert "pageview" in script.lower()
        assert "subdomain" in script

    def test_script_patches_umami_track(self):
        """Script should patch umami.track to auto-include subdomain."""
        result = extra_body_script(None)
        script = result["script"]
        # Should modify umami.track function
        assert "umami.track" in script
```

**Step 2: Run test to verify it fails**

Run: `just test tests/test_plugins/test_umami.py -v`
Expected: FAIL - tests should fail because current implementation has `data-auto-track="true"`

**Step 3: Commit test file**

```bash
git add tests/test_plugins/test_umami.py
git commit -m "test: add tests for umami plugin subdomain tracking"
```

---

## Task 2: Implement Umami Plugin Subdomain Tracking

**Files:**
- Modify: `plugins/umami.py`

**Step 1: Implement the subdomain tracking**

Replace the contents of `plugins/umami.py` with:

```python
"""
Umami Analytics Plugin for Datasette

Injects Umami tracking script with:
- Manual pageview tracking with subdomain property
- Patched umami.track to auto-include subdomain on all custom events
"""

from datasette import hookimpl


@hookimpl
def extra_body_script(datasette):
    """Inject Umami tracking script with subdomain support."""

    # JavaScript that:
    # 1. Loads Umami without auto-track
    # 2. Extracts subdomain from hostname
    # 3. Tracks pageview with subdomain
    # 4. Patches umami.track to auto-include subdomain

    script = '''</script>
<script src="https://analytics.civic.band/sunshine" data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a"></script>
<script>
(function() {
    // Extract subdomain from hostname (everything except last 2 parts)
    var parts = window.location.hostname.split('.');
    var subdomain = parts.length > 2 ? parts.slice(0, -2).join('.') : null;

    // Wait for Umami to load, then set up tracking
    function setupTracking() {
        if (typeof umami === 'undefined') {
            setTimeout(setupTracking, 50);
            return;
        }

        // Track pageview with subdomain
        if (subdomain) {
            umami.track('pageview', { subdomain: subdomain });
        } else {
            umami.track('pageview');
        }

        // Patch umami.track to auto-include subdomain
        var originalTrack = umami.track;
        umami.track = function(eventName, eventData) {
            if (subdomain && eventData && typeof eventData === 'object') {
                eventData.subdomain = subdomain;
            } else if (subdomain && !eventData) {
                eventData = { subdomain: subdomain };
            }
            return originalTrack.call(umami, eventName, eventData);
        };
    }

    setupTracking();
})();
</script>
<script>'''

    return {"script": script}
```

**Step 2: Run tests to verify they pass**

Run: `just test tests/test_plugins/test_umami.py -v`
Expected: PASS - all tests should pass

**Step 3: Run full test suite**

Run: `just test`
Expected: All tests pass

**Step 4: Commit implementation**

```bash
git add plugins/umami.py
git commit -m "feat: add subdomain tracking to all client-side Umami events

- Remove data-auto-track to disable automatic pageview tracking
- Extract subdomain from hostname (everything except last 2 parts)
- Track manual pageview with subdomain property
- Patch umami.track to auto-include subdomain on all custom events"
```

---

## Task 3: Add Tests for SQL Query Deduplication

**Files:**
- Modify: `tests/test_plugins/test_civic_analytics.py`

**Step 1: Write the failing tests**

Add to the end of `tests/test_plugins/test_civic_analytics.py`:

```python
class TestSQLQueryDeduplication:
    """Test SQL query deduplication logic."""

    def test_query_cache_exists(self):
        """SQLQueryCache class should exist."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)
        assert cache is not None

    def test_query_cache_should_track_new_query(self):
        """New queries should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result is True

    def test_query_cache_should_not_track_duplicate(self):
        """Duplicate queries from same IP/subdomain should not be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        # First call - should track
        result1 = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result1 is True

        # Second call - same query, same IP, same subdomain - should not track
        result2 = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result2 is False

    def test_query_cache_different_ip_should_track(self):
        """Same query from different IP should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Different IP - should track
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.2", "alameda.ca")
        assert result is True

    def test_query_cache_different_subdomain_should_track(self):
        """Same query from different subdomain should be tracked."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Different subdomain - should track
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "oakland.ca")
        assert result is True

    def test_query_cache_normalizes_whitespace(self):
        """Queries should be normalized for comparison."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Same query with different whitespace - should not track
        result = cache.should_track("SELECT  *  FROM  agendas", "192.168.1.1", "alameda.ca")
        assert result is False

    def test_query_cache_normalizes_case(self):
        """Queries should be case-insensitive for comparison."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=100, ttl_seconds=3600)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Same query with different case - should not track
        result = cache.should_track("select * from agendas", "192.168.1.1", "alameda.ca")
        assert result is False

    def test_query_cache_max_size(self):
        """Cache should respect max size with LRU eviction."""
        from plugins.civic_analytics import SQLQueryCache
        cache = SQLQueryCache(max_size=3, ttl_seconds=3600)

        # Add 3 entries
        cache.should_track("query1", "192.168.1.1", "alameda.ca")
        cache.should_track("query2", "192.168.1.1", "alameda.ca")
        cache.should_track("query3", "192.168.1.1", "alameda.ca")

        # Add 4th entry - should evict oldest
        cache.should_track("query4", "192.168.1.1", "alameda.ca")

        # query1 should have been evicted, so it should be tracked again
        result = cache.should_track("query1", "192.168.1.1", "alameda.ca")
        assert result is True

    def test_query_cache_ttl_expiry(self):
        """Entries should expire after TTL."""
        import time
        from plugins.civic_analytics import SQLQueryCache

        cache = SQLQueryCache(max_size=100, ttl_seconds=1)

        cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should track again after expiry
        result = cache.should_track("SELECT * FROM agendas", "192.168.1.1", "alameda.ca")
        assert result is True
```

**Step 2: Run test to verify it fails**

Run: `just test tests/test_plugins/test_civic_analytics.py::TestSQLQueryDeduplication -v`
Expected: FAIL - `ImportError: cannot import name 'SQLQueryCache' from 'plugins.civic_analytics'`

**Step 3: Commit test file**

```bash
git add tests/test_plugins/test_civic_analytics.py
git commit -m "test: add tests for SQL query deduplication"
```

---

## Task 4: Implement SQL Query Deduplication Cache

**Files:**
- Modify: `plugins/civic_analytics.py`

**Step 1: Add SQLQueryCache class**

Add after the imports and before the `UmamiEventTracker` class (around line 31):

```python
import hashlib
import re
from collections import OrderedDict


class SQLQueryCache:
    """LRU cache for SQL query deduplication.

    Tracks queries by (normalized_query, client_ip, subdomain) to prevent
    duplicate tracking of the same query from the same user.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, float] = OrderedDict()

    def _normalize_query(self, query: str) -> str:
        """Normalize query for comparison: lowercase, collapse whitespace."""
        normalized = query.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    def _make_key(self, query: str, client_ip: str, subdomain: str) -> str:
        """Create cache key from query, IP, and subdomain."""
        normalized = self._normalize_query(query)
        key_string = f"{normalized}|{client_ip}|{subdomain}"
        return hashlib.sha256(key_string.encode()).hexdigest()

    def should_track(self, query: str, client_ip: str, subdomain: str) -> bool:
        """Check if query should be tracked. Returns True if new, False if duplicate.

        Also updates the cache with the query if it should be tracked.
        """
        current_time = time.time()
        key = self._make_key(query, client_ip, subdomain)

        # Check if key exists and is not expired
        if key in self._cache:
            timestamp = self._cache[key]
            if current_time - timestamp < self.ttl_seconds:
                # Move to end (LRU update) and return False (don't track)
                self._cache.move_to_end(key)
                return False
            else:
                # Expired, remove it
                del self._cache[key]

        # Add new entry
        self._cache[key] = current_time

        # Evict oldest if over max size
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

        return True


# Global cache instance for SQL query deduplication
_sql_query_cache = SQLQueryCache(max_size=1000, ttl_seconds=3600)
```

**Step 2: Run deduplication tests to verify they pass**

Run: `just test tests/test_plugins/test_civic_analytics.py::TestSQLQueryDeduplication -v`
Expected: PASS - all deduplication tests should pass

**Step 3: Commit cache implementation**

```bash
git add plugins/civic_analytics.py
git commit -m "feat: add SQLQueryCache for SQL query deduplication

- LRU cache with configurable max size (default 1000)
- TTL-based expiry (default 1 hour)
- Normalizes queries (lowercase, whitespace collapse)
- Keys on (query, IP, subdomain) tuple"
```

---

## Task 5: Integrate Deduplication into ASGI Middleware

**Files:**
- Modify: `plugins/civic_analytics.py`
- Modify: `tests/test_plugins/test_civic_analytics.py`

**Step 1: Write test for deduplication integration**

Add to `tests/test_plugins/test_civic_analytics.py` in the `TestASGIWrapper` class:

```python
    @pytest.mark.asyncio
    async def test_sql_query_deduplication(self, asgi_receive, asgi_send):
        """Duplicate SQL queries should not be tracked."""
        from plugins.civic_analytics import asgi_wrapper, _sql_query_cache

        # Clear the cache before test
        _sql_query_cache._cache.clear()

        mock_app = AsyncMock()
        scope = {
            "type": "http",
            "path": "/meetings",
            "query_string": b"sql=SELECT+*+FROM+agendas",
            "headers": [
                (b"host", b"alameda.ca.civic.org"),
                (b"x-forwarded-for", b"192.168.1.1"),
            ],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.dict(os.environ, {"UMAMI_ANALYTICS_ENABLED": "true"}):
            wrapper = asgi_wrapper(None)
            wrapped_app = wrapper(mock_app)

            with patch("httpx.AsyncClient", return_value=mock_client):
                # First request - should track
                await wrapped_app(scope, asgi_receive, asgi_send)
                assert mock_client.post.call_count == 1

                # Second identical request - should NOT track
                mock_app.reset_mock()
                await wrapped_app(scope, asgi_receive, asgi_send)
                assert mock_client.post.call_count == 1  # Still 1, not 2
```

**Step 2: Run test to verify it fails**

Run: `just test tests/test_plugins/test_civic_analytics.py::TestASGIWrapper::test_sql_query_deduplication -v`
Expected: FAIL - deduplication not integrated yet

**Step 3: Modify ASGI wrapper to use deduplication**

In `plugins/civic_analytics.py`, find the `asgi_wrapper` function and modify the SQL query section.

First, add a helper function to extract client IP (add after `parse_datasette_path`):

```python
def get_client_ip(headers: Dict[str, str], scope: Dict) -> str:
    """Extract client IP from headers or scope."""
    # Check X-Forwarded-For header first (for proxied requests)
    forwarded_for = headers.get("x-forwarded-for", "")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    real_ip = headers.get("x-real-ip", "")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection
    client = scope.get("client")
    if client:
        return client[0]

    return "unknown"
```

Then, modify the SQL query detection section in the `wrapper` function (around line 238-300). Replace the SQL query block:

```python
            # Detect and track SQL query events
            elif "sql" in query_params and query_params["sql"]:
                sql_text = query_params["sql"][0]

                # Check deduplication cache
                client_ip = get_client_ip(headers, scope)
                if not _sql_query_cache.should_track(sql_text, client_ip, subdomain):
                    # Duplicate query, skip tracking but continue with request
                    await app(scope, receive, send)
                    return

                event_name = "sql_query"

                # Extract database from path
                path_info = parse_datasette_path(path)
                database = path_info.get("database")

                # ... rest of the existing sql_query code ...
```

**Step 4: Run deduplication integration test**

Run: `just test tests/test_plugins/test_civic_analytics.py::TestASGIWrapper::test_sql_query_deduplication -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `just test`
Expected: All tests pass

**Step 6: Commit integration**

```bash
git add plugins/civic_analytics.py tests/test_plugins/test_civic_analytics.py
git commit -m "feat: integrate SQL query deduplication into ASGI middleware

- Extract client IP from X-Forwarded-For, X-Real-IP, or direct connection
- Check deduplication cache before tracking SQL queries
- Skip duplicate queries from same IP/subdomain within 1 hour"
```

---

## Task 6: Final Verification and Cleanup

**Files:**
- Review: All modified files

**Step 1: Run full test suite**

Run: `just test`
Expected: All tests pass

**Step 2: Run linting**

Run: `just lint`
Expected: No linting errors

**Step 3: Run formatting check**

Run: `just format-check`
Expected: No formatting issues (or run `just format` to fix)

**Step 4: Verify the implementation**

Manually review:
- `plugins/umami.py` - Should inject script without `data-auto-track`, with subdomain extraction and patching
- `plugins/civic_analytics.py` - Should have `SQLQueryCache` class and deduplication in ASGI wrapper

**Step 5: Create final commit if any cleanup needed**

If formatting or minor fixes were needed:
```bash
git add -A
git commit -m "chore: formatting and cleanup"
```

---

## Summary

After completing all tasks, you will have:

1. **`plugins/umami.py`** - Modified to:
   - Remove `data-auto-track="true"`
   - Inject JavaScript that extracts subdomain from hostname
   - Track manual pageview with subdomain property
   - Patch `umami.track` to auto-include subdomain on all custom events

2. **`plugins/civic_analytics.py`** - Modified to:
   - Add `SQLQueryCache` class for LRU deduplication
   - Add `get_client_ip` helper function
   - Check deduplication cache before tracking SQL queries
   - Skip duplicate queries from same IP/subdomain within 1 hour

3. **`tests/test_plugins/test_umami.py`** - New file with tests for umami plugin

4. **`tests/test_plugins/test_civic_analytics.py`** - Extended with deduplication tests

All changes follow TDD (tests first), include proper commits, and maintain the existing code style.
