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
        expected_fields = [
            'subdomain', 'name', 'state', 'country', 'kind',
            'pages', 'last_updated', 'lat', 'lng', 'popup'
        ]
        for field in expected_fields:
            assert field in fields

    def test_site_model_str(self):
        """Site model should have string representation."""
        site = Site(subdomain='test.ca', name='Test City')
        assert str(site) == 'Test City (test.ca)'

    @pytest.mark.django_db(databases=['default', 'sites'])
    def test_site_model_queries_sites_database(self):
        """Site model should automatically query sites database."""
        # This test verifies the custom manager routes to sites db
        sites = Site.objects.all()
        assert sites.db == 'sites'

        # Verify we can actually read sites
        count = Site.objects.count()
        assert count > 0  # Should have sites in the database
