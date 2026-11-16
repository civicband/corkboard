import pytest
from django.test import Client, override_settings
from django.urls import reverse


@pytest.mark.django_db
class TestHomeView:
    def test_home_view_renders(self, client: Client):
        """Home view should render successfully."""
        response = client.get(reverse("home"))
        assert response.status_code == 200

    def test_home_view_has_stats(self, client: Client):
        """Home view should include aggregate stats."""
        response = client.get(reverse("home"))
        assert "num_sites" in response.context
        assert "total_pages" in response.context

    def test_home_view_respects_query_params(self, client: Client):
        """Home view should filter based on query params."""
        response = client.get(reverse("home") + "?q=test&state=CA&kind=city&sort=pages")
        assert response.context["query"] == "test"
        assert response.context["state"] == "CA"
        assert response.context["kind"] == "city"
        assert response.context["sort"] == "pages"

    def test_clear_filters_button_shows_with_filters(self, client: Client):
        """Clear filters button should appear when filters are active."""
        response = client.get(reverse("home") + "?state=CA")
        content = response.content.decode()
        assert "Clear filters" in content
        assert (
            'style="display: inline-block;"' in content
            or "display: inline-block" in content
        )

    def test_clear_filters_button_hidden_without_filters(self, client: Client):
        """Clear filters button should be hidden when no filters are active."""
        response = client.get(reverse("home"))
        content = response.content.decode()
        assert "Clear filters" in content  # Button exists in HTML
        assert 'style="display: none;"' in content  # But is hidden

    def test_home_view_is_search_first(self, client: Client):
        """Homepage should target a dedicated results region, not a table."""
        response = client.get(reverse("home"))
        content = response.content.decode()
        assert 'id="home-search-form"' in content
        assert 'id="home-results"' in content
        assert 'id="sites-map"' in content
        assert "sites-table-container" not in content

    def test_home_view_does_not_render_full_directory_table(self, client: Client):
        """Homepage should not render the full municipality table."""
        response = client.get(reverse("home"))
        assert "<table" not in response.content.decode().lower()

    def test_home_view_has_social_icons_without_rss(self, client: Client):
        """Nav should use social icons and omit the RSS link."""
        response = client.get(reverse("home"))
        content = response.content.decode()
        assert 'aria-label="CivicBand on GitHub"' in content
        assert 'aria-label="CivicBand on Mastodon"' in content
        assert 'aria-label="CivicBand on Bluesky"' in content
        assert 'href="/rss.xml"' not in content

    def test_home_view_newsletter_is_in_details(self, client: Client):
        """Newsletter signup should be collapsed behind a details drawer."""
        response = client.get(reverse("home"))
        content = response.content.decode()
        assert "subscribe to our newsletter" in content
        assert "<details" in content

    def test_home_view_links_to_browse_page(self, client: Client):
        """Homepage should link to the full municipalities directory."""
        response = client.get(reverse("home"))
        assert 'href="/municipalities"' in response.content.decode()

    def test_home_view_htmx_search_returns_partial(self, client: Client):
        """HTMX searches should return only the results partial."""
        response = client.get(
            reverse("home"),
            HTTP_HX_REQUEST="true",
            HTTP_HX_TARGET="home-results",
        )
        content = response.content.decode()
        assert "<html" not in content.lower()
        assert 'id="home-results"' in content
        assert "sites:updated" in content

    def test_home_view_filtered_results_have_direct_links(self, client: Client):
        """Filtered homepage results should link straight to the municipal site."""
        response = client.get(reverse("home") + "?q=Test")
        content = response.content.decode()
        assert "Test City" in content
        assert "https://test.ca.civic.band" in content

    def test_home_view_has_visible_fastly_and_raft_credits(self, client: Client):
        """Fastly and Raft credits should be visible in the hero, above the fold."""
        content = client.get(reverse("home")).content.decode()

        assert 'id="project-credits"' in content
        credits = content.split('id="project-credits"', 1)[1].split(
            "<!-- Collapsible secondary information -->", 1
        )[0]
        assert "https://www.fastly.com/fast-forward" in credits
        assert "https://raft.foundation" in credits

    def test_home_view_map_excludes_zero_coordinates(self, client: Client):
        """Sites with placeholder 0,0 coordinates should not break map bounds."""
        from pages.models import Site

        Site.objects.create(
            subdomain="zero.ca",
            name="Zero Coordinate City",
            state="California",
            kind="city",
            pages=10,
            lat="0",
            lng="0",
        )

        content = client.get(reverse("home") + "?q=Zero").content.decode()

        assert "Zero Coordinate City" in content
        assert '"subdomain": "zero.ca"' not in content

    @override_settings(CARTO_API_KEY="test-carto-key")
    def test_home_view_uses_carto_positron_tiles(self, client: Client):
        """Homepage map should use CARTO Positron when an API key is configured."""
        content = client.get(reverse("home")).content.decode()

        assert (
            "basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png?key=test-carto-key"
            in content
        )
        assert "tile.openstreetmap.org" not in content
        assert "CARTO" in content

    @override_settings(CARTO_API_KEY="")
    def test_home_view_falls_back_to_esri_without_carto_key(self, client: Client):
        """Homepage map should keep working without a CARTO key."""
        content = client.get(reverse("home")).content.decode()

        assert "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}" in content
        assert "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}" in content
        assert "basemaps.cartocdn.com" not in content

    def test_home_view_has_mobile_nav_menu(self, client: Client):
        """Mobile nav should hide text links behind a menu, keeping socials/donate."""
        content = client.get(reverse("home")).content.decode()

        assert 'aria-label="Open navigation menu"' in content
        assert "md:hidden" in content
        assert "hidden md:flex" in content
        assert "https://opencollective.com/civicband" in content

    def test_home_view_chat_widget_skips_mobile_homepage(self, client: Client):
        """Chat widget should not load on the mobile homepage."""
        content = client.get(reverse("home")).content.decode()

        assert "tawk-chat-script" in content
        assert "isHomepage && mobileQuery.matches" in content
        assert "embed.tawk.to" in content
