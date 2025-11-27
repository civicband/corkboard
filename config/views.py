from django.http import JsonResponse


def health_check(request):
    """Health check endpoint for load balancer."""
    return JsonResponse({"status": "ok"}, status=200)
