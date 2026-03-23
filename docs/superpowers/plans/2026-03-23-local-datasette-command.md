# Local Datasette Management Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Django management command that starts a standalone Datasette server for local template testing without subdomain configuration.

**Architecture:** A single management command that parses arguments, resolves database paths, queries sites.db for metadata context, renders the Jinja2 metadata template, and starts Datasette with the project's templates and plugins.

**Tech Stack:** Django management commands, Datasette, sqlite-utils, Jinja2, uvicorn

---

## File Structure

| File | Purpose |
|------|---------|
| `pages/management/__init__.py` | Package marker (create) |
| `pages/management/commands/__init__.py` | Package marker (create) |
| `pages/management/commands/datasette.py` | Main command (create) |
| `tests/test_datasette_command.py` | Unit tests (create) |

**Note:** The spec mentions `home/management/commands/` but the project has `pages` as the Django app, not `home`. Using `pages` instead.

---

### Task 1: Create Management Command Directory Structure

**Files:**
- Create: `pages/management/__init__.py`
- Create: `pages/management/commands/__init__.py`

- [ ] **Step 1: Create management directory and __init__.py**

```bash
mkdir -p pages/management/commands
```

- [ ] **Step 2: Create package init files**

Create `pages/management/__init__.py`:
```python
```

Create `pages/management/commands/__init__.py`:
```python
```

- [ ] **Step 3: Verify Django discovers the command location**

```bash
python manage.py help 2>&1 | head -20
```

Expected: No errors about the management directory

- [ ] **Step 4: Commit**

```bash
git add pages/management/__init__.py pages/management/commands/__init__.py
git commit -m "chore: add management command directory structure"
```

---

### Task 2: Test Argument Parsing

**Files:**
- Create: `tests/test_datasette_command.py`
- Create: `pages/management/commands/datasette.py`

- [ ] **Step 1: Write failing tests for argument parsing**

Create `tests/test_datasette_command.py`:
```python
"""Tests for the datasette management command."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


class TestDatasetteCommandArguments:
    """Test argument parsing and validation."""

    def test_requires_site_or_db(self):
        """Command fails without site or --db argument."""
        with pytest.raises(CommandError, match="must provide"):
            call_command("datasette")

    def test_accepts_site_argument(self, mocker):
        """Command accepts a site subdomain as positional argument."""
        # Mock the actual server start to avoid blocking
        mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        # Mock database existence check
        mocker.patch("os.path.exists", return_value=True)
        # Mock sites.db lookup
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value.get.return_value = {
            "name": "Test City",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        # Should not raise
        call_command("datasette", "test.ca")

    def test_accepts_db_flag(self, mocker):
        """Command accepts --db flag for explicit database path."""
        mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)

        # Should not raise
        call_command("datasette", db="/path/to/test.db")

    def test_accepts_port_flag(self, mocker):
        """Command accepts --port flag."""
        mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)

        # Should not raise
        call_command("datasette", db="/path/to/test.db", port=8002)

    def test_default_port_is_8001(self, mocker):
        """Default port is 8001."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)

        call_command("datasette", db="/path/to/test.db")

        # Check the port used
        assert start_mock.call_args is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_datasette_command.py -v
```

Expected: FAIL with "Unknown command: 'datasette'"

- [ ] **Step 3: Implement minimal command with argument parsing**

Create `pages/management/commands/datasette.py`:
```python
"""Django management command to run Datasette for local development."""

import os

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Start a standalone Datasette server for local template testing."""

    help = "Start Datasette for local development without subdomain configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "site",
            nargs="?",
            help="Site subdomain (e.g., alameda.ca). Used to find database and metadata.",
        )
        parser.add_argument(
            "--db",
            dest="db",
            help="Explicit database path. Overrides site-based path.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run Datasette on (default: 8001).",
        )

    def handle(self, *args, **options):
        site = options.get("site")
        db_path = options.get("db")
        port = options.get("port")

        # Validate: must have site or --db
        if not site and not db_path:
            raise CommandError(
                "You must provide either a site subdomain or --db path."
            )

        # Resolve database path
        if db_path:
            resolved_db = db_path
        else:
            resolved_db = f"../sites/{site}/meetings.db"

        # Check database exists
        if not os.path.exists(resolved_db):
            raise CommandError(f"Database not found: {resolved_db}")

        # Start server (stub for now)
        self.start_server(resolved_db, site, port)

    def start_server(self, db_path, site, port):
        """Start the Datasette server. Stubbed for testing."""
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_datasette_command.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_datasette_command.py pages/management/commands/datasette.py
git commit -m "feat: add datasette command with argument parsing"
```

