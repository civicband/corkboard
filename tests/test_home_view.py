import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db(databases=['default', 'sites'])
class TestHomeView:
    def test_home_view_renders(self, client: Client):
        """Home view should render successfully."""
        response = client.get(reverse('home'))
        assert response.status_code == 200

    def test_home_view_has_stats(self, client: Client):
        """Home view should include aggregate stats."""
        response = client.get(reverse('home'))
        assert 'num_sites' in response.context
        assert 'total_pages' in response.context

    def test_home_view_respects_query_params(self, client: Client):
        """Home view should filter based on query params."""
        response = client.get(reverse('home') + '?q=test&state=CA&kind=city&sort=pages')
        assert response.context['query'] == 'test'
        assert response.context['state'] == 'CA'
        assert response.context['kind'] == 'city'
        assert response.context['sort'] == 'pages'
