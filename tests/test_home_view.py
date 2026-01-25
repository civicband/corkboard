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

    def test_clear_filters_button_shows_with_filters(self, client: Client):
        """Clear filters button should appear when filters are active."""
        response = client.get(reverse('home') + '?state=CA')
        content = response.content.decode()
        assert 'Clear filters' in content
        assert 'style="display: inline-block;"' in content or 'display: inline-block' in content

    def test_clear_filters_button_hidden_without_filters(self, client: Client):
        """Clear filters button should be hidden when no filters are active."""
        response = client.get(reverse('home'))
        content = response.content.decode()
        assert 'Clear filters' in content  # Button exists in HTML
        assert 'style="display: none;"' in content  # But is hidden