---

### Task 3: Test Database Path Resolution

**Files:**
- Modify: `tests/test_datasette_command.py`
- Modify: `pages/management/commands/datasette.py`

- [ ] **Step 1: Write failing tests for database path resolution**

Add to `tests/test_datasette_command.py`:
```python
class TestDatabasePathResolution:
    """Test database path resolution logic."""

    def test_site_resolves_to_convention_path(self, mocker):
        """Site subdomain resolves to ../sites/{subdomain}/meetings.db."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-01-01",
        }
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        call_command("datasette", "alameda.ca")

        # Check the db_path passed to start_server
        call_args = start_mock.call_args
        assert call_args[0][0] == "../sites/alameda.ca/meetings.db"

    def test_db_flag_overrides_convention(self, mocker):
        """--db flag overrides the convention-based path."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)

        call_command("datasette", db="/custom/path/meetings.db")

        call_args = start_mock.call_args
        assert call_args[0][0] == "/custom/path/meetings.db"

    def test_site_with_db_uses_db_path(self, mocker):
        """When both site and --db provided, --db takes precedence for path."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-01-01",
        }
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        call_command("datasette", "alameda.ca", db="/custom/db.db")

        call_args = start_mock.call_args
        assert call_args[0][0] == "/custom/db.db"

    def test_missing_database_raises_error(self, mocker):
        """Error when database file doesn't exist."""
        mocker.patch("os.path.exists", return_value=False)

        with pytest.raises(CommandError, match="Database not found"):
            call_command("datasette", db="/nonexistent/db.db")
```

- [ ] **Step 2: Run tests to verify they pass (already implemented)**

```bash
pytest tests/test_datasette_command.py::TestDatabasePathResolution -v
```

Expected: All tests PASS (path resolution already implemented in Task 2)

- [ ] **Step 3: Commit**

```bash
git add tests/test_datasette_command.py
git commit -m "test: add database path resolution tests"
```

---

### Task 4: Test Metadata Context Building

**Files:**
- Modify: `tests/test_datasette_command.py`
- Modify: `pages/management/commands/datasette.py`

- [ ] **Step 1: Write failing tests for metadata context**

Add to `tests/test_datasette_command.py`:
```python
class TestMetadataContext:
    """Test metadata context building from sites.db or defaults."""

    def test_site_lookup_builds_context_from_sitesdb(self, mocker):
        """Site subdomain triggers sites.db lookup for context."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)
        mock_table = mocker.MagicMock()
        mock_table.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-03-15",
        }
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value = mock_table
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        call_command("datasette", "alameda.ca")

        # Verify sites.db was queried
        mock_db.__getitem__.assert_called_with("sites")
        mock_table.get.assert_called_with("alameda.ca")

    def test_site_not_found_raises_error(self, mocker):
        """Error when site not found in sites.db."""
        mocker.patch("os.path.exists", return_value=True)
        mock_table = mocker.MagicMock()
        mock_table.get.return_value = None
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value = mock_table
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        with pytest.raises(CommandError, match="Site not found"):
            call_command("datasette", "nonexistent.ca")

    def test_db_only_uses_placeholder_defaults(self, mocker):
        """--db only mode uses placeholder defaults for context."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)
        # Should NOT query sites.db
        db_mock = mocker.patch("sqlite_utils.Database")

        call_command("datasette", db="/path/to/test.db")

        # sites.db should not be opened
        db_mock.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_datasette_command.py::TestMetadataContext -v
```

Expected: FAIL (sites.db lookup not implemented)

- [ ] **Step 3: Implement metadata context building**

