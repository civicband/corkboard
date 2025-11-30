# API Key Authentication Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Require API key authentication for JSON endpoints (*.json) while keeping HTML endpoints freely accessible. First-party browser requests (like datasette-search-all) should bypass auth via Referer header matching.

**Architecture:** Add auth checking in `datasette_by_subdomain.py` ASGI wrapper with:
1. First-party request detection via Referer header
2. Redis caching for validated API keys
3. civic.observer validation (stubbed for now)

**Tech Stack:** Python async, Redis, httpx

---

## Task 1: Add Redis Dependency and Configuration

**Files:**
- Modify: `pyproject.toml`
- Modify: `config/settings.py`
- Modify: `docker-compose.yml`

**Step 1: Add redis dependency to pyproject.toml**

In `pyproject.toml`, add `redis[hiredis]` to the dependencies list (after `whitenoise`):

```toml
dependencies = [
    "Django>=4.2.0",
    "datasette>=0.64.0",
    "djp>=0.0.6",
    "jinja2>=3.0.0",
    "sqlite-utils>=3.30.0",
    "httpx>=0.24.0",
    "requests>=2.28.0",
    "whitenoise>=6.0.0",
    "redis[hiredis]>=5.0.0",
]
```

**Step 2: Add settings to config/settings.py**

Add at the end of `config/settings.py`:

```python
# API Key Authentication Settings
REDIS_URL = get_env_variable("REDIS_URL", "redis://localhost:6379")
CIVIC_OBSERVER_URL = get_env_variable("CIVIC_OBSERVER_URL", "http://localhost:8080")
CIVIC_OBSERVER_SECRET = get_env_variable("CIVIC_OBSERVER_SECRET", "dev-secret-change-me")

# Cache TTLs (in seconds)
API_KEY_VALID_TTL = 7200  # 2 hours for valid keys
API_KEY_INVALID_TTL = 300  # 5 minutes for invalid keys
```

**Step 3: Add Redis service to docker-compose.yml**

Add a Redis service at the end of `docker-compose.yml`:

```yaml
  redis:
    image: redis:7-alpine
    ports:
      - 6379:6379
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

Also add `REDIS_URL=redis://redis:6379` to the environment for both `django_blue` and `django_green` services.

**Step 4: Sync dependencies**

Run: `uv sync`

**Step 5: Commit**

```bash
git add pyproject.toml config/settings.py docker-compose.yml uv.lock
git commit -m "feat: add Redis dependency and API auth settings"
```

---

## Task 2: Create API Key Validation Module

**Files:**
- Create: `django_plugins/api_key_auth.py`

**Step 1: Create the validation module**

Create `django_plugins/api_key_auth.py`:

```python
"""
API Key authentication for JSON endpoints.

Validates API keys against civic.observer with Redis caching.
"""

import hashlib
import json
import logging
from typing import Optional

import httpx
import redis.asyncio as redis

from django.conf import settings

logger = logging.getLogger(__name__)

# Redis connection (lazy initialization)
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client


def _cache_key(api_key: str) -> str:
    """Generate cache key from API key (hashed for security)."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    return f"apikey:{key_hash}"


async def validate_api_key(api_key: str, subdomain: str) -> dict:
    """
    Validate an API key, using cache when available.

    Returns:
        {"valid": True, "org_id": "...", "org_name": "..."} or
        {"valid": False}
    """
    cache_key = _cache_key(api_key)
    redis_client = await get_redis()

    # Check cache first
    cached = await redis_client.get(cache_key)
    if cached:
        logger.debug(f"API key cache hit for {cache_key}")
        return json.loads(cached)

    # Cache miss - validate against civic.observer
    logger.debug(f"API key cache miss for {cache_key}, calling civic.observer")
    result = await _call_civic_observer(api_key, subdomain)

    # Cache the result
    ttl = settings.API_KEY_VALID_TTL if result["valid"] else settings.API_KEY_INVALID_TTL
    await redis_client.setex(cache_key, ttl, json.dumps(result))

    return result


async def _call_civic_observer(api_key: str, subdomain: str) -> dict:
    """
    Call civic.observer to validate an API key.

    For now, this is stubbed to return invalid for all keys.
    When civic.observer endpoint is ready, this will make an HTTP call.
    """
    # TODO: Replace stub with actual HTTP call when civic.observer is ready
    #
    # async with httpx.AsyncClient() as client:
    #     try:
    #         response = await client.post(
    #             f"{settings.CIVIC_OBSERVER_URL}/api/v1/validate-key",
    #             json={"api_key": api_key, "subdomain": subdomain},
    #             headers={"X-Service-Secret": settings.CIVIC_OBSERVER_SECRET},
    #             timeout=5.0,
    #         )
    #         if response.status_code == 200:
    #             return response.json()
    #     except httpx.RequestError as e:
    #         logger.error(f"Error calling civic.observer: {e}")
    #
    #     return {"valid": False}

    # STUB: For development only, accept keys starting with "dev_"
    if settings.DEBUG and api_key.startswith("dev_"):
        logger.debug("Accepting dev_ key in DEBUG mode")
        return {"valid": True, "org_id": "dev", "org_name": "Development"}

    return {"valid": False}


def extract_api_key(headers: list, query_string: bytes) -> Optional[str]:
    """
    Extract API key from request.

    Checks (in order):
    1. Authorization: Bearer <key> header
    2. X-API-Key: <key> header
    3. api_key query parameter

    Returns None if no key found.
    """
    # Check headers
    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        value = header_value.decode("utf-8")

        if name == "authorization" and value.lower().startswith("bearer "):
            return value[7:].strip()

        if name == "x-api-key":
            return value.strip()

    # Check query string
    if query_string:
        from urllib.parse import parse_qs
        params = parse_qs(query_string.decode("utf-8"))
        if "api_key" in params:
            return params["api_key"][0]

    return None


def is_json_endpoint(path: str) -> bool:
    """Check if the request path is a JSON endpoint."""
    return path.endswith(".json")


def is_first_party_request(headers: list, subdomain: str) -> bool:
    """
    Check if request is a first-party browser request via Referer header.

    First-party requests (e.g., datasette-search-all AJAX calls) are allowed
    without API key authentication. The Referer must match the subdomain
    being requested to prevent cross-origin scraping.

    Args:
        headers: List of (name, value) tuples from ASGI scope
        subdomain: The subdomain being accessed (e.g., "alameda.ca")

    Returns:
        True if Referer matches the expected origin for this subdomain
    """
    # Must match origin exactly, followed by /
    # This prevents prefix attacks like "alameda.ca.civic.band.evil.com"
    expected_origin = f"https://{subdomain}.civic.band/"

    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        if name == "referer":
            referer = header_value.decode("utf-8")
            if referer.startswith(expected_origin):
                return True

    return False


def make_401_response() -> tuple:
    """Create a 401 Unauthorized JSON response."""
    body = json.dumps({
        "error": "API key required",
        "docs": "https://civic.observer/api-keys"
    }).encode("utf-8")

    return body, [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
```

**Step 2: Commit**

```bash
git add django_plugins/api_key_auth.py
git commit -m "feat: add API key validation module with Redis caching"
```

---

## Task 3: Integrate Auth into ASGI Wrapper

**Files:**
- Modify: `django_plugins/datasette_by_subdomain.py`

**Step 1: Add imports at top of file**

Add after existing imports:

```python
from django_plugins.api_key_auth import (
    extract_api_key,
    is_first_party_request,
    is_json_endpoint,
    make_401_response,
    validate_api_key,
)
```

**Step 2: Add helper function to send 401 response**

Add before `datasette_by_subdomain_wrapper`:

```python
async def send_401_response(send):
    """Send a 401 Unauthorized response."""
    body, headers = make_401_response()

    await send({
        "type": "http.response.start",
        "status": 401,
        "headers": headers,
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })
```

**Step 3: Add auth check in datasette_by_subdomain_wrapper**

In `datasette_by_subdomain_wrapper`, after the subdomain is determined and site is looked up (after line 44 `return`), add the JSON auth check:

```python
        # Check API key for JSON endpoints (unless first-party browser request)
        path = scope.get("path", "")
        if is_json_endpoint(path):
            # Allow first-party browser requests (e.g., datasette-search-all)
            # by checking if Referer matches this subdomain
            if not is_first_party_request(headers, subdomain):
                api_key = extract_api_key(headers, scope.get("query_string", b""))

                # No key = instant 401
                if not api_key:
                    await send_401_response(send)
                    return

                # Validate key
                result = await validate_api_key(api_key, subdomain)
                if not result["valid"]:
                    await send_401_response(send)
                    return
```

**Step 4: Commit**

```bash
git add django_plugins/datasette_by_subdomain.py
git commit -m "feat: integrate API key auth into ASGI wrapper for JSON endpoints"
```

---

## Task 4: Add Tests

**Files:**
- Create: `tests/test_api_key_auth.py`

**Step 1: Create test file**

Create `tests/test_api_key_auth.py`:

```python
"""Tests for API key authentication."""

import pytest

from django_plugins.api_key_auth import (
    extract_api_key,
    is_first_party_request,
    is_json_endpoint,
    make_401_response,
)


class TestIsJsonEndpoint:
    """Test JSON endpoint detection."""

    def test_json_endpoint(self):
        assert is_json_endpoint("/meetings/minutes.json") is True

    def test_query_json_endpoint(self):
        assert is_json_endpoint("/meetings/-/query.json") is True

    def test_html_endpoint(self):
        assert is_json_endpoint("/meetings/minutes") is False

    def test_html_query_endpoint(self):
        assert is_json_endpoint("/meetings/-/query") is False

    def test_json_in_path_but_not_extension(self):
        assert is_json_endpoint("/meetings/json/minutes") is False


class TestIsFirstPartyRequest:
    """Test first-party request detection via Referer header."""

    def test_matching_referer_allowed(self):
        """Referer from same subdomain should be first-party."""
        headers = [(b"referer", b"https://alameda.ca.civic.band/meetings/minutes")]
        assert is_first_party_request(headers, "alameda.ca") is True

    def test_different_subdomain_rejected(self):
        """Referer from different subdomain should not be first-party."""
        headers = [(b"referer", b"https://oakland.ca.civic.band/meetings/minutes")]
        assert is_first_party_request(headers, "alameda.ca") is False

    def test_external_referer_rejected(self):
        """Referer from external site should not be first-party."""
        headers = [(b"referer", b"https://example.com/scraper")]
        assert is_first_party_request(headers, "alameda.ca") is False

    def test_no_referer_rejected(self):
        """Request without Referer should not be first-party."""
        headers = [(b"content-type", b"application/json")]
        assert is_first_party_request(headers, "alameda.ca") is False

    def test_subdomain_prefix_attack_rejected(self):
        """Subdomain prefix attack should not be first-party."""
        headers = [(b"referer", b"https://alameda.ca.civic.band.evil.com/")]
        assert is_first_party_request(headers, "alameda.ca") is False


class TestExtractApiKey:
    """Test API key extraction from requests."""

    def test_bearer_token(self):
        headers = [(b"authorization", b"Bearer test_key_123")]
        assert extract_api_key(headers, b"") == "test_key_123"

    def test_bearer_token_case_insensitive(self):
        headers = [(b"authorization", b"bearer test_key_123")]
        assert extract_api_key(headers, b"") == "test_key_123"

    def test_x_api_key_header(self):
        headers = [(b"x-api-key", b"test_key_456")]
        assert extract_api_key(headers, b"") == "test_key_456"

    def test_query_param(self):
        headers = []
        query = b"api_key=test_key_789&other=value"
        assert extract_api_key(headers, query) == "test_key_789"

    def test_header_takes_precedence_over_query(self):
        headers = [(b"authorization", b"Bearer header_key")]
        query = b"api_key=query_key"
        assert extract_api_key(headers, query) == "header_key"

    def test_no_key(self):
        headers = [(b"content-type", b"application/json")]
        assert extract_api_key(headers, b"") is None

    def test_empty_request(self):
        assert extract_api_key([], b"") is None


class TestMake401Response:
    """Test 401 response generation."""

    def test_response_body(self):
        body, headers = make_401_response()
        assert b"API key required" in body
        assert b"https://civic.observer/api-keys" in body

    def test_response_headers(self):
        body, headers = make_401_response()
        header_dict = {k.decode(): v.decode() for k, v in headers}
        assert header_dict["content-type"] == "application/json"
        assert header_dict["content-length"] == str(len(body))


@pytest.mark.asyncio
class TestValidateApiKey:
    """Test API key validation (with stubbed civic.observer)."""

    @pytest.fixture(autouse=True)
    def reset_redis_client(self):
        """Reset Redis client between tests."""
        from django_plugins import api_key_auth
        api_key_auth._redis_client = None

    async def test_dev_key_valid_in_debug_mode(self, settings):
        from django_plugins.api_key_auth import validate_api_key

        settings.DEBUG = True
        # Dev keys are accepted by the stub in DEBUG mode
        result = await validate_api_key("dev_test_key", "alameda.ca")
        assert result["valid"] is True
        assert result["org_id"] == "dev"

    async def test_dev_key_rejected_in_production(self, settings):
        from django_plugins.api_key_auth import validate_api_key

        settings.DEBUG = False
        # Dev keys are rejected when DEBUG=False
        result = await validate_api_key("dev_test_key", "alameda.ca")
        assert result["valid"] is False

    async def test_invalid_key(self, settings):
        from django_plugins.api_key_auth import validate_api_key

        settings.DEBUG = True
        # Non-dev keys are rejected by the stub
        result = await validate_api_key("invalid_key", "alameda.ca")
        assert result["valid"] is False
```

