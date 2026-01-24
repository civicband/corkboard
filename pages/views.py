from django.shortcuts import render
from django.db.models import Q, Sum
from pages.models import Site


def home_view(request):
    """Homepage with sites directory."""
    # Get filter params
    query = request.GET.get('q', '')
    state = request.GET.get('state', '')
    kind = request.GET.get('kind', '')
    sort = request.GET.get('sort', 'pages')

    # Base queryset
    sites = Site.objects.all()

    # Apply filters
    if query:
        sites = sites.filter(
            Q(name__icontains=query) |
            Q(subdomain__icontains=query) |
            Q(state__icontains=query)
        )
    if state:
        sites = sites.filter(state=state)
    if kind:
        sites = sites.filter(kind=kind)

    # Apply sorting
    if sort == 'last_updated':
        sites = sites.order_by('-last_updated')
    else:
        sites = sites.order_by('-pages')

    # Get aggregate stats (from all sites, not filtered)
    all_sites = Site.objects.all()
    num_sites = all_sites.count()
    total_pages = all_sites.aggregate(total=Sum('pages'))['total'] or 0

    # Get unique states for filter dropdown
    states = Site.objects.values_list('state', flat=True).distinct().order_by('state')

    context = {
        'sites': sites,
        'query': query,
        'state': state,
        'kind': kind,
        'sort': sort,
        'num_sites': num_sites,
        'total_pages': total_pages,
        'states': states,
    }

    return render(request, 'pages/home.html', context)


def sites_search_view(request):
    """HTMX endpoint for filtering sites table."""
    # Get filter params (same logic as home_view)
    query = request.GET.get('q', '')
    state = request.GET.get('state', '')
    kind = request.GET.get('kind', '')
    sort = request.GET.get('sort', 'pages')

    # Base queryset
    sites = Site.objects.all()

    # Apply filters
    if query:
        sites = sites.filter(
            Q(name__icontains=query) |
            Q(subdomain__icontains=query) |
            Q(state__icontains=query)
        )
    if state:
        sites = sites.filter(state=state)
    if kind:
        sites = sites.filter(kind=kind)

    # Apply sorting
    if sort == 'last_updated':
        sites = sites.order_by('-last_updated')
    else:
        sites = sites.order_by('-pages')

    # Get total count for stats
    total_sites = Site.objects.count()

    context = {
        'sites': sites,
        'visible_count': sites.count(),
        'total_count': total_sites,
        'query': query,
    }

    return render(request, 'pages/_sites_table.html', context)


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