Update `pages/management/commands/datasette.py`:
```python
"""Django management command to run Datasette for local development."""

import os

import sqlite_utils
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Start a standalone Datasette server for local template testing."""

    help = "Start Datasette for local development without subdomain configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "site",
            nargs="?",
            help="Site subdomain (e.g., alameda.ca). Used to find database and metadata.",
        )
        parser.add_argument(
            "--db",
            dest="db",
            help="Explicit database path. Overrides site-based path.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run Datasette on (default: 8001).",
        )

    def handle(self, *args, **options):
        site = options.get("site")
        db_path = options.get("db")
        port = options.get("port")

        # Validate: must have site or --db
        if not site and not db_path:
            raise CommandError(
                "You must provide either a site subdomain or --db path."
            )

        # Resolve database path
        if db_path:
            resolved_db = db_path
        else:
            resolved_db = f"../sites/{site}/meetings.db"

        # Check database exists
        if not os.path.exists(resolved_db):
            raise CommandError(f"Database not found: {resolved_db}")

        # Build metadata context
        if site:
            context = self.get_site_context(site)
        else:
            context = self.get_placeholder_context()

        # Start server
        self.start_server(resolved_db, site, port, context)

    def get_site_context(self, subdomain):
        """Look up site in sites.db and return context dict."""
        db = sqlite_utils.Database("sites.db")
        site = db["sites"].get(subdomain)

        if site is None:
            raise CommandError(
                f"Site not found: {subdomain}. "
                "Run with --db to use a database without site metadata."
            )

        return {
            "name": site["name"],
            "state": site["state"],
            "subdomain": site["subdomain"],
            "last_updated": site["last_updated"],
        }

    def get_placeholder_context(self):
        """Return placeholder defaults for --db only mode."""
        return {
            "name": "Local Dev",
            "state": "",
            "subdomain": "local",
            "last_updated": "",
        }

    def start_server(self, db_path, site, port, context):
        """Start the Datasette server. Stubbed for testing."""
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_datasette_command.py::TestMetadataContext -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_datasette_command.py pages/management/commands/datasette.py
git commit -m "feat: add sites.db lookup and placeholder context"
```

---

### Task 5: Test Metadata Template Rendering

**Files:**
- Modify: `tests/test_datasette_command.py`
- Modify: `pages/management/commands/datasette.py`

- [ ] **Step 1: Write failing tests for template rendering**

Add to `tests/test_datasette_command.py`:
```python
import json


class TestMetadataTemplateRendering:
    """Test Jinja2 metadata template rendering."""

    def test_renders_metadata_template_with_context(self, mocker, tmp_path):
        """Metadata template is rendered with site context."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)
        mock_table = mocker.MagicMock()
        mock_table.get.return_value = {
            "name": "Alameda",
            "state": "CA",
            "subdomain": "alameda.ca",
            "last_updated": "2026-03-15",
        }
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value = mock_table
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        call_command("datasette", "alameda.ca")

        # Check context was passed to start_server
        call_args = start_mock.call_args
        context = call_args[0][3]  # Fourth positional arg
        assert context["name"] == "Alameda"
        assert context["state"] == "CA"
        assert context["subdomain"] == "alameda.ca"

    def test_placeholder_context_used_for_db_only(self, mocker):
        """Placeholder context used when only --db provided."""
        start_mock = mocker.patch(
            "pages.management.commands.datasette.Command.start_server"
        )
        mocker.patch("os.path.exists", return_value=True)

        call_command("datasette", db="/path/to/test.db")

        call_args = start_mock.call_args
        context = call_args[0][3]
        assert context["name"] == "Local Dev"
        assert context["state"] == ""
        assert context["subdomain"] == "local"
```

- [ ] **Step 2: Run tests to verify they pass (already implemented)**

```bash
pytest tests/test_datasette_command.py::TestMetadataTemplateRendering -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_datasette_command.py
git commit -m "test: add metadata template rendering tests"
```

---

### Task 6: Implement Datasette Server Startup

**Files:**
- Modify: `pages/management/commands/datasette.py`
- Modify: `tests/test_datasette_command.py`

- [ ] **Step 1: Write integration test for server startup components**

