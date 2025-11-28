"""
Tests for config app views.

Tests cover:
- health_check - Health check endpoint for load balancer
"""

import json

import pytest
from django.test import Client, RequestFactory

from config.views import health_check


class TestConfigViews:
    """Test Django config views."""

    @pytest.fixture
    def client(self):
        """Create Django test client."""
        return Client()

    @pytest.fixture
    def request_factory(self):
        """Create request factory for unit tests."""
        return RequestFactory()

    def test_health_check_view(self, request_factory):
        """Test health check view returns 200."""
        request = request_factory.get("/health")
        response = health_check(request)

        assert response.status_code == 200

    def test_health_check_response_json(self, request_factory):
        """Test health check view returns correct JSON."""
        request = request_factory.get("/health")
        response = health_check(request)

        # Parse JSON response
        data = json.loads(response.content)
        assert data == {"status": "ok"}

    # Integration tests with full Django test client
    @pytest.mark.django_db
    def test_health_check_view_integration(self, client):
        """Test health check via test client."""
        response = client.get("/health/")

        assert response.status_code == 200

    @pytest.mark.django_db
    def test_health_check_response_json_integration(self, client):
        """Test health check JSON response via test client."""
        response = client.get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
