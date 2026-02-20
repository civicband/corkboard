"""Django admin configuration for pages app."""

from django.contrib import admin

from .models import Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    """Admin interface for Site model."""

    list_display = [
        "subdomain",
        "name",
        "state",
        "kind",
        "pages",
        "last_updated",
        "has_finance_data",
    ]
    list_filter = ["state", "country", "kind", "has_finance_data"]
    search_fields = ["subdomain", "name", "state"]
    readonly_fields = [
        "subdomain",
        "name",
        "state",
        "country",
        "kind",
        "pages",
        "last_updated",
        "lat",
        "lng",
        "has_finance_data",
    ]
    ordering = ["-pages"]

    fieldsets = [
        (
            "Basic Information",
            {
                "fields": [
                    "subdomain",
                    "name",
                    "state",
                    "country",
                    "kind",
                    "pages",
                    "last_updated",
                    "has_finance_data",
                ]
            },
        ),
        (
            "Location",
            {
                "fields": ["lat", "lng"],
                "classes": ["collapse"],
            },
        ),
    ]
