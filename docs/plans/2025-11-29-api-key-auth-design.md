# API Key Authentication Design

## Problem Statement

CivicBand's JSON API endpoints (*.json) are currently open to anyone. We need to require API key authentication for JSON endpoints while keeping HTML endpoints freely accessible. Additionally, first-party browser requests (like datasette-search-all AJAX calls) should work without requiring an API key.

## Solution Overview

Add API key checking in the ASGI wrapper (`datasette_by_subdomain.py`) that:
1. Allows first-party browser requests (matching Referer header) without auth
2. Instantly rejects JSON requests with no key (DDoS protection)
3. Validates keys against civic.observer over Tailscale
4. Caches results in Redis for performance

### Design Decisions

1. **Intercept location:** ASGI wrapper in `datasette_by_subdomain.py` (before Datasette is created)
2. **First-party bypass:** Requests with Referer matching the subdomain are allowed (e.g., datasette-search-all)
3. **Key validation:** HTTP call to civic.observer, cached in Redis
4. **Key passing:** Header preferred (`Authorization: Bearer <key>`), query param fallback (`?api_key=<key>`)
5. **Auth failure:** 401 JSON error with docs link
6. **Cache TTL:** Valid keys 2 hours, invalid keys 5 minutes
7. **Service auth:** Shared secret header + Tailscale-only access
8. **Missing key:** Instant 401 with no cache/network overhead

## Request Flow

```
Request: /meetings/-/query.json
              │
              ▼
    ┌─────────────────────┐
    │ Is .json endpoint?  │──No──▶ Proceed to Datasette
    └─────────────────────┘
              │Yes
              ▼
    ┌─────────────────────┐
    │ Referer matches     │──Yes─▶ Proceed to Datasette
    │ request subdomain?  │        (first-party browser request)
    └─────────────────────┘
              │No
              ▼
    ┌─────────────────────┐
    │ API key present?    │──No──▶ Instant 401
    └─────────────────────┘
              │Yes
              ▼
    ┌─────────────────────┐
    │ Key in Redis cache? │──Yes─▶ Valid? → Datasette / Invalid? → 401
    └─────────────────────┘
              │No (cache miss)
              ▼
    ┌─────────────────────┐
    │ Call civic.observer │
    │ Cache result        │──────▶ Valid? → Datasette / Invalid? → 401
    └─────────────────────┘
```

## First-Party Request Detection

Browser requests from the same subdomain are detected via the `Referer` header:

- Request to `alameda.ca.civic.band/meetings/minutes.json`
- Referer must start with `https://alameda.ca.civic.band/`
- This allows datasette-search-all and other first-party AJAX to work
- Scrapers without valid matching referer need an API key

**Security considerations:**
- Referer can be spoofed, but this raises the bar for scrapers
- The goal is scraping prevention, not bulletproof security
- Exact subdomain match prevents cross-origin attacks
- Trailing slash in match prevents prefix attacks (e.g., `alameda.ca.civic.band.evil.com`)

## civic.observer Contract (to build later)

**Endpoint:** `POST http://<tailscale-hostname>/api/v1/validate-key`

**Request:**
```json
{
  "api_key": "cb_live_abc123...",
  "subdomain": "alameda.ca"
}
```

**Response (valid):**
```json
{
  "valid": true,
  "org_id": "org_123",
  "org_name": "Alameda Research Lab"
}
```

**Response (invalid):**
```json
{
  "valid": false
}
```

**Authentication:** `X-Service-Secret` header + Tailscale network only

## Error Response

```json
{
  "error": "API key required",
  "docs": "https://civic.observer/api-keys"
}
```

## Files Modified/Created

- `django_plugins/api_key_auth.py` - Validation module with referer checking
- `django_plugins/datasette_by_subdomain.py` - Integrated auth logic
- `docker-compose.yml` - Added Redis service
- `config/settings.py` - Added Redis and civic.observer settings
- `pyproject.toml` - Added redis dependency
- `tests/test_api_key_auth.py` - Comprehensive tests

## Environment Variables

- `REDIS_URL` - Redis connection string (default: `redis://localhost:6379`)
- `CIVIC_OBSERVER_URL` - Tailscale URL for civic.observer (e.g., `http://civic-observer.tail1234.ts.net`)
- `CIVIC_OBSERVER_SECRET` - Shared secret for service-to-service auth
