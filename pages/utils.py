"""Utility functions for pages app."""

from django.db.models import Q

from pages.models import Site

# Allowed sort fields to prevent potential errors
ALLOWED_SORT_FIELDS = {"pages", "last_updated"}


def apply_site_filters(request):
    """
    Apply filtering and sorting to Site queryset based on request params.

    Args:
        request: Django request object with GET parameters

    Returns:
        tuple: (filtered_sites_queryset, query, state, kind, sort)
    """
    # Get filter params
    query = request.GET.get("q", "")
    state = request.GET.get("state", "")
    kind = request.GET.get("kind", "")
    sort = request.GET.get("sort", "pages")

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

    # Apply sorting
    if sort == "last_updated":
        sites = sites.order_by("-last_updated")
    else:
        sites = sites.order_by("-pages")

    return sites, query, state, kind, sort
