"""
CivicBand Analytics Plugin

Tracks search queries and SQL queries by sending events to Umami Analytics.
This plugin intercepts requests and sends detailed event data to Umami for analysis.

Events tracked:
- search_query: Full-text searches (via ?_search=) with query terms and filters
- sql_query: Custom SQL queries (via ?sql=) with query text and parameters

Note: Table views and row views are already tracked by client-side Umami integration.
"""

import hashlib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Dict, Optional
from urllib.parse import parse_qs

import httpx
from datasette import hookimpl

logger = logging.getLogger(__name__)

# Configuration from environment
UMAMI_URL = os.getenv("UMAMI_URL", "https://analytics.civic.band")
UMAMI_WEBSITE_ID = os.getenv("UMAMI_WEBSITE_ID", "6250918b-6a0c-4c05-a6cb-ec8f86349e1a")
UMAMI_API_KEY = os.getenv("UMAMI_API_KEY")  # Optional API key for authentication
UMAMI_ENABLED = os.getenv("UMAMI_ANALYTICS_ENABLED", "true").lower() == "true"


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
        normalized = re.sub(r"\s+", " ", normalized)
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


class UmamiEventTracker:
    """Sends events to Umami Analytics API."""

    def __init__(self, url: str, website_id: str):
        self.url = url.rstrip("/")
        self.website_id = website_id
        self.endpoint = f"{self.url}/api/send"

    async def track_event(
        self,
        event_name: str,
        url: str,
        title: str = None,
        referrer: str = None,
        hostname: str = "civic.band",
        event_data: Dict = None,
    ):
        """Send an event to Umami Analytics."""
        if not UMAMI_ENABLED:
            return

        try:
            payload = {
                "type": "event",
                "payload": {
                    "hostname": hostname,
                    "language": "en-US",
                    "referrer": referrer or "",
                    "screen": "1920x1080",
                    "title": title or event_name,
                    "url": url,
                    "website": self.website_id,
                    "name": event_name,
                },
            }

            # Add custom event data if provided
            if event_data:
                # Ensure data meets Umami constraints
                cleaned_data = self._clean_event_data(event_data)
                payload["payload"]["data"] = cleaned_data

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            # Add API key if available
            if UMAMI_API_KEY:
                headers["Authorization"] = f"Bearer {UMAMI_API_KEY}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=5.0,
                )

                if response.status_code == 200:
                    print(f"Event tracked: {event_name}")
                else:
                    logger.warning(f"Event tracking failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Failed to track event: {e}")
            # Don't raise - tracking failures shouldn't break the app

    def _clean_event_data(self, data: Dict) -> Dict:
        """Clean event data to meet Umami constraints."""
        cleaned = {}
        property_count = 0

        for key, value in data.items():
            if property_count >= 50:
                break

            # Skip None values
            if value is None:
                continue

            # Truncate strings to 500 characters
            if isinstance(value, str):
                cleaned[key] = value[:500]
            # Round numbers to 4 decimal places
            elif isinstance(value, float):
                cleaned[key] = round(value, 4)
            # Convert lists to comma-separated strings
            elif isinstance(value, list):
                cleaned[key] = ",".join(str(v) for v in value)[:500]
            else:
                cleaned[key] = value

            property_count += 1

        return cleaned


def extract_subdomain(host: str) -> Optional[str]:
    """Extract full subdomain from host header.

    Uses the same logic as datasette_by_subdomain.py:
    Takes everything except the last 2 parts (base domain).

    Examples:
        alameda.ca.civic.org -> alameda.ca
        vancouver.bc.canada.civic.org -> vancouver.bc.canada
        alameda.civic.org -> alameda
        civic.org -> None (empty subdomain)
        localhost -> None
    """
    if not host:
        return None

    # Remove port if present
    host = host.split(":")[0]

    # Skip localhost
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        return None

    # Split by dots and take everything except last 2 parts (base domain)
    parts = host.split(".")
    if len(parts) <= 2:
        # No subdomain (e.g., "civic.org")
        return None

    subdomain = ".".join(parts[:-2])
    return subdomain if subdomain else None


