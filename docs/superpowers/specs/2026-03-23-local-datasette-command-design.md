# Local Datasette Management Command Design

**Date:** 2026-03-23
**Status:** Approved
**Scope:** Django management command for local Datasette development

## Overview

A Django management command that starts a standalone Datasette server for local template and feature testing, without requiring subdomain configuration or /etc/hosts changes.

## Problem

The `datasette_by_subdomain` ASGI wrapper requires subdomain-based routing to serve Datasette content. For local development, this means:
- Editing `/etc/hosts` to map subdomains to localhost
- Configuring browsers to handle the custom domains
- Clunky onboarding for new developers

Most local testing just needs to verify template rendering with real data, not the full subdomain routing flow.

## Solution

A `datasette` management command that starts Datasette directly with:
- Site database and metadata (from `sites.db` or defaults)
- Project templates and plugins
- Dev-friendly settings

## Command Usage

```bash
# Using site from sites.db (looks up metadata, finds database)
python manage.py datasette alameda.ca

# Using site but different database
python manage.py datasette alameda.ca --db /path/to/other.db

# Just a database file (uses placeholder metadata)
python manage.py datasette --db /path/to/meetings.db

# Custom port
python manage.py datasette alameda.ca --port 8002
```

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `site` | No | None | Site subdomain (e.g., `alameda.ca`). Used to find database and look up metadata. |
| `--db` | No | None | Explicit database path. Overrides site-based path. |
| `--port` | No | 8001 | Port to run Datasette on. |

At least one of `site` or `--db` must be provided.

## Behavior Matrix

| Arguments | Database Path | Metadata Source |
|-----------|---------------|-----------------|
| `alameda.ca` | `../sites/alameda.ca/meetings.db` | `sites.db` lookup → render template |
| `alameda.ca --db /x.db` | `/x.db` | `sites.db` lookup → render template |
| `--db /x.db` | `/x.db` | Placeholder defaults |

### Placeholder Defaults

When only `--db` is provided (no site lookup):

```python
context = {
    "name": "Local Dev",
    "state": "",
    "subdomain": "local",
    "last_updated": "",
}
```

## Implementation

### Command Flow

1. **Parse arguments** - Validate that site or --db is provided
2. **Resolve database path**
   - If `--db` provided: use that path
   - Else: construct `../sites/{site}/meetings.db`
3. **Verify database exists** - Exit with error if not found
4. **Build metadata context**
   - If site provided: look up in `sites.db`, extract name/state/subdomain/last_updated
   - Else: use placeholder defaults
5. **Render metadata template** - `templates/config/metadata.json` with context
6. **Create Datasette instance** with:
   - Database file(s)
   - Rendered metadata as `config`
   - `plugins_dir="plugins"`
   - `template_dir="templates/datasette"`
   - Dev settings (see below)
7. **Start server** - Run until Ctrl+C

### Datasette Settings

```python
settings = {
    "force_https_urls": False,  # Dev-friendly, unlike production
    "default_page_size": 100,
    "sql_time_limit_ms": 3000,
    "num_sql_threads": 5,
    "default_facet_size": 10,
    "facet_time_limit_ms": 100,
    "allow_download": True,     # Useful for dev
    "allow_csv_stream": True,   # Useful for dev
}
```

### Additional Databases

If the site has additional databases (finance, items), include them:

```python
db_list = [meetings_db]

finance_db = f"../sites/{site}/finance/election_finance.db"
if os.path.exists(finance_db):
    db_list.append(finance_db)

items_db = f"../sites/{site}/finance/items.db"
if os.path.exists(items_db):
    db_list.append(items_db)
```

## What It Skips

- ASGI wrapper (`datasette_by_subdomain_wrapper`)
- Subdomain detection and routing
- API key authentication
- Rate limiting
- Bot protection (query length checks)
- `sites.db` validation (for `--db` only mode)

## File Location

```
home/management/commands/datasette.py
```

Following Django's management command convention.

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Neither site nor --db provided | Exit with usage error |
| Database file not found | Exit with clear error message |
| Site not found in sites.db | Exit with error listing available sites |
| Port already in use | Let Datasette's error propagate |

## Example Output

```
$ python manage.py datasette alameda.ca
Starting Datasette for alameda.ca
Database: ../sites/alameda.ca/meetings.db
Metadata: Alameda Civic Data

Running at http://localhost:8001/
Press Ctrl+C to stop.
```

## Testing

The command itself is simple enough that manual testing is sufficient. The templates and plugins it loads are tested separately.

## Out of Scope

- Hot reloading of templates (use Datasette's built-in `--reload` if needed)
- Multiple simultaneous sites
- Integration with Django's runserver
- Production use
