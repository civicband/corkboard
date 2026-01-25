"""
Tests for pages app views.

Tests cover:
- home_view - Renders home page
- how_view - Renders how it works page
- why_view - Renders why page
- feed_view - Renders RSS feed
"""

import pytest
from django.test import Client, RequestFactory

from pages.views import feed_view, home_view, how_view, why_view


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
        """Test RSS feed via test client."""
        response = client.get("/rss.xml")

        assert response.status_code == 200
