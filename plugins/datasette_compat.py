"""
Compatibility shims for the datasette 1.0 alphas.

1. datasette-dashboards 0.8.0 (latest release) calls
   ``Datasette.permission_allowed()``, which was removed in the datasette 1.0
   alphas and replaced by the keyword-only ``Datasette.allowed()`` API. We
   restore the removed method, delegating to the new API, so plugins that have
   not yet migrated keep working. It can be removed once datasette-dashboards
   publishes a release built against datasette 1.0.

2. ``Datasette.refresh_schemas()`` throttles to once per second and returns
   immediately when the refresh lock is held. On a freshly built instance the
   first requests run concurrently and can all take those fast paths before
   ``init_internal_db()`` has created the internal schema, so a subsequent
   query (e.g. ``get_column_types()`` during a table view) fails with
   ``no such table: column_types``. When the internal schema does not exist yet
   we bypass the fast paths and initialise it, serialised on the existing lock.

3. ``AsgiRunOnFirstRequest`` marks startup as begun *before* awaiting it, so
   concurrent first requests skip startup and can run against a half-started
   instance (``render_template()`` then raises "called before await
   ds.invoke_startup()"). We serialise it so later requests wait for the first
   startup to finish.
"""

import asyncio

from datasette.app import Datasette
from datasette.database import Database
from datasette.resources import DatabaseResource, TableResource
from datasette.utils.asgi import AsgiRunOnFirstRequest


async def permission_allowed(
    self, actor, action, resource=None, default=None, **kwargs
):
    # Old API accepted plain strings (database names) and
    # (database, table) tuples; the new API requires Resource objects.
    if isinstance(resource, (Database, str)):
        resource = DatabaseResource(getattr(resource, "name", resource))
    elif isinstance(resource, tuple):
        resource = TableResource(*resource)
    return await self.allowed(action=action, resource=resource, actor=actor)


if not hasattr(Datasette, "permission_allowed"):
    Datasette.permission_allowed = permission_allowed


_original_refresh_schemas = Datasette.refresh_schemas


async def refresh_schemas(self, *, force=False):
    if not self.internal_db_created:
        # Internal schema missing: never let the throttle or the
        # locked fast-path skip initialisation. Wait for the lock so callers
        # serialise instead of racing `init_internal_db()`.
        async with self._refresh_schemas_lock:
            await self._refresh_schemas()
        return
    return await _original_refresh_schemas(self, force=force)


Datasette.refresh_schemas = refresh_schemas


_original_first_request_init = AsgiRunOnFirstRequest.__init__


def _first_request_init(self, asgi, on_startup):
    _original_first_request_init(self, asgi, on_startup)
    self._compat_startup_lock = asyncio.Lock()


AsgiRunOnFirstRequest.__init__ = _first_request_init


async def _first_request_call(self, scope, receive, send):
    # Datasette flips ``_started`` to True *before* awaiting startup, so a
    # concurrent request skips startup entirely and is routed against a
    # half-started instance. Only treat startup as done once the hooks have
    # finished, and make later requests wait on the lock until then.
    if not self._started:
        async with self._compat_startup_lock:
            if not self._started:
                for hook in self.on_startup:
                    await hook()
                self._started = True
    return await self.asgi(scope, receive, send)


AsgiRunOnFirstRequest.__call__ = _first_request_call
