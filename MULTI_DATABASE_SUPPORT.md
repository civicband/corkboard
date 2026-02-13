# Corkboard Multi-Database Support Plan

## Overview
This document details the changes needed in the corkboard repository to serve multiple databases (meetings.db and election_finance.db) from a single subdomain. This is part of the larger integration plan documented in `clerk/ELECTION_FINANCE_INTEGRATION.md`.

## Current State
- Serves single database (meetings.db) per subdomain
- URL pattern: `https://{subdomain}.civic.band/meetings/`
- Datasette configuration hardcoded for meetings only
- Plugin: datasette_by_subdomain.py handles routing

## Target State
- Serve multiple databases per subdomain
- URL patterns:
  - `https://{subdomain}.civic.band/meetings/` - Meeting data
  - `https://{subdomain}.civic.band/election_finance/` - Finance data
- Dynamic database discovery based on file existence
- Backward compatible with sites that only have meetings data

## Implementation Details

### 1. Update datasette_by_subdomain.py

#### File: datasette_by_subdomain.py (UPDATE)

```python
import os
import json
import logging
from datasette import Datasette
from datasette.app import Request, Response
from datasette.utils import RoutePattern

logger = logging.getLogger(__name__)


class DatasetteBySubdomainPlugin:
    """Plugin to route requests to appropriate databases based on subdomain."""

    def __init__(self, app):
        self.app = app
        self.datasette_instances = {}
        self.metadata_cache = {}

    def get_subdomain(self, request):
        """Extract subdomain from request host."""
        host = request.headers.get("host", "")

        # Handle localhost development
        if "localhost" in host or "127.0.0.1" in host:
            # Extract from path for development: /subdomain/...
            path_parts = request.path.strip("/").split("/")
            if path_parts:
                return path_parts[0]
            return None

        # Production: extract from subdomain
        if ".civic.band" in host:
            return host.split(".civic.band")[0]

        return None

    def get_databases_for_subdomain(self, subdomain):
        """Get list of database paths for a subdomain.

        Args:
            subdomain: Municipality subdomain

        Returns:
            List of tuples: [(db_name, db_path), ...]
        """
        databases = []

        # Primary database: meetings.db
        meetings_db = f"../sites/{subdomain}/meetings.db"
        if os.path.exists(meetings_db):
            databases.append(("meetings", meetings_db))
        else:
            logger.warning(f"No meetings database found for {subdomain}")

        # Finance database: election_finance.db
        finance_db = f"../sites/{subdomain}/finance/election_finance.db"
        if os.path.exists(finance_db):
            databases.append(("election_finance", finance_db))
            logger.info(f"Found finance database for {subdomain}")

        # Future: Add more database types here
        # budget_db = f"../sites/{subdomain}/budget/budget.db"
        # if os.path.exists(budget_db):
        #     databases.append(("budget", budget_db))

        return databases

    def get_or_create_datasette_instance(self, subdomain):
        """Get or create a Datasette instance for the subdomain.

        Args:
            subdomain: Municipality subdomain

        Returns:
            Datasette instance or None if no databases found
        """
        # Check cache
        if subdomain in self.datasette_instances:
            return self.datasette_instances[subdomain]

        # Get databases for this subdomain
        databases = self.get_databases_for_subdomain(subdomain)
        if not databases:
            logger.error(f"No databases found for subdomain: {subdomain}")
            return None

        # Build database list for Datasette
        db_list = []
        db_metadata = {}

        for db_name, db_path in databases:
            db_list.append(db_path)

            # Set metadata for each database
            if db_name == "meetings":
                db_metadata[db_name] = {
                    "title": "Meeting Minutes & Agendas",
                    "description": "City council and commission meeting records",
                    "tables": {
                        "minutes": {
                            "title": "Meeting Minutes",
                            "description": "Transcribed meeting minutes"
                        },
                        "agendas": {
                            "title": "Meeting Agendas",
                            "description": "Meeting agenda documents"
                        }
                    }
                }
            elif db_name == "election_finance":
                db_metadata[db_name] = {
                    "title": "Campaign Finance Data",
                    "description": "Election contributions and expenditures",
                    "tables": {
                        "monetary_contributions": {
                            "title": "Monetary Contributions",
                            "description": "Campaign contributions"
                        },
                        "expenditure_summaries": {
                            "title": "Expenditures",
                            "description": "Campaign expenditures"
                        }
                    }
                }

        # Create metadata configuration
        metadata = {
            "title": f"{subdomain.replace('.ca', '').title()} Civic Data",
            "description": f"Public records for {subdomain}",
            "databases": db_metadata,
            "plugins": {
                "datasette-cluster-map": {
                    "latitude_column": "lat",
                    "longitude_column": "lng"
                }
            }
        }

        # Configure Datasette instance
        config = {
            "force_https_urls": True,
            "default_page_size": 100,
            "sql_time_limit_ms": 3000,
            "num_sql_threads": 5,
            "default_facet_size": 10,
            "facet_time_limit_ms": 100,
            "allow_download": True,  # Allow database downloads
            "allow_csv_stream": True,  # Allow CSV exports
            "max_csv_mb": 100,
            "suggest_facets": False,  # Disable for performance
            "allow_sql": {
                "meetings": ["select"],  # Read-only SQL for meetings
                "election_finance": ["select"]  # Read-only SQL for finance
            }
        }

        # Create Datasette instance
        try:
            datasette_instance = Datasette(
                db_list,
                metadata=metadata,
                config=config,
                cors=True,  # Enable CORS for API access
                immutable=True,  # Mark databases as immutable for caching
            )

            # Cache the instance
            self.datasette_instances[subdomain] = datasette_instance
            self.metadata_cache[subdomain] = metadata

            logger.info(f"Created Datasette instance for {subdomain} with databases: {[name for name, _ in databases]}")

            return datasette_instance

        except Exception as e:
            logger.error(f"Failed to create Datasette instance for {subdomain}: {str(e)}")
            return None

    async def handle_request(self, scope, receive, send):
        """Main request handler for subdomain routing.

        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        request = Request(scope)
        subdomain = self.get_subdomain(request)

        if not subdomain:
            # No subdomain found - show index or error
            response = Response.text(
                "Welcome to civic.band - Please use a municipality subdomain",
                status=404
            )
            await response.asgi_send(send)
            return

        # Get or create Datasette instance for this subdomain
        datasette = self.get_or_create_datasette_instance(subdomain)

        if not datasette:
            response = Response.text(
                f"No data available for {subdomain}",
                status=404
            )
            await response.asgi_send(send)
            return

        # Adjust path for routing
        # Remove subdomain from path if present (for development)
        path = request.path
        if path.startswith(f"/{subdomain}"):
            path = path[len(f"/{subdomain}"):]

        # Update scope with adjusted path
        scope = dict(scope)
        scope["path"] = path

        # Pass request to Datasette instance
        await datasette.app(scope, receive, send)

    def __call__(self, scope):
        """ASGI application entry point."""
        async def asgi_wrapper(receive, send):
            await self.handle_request(scope, receive, send)
        return asgi_wrapper


# Additional utility functions

def get_available_subdomains():
    """Get list of all available subdomains with their databases.

    Returns:
        Dict mapping subdomain to list of available databases
    """
    sites_dir = "../sites"
    subdomains = {}

    if not os.path.exists(sites_dir):
        return subdomains

    for entry in os.listdir(sites_dir):
        path = os.path.join(sites_dir, entry)
        if os.path.isdir(path):
            available_dbs = []

            # Check for meetings database
            if os.path.exists(os.path.join(path, "meetings.db")):
                available_dbs.append("meetings")

            # Check for finance database
            if os.path.exists(os.path.join(path, "finance", "election_finance.db")):
                available_dbs.append("election_finance")

            if available_dbs:
                subdomains[entry] = available_dbs

    return subdomains


def generate_index_page():
    """Generate an index page showing all available municipalities.

    Returns:
        HTML string for index page
    """
    subdomains = get_available_subdomains()

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Civic Band - Municipality Data</title>
        <style>
            body { font-family: sans-serif; margin: 40px; }
            h1 { color: #333; }
            .municipality { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
            .databases { margin-top: 10px; }
            .db-link { margin-right: 15px; }
        </style>
    </head>
    <body>
        <h1>Available Municipalities</h1>
    """

    for subdomain, databases in sorted(subdomains.items()):
        name = subdomain.replace(".ca", "").replace("-", " ").title()
        html += f"""
        <div class="municipality">
            <h3>{name}</h3>
            <div class="databases">
        """

        for db in databases:
            if db == "meetings":
                html += f'<a class="db-link" href="https://{subdomain}.civic.band/meetings/">Meeting Records</a>'
            elif db == "election_finance":
                html += f'<a class="db-link" href="https://{subdomain}.civic.band/election_finance/">Campaign Finance</a>'

        html += """
            </div>
        </div>
        """

    html += """
    </body>
    </html>
    """

    return html
```

