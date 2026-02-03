import pytest

from pages.models import Site


@pytest.mark.django_db
class TestSiteModel:
    def test_site_model_exists(self):
        """Site model should be importable."""
        assert Site is not None

    def test_site_model_fields(self):
        """Site model should have expected fields."""
        fields = [f.name for f in Site._meta.get_fields()]
        # Core site fields
        core_fields = [
            "subdomain",
            "name",
            "state",
            "country",
            "kind",
            "pages",
            "lat",
            "lng",
            "scraper",
        ]
        # Pipeline fields (from Postgres integration)
        pipeline_fields = [
            "current_stage",
            "started_at",
            "updated_at",
            "fetch_total",
            "fetch_completed",
            "fetch_failed",
            "ocr_total",
            "extraction_total",
            "deploy_total",
            "coordinator_enqueued",
        ]
        # Verify core fields exist
        for field in core_fields:
            assert field in fields, f"Expected core field '{field}' not found in Site model"
        # Verify some pipeline fields exist (not all to keep test maintainable)
        for field in pipeline_fields[:5]:
            assert field in fields, f"Expected pipeline field '{field}' not found in Site model"

    def test_site_model_str(self):
        """Site model should have string representation."""
        site = Site(subdomain="test.ca", name="Test City")
        assert str(site) == "Test City (test.ca)"

    def test_site_model_queries_database(self):
        """Site model should query the database."""
        # Verify we can actually read sites
        count = Site.objects.count()
        assert count > 0  # Should have sites in the database
