"""
Tests for pages app views.

Tests cover:
- home_view - Renders home page
- how_view - Renders how it works page
- why_view - Renders why page
- feed_view - Renders RSS feed
"""

import pytest
from django.test import Client, RequestFactory, override_settings

from pages.views import feed_view, home_view, how_view, municipalities_view, why_view


class TestPageViews:
    """Test Django page views."""

    @pytest.fixture
    def client(self):
        """Create Django test client."""
        return Client()

    @pytest.fixture
    def request_factory(self):
        """Create request factory for unit tests."""
        return RequestFactory()

    @pytest.mark.django_db
    def test_home_view(self, request_factory):
        """Test home page view returns 200."""
        request = request_factory.get("/")
        response = home_view(request)

        assert response.status_code == 200

    def test_how_view(self, request_factory):
        """Test how it works page view returns 200."""
        request = request_factory.get("/how.html")
        response = how_view(request)

        assert response.status_code == 200

    def test_why_view(self, request_factory):
        """Test why page view returns 200."""
        request = request_factory.get("/why.html")
        response = why_view(request)

        assert response.status_code == 200

    def test_feed_view(self, request_factory):
        """Test RSS feed view returns 200."""
        request = request_factory.get("/rss.xml")
        response = feed_view(request)

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_municipalities_view(self, request_factory):
        """Test municipalities browse view returns 200."""
        request = request_factory.get("/municipalities")
        response = municipalities_view(request)

        assert response.status_code == 200

    # Integration tests with full Django test client
    @pytest.mark.django_db
    def test_home_view_integration(self, client):
        """Test home page via test client."""
        response = client.get("/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_how_view_integration(self, client):
        """Test how page via test client."""
        response = client.get("/how.html")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_why_view_integration(self, client):
        """Test why page via test client."""
        response = client.get("/why.html")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_feed_view_integration(self, client):
        """Test RSS feed view via test client."""
        response = client.get("/rss.xml")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_shared_nav_has_social_icons_without_rss(self, client):
        """Shared navigation should use social icons and omit RSS."""
        response = client.get("/how.html")
        content = response.content.decode()

        assert 'aria-label="CivicBand on GitHub"' in content
        assert 'aria-label="CivicBand on Mastodon"' in content
        assert 'aria-label="CivicBand on Bluesky"' in content
        assert 'href="/rss.xml"' not in content

    @pytest.mark.django_db
    def test_footer_newsletter_is_in_details(self, client):
        """Footer newsletter should be collapsed behind a details drawer."""
        response = client.get("/how.html")
        content = response.content.decode()

        assert "subscribe to our newsletter" in content
        assert "<details" in content

    @pytest.mark.django_db
    @override_settings(CARTO_API_KEY="test-carto-key")
    def test_map_view_uses_carto_voyager_tiles(self, client):
        """Full map should use CARTO Voyager when an API key is configured."""
        response = client.get("/map")
        content = response.content.decode()

        assert response.status_code == 200
        assert (
            "basemaps.cartocdn.com/rastertiles/voyager/"
            "{z}/{x}/{y}{r}.png?key=test-carto-key" in content
        )
        assert "tile.openstreetmap.org" not in content
        assert "CARTO" in content

    @pytest.mark.django_db
    @override_settings(CARTO_API_KEY="")
    def test_map_view_falls_back_to_esri_without_carto_key(self, client):
        """Full map should keep working without a CARTO key."""
        response = client.get("/map")
        content = response.content.decode()

        assert response.status_code == 200
        assert "World_Street_Map/MapServer/tile/{z}/{y}/{x}" in content
        assert "basemaps.cartocdn.com" not in content

    @pytest.mark.django_db
    def test_shared_nav_has_mobile_nav_menu(self, client):
        """Shared nav should hide text links behind a menu on mobile."""
        content = client.get("/how.html").content.decode()

        assert 'aria-label="Open navigation menu"' in content
        assert "md:hidden" in content
        assert "hidden md:flex" in content
        assert "https://opencollective.com/civicband" in content
