# CivicBand Analytics Implementation Guide

This guide explains the Umami Analytics integration for tracking searches and queries in CivicBand.

## Overview

The analytics system consists of two main components:

1. **Server-Side Event Tracking** (`plugins/civic_analytics.py`) - Sends detailed events to Umami in real-time
2. **Data Retrieval Cron Job** (`scripts/retrieve_umami_analytics.py`) - Pulls data from Umami into SQLite for analysis

## Architecture

```
┌─────────────────┐
│ User Search     │
└────────┬────────┘
         │
         ▼
┌──────────────────────────────────┐
│  civic_analytics.py Plugin       │
│  (ASGI Middleware - Read Only)   │
│  - Intercepts requests            │
│  - Extracts event data            │
│  - Sends to Umami API             │
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
# Umami URL and Website ID (already configured)
UMAMI_URL=https://analytics.civic.band
UMAMI_WEBSITE_ID=6250918b-6a0c-4c05-a6cb-ec8f86349e1a

# Enable analytics tracking
UMAMI_ANALYTICS_ENABLED=true

# Umami API credentials (for data retrieval only)
UMAMI_USERNAME=your_username
UMAMI_PASSWORD=your_password
```

**Note:** `UMAMI_USERNAME` and `UMAMI_PASSWORD` are ONLY needed for the data retrieval script. The event tracking plugin does NOT require authentication.

### 3. Test Event Tracking

Start your development server and perform a search:

```bash
python manage.py runserver
```

Visit `http://alameda.localhost:8000/meetings/agendas?_search=council` and the search event should be sent to Umami.

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

Tracked when users perform full-text searches.

**Event Data:**
- `subdomain` - Municipality (e.g., "alameda")
- `query_text` - Search term (max 500 chars)
- `query_length` - Length of search query
- `results_count` - Number of results found
- `has_results` - Boolean (true/false)
- `search_type` - "full_text"
- `database` - Database name (e.g., "meetings")
- `table` - Table name (e.g., "agendas")
- `has_where_filter` - Boolean if WHERE filters applied
- `sort_column` - Column being sorted by
- `facets` - Facets applied

**Example:**
```json
{
  "event_name": "search_query",
  "event_data": {
    "subdomain": "alameda",
    "query_text": "city council meeting",
    "query_length": 21,
    "results_count": 42,
    "has_results": true,
    "search_type": "full_text",
    "database": "meetings",
    "table": "agendas"
  }
}
```

### 2. Table View Events (`table_view`)

Tracked when users view a specific table (e.g., agendas, minutes).

**Event Data:**
- `subdomain` - Municipality
- `database` - Database name
- `table` - Table name
- `has_filters` - Boolean if filters applied
- `sorted_by` - Sort column if sorted

### 3. Row View Events (`row_view`)

Tracked when users view a specific row (individual agenda/minute page).

**Event Data:**
- `subdomain` - Municipality
- `database` - Database name
- `table` - Table name
- `row_id` - Primary key of the row

## Analytics Queries

The `analytics-metadata.json` file includes pre-configured queries:

1. **Top Search Queries** - Most common searches
2. **Searches by Municipality** - Search activity per municipality
3. **Most Viewed Tables** - Popular tables and content
4. **Search Performance** - Average results and execution time
5. **Zero Result Searches** - Searches that returned no results (for improvement)
6. **Recent Searches** - Latest search activity
7. **Activity by Hour** - Hourly usage patterns
8. **Municipality Comparison** - Comparative activity across municipalities

Access these in Datasette at the "Queries" section.

## Privacy & Data Retention

### Privacy Measures

- **No IP Storage:** IP addresses are never sent to Umami or stored
- **No Cookies:** Client-side tracking uses localStorage, no cookies
- **No PII:** No personally identifiable information is collected
- **Anonymous:** All data is aggregated and anonymous

### Data Retention

Analytics data is stored indefinitely in the local SQLite database. To implement retention:

```python
# Add to cron job or separate cleanup script
DELETE FROM events WHERE datetime(retrieved_at) < datetime('now', '-90 days');
DELETE FROM website_stats WHERE datetime(retrieved_at) < datetime('now', '-90 days');
```

## Troubleshooting

### Events Not Appearing in Umami

1. Check that `UMAMI_ANALYTICS_ENABLED=true` in `.env`
2. Verify the Umami URL is correct: `https://analytics.civic.band`
3. Check the Website ID matches: `6250918b-6a0c-4c05-a6cb-ec8f86349e1a`
4. Look for errors in application logs
5. Test with `curl`:

```bash
curl -X POST https://analytics.civic.band/api/send \
  -H "Content-Type: application/json" \
  -H "User-Agent: Test/1.0" \
  -d '{
    "type": "event",
    "payload": {
      "hostname": "test.civic.band",
      "url": "/test",
      "website": "6250918b-6a0c-4c05-a6cb-ec8f86349e1a",
      "name": "test_event"
    }
  }'
```

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

### Database Locked Errors

If you get "database is locked" errors:

1. Close any open Datasette instances viewing `umami_events.db`
2. Ensure cron job isn't running multiple times
3. Check file permissions on `analytics/` directory

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

1. **Customize Event Tracking** - Add more event types or data fields in `plugins/civic_analytics.py`
2. **Create Dashboards** - Use Metabase or another BI tool for executive dashboards
3. **Set Up Alerts** - Monitor for unusual patterns (spike in searches, zero-result searches)
4. **Optimize Searches** - Use zero-result search data to improve search functionality
5. **A/B Testing** - Use events to measure feature adoption

## Support

For issues or questions:

- Check application logs for event tracking errors
- Verify Umami dashboard shows events
- Review SQLite database for retrieved data
- Open an issue in the repository

## License

This analytics implementation is part of CivicBand and follows the same license.
