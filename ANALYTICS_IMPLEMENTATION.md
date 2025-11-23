# CivicBand Analytics Implementation Guide

This guide explains the Umami Analytics integration for tracking searches and SQL queries in CivicBand.

## Overview

The analytics system consists of two main components:

1. **Server-Side Event Tracking** (`plugins/civic_analytics.py`) - Sends detailed search and SQL query events to Umami in real-time
2. **Data Retrieval Cron Job** (`scripts/retrieve_umami_analytics.py`) - Pulls data from Umami into SQLite for analysis

**Note:** Table views and row views are already tracked by the existing client-side Umami integration. This server-side plugin specifically tracks search queries and SQL queries with detailed metadata.

## Architecture

```
┌─────────────────┐
│ User Search/SQL │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────┐
│  civic_analytics.py Plugin       │
│  (ASGI Middleware - Read Only)   │
│  - Intercepts HTTP requests      │
│  - Extracts search/SQL queries   │
│  - Sends to Umami API            │
└────────┬────────────────┬─────────┘
         │                │
         ▼                ▼
┌──────────────┐  ┌───────────────────┐
│ Datasette    │  │ Umami Analytics   │
│ (Read-Only)  │  │ (analytics.civic  │
│              │  │  .band)            │
│ meetings.db  │  │                   │
│ (no writes!) │  │ Stores events     │
└──────────────┘  └───────────┬───────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ Cron Job (daily)      │
                  │ retrieve_umami_       │
                  │ analytics.py          │
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │ analytics/            │
                  │ umami_events.db       │
                  │ (SQLite - Writable)   │
                  └───────────────────────┘
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install new dependencies
uv pip install httpx requests

# Or use uv sync to install from pyproject.toml
uv sync
```

### 2. Configure Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` and set:

```bash
# Umami Analytics Configuration
UMAMI_URL=https://analytics.civic.band
UMAMI_WEBSITE_ID=6250918b-6a0c-4c05-a6cb-ec8f86349e1a

# API Key for server-side tracking (REQUIRED for event tracking)
UMAMI_API_KEY=your_api_key_here

# Enable/disable analytics tracking
UMAMI_ANALYTICS_ENABLED=true

# Umami API credentials (for data retrieval script only)
UMAMI_USERNAME=your_username
UMAMI_PASSWORD=your_password
```

**Important:**
- `UMAMI_API_KEY` is **required** for server-side event tracking to bypass bot detection
- `UMAMI_USERNAME` and `UMAMI_PASSWORD` are only needed for the data retrieval cron job
- Get your API key from Umami: Settings → Profile → Generate API Key

### 3. Test Event Tracking

Start your development server and perform a search:

```bash
python manage.py runserver
```

Visit `http://alameda.ca.localhost:8000/meetings/agendas?_search=council` and the search event should be sent to Umami.

Check the Umami dashboard at `https://analytics.civic.band` to verify events are being received.

### 4. Test Data Retrieval

Run the retrieval script manually to test:

```bash
# Retrieve last 7 days with events and summary
python scripts/retrieve_umami_analytics.py --days 7 --events --summary

# Check the output
ls -lh analytics/
# Should see: umami_events.db and summary_*.json
```

### 5. View Analytics Data

Use Datasette to explore the analytics database:

```bash
datasette analytics/umami_events.db --metadata analytics-metadata.json
```

Visit `http://localhost:8001` to see:
- Pre-configured queries (Top Searches, Searches by Municipality, etc.)
- Filterable event tables
- JSON event data with full details

### 6. Set Up Cron Job

Add to your crontab:

```bash
crontab -e
```

Add these entries:

```bash
# Retrieve daily analytics at 2 AM
0 2 * * * cd /path/to/corkboard && /path/to/venv/bin/python scripts/retrieve_umami_analytics.py --days 1 --events >> /var/log/umami_cron.log 2>&1

# Generate weekly summary on Mondays at 3 AM
0 3 * * 1 cd /path/to/corkboard && /path/to/venv/bin/python scripts/retrieve_umami_analytics.py --days 7 --events --summary >> /var/log/umami_cron.log 2>&1
```

## Events Tracked

### 1. Search Query Events (`search_query`)

Tracked when users perform full-text searches via the `?_search=` parameter.

**Event Data:**
- `subdomain` - Full municipality subdomain (e.g., "alameda.ca", "vancouver.bc.canada")
- `query_text` - Search term (max 500 chars)
- `query_length` - Length of search query
- `search_type` - Always "full_text_search"
- `database` - Database name (e.g., "meetings")
- `table` - Table name (e.g., "agendas", "minutes")
- `has_where_filter` - Boolean if WHERE filters applied (optional)
- `sort_column` - Column being sorted by (optional)
- `facets` - Comma-separated facets applied (optional)

**Example:**
```json
{
  "event_name": "search_query",
  "event_data": {
    "subdomain": "alameda.ca",
    "query_text": "city council meeting",
    "query_length": 21,
    "search_type": "full_text_search",
    "database": "meetings",
    "table": "agendas",
    "has_where_filter": true,
    "sort_column": "date",
    "facets": "meeting,date"
  }
}
```

### 2. SQL Query Events (`sql_query`)

Tracked when users execute custom SQL queries via the `?sql=` parameter.

**Event Data:**
- `subdomain` - Full municipality subdomain (e.g., "alameda.ca")
- `query_text` - SQL query text (max 500 chars)
- `query_length` - Length of SQL query string
- `query_type` - Always "custom_sql"
- `database` - Database being queried
- `sql_operation` - Type of SQL operation: "select", "write", or "ddl"
- `page_size` - Result page size if specified (optional)
- `sort_column` - Sort column if specified (optional)

