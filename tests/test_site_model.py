import pytest

from pages.models import Site


@pytest.mark.django_db
class TestSiteModel:
    def test_site_model_exists(self):
        """Site model should be importable."""
        assert Site is not None

    def test_site_model_fields(self):
        """Site model should have expected fields matching sites.db schema."""
        fields = [f.name for f in Site._meta.get_fields()]
        # Fields that match the actual sites.db SQLite schema
        expected_fields = [
            "subdomain",
            "name",
            "state",
            "country",
            "kind",
            "pages",
            "last_updated",
            "lat",
            "lng",
            "popup",
            "has_finance_data",
        ]
        # Verify all expected fields exist
        for field in expected_fields:
            assert field in fields, f"Expected field '{field}' not found in Site model"

    def test_site_model_str(self):
        """Site model should have string representation."""
        site = Site(subdomain="test.ca", name="Test City")
        assert str(site) == "Test City (test.ca)"

    def test_site_model_queries_database(self):
        """Site model should query the database."""
        # Verify we can actually read sites
        count = Site.objects.count()
        assert count > 0  # Should have sites in the database
