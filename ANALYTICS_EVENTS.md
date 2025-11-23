# CivicBand Analytics Events Reference

This document describes the events tracked and sent to Umami Analytics.

## Event Types

Only **search queries** and **SQL queries** are tracked server-side. Table views and row views are already captured by the existing client-side Umami integration.

---

## 1. Search Query Event (`search_query`)

**When tracked:** User performs a full-text search via `?_search=` parameter

**Event name:** `search_query`

**Event data structure:**
```json
{
  "subdomain": "alameda",
  "timestamp": 1705932000000,
  "query_text": "city council meeting",
  "query_length": 21,
  "search_type": "full_text_search",
  "database": "meetings",
  "table": "agendas",
  "has_where_filter": true,
  "sort_column": "date",
  "facets": "meeting,date"
}
```

**Field descriptions:**
- `subdomain` - Municipality identifier (e.g., "alameda")
- `timestamp` - Unix timestamp in milliseconds
- `query_text` - Search term (max 500 characters)
- `query_length` - Length of search query string
- `search_type` - Always "full_text_search"
- `database` - Database being searched (e.g., "meetings")
- `table` - Table being searched (e.g., "agendas", "minutes")
- `has_where_filter` - Boolean, true if WHERE filters applied
- `sort_column` - Column being sorted by (optional)
- `facets` - Comma-separated list of facets applied (optional)

**Example URLs that trigger this event:**
```
/meetings/agendas?_search=council
/meetings/minutes?_search=budget&_where=date>2024-01-01
/meetings/agendas?_search=zoning&_sort=date&_facet=meeting
```

---

## 2. SQL Query Event (`sql_query`)

**When tracked:** User executes a custom SQL query via `?sql=` parameter

**Event name:** `sql_query`

**Event data structure:**
```json
{
  "subdomain": "alameda",
  "timestamp": 1705932000000,
  "query_text": "SELECT * FROM agendas WHERE date > '2024-01-01'",
  "query_length": 52,
  "query_type": "custom_sql",
  "database": "meetings",
  "page_size": "100",
  "sort_column": "date",
  "sql_operation": "select"
}
```

**Field descriptions:**
- `subdomain` - Municipality identifier
- `timestamp` - Unix timestamp in milliseconds
- `query_text` - SQL query text (max 500 characters)
- `query_length` - Length of SQL query string
- `query_type` - Always "custom_sql"
- `database` - Database being queried
- `page_size` - Result page size if specified
- `sort_column` - Sort column if specified
- `sql_operation` - Type of SQL operation: "select", "write", or "ddl"

**SQL operation detection:**
- `select` - Query starts with SELECT
- `write` - Query starts with INSERT, UPDATE, or DELETE
- `ddl` - Query starts with CREATE, DROP, or ALTER

**Example URLs that trigger this event:**
```
/meetings?sql=SELECT * FROM agendas LIMIT 10
/meetings?sql=SELECT meeting, COUNT(*) FROM agendas GROUP BY meeting
/meetings?sql=SELECT COUNT(*) FROM agendas WHERE date > '2024-01-01'
```

---

## Data Constraints

All events follow Umami's data constraints:
- **Event names**: Max 50 characters
- **String values**: Max 500 characters
- **Numbers**: Max 4 decimal precision
- **Total properties**: Max 50 per event
- **Arrays**: Converted to comma-separated strings

---

## Privacy & Security

- **No IP addresses** stored
- **No PII** collected
- **Read-only** - Never writes to meeting databases
- **Query sanitization** - SQL text truncated to 500 chars
- **Anonymous** - All data is aggregated by municipality only

---

## Testing Events

### Test Search Query
```bash
# Visit in browser
https://alameda.civic.band/meetings/agendas?_search=council

# Expected event
{
  "event_name": "search_query",
  "event_data": {
    "subdomain": "alameda",
    "query_text": "council",
    "search_type": "full_text_search",
    "database": "meetings",
    "table": "agendas"
  }
}
```

### Test SQL Query
```bash
# Visit in browser
https://alameda.civic.band/meetings?sql=SELECT COUNT(*) FROM agendas

# Expected event
{
  "event_name": "sql_query",
  "event_data": {
    "subdomain": "alameda",
    "query_text": "SELECT COUNT(*) FROM agendas",
    "query_type": "custom_sql",
    "database": "meetings",
    "sql_operation": "select"
  }
}
```

---

## Analyzing Events in SQLite

After running the cron job, query the analytics database:

```sql
-- Top search terms
SELECT
  json_extract(event_data, '$.query_text') as search_term,
  json_extract(event_data, '$.subdomain') as municipality,
  COUNT(*) as count
FROM events
WHERE event_name = 'search_query'
GROUP BY search_term, municipality
ORDER BY count DESC
LIMIT 20;

-- Most common SQL queries
SELECT
  json_extract(event_data, '$.query_text') as sql_query,
  json_extract(event_data, '$.subdomain') as municipality,
  COUNT(*) as count
FROM events
WHERE event_name = 'sql_query'
GROUP BY sql_query, municipality
ORDER BY count DESC
LIMIT 20;

-- Search vs SQL query breakdown by municipality
SELECT
  json_extract(event_data, '$.subdomain') as municipality,
  SUM(CASE WHEN event_name = 'search_query' THEN 1 ELSE 0 END) as searches,
  SUM(CASE WHEN event_name = 'sql_query' THEN 1 ELSE 0 END) as sql_queries,
  COUNT(*) as total
FROM events
GROUP BY municipality
ORDER BY total DESC;
```

---

## Event Flow

```
User Action (Search/SQL Query)
         ↓
civic_analytics.py (ASGI middleware)
         ↓
Extract event data from request
         ↓
Send to Umami API (POST /api/send)
         ↓
Event stored in Umami
         ↓
[Later: Cron job runs]
         ↓
retrieve_umami_analytics.py
         ↓
Fetch events from Umami API
         ↓
Store in analytics/umami_events.db
         ↓
Query with Datasette
```