**SQL Operation Detection:**
- `select` - Query starts with SELECT
- `write` - Query starts with INSERT, UPDATE, or DELETE
- `ddl` - Query starts with CREATE, DROP, or ALTER

**Example:**
```json
{
  "event_name": "sql_query",
  "event_data": {
    "subdomain": "alameda.ca",
    "query_text": "SELECT * FROM agendas WHERE date > '2024-01-01'",
    "query_length": 52,
    "query_type": "custom_sql",
    "database": "meetings",
    "sql_operation": "select",
    "page_size": "100"
  }
}
```

## Subdomain Extraction

The plugin uses the **same subdomain extraction logic** as `datasette_by_subdomain.py`:

```python
# Split host by dots and take everything except last 2 parts (base domain)
parts = host.split(".")
subdomain = ".".join(parts[:-2])
```

**Examples:**
- `alameda.ca.civic.org` → `alameda.ca`
- `vancouver.bc.canada.civic.org` → `vancouver.bc.canada`
- `alameda.civic.org` → `alameda`
- `civic.org` → `None` (no subdomain)

This works for any base domain (civic.org, civic.band, etc.) without requiring configuration.

## Analytics Queries

The `analytics-metadata.json` file includes pre-configured queries:

1. **Top Search Queries** - Most common searches across all municipalities
2. **Searches by Municipality** - Search activity per municipality
3. **Popular Tables** - Most viewed tables
4. **Search Performance** - Average results and execution time
5. **Zero Result Searches** - Searches that returned no results (for improvement)
6. **Recent Searches** - Latest search activity
7. **Activity by Hour** - Hourly usage patterns
8. **Municipality Comparison** - Comparative activity (searches vs SQL queries)

Access these in Datasette at the "Queries" section.

## Privacy & Data Retention

### Privacy Measures

- **No IP Storage:** IP addresses are never sent to Umami or stored
- **No Cookies:** Server-side tracking doesn't use cookies
- **No PII:** No personally identifiable information is collected
- **Anonymous:** All data is aggregated by municipality only
- **Read-Only:** Never modifies meeting databases

### Data Retention

Analytics data is stored indefinitely in the local SQLite database. To implement retention:

```python
# Add to cron job or separate cleanup script
DELETE FROM events WHERE datetime(retrieved_at) < datetime('now', '-90 days');
DELETE FROM website_stats WHERE datetime(retrieved_at) < datetime('now', '-90 days');
```

## Troubleshooting

### Events Not Appearing in Umami

1. **Check API Key:** Verify `UMAMI_API_KEY` is set correctly in `.env`
2. **Check Response:** If getting `{"beep":"boop"}`, the API key is missing or invalid
3. **Verify Umami URL:** Should be `https://analytics.civic.band`
4. **Check Website ID:** Should match your Umami dashboard
5. **Check Logs:** Look for errors in application logs

**Common Issues:**
- **Missing API Key:** Events return 200 but show `{"beep":"boop"}` (bot protection)
- **Wrong Website ID:** Events accepted but don't appear in dashboard
- **UMAMI_ANALYTICS_ENABLED=false:** Tracking is disabled

### Data Retrieval Script Fails

1. Verify `UMAMI_USERNAME` and `UMAMI_PASSWORD` are set
2. Check authentication:

```python
python -c "
import os, requests
url = os.getenv('UMAMI_URL', 'https://analytics.civic.band')
r = requests.post(f'{url}/api/auth/login',
    json={'username': os.getenv('UMAMI_USERNAME'),
          'password': os.getenv('UMAMI_PASSWORD')})
print(r.status_code, r.json())
"
```

3. Check for network connectivity to Umami instance
4. Verify the website ID is accessible to your user account

### No Subdomain Extracted

If subdomain is showing as `None`:
- Check that host has more than 2 parts (e.g., `alameda.ca.civic.org` not just `civic.org`)
- For localhost testing, use format like `alameda.ca.localhost:8000`
- Verify host header is being passed correctly in your deployment

## Deployment Considerations

### Docker Integration

If using Docker, mount the analytics directory:

```yaml
# docker-compose.yml
volumes:
  - ./sites:/sites:ro          # Read-only meeting databases
  - ./analytics:/analytics:rw  # Writable analytics storage
```

### Production Settings

1. Use environment variables for all configuration
2. Run cron job on a schedule that doesn't overlap with high traffic
3. Consider using a separate analytics Datasette instance:

```yaml
# docker-compose.yml
analytics_datasette:
  image: datasette/datasette
  ports:
    - "8002:8001"
  volumes:
    - ./analytics:/data:ro
  command: >
    datasette /data/umami_events.db
    --metadata /data/analytics-metadata.json
    --setting sql_time_limit_ms 5000
```

### Monitoring

Monitor the analytics system:

```bash
# Check cron job logs
tail -f /var/log/umami_cron.log

# Check database size
du -sh analytics/umami_events.db

# Count events by type
sqlite3 analytics/umami_events.db \
  "SELECT event_name, COUNT(*) FROM events GROUP BY event_name;"
```

## Next Steps

1. **Analyze Search Patterns** - Use zero-result searches to improve search functionality
2. **Monitor Popular Queries** - Understand what users are looking for
3. **Track Municipality Engagement** - See which municipalities are most active
4. **Set Up Alerts** - Monitor for unusual patterns or errors
5. **Create Custom Dashboards** - Use Metabase or another BI tool for executive reports

## Support

For issues or questions:

- Check application logs for event tracking errors
- Verify Umami dashboard shows events with correct data
- Review SQLite database for retrieved data
- Check that API key has proper permissions
- Open an issue in the repository

## License

This analytics implementation is part of CivicBand and follows the same license.
