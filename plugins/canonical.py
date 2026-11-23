"""Canonical permalink helpers for the embedded Datasette sites.

Every page served by ``django_plugins/datasette_by_subdomain.py`` renders
``templates/datasette/base.html``, which emits a single
``<link rel="canonical">`` and ``og:url`` pointing at this municipality's
stable permalink (never at a POST URL, a filter/sort query string or a
relative triangle-host URL).

Phase 1 of the sharing plan locks the public permalink shape at::

    https://<subdomain>.civic.band/<database>/<table>/<row id>

Table pages canonicalize to the table root (query strings such as
``_search``, ``meeting__exact`` or ``_sort`` are not part of the permalink).
``/-/search`` is POST-only, so its canonical is the municipality landing
page (``https://<subdomain>.civic.band/``).

The helpers return **paths** rather than absolute URLs so the "what is the
canonical path for this page?" decision stays testable without an HTTP
request; ``canonical_url()`` then prefixes the canonical host.
"""

from datasette import hookimpl

CANONICAL_SCHEME = "https"
CANONICAL_HOST_SUFFIX = "civic.band"


def municipality_host(subdomain: str) -> str:
    """Canonical host for a municipality, e.g. ``alameda.ca.civic.band``."""
    return f"{(subdomain or '').strip('.')}.{CANONICAL_HOST_SUFFIX}".lstrip(".")


def canonical_path(database=None, table=None, row_id=None) -> str:
    """Return the canonical path for a page in a municipality's Datasette.

    - database + table + row id -> ``/<database>/<table>/<row id>``
    - database + table           -> ``/<database>/<table>``
    - database only              -> ``/<database>``
    - nothing                    -> ``/`` (municipality landing page)
    """
    segments = []
    for part in (database, table):
        if not part:
            break
        segments.append(str(part))
    if segments and row_id is not None and str(row_id) != "":
        segments.append(str(row_id))
    return "/" + "/".join(segments)


def canonical_url(subdomain: str, database=None, table=None, row_id=None) -> str:
    """Absolute canonical URL for a municipality page.

    Always uses ``https://<subdomain>.civic.band`` rather than the request
    host so the production permalink is emitted even when viewed through an
    alternate root domain or a preview deployment.
    """
    path = canonical_path(database=database, table=table, row_id=row_id)
    return f"{CANONICAL_SCHEME}://{municipality_host(subdomain)}{path}"


def page_anchor(page) -> str:
    """``#page-N`` anchor for a page badge, or empty string when unknown."""
    if page is None or str(page) == "":
        return ""
    return f"page-{page}"


def make_canonical_url(subdomain: str):
    """Return a Jinja filter bound to a municipality subdomain.

    Usage in ``base.html``: ``database | canonical_url(table, row_id)``.
    """

    def filter_canonical_url(database=None, table=None, row_id=None):
        return canonical_url(subdomain, database=database, table=table, row_id=row_id)

    return filter_canonical_url


@hookimpl
def prepare_jinja2_environment(env, datasette):
    """Register the ``canonical_url`` filter bound to this municipality.

    A filter (rather than a template variable) survives inheritance from
    ``default:row.html`` and is available in every template that Datasette
    renders, including error pages.
    """
    subdomain = (datasette.plugin_config("corkboard") or {}).get("subdomain") or ""
    env.filters["canonical_url"] = make_canonical_url(subdomain)
    # The canonical host, for templates that must build a *different* absolute
    # URL on the same host (e.g. the OG image, which is not a page permalink).
    env.globals["canonical_host"] = municipality_host(subdomain)
    # Templates check this flag instead of probing ``canonical_url is filter``
    # (Jinja 3.1.6 does not reliably expose the built-in ``filter`` test).
    env.globals["canonical_plugin_enabled"] = True
