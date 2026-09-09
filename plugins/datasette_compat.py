"""
Compatibility shim for pre-1.0 datasette plugins.

datasette-dashboards 0.8.0 (latest release) calls
``Datasette.permission_allowed()``, which was removed in the datasette 1.0
alphas and replaced by the keyword-only ``Datasette.allowed()`` API.

This module restores the removed method, delegating to the new API so
plugins that have not yet migrated keep working. It can be removed once
datasette-dashboards publishes a release built against datasette 1.0.
"""

from datasette.app import Datasette
from datasette.database import Database
from datasette.resources import DatabaseResource, TableResource


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