Add to `tests/test_datasette_command.py`:
```python
class TestDatasetteServerSetup:
    """Test Datasette instance configuration."""

    def test_creates_datasette_with_correct_settings(self, mocker):
        """Datasette instance created with dev-friendly settings."""
        mocker.patch("os.path.exists", return_value=True)
        mock_table = mocker.MagicMock()
        mock_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value = mock_table
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        # Mock Datasette to capture instantiation args
        datasette_mock = mocker.patch("datasette.app.Datasette")
        # Mock uvicorn to prevent actual server start
        mocker.patch("uvicorn.run")
        # Mock Jinja2 template rendering
        mock_template = mocker.MagicMock()
        mock_template.render.return_value = '{"title": "Test"}'
        mock_env = mocker.MagicMock()
        mock_env.get_template.return_value = mock_template
        mocker.patch(
            "jinja2.Environment",
            return_value=mock_env,
        )

        call_command("datasette", "test.ca")

        # Verify Datasette was instantiated
        datasette_mock.assert_called_once()
        call_kwargs = datasette_mock.call_args.kwargs

        # Check settings
        assert call_kwargs["settings"]["force_https_urls"] is False
        assert call_kwargs["settings"]["allow_download"] is True
        assert call_kwargs["plugins_dir"] == "plugins"
        assert call_kwargs["template_dir"] == "templates/datasette"

    def test_includes_additional_databases_if_present(self, mocker):
        """Finance and items databases included if they exist."""
        # Make meetings.db exist, plus finance dbs
        def path_exists(path):
            return path in [
                "../sites/test.ca/meetings.db",
                "../sites/test.ca/finance/election_finance.db",
                "../sites/test.ca/finance/items.db",
            ]

        mocker.patch("os.path.exists", side_effect=path_exists)
        mock_table = mocker.MagicMock()
        mock_table.get.return_value = {
            "name": "Test",
            "state": "CA",
            "subdomain": "test.ca",
            "last_updated": "2026-01-01",
        }
        mock_db = mocker.MagicMock()
        mock_db.__getitem__.return_value = mock_table
        mocker.patch("sqlite_utils.Database", return_value=mock_db)

        datasette_mock = mocker.patch("datasette.app.Datasette")
        mocker.patch("uvicorn.run")
        mock_template = mocker.MagicMock()
        mock_template.render.return_value = '{"title": "Test"}'
        mock_env = mocker.MagicMock()
        mock_env.get_template.return_value = mock_template
        mocker.patch("jinja2.Environment", return_value=mock_env)

        call_command("datasette", "test.ca")

        # Check all three databases were passed
        call_args = datasette_mock.call_args
        db_list = call_args[0][0]
        assert len(db_list) == 3
        assert "../sites/test.ca/meetings.db" in db_list
        assert "../sites/test.ca/finance/election_finance.db" in db_list
        assert "../sites/test.ca/finance/items.db" in db_list
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_datasette_command.py::TestDatasetteServerSetup -v
```

Expected: FAIL (server setup not implemented)

- [ ] **Step 3: Implement full server startup**