### 2. Update Configuration Files

#### File: config/datasette.json (CREATE/UPDATE)
```json
{
  "title": "Civic Band Data Platform",
  "description": "Public records and civic data",
  "databases": {
    "meetings": {
      "title": "Meeting Records",
      "source": "Municipal websites",
      "license": "Public Domain"
    },
    "election_finance": {
      "title": "Campaign Finance",
      "source": "California NetFile API",
      "license": "Public Domain"
    }
  },
  "extra_css_urls": [
    "/static/civic-band.css"
  ],
  "extra_js_urls": [
    "/static/civic-band.js"
  ]
}
```

### 3. Add Database Detection Logic

#### File: utils/database_discovery.py (NEW)
```python
"""Utilities for discovering available databases."""

import os
import json
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class DatabaseDiscovery:
    """Discover and manage multiple databases per municipality."""

    # Define known database types and their locations
    DATABASE_TYPES = {
        "meetings": {
            "path": "meetings.db",
            "title": "Meeting Records",
            "description": "City council and commission meetings"
        },
        "election_finance": {
            "path": "finance/election_finance.db",
            "title": "Campaign Finance",
            "description": "Election contributions and expenditures"
        },
        "budget": {
            "path": "budget/budget.db",
            "title": "Budget Data",
            "description": "Municipal budget information"
        },
        "permits": {
            "path": "permits/permits.db",
            "title": "Permits",
            "description": "Building and business permits"
        }
    }

    @classmethod
    def discover_databases(cls, subdomain: str, base_path: str = "../sites") -> List[Tuple[str, str]]:
        """Discover all available databases for a subdomain.

        Args:
            subdomain: Municipality subdomain
            base_path: Base path to sites directory

        Returns:
            List of (database_name, database_path) tuples
        """
        databases = []
        site_path = os.path.join(base_path, subdomain)

        if not os.path.exists(site_path):
            logger.warning(f"Site path does not exist: {site_path}")
            return databases

        for db_name, db_config in cls.DATABASE_TYPES.items():
            db_path = os.path.join(site_path, db_config["path"])
            if os.path.exists(db_path):
                databases.append((db_name, db_path))
                logger.info(f"Found {db_name} database for {subdomain}")

        return databases

    @classmethod
    def get_database_metadata(cls, db_name: str) -> Dict[str, Any]:
        """Get metadata for a database type.

        Args:
            db_name: Database name

        Returns:
            Dictionary with title and description
        """
        if db_name in cls.DATABASE_TYPES:
            config = cls.DATABASE_TYPES[db_name]
            return {
                "title": config["title"],
                "description": config["description"]
            }
        return {
            "title": db_name.replace("_", " ").title(),
            "description": f"{db_name} database"
        }
```