def parse_datasette_path(path: str) -> Dict[str, Optional[str]]:
    """Parse Datasette URL path to extract database and table."""
    parts = [p for p in path.split("/") if p]

    result = {"database": None, "table": None}

    if len(parts) >= 1:
        result["database"] = parts[0]
    if len(parts) >= 2:
        result["table"] = parts[1]

    return result


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


@hookimpl
def asgi_wrapper(datasette):
    """Wrap ASGI application to track analytics events."""
    tracker = UmamiEventTracker(UMAMI_URL, UMAMI_WEBSITE_ID)

    def wrap(app):
        async def wrapper(scope, receive, send):
            # Only process HTTP requests
            if scope["type"] != "http":
                await app(scope, receive, send)
                return

            # Extract request information
            path = scope.get("path", "")
            query_string = scope.get("query_string", b"").decode("utf-8")
            headers_list = scope.get("headers", [])
            headers = {k.decode("utf-8"): v.decode("utf-8") for k, v in headers_list}

            # Parse query parameters
            query_params = parse_qs(query_string)

            # Extract subdomain
            host = headers.get("host", "")
            subdomain = extract_subdomain(host)

            # Skip tracking for non-subdomain requests or admin paths
            if not subdomain or path.startswith("/-/") or path.startswith("/static/"):
                await app(scope, receive, send)
                return

            # Prepare event tracking data
            event_name = None
            event_data = {"subdomain": subdomain, "timestamp": int(time.time() * 1000)}

            # Detect and track full-text search events
            if "_search" in query_params and query_params["_search"]:
                event_name = "search_query"
                search_term = query_params["_search"][0]
                path_info = parse_datasette_path(path)

                event_data.update(
                    {
                        "query_text": search_term[:500],
                        "query_length": len(search_term),
                        "search_type": "full_text_search",
                        "database": path_info.get("database"),
                        "table": path_info.get("table"),
                    }
                )

                # Add filter information if present
                if "_where" in query_params:
                    event_data["has_where_filter"] = True
                if "_sort" in query_params:
                    event_data["sort_column"] = query_params["_sort"][0]
                if "_facet" in query_params:
                    event_data["facets"] = ",".join(query_params["_facet"])

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

                # Extract SQL parameter values from query string
                # Exclude known Datasette system parameters
                system_params = {
                    "sql",
                    "_search",
                    "_size",
                    "_sort",
                    "_facet",
                    "_where",
                    "_shape",
                    "_labels",
                    "_extra",
                    "_col",
                    "_nocol",
                    "_trace",
                    "_timelimit",
                    "_ttl",
                    "_next",
                }

                sql_params = {}
                for key, values in query_params.items():
                    if key not in system_params:
                        sql_params[key] = values[0] if values else None

                event_data.update(
                    {
                        "query_text": sql_text[:500],
                        "query_length": len(sql_text),
                        "query_type": "custom_sql",
                        "database": database,
                        "sql_params": json.dumps(sql_params) if sql_params else None,
                        "param_count": len(sql_params),
                    }
                )

                # Track query parameters
                if "_size" in query_params:
                    event_data["page_size"] = query_params["_size"][0]
                if "_sort" in query_params:
                    event_data["sort_column"] = query_params["_sort"][0]

                # Detect query type from SQL keywords
                sql_lower = sql_text.lower().strip()
                if sql_lower.startswith("select"):
                    event_data["sql_operation"] = "select"
                elif any(
                    sql_lower.startswith(kw) for kw in ["insert", "update", "delete"]
                ):
                    event_data["sql_operation"] = "write"
                elif any(
                    sql_lower.startswith(kw) for kw in ["create", "drop", "alter"]
                ):
                    event_data["sql_operation"] = "ddl"

            # Track the event if we identified one
            if event_name and subdomain:
                await tracker.track_event(
                    event_name=event_name,
                    url=f"{path}",
                    title=f"{event_name.replace('_', ' ').title()} - {subdomain}",
                    referrer=headers.get("referer"),
                    hostname=f"{subdomain}.civic.band",
                    event_data=event_data,
                )

            # Continue with the normal request handling
            await app(scope, receive, send)

        return wrapper

    return wrap
