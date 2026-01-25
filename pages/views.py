from django.shortcuts import render
from django.db.models import Sum
from pages.models import Site
from pages.utils import apply_site_filters


def home_view(request):
    """Homepage with sites directory."""
    # Apply filters and sorting
    sites, query, state, kind, sort = apply_site_filters(request)

    # Get aggregate stats (from all sites, not filtered)
    all_sites = Site.objects.all()
    num_sites = all_sites.count()
    total_pages = all_sites.aggregate(total=Sum('pages'))['total'] or 0

    # Get unique states and kinds for filter dropdowns
    states = Site.objects.values_list('state', flat=True).distinct().order_by('state')
    kinds = Site.objects.values_list('kind', flat=True).distinct().order_by('kind')

    context = {
        'sites': sites,
        'query': query,
        'state': state,
        'kind': kind,
        'sort': sort,
        'num_sites': num_sites,
        'total_pages': total_pages,
        'states': states,
        'kinds': kinds,
        'visible_count': sites.count(),
        'total_count': num_sites,
    }

    return render(request, 'pages/home.html', context)


def sites_search_view(request):
    """HTMX endpoint for filtering sites table."""
    # If this is a direct navigation (not HTMX), redirect to home with query params
    if not request.headers.get('HX-Request'):
        from django.shortcuts import redirect
        from urllib.parse import urlencode
        query_params = request.GET.dict()
        if query_params:
            return redirect(f"/?{urlencode(query_params)}")
        return redirect('/')

    # Apply filters and sorting
    sites, query, state, kind, sort = apply_site_filters(request)

    # Get total count for stats
    total_sites = Site.objects.count()

    context = {
        'sites': sites,
        'visible_count': sites.count(),
        'total_count': total_sites,
        'query': query,
    }

    return render(request, 'pages/_sites_table_only.html', context)


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
