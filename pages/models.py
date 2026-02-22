from django.db import models


class SiteManager(models.Manager):
    """Custom manager for Site model."""

    pass


class Site(models.Model):
    """Municipality site in the CivicBand directory.

    This model mirrors the sites table in sites.db, which is a simplified
    SQLite database containing basic information about each municipality.
    """

    # Basic site info (matches actual sites.db schema)
    subdomain = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    kind = models.CharField(max_length=255, null=True, blank=True)
    pages = models.IntegerField(null=True, blank=True)
    last_updated = models.CharField(max_length=255, null=True, blank=True)
    lat = models.CharField(max_length=255, null=True, blank=True)
    lng = models.CharField(max_length=255, null=True, blank=True)
    popup = models.TextField(null=True, blank=True)  # JSON data for map popup
    has_finance_data = models.BooleanField(default=False)

    objects = SiteManager()

    class Meta:
        db_table = "sites"
        managed = False  # Sites table is managed externally, Django is read-only
        ordering = ["-pages"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"

    @property
    def updated_at(self):
        """Parse last_updated string to datetime for compatibility."""
        if not self.last_updated:
            return None
        from datetime import datetime

        try:
            # Assuming format like "2024-01-15" or similar
            return datetime.fromisoformat(self.last_updated.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
