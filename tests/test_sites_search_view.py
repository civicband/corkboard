import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db(databases=['default', 'sites'])
class TestSitesSearchView:
    def test_sites_search_view_renders(self, client: Client):
        """Sites search view should render successfully."""
        response = client.get(reverse('sites_search'), HTTP_HX_REQUEST='true')
        assert response.status_code == 200

    def test_sites_search_filters_by_query(self, client: Client):
        """Sites search should filter by query param."""
        response = client.get(reverse('sites_search') + '?q=test', HTTP_HX_REQUEST='true')
        content = response.content.decode()
        # Should not render full page, just fragment
        assert '<html' not in content.lower()
        assert '<table' in content.lower() or 'sites-table' in content.lower()

    def test_sites_search_returns_geojson(self, client: Client):
        """Sites search should return GeoJSON for map."""
        response = client.get(reverse('sites_search'), HTTP_HX_REQUEST='true')
        content = response.content.decode()
        assert 'sites:updated' in content  # Custom event trigger
        assert 'FeatureCollection' in content or 'features' in content

    def test_sites_search_redirects_direct_navigation(self, client: Client):
        """Direct navigation to search endpoint should redirect to home."""
        response = client.get(reverse('sites_search'))
        assert response.status_code == 302
        assert response.url == '/'

    def test_sites_search_preserves_params_on_redirect(self, client: Client):
        """Direct navigation with params should redirect to home with params."""
        response = client.get(reverse('sites_search') + '?state=CA&q=test')
        assert response.status_code == 302
        assert 'state=CA' in response.url
        assert 'q=test' in response.url
