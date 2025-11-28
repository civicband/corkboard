# Analytics Improvement Design

## Problem Statement

Current Umami analytics setup has three issues:

1. **Subdomain not a first-class dimension** - Subdomain is captured in hostname but not easily filterable in Umami's UI for dashboards and breakdowns
2. **sql_query event volume** - Orders of magnitude more sql_query events than other events, overwhelming useful data
3. **Inconsistent subdomain tracking** - Server-side events include subdomain property, client-side events don't

## Solution Overview

### Immediate Changes

1. Add subdomain property to all client-side events (pageviews + custom events)
2. Deduplicate sql_query events per user/subdomain/query
3. Accept Umami UI limitations; build custom dashboards via Metabase pipeline

### Future Work

Pipeline: Umami → Sync Script → Local SQLite → Metabase

## Design Details

### 1. Client-Side Subdomain Tracking

**File:** `plugins/umami.py`

**Current state:**
```python
@hookimpl
def extra_body_script(datasette):
    return {
        "script": '</script><script src="https://analytics.civic.band/sunshine" data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a" data-auto-track="true">'
    }
```

**Changes:**
- Remove `data-auto-track="true"` to disable automatic pageview tracking
- Inject JavaScript that:
  1. Extracts subdomain from `window.location.hostname`
  2. Fires manual pageview with subdomain property
  3. Patches `umami.track` to auto-include subdomain on all custom events

**Resulting behavior:**
- All pageviews include `subdomain` property
- All custom events (via `data-umami-event` attributes) include `subdomain` property
- Zero changes required to individual template event attributes

### 2. SQL Query Deduplication

**File:** `plugins/civic_analytics.py`

**Problem:** Every `?sql=` request triggers an event, including:
- Same user running same query repeatedly
- Bots hitting SQL URLs
- Shared query links clicked multiple times

**Solution:** In-memory LRU cache with per-user deduplication

**Deduplication logic:**
- Hash key: `(normalized_query_text, client_ip, subdomain)`
- Cache: In-memory LRU dict, bounded to ~1000 entries
- Window: Skip tracking if same hash seen within 1 hour
- Normalization: lowercase, collapse whitespace

**Tradeoffs:**
- Cache resets on process restart (acceptable - we're sampling, not auditing)
- Each worker has its own cache (acceptable - up to 10% miss rate is fine)
- Shared query links tracked once per user (correct - represents genuine interest)

**What gets tracked:**
- First occurrence of each unique query per IP per subdomain per hour
- All existing metadata preserved (query_text, database, sql_operation, etc.)

**What gets skipped:**
- Repeated executions of same query by same user
- Bot traffic hammering same queries

### 3. Metabase Pipeline (Future Work)

**Architecture:**
```
Umami (capture) → Umami API → Sync Script → Local SQLite → Metabase
```

**Components:**

1. **Umami** - Unchanged, lightweight event capture
2. **Sync script** - Extend `scripts/retrieve_umami_analytics.py`
   - Pull events via Umami API (daily cron)
   - Write to local SQLite with denormalized schema
3. **Local SQLite** - Analytics warehouse (`analytics.db`)
   - Subdomain as proper indexed column
   - Optimized for dashboard queries
4. **Metabase** - Connect to SQLite for dashboards

**Events table schema:**

| Column | Type | Notes |
|--------|------|-------|
| id | integer | primary key |
| timestamp | datetime | event time |
| event_name | text | search_query, sql_query, muni_quicklink, etc. |
| subdomain | text | extracted from hostname, indexed |
| hostname | text | full hostname |
| url | text | page URL |
| event_data | JSON | additional properties (query_text, etc.) |

**Benefits:**
- Full subdomain filtering in Metabase UI
- SQL access for ad-hoc analysis
- Custom dashboards tailored to CivicBand needs
- Umami stays lightweight for capture

## Files Modified

**Immediate:**
- `plugins/umami.py` - Client-side subdomain injection
- `plugins/civic_analytics.py` - SQL query deduplication

**Future:**
- `scripts/retrieve_umami_analytics.py` - Extend for Metabase pipeline
- `analytics.db` - New database for warehoused events

## Alternatives Considered

### Subdomain tracking approaches

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| Separate Umami website per subdomain | Perfect isolation, native filtering | Fragments data, management overhead | Rejected |
| Encode subdomain in event names | Visible in event list | Can't aggregate across subdomains | Rejected (tried, didn't work) |
| data-umami-event-subdomain on each element | Explicit | 35+ template changes needed | Rejected |
| Patch umami.track globally | Zero template changes, automatic | Slightly more complex JS | **Selected** |

### Analytics platforms

| Platform | Dimension filtering | Weight | Decision |
|----------|---------------------|--------|----------|
| Umami | Limited (properties not in all dashboards) | Light | Keep for capture |
| Plausible | Same limitations | Light | No benefit |
| PostHog | Full property filtering | Heavy | Overkill |
| Matomo | Custom dimensions in segments | Heavy | Overkill |
| Umami + Metabase | Full control via SQL | Medium | **Selected** |

### SQL deduplication storage

| Storage | Persistence | Shared | Complexity | Decision |
|---------|-------------|--------|------------|----------|
| In-memory LRU | No | No (per-worker) | Simple | **Selected** |
| SQLite table | Yes | Yes | Medium | Rejected (unnecessary) |
| Redis | Yes | Yes | High | Rejected (overkill) |
