"""Tests for pages app utility functions."""

import pytest
from django.test import RequestFactory

from pages.utils import apply_site_filters


@pytest.mark.django_db
class TestApplySiteFilters:
    """Tests for apply_site_filters utility function."""

    def test_apply_filters_with_valid_sort(self):
        """Should accept valid sort parameters."""
        factory = RequestFactory()
        request = factory.get("/", {"sort": "pages"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert sort == "pages"
        assert sites is not None

    def test_apply_filters_with_invalid_sort_defaults_to_pages(self):
        """Should default to 'pages' when sort parameter is invalid."""
        factory = RequestFactory()
        request = factory.get("/", {"sort": "invalid_field"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert sort == "pages"  # Should default to 'pages'

    def test_apply_filters_with_updated_at_sort(self):
        """Should accept 'updated_at' as valid sort parameter."""
        factory = RequestFactory()
        request = factory.get("/", {"sort": "updated_at"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert sort == "updated_at"

    def test_apply_filters_with_query(self):
        """Should return query parameter."""
        factory = RequestFactory()
        request = factory.get("/", {"q": "berkeley"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert query == "berkeley"

    def test_apply_filters_with_state(self):
        """Should return state parameter."""
        factory = RequestFactory()
        request = factory.get("/", {"state": "CA"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert state == "CA"

    def test_apply_filters_with_kind(self):
        """Should return kind parameter."""
        factory = RequestFactory()
        request = factory.get("/", {"kind": "city"})

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert kind == "city"

    def test_apply_filters_with_all_parameters(self):
        """Should handle all parameters together."""
        factory = RequestFactory()
        request = factory.get(
            "/",
            {
                "q": "test",
                "state": "CA",
                "kind": "city",
                "sort": "updated_at",
                "has_finance": "1",
            },
        )

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert query == "test"
        assert state == "CA"
        assert kind == "city"
        assert sort == "updated_at"
        assert has_finance == "1"
        assert sites is not None

    def test_apply_filters_with_no_parameters(self):
        """Should handle request with no parameters."""
        factory = RequestFactory()
        request = factory.get("/")

        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert query == ""
        assert state == ""
        assert kind == ""
        assert sort == "pages"  # Default sort
        assert has_finance == ""
        assert sites is not None

    def test_sql_injection_attempt_in_query(self):
        """Should safely handle SQL injection attempts in query parameter."""
        factory = RequestFactory()
        request = factory.get("/", {"q": "'; DROP TABLE sites; --"})

        # Should not raise an exception
        sites, query, state, kind, sort, has_finance = apply_site_filters(request)

        assert query == "'; DROP TABLE sites; --"
        # Query should be safely escaped by Django ORM
        assert sites is not None
