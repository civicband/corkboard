"""
Tests for structured JSON logging: formatter, request middleware, and the
Datasette subdomain wrapper's access records.
"""

import json
import logging
import os
import sys
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.fixture(autouse=True)
def clear_datasette_cache():
    """Keep the module-level Datasette cache from leaking between tests."""
    from django_plugins import datasette_by_subdomain

    datasette_by_subdomain._datasette_cache.clear()
    yield
    datasette_by_subdomain._datasette_cache.clear()


def parse_record_line(record):
    """Run the record through CorkboardJsonFormatter and return the dict."""
    from config.logging import CorkboardJsonFormatter

    fmt = CorkboardJsonFormatter()
    return json.loads(fmt.format(record))


def make_record(
    message="hello world",
    level=logging.INFO,
    pathname="/app/x.py",
    lineno=42,
    func="my_func",
    exc_info=None,
    **extra,
):
    record = logging.LogRecord(
        name=__name__,
        level=level,
        pathname=pathname,
        lineno=lineno,
        msg=message,
        args=(),
        exc_info=exc_info,
        func=func,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestCorkboardJsonFormatter:
    def test_includes_standard_metadata(self):
        out = parse_record_line(make_record())

        assert out["name"] == __name__
        assert out["level"] == "info"
        assert out["module"] == "x"
        assert out["function"] == "my_func"
        assert out["line"] == 42
        assert out["pathname"] == "/app/x.py"
        assert out["process"] == os.getpid()
        assert out["message"] == "hello world"
        assert out["timestamp"]
        assert "levelname" not in out
        assert "asctime" not in out
        assert "levelno" not in out
        assert "args" not in out
        assert "msg" not in out

    def test_level_is_lowercased(self):
        out = parse_record_line(make_record(level=logging.WARNING))
        assert out["level"] == "warning"

    def test_includes_extra_fields(self):
        out = parse_record_line(
            make_record(
                message="done",
                status_code=200,
                subdomain="alameda",
                duration_ms=12.5,
                request_method="GET",
            )
        )
        assert out["status_code"] == 200
        assert out["subdomain"] == "alameda"
        assert out["duration_ms"] == 12.5
        assert out["request_method"] == "GET"

    def test_renders_traceback_when_exc_info_present(self):
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        out = parse_record_line(
            make_record(message="failed", level=logging.ERROR, exc_info=exc_info)
        )
        assert "ValueError: boom" in out["traceback"]


def _capture_corkboard_access():
    """Attach a handler to the corkboard.access logger and return records + teardown."""
    records = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record)
    logger = logging.getLogger("corkboard.access")
    logger.addHandler(handler)
    return records, lambda: logger.removeHandler(handler)


class TestRequestLogMiddleware:
    def test_emits_single_structured_access_record(self):
        records, teardown = _capture_corkboard_access()
        try:
            Client().get("/health/")
        finally:
            teardown()

        assert len(records) == 1
        record = records[0]
        assert record.levelname == "INFO"
        assert record.request_method == "GET"
        assert record.request_path == "/health/"
        assert record.status_code == 200
        assert record.scheme == "http"
        assert record.request_host
        assert record.duration_ms >= 0

    def test_captures_user_agent_and_query_string(self):
        records, teardown = _capture_corkboard_access()
        try:
            Client().get("/health/?page=2", HTTP_USER_AGENT="corkboard-tests/1.0")
        finally:
            teardown()

        record = records[0]
        assert record.user_agent == "corkboard-tests/1.0"
        assert record.request_path == "/health/?page=2"


@pytest.mark.asyncio
async def test_datasette_wrapper_emits_access_record():
    """A successful Datasette subdomain request logs one access record."""
    from django_plugins import datasette_by_subdomain

    records, teardown = _capture_corkboard_access()
    mock_app = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    mock_receive = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    mock_send = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(b"host", b"testcity.civic.band")],
    }

    with (
        patch("django_plugins.datasette_by_subdomain.sqlite3.connect"),
        patch("django_plugins.datasette_by_subdomain.sqlite_utils") as mock_sqlite,
        patch("datasette.app.Datasette") as mock_datasette,
        patch("django_plugins.datasette_by_subdomain.Environment") as mock_environment,
        patch("django_plugins.datasette_by_subdomain.FileSystemLoader"),
    ):
        mock_db = mock_sqlite.Database.return_value
        mock_db["sites"].get.return_value = {
            "name": "Test City",
            "subdomain": "testcity",
            "state": "CA",
            "last_updated": "2024-01-01",
        }
        template = mock_environment.return_value.get_template.return_value
        template.render.return_value = json.dumps({"title": "Test City"})
        mock_ds = mock_datasette.return_value

        async def fake_ds(recv_scope, recv_receive, recv_send):
            assert recv_scope is scope
            assert recv_receive is mock_receive
            await recv_send(
                {"type": "http.response.start", "status": 200, "headers": []}
            )
            await recv_send({"type": "http.response.body", "body": b""})

        mock_ds.app.return_value = fake_ds

        try:
            wrapper = datasette_by_subdomain.wrap(mock_app)
            await wrapper(scope, mock_receive, mock_send)
        finally:
            teardown()

    assert len(records) == 1
    record = records[0]
    assert record.subdomain == "testcity"
    assert record.method == "GET"
    assert record.path == "/"
    assert record.status_code == 200
    assert record.duration_ms >= 0
    assert record.request_host == "testcity.civic.band"


@pytest.mark.asyncio
async def test_datasette_wrapper_emits_access_record_for_404():
    """A Datasette request that 404s still logs one access record."""
    from datasette.utils.asgi import NotFound

    from django_plugins import datasette_by_subdomain

    records, teardown = _capture_corkboard_access()
    mock_app = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    mock_receive = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    mock_send = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/missing",
        "query_string": b"",
        "headers": [(b"host", b"testcity.civic.band")],
    }

    with (
        patch("django_plugins.datasette_by_subdomain.sqlite3.connect"),
        patch("django_plugins.datasette_by_subdomain.sqlite_utils") as mock_sqlite,
        patch("datasette.app.Datasette") as mock_datasette,
        patch("django_plugins.datasette_by_subdomain.Environment") as mock_environment,
        patch("django_plugins.datasette_by_subdomain.FileSystemLoader"),
    ):
        mock_db = mock_sqlite.Database.return_value
        mock_db["sites"].get.return_value = {
            "name": "Test City",
            "subdomain": "testcity",
            "state": "CA",
            "last_updated": "2024-01-01",
        }
        template = mock_environment.return_value.get_template.return_value
        template.render.return_value = json.dumps({"title": "Test City"})
        mock_ds = mock_datasette.return_value

        async def not_found_ds(recv_scope, recv_receive, recv_send):
            raise NotFound("missing")

        mock_ds.app.return_value = not_found_ds

        try:
            wrapper = datasette_by_subdomain.wrap(mock_app)
            await wrapper(scope, mock_receive, mock_send)
        finally:
            teardown()

    assert len(records) == 1
    record = records[0]
    assert record.status_code == 404
    assert record.path == "/missing"
