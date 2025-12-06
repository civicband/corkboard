"""
API Key authentication for JSON endpoints.

Validates API keys against civic.observer with Redis caching.
Also includes rate limiting and research tool detection.
"""

import hashlib
import json
import logging
from typing import Optional
from urllib.parse import parse_qs, urlencode

import redis.asyncio as redis
from django.conf import settings

logger = logging.getLogger(__name__)

# Research tools that get full JSON access without API key
# These are legitimate academic tools that shouldn't be rate-limited
RESEARCH_TOOL_USER_AGENTS = ["zotero", "mendeley", "endnote", "papers"]

# Rate limiting settings
RATE_LIMIT_REQUESTS = 15  # requests per window
RATE_LIMIT_WINDOW_SECONDS = 60  # 1 minute window

# Result size cap for unauthenticated requests
MAX_RESULTS_UNAUTHENTICATED = 100

# Redis connection (lazy initialization)
_redis_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get or create Redis connection."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL)
    return _redis_client


def set_redis_client(client: redis.Redis) -> None:
    """Set the Redis client (for testing)."""
    global _redis_client
    _redis_client = client


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
    ttl = (
        settings.API_KEY_VALID_TTL if result["valid"] else settings.API_KEY_INVALID_TTL
    )
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
    # import httpx
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
        params = parse_qs(query_string.decode("utf-8"))
        if "api_key" in params:
            return params["api_key"][0]

    return None


def is_json_endpoint(path: str) -> bool:
    """Check if the request path is a JSON endpoint."""
    return path.endswith(".json")


def is_internal_service_request(headers: list) -> bool:
    """
    Check if request is from an internal service (e.g., civic.observer).

    Internal services authenticate via X-Service-Secret header matching
    the CIVIC_OBSERVER_SECRET setting.

    Args:
        headers: List of (name, value) tuples from ASGI scope

    Returns:
        True if X-Service-Secret header matches the configured secret
    """
    expected_secret = settings.CIVIC_OBSERVER_SECRET
    if not expected_secret or expected_secret == "dev-secret-change-me":
        # Don't allow bypass if secret is not configured
        return False

    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        if name == "x-service-secret":
            provided_secret = header_value.decode("utf-8")
            # Use constant-time comparison to prevent timing attacks
            import hmac

            return hmac.compare_digest(provided_secret, expected_secret)

    return False


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
    # Domain is configurable via CIVIC_BAND_DOMAIN env var for development
    domain = settings.CIVIC_BAND_DOMAIN
    expected_origin = f"https://{subdomain}.{domain}/"
    if settings.DEBUG:
        expected_origin = f"http://{subdomain}.{domain}/"

    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        if name == "referer":
            referer = header_value.decode("utf-8")
            if referer.startswith(expected_origin):
                return True

    return False


def make_401_response() -> tuple:
    """Create a 401 Unauthorized JSON response."""
    body = json.dumps(
        {"error": "API key required", "docs": "https://civic.observer/api-keys"}
    ).encode("utf-8")

    return body, [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]


def is_research_tool_request(headers: list) -> bool:
    """
    Check if request is from a known research tool via User-Agent.

    Research tools like Zotero, Mendeley, EndNote, and Papers are allowed
    full JSON access without API key authentication, as they represent
    legitimate academic use cases.

    Args:
        headers: List of (name, value) tuples from ASGI scope

    Returns:
        True if User-Agent contains a known research tool identifier
    """
    for header_name, header_value in headers:
        name = header_name.decode("utf-8").lower()
        if name == "user-agent":
            user_agent = header_value.decode("utf-8").lower()
            for tool in RESEARCH_TOOL_USER_AGENTS:
                if tool in user_agent:
                    logger.debug(f"Research tool detected: {tool} in User-Agent")
                    return True
    return False


def _rate_limit_key(ip_address: str) -> str:
    """Generate Redis key for rate limiting by IP."""
    return f"ratelimit:{ip_address}"


async def check_rate_limit(ip_address: str) -> bool:
    """
    Check if an IP address has exceeded the rate limit.

    Uses a fixed-window rate limiting approach with Redis.
    Allows RATE_LIMIT_REQUESTS requests per RATE_LIMIT_WINDOW_SECONDS.

    Args:
        ip_address: The client's IP address

    Returns:
        True if rate limit exceeded, False if request is allowed
    """
    redis_client = await get_redis()
    key = _rate_limit_key(ip_address)

    # Get current count
    current = await redis_client.get(key)

    if current is None:
        # First request in window - set count to 1 with expiry
        await redis_client.setex(key, RATE_LIMIT_WINDOW_SECONDS, 1)
        return False

    count = int(current)
    if count >= RATE_LIMIT_REQUESTS:
        logger.info(f"Rate limit exceeded for IP {ip_address}: {count} requests")
        return True

    # Increment count
    await redis_client.incr(key)
    return False


def cap_result_size(query_string: bytes) -> bytes:
    """
    Cap the _size parameter to MAX_RESULTS_UNAUTHENTICATED.

    If _size is not present or exceeds the maximum, set it to the max.
    This ensures unauthenticated requests can't retrieve unlimited data.

    Args:
        query_string: Original query string bytes

    Returns:
        Modified query string with capped _size parameter
    """
    if not query_string:
        return f"_size={MAX_RESULTS_UNAUTHENTICATED}".encode("utf-8")

    params = parse_qs(query_string.decode("utf-8"), keep_blank_values=True)

    # Get current _size value
    current_size = params.get("_size", [None])[0]

    if current_size is None:
        # No _size specified - add the cap
        params["_size"] = [str(MAX_RESULTS_UNAUTHENTICATED)]
    else:
        try:
            size_int = int(current_size)
            if size_int > MAX_RESULTS_UNAUTHENTICATED:
                params["_size"] = [str(MAX_RESULTS_UNAUTHENTICATED)]
        except ValueError:
            # Invalid _size value - set to max
            params["_size"] = [str(MAX_RESULTS_UNAUTHENTICATED)]

    # Rebuild query string - flatten lists back to single values for urlencode
    flat_params = {}
    for key, values in params.items():
        if len(values) == 1:
            flat_params[key] = values[0]
        else:
            # Multiple values for same key - keep as list for urlencode's doseq
            flat_params[key] = values

    # Use doseq=True to handle multi-value params properly
    return urlencode(flat_params, doseq=True).encode("utf-8")


def make_402_rate_limit_response() -> tuple:
    """Create a 402 Payment Required JSON response for rate limiting."""
    body = json.dumps(
        {
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded. Maximum {RATE_LIMIT_REQUESTS} requests per minute.",
            "get_api_key": "https://civic.observer/api-keys",
        }
    ).encode("utf-8")

    return body, [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