### 4. Add Caching for Performance

#### File: utils/cache.py (NEW)
```python
"""Caching utilities for Datasette instances."""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DatasetteCache:
    """Cache Datasette instances to avoid recreation overhead."""

    def __init__(self, ttl: int = 3600):
        """Initialize cache.

        Args:
            ttl: Time to live in seconds (default 1 hour)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired.

        Args:
            key: Cache key (subdomain)

        Returns:
            Cached value or None
        """
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                logger.debug(f"Cache hit for {key}")
                return entry["value"]
            else:
                logger.debug(f"Cache expired for {key}")
                del self.cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set item in cache.

        Args:
            key: Cache key (subdomain)
            value: Value to cache
        """
        self.cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
        logger.debug(f"Cached {key}")

    def invalidate(self, key: str) -> None:
        """Invalidate cache entry.

        Args:
            key: Cache key to invalidate
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Invalidated cache for {key}")

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        logger.info("Cache cleared")
```

## Testing Strategy

### Unit Tests
- Test subdomain extraction logic
- Test database discovery for various configurations
- Test metadata generation
- Test caching behavior

### Integration Tests
- Test with single database (backward compatibility)
- Test with multiple databases
- Test missing database handling
- Test URL routing for different database types

### Performance Tests
- Measure response time with caching
- Test concurrent requests to different subdomains
- Monitor memory usage with multiple instances

