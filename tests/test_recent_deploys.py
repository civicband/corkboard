"""Tests for the recent deploys API endpoint."""

import json
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.test import Client
from django.utils import timezone


class TestRecentDeploys:
    """Test /api/recent-deploys/ endpoint."""

    @pytest.fixture
    def client(self):
        return Client()

    @pytest.fixture
    def authenticated_client(self):
        User.objects.create_user(username="testuser", password="testpass")
        client = Client()
        client.login(username="testuser", password="testpass")
        return client

    @pytest.mark.django_db
    def test_anonymous_returns_403(self, client):
        """Anonymous users get 403."""
        response = client.get("/api/recent-deploys/")
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_authenticated_returns_200(self, authenticated_client):
        """Authenticated users get 200 with JSON array."""
        since = timezone.now().isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert isinstance(data, list)

    @pytest.mark.django_db
    def test_missing_since_uses_now(self, authenticated_client):
        """Missing since param defaults to now (returns empty)."""
        response = authenticated_client.get("/api/recent-deploys/")
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data == []

    @pytest.mark.django_db
    def test_returns_recent_deploys(self, authenticated_client):
        """Returns sites with deploy stage updated after since."""
        from pages.models import Site

        now = timezone.now()
        Site.objects.create(
            subdomain="deploy-test.ca",
            name="Test City",
            state="CA",
            lat="37.0",
            lng="-122.0",
            current_stage="deploy",
            deploy_completed=5,
            updated_at=now,
        )
        Site.objects.create(
            subdomain="old.ca",
            name="Old City",
            state="CA",
            lat="38.0",
            lng="-121.0",
            current_stage="fetch",
            updated_at=now,
        )

        since = (now - timedelta(minutes=1)).isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        data = json.loads(response.content)

        assert len(data) == 1
        assert data[0]["subdomain"] == "deploy-test.ca"
        assert data[0]["name"] == "Test City"
        assert data[0]["state"] == "CA"
        assert data[0]["lat"] == "37.0"
        assert data[0]["lng"] == "-122.0"
        assert data[0]["deploy_completed"] == 5
        assert "updated_at" in data[0]

    @pytest.mark.django_db
    def test_excludes_old_deploys(self, authenticated_client):
        """Sites updated before since are excluded."""
        from pages.models import Site

        old_time = timezone.now() - timedelta(hours=1)
        Site.objects.create(
            subdomain="old-deploy.ca",
            name="Old Deploy",
            state="CA",
            lat="37.0",
            lng="-122.0",
            current_stage="deploy",
            deploy_completed=3,
            updated_at=old_time,
        )

        since = timezone.now().isoformat()
        response = authenticated_client.get(f"/api/recent-deploys/?since={since}")
        data = json.loads(response.content)
        assert data == []

    @pytest.mark.django_db
    def test_invalid_since_returns_400(self, authenticated_client):
        """Invalid since parameter returns 400."""
        response = authenticated_client.get("/api/recent-deploys/?since=not-a-date")
        assert response.status_code == 400
        data = json.loads(response.content)
        assert "error" in data
