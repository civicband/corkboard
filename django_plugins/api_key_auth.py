"""
API Key authentication for JSON endpoints.

Validates API keys against civic.observer with Redis caching.
"""

import hashlib
import json
import logging
from typing import Optional
from urllib.parse import parse_qs

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
