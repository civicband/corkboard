from django.db import models


class SiteManager(models.Manager):
    """Custom manager for Site model."""

    pass


class Site(models.Model):
    """Municipality site in the CivicBand directory."""

    subdomain = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    kind = models.CharField(max_length=100)
    pages = models.IntegerField(default=0)
    last_updated = models.DateTimeField()
    lat = models.CharField(max_length=50, blank=True)
    lng = models.CharField(max_length=50, blank=True)
    popup = models.JSONField(default=dict, blank=True)

    objects = SiteManager()  # Add custom manager

    class Meta:
        db_table = "sites"
        managed = False  # Don't let Django manage this table
        ordering = ["-pages"]

    def __str__(self):
        return f"{self.name} ({self.subdomain})"
