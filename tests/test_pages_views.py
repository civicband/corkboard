"""
Tests for pages app views.

Tests cover:
- home_view - Renders home page
- how_view - Renders how it works page
- why_view - Renders why page
- privacy_view - Renders privacy page
- feed_view - Renders RSS feed
"""

import pytest
from django.test import Client, RequestFactory

from pages.views import feed_view, home_view, how_view, privacy_view, why_view


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

    def test_home_view(self, request_factory):
        """Test home page view."""
        request = request_factory.get("/")
        response = home_view(request)

        assert response.status_code == 200
        assert "pages/index.html" in [t.name for t in response.templates]

    def test_how_view(self, request_factory):
        """Test how it works page view."""
        request = request_factory.get("/how/")
        response = how_view(request)

        assert response.status_code == 200
        assert "pages/how.html" in [t.name for t in response.templates]

    def test_why_view(self, request_factory):
        """Test why page view."""
        request = request_factory.get("/why/")
        response = why_view(request)

        assert response.status_code == 200
        assert "pages/why.html" in [t.name for t in response.templates]

    def test_privacy_view(self, request_factory):
        """Test privacy page view."""
        request = request_factory.get("/privacy/")
        response = privacy_view(request)

        assert response.status_code == 200
        assert "pages/privacy.html" in [t.name for t in response.templates]

    def test_feed_view(self, request_factory):
        """Test RSS feed view."""
        request = request_factory.get("/rss.xml")
        response = feed_view(request)

        assert response.status_code == 200
        assert "pages/rss.xml" in [t.name for t in response.templates]

    # Integration tests with full Django test client
    @pytest.mark.django_db
    def test_home_view_integration(self, client):
        """Test home page via test client."""
        response = client.get("/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_how_view_integration(self, client):
        """Test how page via test client."""
        response = client.get("/how/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_why_view_integration(self, client):
        """Test why page via test client."""
        response = client.get("/why/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_privacy_view_integration(self, client):
        """Test privacy page via test client."""
        response = client.get("/privacy/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_feed_view_integration(self, client):
        """Test RSS feed via test client."""
        response = client.get("/rss.xml")

        assert response.status_code == 200
