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
        "pages",
        "current_stage",
        "updated_at",
        "get_progress",
    ]
    list_filter = ["state", "country", "kind", "current_stage"]
    search_fields = ["subdomain", "name", "state"]
    readonly_fields = [
        "subdomain",
        "started_at",
        "updated_at",
        "last_error_at",
        "fetch_total",
        "fetch_completed",
        "fetch_failed",
        "ocr_total",
        "ocr_completed",
        "ocr_failed",
        "compilation_total",
        "compilation_completed",
        "compilation_failed",
        "extraction_total",
        "extraction_completed",
        "extraction_failed",
        "deploy_total",
        "deploy_completed",
        "deploy_failed",
        "coordinator_enqueued",
    ]
    ordering = ["-pages"]
    date_hierarchy = "updated_at"

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
                    "scraper",
                    "pages",
                    "start_year",
                    "lat",
                    "lng",
                ]
            },
        ),
        (
            "Pipeline Status",
            {
                "fields": [
                    "current_stage",
                    "started_at",
                    "updated_at",
                    "coordinator_enqueued",
                ]
            },
        ),
        (
            "Fetch Progress",
            {
                "fields": ["fetch_total", "fetch_completed", "fetch_failed"],
                "classes": ["collapse"],
            },
        ),
        (
            "OCR Progress",
            {
                "fields": ["ocr_total", "ocr_completed", "ocr_failed"],
                "classes": ["collapse"],
            },
        ),
        (
            "Compilation Progress",
            {
                "fields": [
                    "compilation_total",
                    "compilation_completed",
                    "compilation_failed",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Extraction Progress",
            {
                "fields": [
                    "extraction_total",
                    "extraction_completed",
                    "extraction_failed",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Deploy Progress",
            {
                "fields": ["deploy_total", "deploy_completed", "deploy_failed"],
                "classes": ["collapse"],
            },
        ),
        (
            "Error Information",
            {
                "fields": ["last_error_stage", "last_error_message", "last_error_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def get_progress(self, obj):
        """Display overall progress across all stages."""
        if obj.current_stage == "fetch":
            total = obj.fetch_total
            completed = obj.fetch_completed
        elif obj.current_stage == "ocr":
            total = obj.ocr_total
            completed = obj.ocr_completed
        elif obj.current_stage == "compilation":
            total = obj.compilation_total
            completed = obj.compilation_completed
        elif obj.current_stage == "extraction":
            total = obj.extraction_total
            completed = obj.extraction_completed
        elif obj.current_stage == "deploy":
            total = obj.deploy_total
            completed = obj.deploy_completed
        else:
            return "N/A"

        if total and total > 0:
            percentage = (completed / total) * 100
            return f"{completed}/{total} ({percentage:.1f}%)"
        return "0/0"

    get_progress.short_description = "Current Progress"
