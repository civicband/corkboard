from django.shortcuts import render


def home_view(request):
    return render(request, "pages/index.html")


def how_view(request):
    return render(request, "pages/how.html")


def why_view(request):
    return render(request, "pages/why.html")


def privacy_view(request):
    return render(request, "pages/privacy.html")


def feed_view(request):
    return render(request, "pages/rss.xml")