Update `pages/management/commands/datasette.py`:
```python
"""Django management command to run Datasette for local development."""

import json
import os

import sqlite_utils
import uvicorn
from datasette.app import Datasette
from django.core.management.base import BaseCommand, CommandError
from jinja2 import Environment, FileSystemLoader


class Command(BaseCommand):
    """Start a standalone Datasette server for local template testing."""

    help = "Start Datasette for local development without subdomain configuration"

    def add_arguments(self, parser):
        parser.add_argument(
            "site",
            nargs="?",
            help="Site subdomain (e.g., alameda.ca). Used to find database and metadata.",
        )
        parser.add_argument(
            "--db",
            dest="db",
            help="Explicit database path. Overrides site-based path.",
        )
        parser.add_argument(
            "--port",
            type=int,
            default=8001,
            help="Port to run Datasette on (default: 8001).",
        )

    def handle(self, *args, **options):
        site = options.get("site")
        db_path = options.get("db")
        port = options.get("port")

        # Validate: must have site or --db
        if not site and not db_path:
            raise CommandError(
                "You must provide either a site subdomain or --db path."
            )

        # Resolve database path
        if db_path:
            resolved_db = db_path
        else:
            resolved_db = f"../sites/{site}/meetings.db"

        # Check database exists
        if not os.path.exists(resolved_db):
            raise CommandError(f"Database not found: {resolved_db}")

        # Build metadata context
        if site:
            context = self.get_site_context(site)
        else:
            context = self.get_placeholder_context()

        # Start server
        self.start_server(resolved_db, site, port, context)

    def get_site_context(self, subdomain):
        """Look up site in sites.db and return context dict."""
        db = sqlite_utils.Database("sites.db")
        site = db["sites"].get(subdomain)

        if site is None:
            raise CommandError(
                f"Site not found: {subdomain}. "
                "Run with --db to use a database without site metadata."
            )

        return {
            "name": site["name"],
            "state": site["state"],
            "subdomain": site["subdomain"],
            "last_updated": site["last_updated"],
        }

    def get_placeholder_context(self):
        """Return placeholder defaults for --db only mode."""
        return {
            "name": "Local Dev",
            "state": "",
            "subdomain": "local",
            "last_updated": "",
        }

    def start_server(self, db_path, site, port, context):
        """Start the Datasette server."""
        # Build database list
        db_list = [db_path]

        # Check for additional databases (only when using site convention)
        if site:
            finance_db = f"../sites/{site}/finance/election_finance.db"
            if os.path.exists(finance_db):
                db_list.append(finance_db)

            items_db = f"../sites/{site}/finance/items.db"
            if os.path.exists(items_db):
                db_list.append(items_db)

        # Render metadata template
        jinja_env = Environment(loader=FileSystemLoader("templates/config"))
        template = jinja_env.get_template("metadata.json")
        metadata = json.loads(template.render(context=context))

        # Create Datasette instance with dev-friendly settings
        datasette_instance = Datasette(
            db_list,
            config=metadata,
            plugins_dir="plugins",
            template_dir="templates/datasette",
            settings={
                "force_https_urls": False,
                "default_page_size": 100,
                "sql_time_limit_ms": 3000,
                "num_sql_threads": 5,
                "default_facet_size": 10,
                "facet_time_limit_ms": 100,
                "allow_download": True,
                "allow_csv_stream": True,
            },
        )

        # Print startup info
        site_name = context.get("name", "Local Dev")
        self.stdout.write(f"Starting Datasette for {site_name}")
        self.stdout.write(f"Database: {db_path}")
        self.stdout.write(f"Metadata: {site_name} Civic Data")
        self.stdout.write("")
        self.stdout.write(f"Running at http://localhost:{port}/")
        self.stdout.write("Press Ctrl+C to stop.")

        # Run the server
        uvicorn.run(datasette_instance.app(), host="127.0.0.1", port=port)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_datasette_command.py::TestDatasetteServerSetup -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add pages/management/commands/datasette.py tests/test_datasette_command.py
git commit -m "feat: implement datasette server startup with uvicorn"
```

---

### Task 7: Run All Tests and Final Verification

**Files:**
- All test files

- [ ] **Step 1: Run all tests**

```bash
pytest tests/test_datasette_command.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Run full project test suite**

```bash
pytest
```

Expected: All tests PASS

- [ ] **Step 3: Verify command appears in Django help**

```bash
python manage.py help datasette
```

Expected: Shows command help with arguments

- [ ] **Step 4: Commit any fixes**

If any fixes were needed:
```bash
git add -A
git commit -m "fix: address test failures"
```

---

### Task 8: Manual Testing (User Verification)

**Files:**
- None (manual testing)

- [ ] **Step 1: Test with a real site (requires ../sites/ directory with data)**

```bash
python manage.py datasette alameda.ca
```

Expected output:
```
Starting Datasette for Alameda
Database: ../sites/alameda.ca/meetings.db
Metadata: Alameda Civic Data

Running at http://localhost:8001/
Press Ctrl+C to stop.
```

Then open http://localhost:8001/ in browser and verify:
- Templates load correctly
- Plugins render (entities, votes, images)
- Pages display with card layout

- [ ] **Step 2: Test with --db flag**

```bash
python manage.py datasette --db ../sites/alameda.ca/meetings.db
```

Expected: Uses placeholder metadata ("Local Dev")

- [ ] **Step 3: Test custom port**

```bash
python manage.py datasette alameda.ca --port 8002
```

Expected: Server runs on port 8002

- [ ] **Step 4: Test error cases**

```bash
# No arguments
python manage.py datasette
# Expected: Error about requiring site or --db

# Nonexistent database
python manage.py datasette --db /nonexistent/path.db
# Expected: Error about database not found

# Nonexistent site
python manage.py datasette nonexistent.ca
# Expected: Error about site not found
```
