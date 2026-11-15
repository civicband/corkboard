import pytest
from django.test import Client
from django.urls import reverse

from pages.models import Site


@pytest.mark.django_db
class TestMunicipalitiesView:
    def test_renders(self, client: Client):
        """Municipalities page should render the browse directory."""
        response = client.get(reverse("municipalities"))
        content = response.content.decode()

        assert response.status_code == 200
        assert "municipalities-table-container" in content
        assert "All municipalities" in content

    def test_filters_by_state(self, client: Client):
        """Browse page should filter by state."""
        response = client.get(reverse("municipalities") + "?state=California")
        content = response.content.decode()

        assert "Test City" in content

    def test_has_direct_site_links(self, client: Client):
        """Browse table should link directly to municipal sites."""
        response = client.get(reverse("municipalities"))

        assert "https://test.ca.civic.band" in response.content.decode()

    def test_htmx_returns_table_partial(self, client: Client):
        """HTMX filtering should return only the table partial."""
        response = client.get(
            reverse("municipalities"),
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="municipalities-table-container",
        )
        content = response.content.decode()

        assert "<html" not in content.lower()
        assert "municipalities-table-container" in content
        assert "sites:updated" not in content

    def test_paginates(self, client: Client):
        """Browse page should paginate the full directory."""
        Site.objects.bulk_create(
            [
                Site(
                    subdomain=f"test-{i}.ca",
                    name=f"Test City {i}",
                    state="California",
                    kind="city",
                    pages=i,
                )
                for i in range(55)
            ]
        )

        response = client.get(reverse("municipalities") + "?page=2")

        assert response.status_code == 200
        assert response.context["page_obj"].number == 2
        assert len(response.context["page_obj"].object_list) <= 50