## Migration Path

1. **Deploy updated plugin** with backward compatibility
2. **Test with existing sites** (meetings.db only)
3. **Test with pilot sites** that have finance data
4. **Monitor performance** and adjust caching
5. **Full rollout** when stable

## Backward Compatibility
- Sites with only meetings.db continue to work unchanged
- URL structure preserved for existing links
- No changes required to existing data

## Configuration Options

### Environment Variables
```bash
# Cache configuration
DATASETTE_CACHE_TTL=3600  # Cache TTL in seconds
DATASETTE_MAX_INSTANCES=100  # Maximum cached instances

# Database discovery
DATASETTE_SITES_PATH="../sites"  # Path to sites directory
DATASETTE_DISCOVER_INTERVAL=300  # Re-scan interval in seconds

# Performance
DATASETTE_MAX_DBS_PER_INSTANCE=10  # Maximum databases per instance
```

## URL Structure

### Current (unchanged)
- `https://alameda.ca.civic.band/meetings/` - Meeting minutes and agendas
- `https://alameda.ca.civic.band/meetings/minutes` - Minutes table
- `https://alameda.ca.civic.band/meetings/agendas` - Agendas table

### New (additional)
- `https://alameda.ca.civic.band/election_finance/` - Finance database home
- `https://alameda.ca.civic.band/election_finance/monetary_contributions` - Contributions table
- `https://alameda.ca.civic.band/election_finance/expenditure_summaries` - Expenditures table

## Files to Modify/Create
1. `datasette_by_subdomain.py` - Main plugin file (UPDATE)
2. `config/datasette.json` - Configuration (CREATE/UPDATE)
3. `utils/database_discovery.py` - Database discovery (NEW)
4. `utils/cache.py` - Caching utilities (NEW)
5. `tests/test_multi_database.py` - Tests (NEW)
6. `README.md` - Documentation (UPDATE)

## Success Criteria
- ✅ Single subdomain serves multiple databases
- ✅ Backward compatible with meetings-only sites
- ✅ Dynamic database discovery
- ✅ Proper URL routing for each database
- ✅ Performance acceptable with caching
- ✅ Clean separation between database types

## Timeline
- Day 1: Update datasette_by_subdomain.py
- Day 2: Add database discovery and caching
- Day 3: Testing with various configurations
- Day 4: Documentation and deployment preparation