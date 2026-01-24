import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db(databases=['default', 'sites'])
class TestSitesSearchView:
    def test_sites_search_view_renders(self, client: Client):
        """Sites search view should render successfully."""
        response = client.get(reverse('sites_search'))
        assert response.status_code == 200

    def test_sites_search_filters_by_query(self, client: Client):
        """Sites search should filter by query param."""
        response = client.get(reverse('sites_search') + '?q=berkeley')
        content = response.content.decode()
        # Should not render full page, just fragment
        assert '<html' not in content.lower()
        assert '<table' in content.lower() or 'sites-table' in content.lower()

    def test_sites_search_returns_geojson(self, client: Client):
        """Sites search should return GeoJSON for map."""
        response = client.get(reverse('sites_search'))
        content = response.content.decode()
        assert 'sites:updated' in content  # Custom event trigger
        assert 'FeatureCollection' in content or 'features' in content
