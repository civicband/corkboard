from django.db import models


class SiteManager(models.Manager):
    """Custom manager for Site model."""

    pass


class Site(models.Model):
    """Municipality site in the CivicBand directory.

    This model mirrors clerk's sites_table schema and connects to
    the same Postgres database that clerk workers use for coordination.
    """

    # Basic site info
    subdomain = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    kind = models.CharField(max_length=255, null=True, blank=True)
    scraper = models.CharField(max_length=255, null=True, blank=True)
    pages = models.IntegerField(null=True, blank=True)
    start_year = models.IntegerField(null=True, blank=True)
    extra = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    lat = models.CharField(max_length=255, null=True, blank=True)
    lng = models.CharField(max_length=255, null=True, blank=True)
    has_finance_data = models.BooleanField(default=False)

    # Pipeline state (managed by clerk)
    current_stage = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    # Fetch counters
    fetch_total = models.IntegerField(default=0)
    fetch_completed = models.IntegerField(default=0)
    fetch_failed = models.IntegerField(default=0)

    # OCR counters
    ocr_total = models.IntegerField(default=0)
    ocr_completed = models.IntegerField(default=0)
    ocr_failed = models.IntegerField(default=0)

    # Compilation counters
    compilation_total = models.IntegerField(default=0)
    compilation_completed = models.IntegerField(default=0)
    compilation_failed = models.IntegerField(default=0)

    # Extraction counters
    extraction_total = models.IntegerField(default=0)
    extraction_completed = models.IntegerField(default=0)
    extraction_failed = models.IntegerField(default=0)

    # Deploy counters
    deploy_total = models.IntegerField(default=0)
    deploy_completed = models.IntegerField(default=0)
    deploy_failed = models.IntegerField(default=0)

    # Coordinator tracking
    coordinator_enqueued = models.BooleanField(default=False)

    # Error tracking
    last_error_stage = models.CharField(max_length=255, null=True, blank=True)
    last_error_message = models.TextField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)

    # Deprecated fields (kept for migration compatibility)
    status = models.CharField(max_length=255, null=True, blank=True)
    extraction_status = models.CharField(max_length=255, default="pending")
    last_updated = models.CharField(max_length=255, null=True, blank=True)
    last_deployed = models.CharField(max_length=255, null=True, blank=True)
    last_extracted = models.CharField(max_length=255, null=True, blank=True)

    objects = SiteManager()

    class Meta:
        db_table = "sites"
        managed = False  # Clerk manages schema, Django is read-only consumer
        ordering = ["-pages"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    @property
    def popup(self):
        """Legacy property for backward compatibility."""
        return {}  # Can implement if needed
