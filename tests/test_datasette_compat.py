"""Tests for the datasette compatibility shim (plugins/datasette_compat.py)."""

import asyncio
import time

import pytest
from datasette.app import Datasette
from datasette.utils.asgi import AsgiRunOnFirstRequest


@pytest.mark.asyncio
async def test_refresh_schemas_initializes_when_throttled():
    """refresh_schemas must not skip internal schema creation.

    Datasette throttles refresh_schemas() to once per second and returns
    immediately when the refresh lock is held. On a freshly-built instance
    concurrent requests can therefore all skip before init_internal_db() has
    run, and a later query fails with "no such table: column_types". When the
    internal schema does not exist yet, the throttle must not apply.
    """
    import plugins.datasette_compat  # noqa: F401  - applies the shim

    ds = Datasette([])
    # Simulate a refresh that just happened but did not create the internal
    # schema, as happens during the concurrent first-request startup race.
    ds._last_schema_refresh = time.monotonic()
    assert ds.internal_db_created is False

    await ds.refresh_schemas()

    rows = await ds.get_internal_database().execute(
        "select name from sqlite_master where name = 'column_types'"
    )
    assert rows.rows


@pytest.mark.asyncio
async def test_concurrent_first_requests_wait_for_startup():
    """Concurrent first requests must not route until startup has finished.

    Datasette flips its started flag before awaiting startup, so a second
    request can otherwise be routed against a half-started instance.
    """
    import plugins.datasette_compat  # noqa: F401  - applies the shim

    started = []
    seen = []

    async def on_startup():
        await asyncio.sleep(0.02)
        started.append(True)

    async def inner(scope, receive, send):
        seen.append(list(started))

    async def noop_receive():
        return {"type": "http.request"}

    async def noop_send(message):
        pass

    app = AsgiRunOnFirstRequest(inner, on_startup=[on_startup])

    await asyncio.gather(
        app({}, noop_receive, noop_send),
        app({}, noop_receive, noop_send),
    )

    assert started == [True]
    assert seen == [[True], [True]]