**Step 2: Run tests**

Run: `just test tests/test_api_key_auth.py`

**Step 3: Commit**

```bash
git add tests/test_api_key_auth.py
git commit -m "test: add tests for API key authentication"
```

---

## Task 5: Add pytest-redis for Integration Tests

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add fakeredis for testing**

In `pyproject.toml`, add `fakeredis` to test dependencies:

```toml
test = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "pytest-django>=4.5.0",
    "fakeredis>=2.20.0",
]
```

Also add to dev dependencies.

**Step 2: Sync dependencies**

Run: `uv sync`

**Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add fakeredis for testing"
```

---

## Task 6: Final Verification

**Files:**
- Review all modified files

**Step 1: Run linting**

Run: `just lint`

If there are issues, run: `just lint-fix`

**Step 2: Run all tests**

Run: `just test`

Expected: All tests pass

**Step 3: Manual testing (if Redis is available)**

Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`

Run: `just serve`

Test JSON endpoint without key:
```bash
curl -i "http://localhost:8001/meetings/-/query.json?sql=select+1"
# Should return 401
```

Test with dev key:
```bash
curl -i -H "Authorization: Bearer dev_test" "http://localhost:8001/meetings/-/query.json?sql=select+1"
# Should work (in dev mode)
```

**Step 4: Final commit if any cleanup needed**

```bash
git add -A
git commit -m "chore: API key auth cleanup"
```

---

## Summary

After completing all tasks, you will have:

1. **Redis dependency** added to project
2. **`django_plugins/api_key_auth.py`** - Validation module with:
   - First-party request detection via Referer header
   - Redis caching (2hr valid, 5min invalid TTL)
   - Key extraction from header/query param
   - Stubbed civic.observer call (accepts `dev_*` keys in DEBUG mode)
3. **`django_plugins/datasette_by_subdomain.py`** - Modified to:
   - Check if request is JSON endpoint
   - Allow first-party browser requests (matching Referer) without auth
   - Instant 401 if no key present for non-first-party requests
   - Validate key and 401 if invalid
4. **Tests** for all auth logic including first-party detection
5. **Docker compose** with Redis service

**To enable real validation later:**
1. Build the `/api/v1/validate-key` endpoint in civic.observer
2. Uncomment the HTTP call in `_call_civic_observer()`
3. Remove the dev key stub
4. Set `CIVIC_OBSERVER_URL` and `CIVIC_OBSERVER_SECRET` env vars
