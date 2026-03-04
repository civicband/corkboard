from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from pages.models import Site
from pages.utils import apply_site_filters


def home_view(request):
    """Homepage with sites directory."""
    # Apply filters and sorting
    sites, query, state, kind, sort, has_finance = apply_site_filters(request)

    # Get aggregate stats (from all sites, not filtered)
    all_sites = Site.objects.all()
    num_sites = all_sites.count()
    total_pages = all_sites.aggregate(total=Sum("pages"))["total"] or 0
    finance_sites_count = all_sites.filter(has_finance_data=True).count()

    # Get unique states and kinds for filter dropdowns
    states = Site.objects.values_list("state", flat=True).distinct().order_by("state")
    kinds = Site.objects.values_list("kind", flat=True).distinct().order_by("kind")

    context = {
        "sites": sites,
        "query": query,
        "state": state,
        "kind": kind,
        "sort": sort,
        "num_sites": num_sites,
        "total_pages": total_pages,
        "states": states,
        "kinds": kinds,
        "visible_count": sites.count(),
        "total_count": num_sites,
        "finance_sites_count": finance_sites_count,
        "has_finance": has_finance,
    }

    return render(request, "pages/home.html", context)


def sites_search_view(request):
    """HTMX endpoint for filtering sites table."""
    # If this is a direct navigation (not HTMX), redirect to home with query params
    if not request.headers.get("HX-Request"):
        from urllib.parse import urlencode

        from django.shortcuts import redirect

        query_params = request.GET.dict()
        if query_params:
            return redirect(f"/?{urlencode(query_params)}")
        return redirect("/")

    # Apply filters and sorting
    sites, query, state, kind, sort, has_finance = apply_site_filters(request)

    # Get total count for stats
    total_sites = Site.objects.count()

    context = {
        "sites": sites,
        "visible_count": sites.count(),
        "total_count": total_sites,
        "query": query,
        "state": state,
        "kind": kind,
        "sort": sort,
        "has_finance": has_finance,
    }

    return render(request, "pages/_sites_table_only.html", context)


def how_view(request):
    return render(request, "pages/how.html")


def why_view(request):
    return render(request, "pages/why.html")


def privacy_view(request):
    return render(request, "pages/privacy.html")


def researchers_view(request):
    return render(request, "pages/researchers.html")


def feed_view(request):
    return render(request, "pages/rss.xml")


def map_view(request):
    """Full-page map of all CivicBand sites."""
    sites = Site.objects.filter(lat__isnull=False, lng__isnull=False)
    return render(request, "pages/map.html", {"sites": sites})


def recent_deploys_view(request):
    """API endpoint returning recently deployed sites.

    Query params:
        since: ISO timestamp — only return sites updated after this time.
               Defaults to now (returns empty).

    Returns 403 for anonymous users.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=403)

    since_param = request.GET.get("since")
    if since_param:
        # URL query strings decode '+' as space; restore it for ISO parsing
        since = parse_datetime(since_param.replace(" ", "+"))
        if since is None:
            return JsonResponse(
                {"error": f"Invalid 'since' parameter: {since_param}"}, status=400
            )
    else:
        since = timezone.now()

    sites = Site.objects.filter(
        current_stage="completed",
        deploy_completed__gt=0,
        updated_at__gt=since,
        lat__isnull=False,
        lng__isnull=False,
    ).order_by("-updated_at")[:50]

    data = [
        {
            "subdomain": site.subdomain,
            "name": site.name,
            "state": site.state,
            "kind": site.kind,
            "pages": site.pages,
            "lat": site.lat,
            "lng": site.lng,
            "deploy_completed": site.deploy_completed,
            "updated_at": site.updated_at.isoformat() if site.updated_at else None,
        }
        for site in sites
    ]

    return JsonResponse(data, safe=False)
