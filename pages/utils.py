"""Utility functions for pages app."""

from django.db.models import Q

from pages.models import Site

# Allowed sort fields to prevent potential errors
ALLOWED_SORT_FIELDS = {"pages", "updated_at"}


def apply_site_filters(request):
    """
    Apply filtering and sorting to Site queryset based on request params.

    Args:
        request: Django request object with GET parameters

    Returns:
        tuple: (filtered_sites_queryset, query, state, kind, sort, has_finance)
    """
    # Get filter params
    query = request.GET.get("q", "")
    state = request.GET.get("state", "")
    kind = request.GET.get("kind", "")
    sort = request.GET.get("sort", "pages")
    has_finance = request.GET.get("has_finance", "")

    # Validate sort parameter
    if sort not in ALLOWED_SORT_FIELDS:
        sort = "pages"

    # Base queryset
    sites = Site.objects.all()

    # Apply filters
    if query:
        sites = sites.filter(
            Q(name__icontains=query)
            | Q(subdomain__icontains=query)
            | Q(state__icontains=query)
        )
    if state:
        sites = sites.filter(state=state)
    if kind:
        sites = sites.filter(kind=kind)
    if has_finance:
        sites = sites.filter(has_finance_data=True)

    # Apply sorting
    if sort == "updated_at":
        sites = sites.order_by("-updated_at")
    else:
        sites = sites.order_by("-pages")

    return sites, query, state, kind, sort, has_finance
