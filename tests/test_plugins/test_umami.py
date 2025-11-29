"""
Tests for umami.py plugin.

Tests cover:
- Script injection without auto-track
- Subdomain extraction JavaScript
- Manual pageview tracking
- umami.track patching for custom events
"""

from plugins.umami import extra_body_script


class TestUmamiPlugin:
    """Test Umami plugin script injection."""

    def test_script_does_not_have_auto_track(self):
        """Script should not have data-auto-track attribute."""
        result = extra_body_script(None)
        script = result["script"]
        assert "data-auto-track" not in script

    def test_script_includes_umami_loader(self):
        """Script should include Umami script loader."""
        result = extra_body_script(None)
        script = result["script"]
        assert "https://analytics.civic.band/sunshine" in script
        assert "6250918b-6a0c-4c05-a6cb-ec8f86349e1a" in script

    def test_script_extracts_subdomain(self):
        """Script should extract subdomain from hostname."""
        result = extra_body_script(None)
        script = result["script"]
        # Should have subdomain extraction logic
        assert "hostname" in script.lower() or "subdomain" in script.lower()

    def test_script_tracks_pageview_with_subdomain(self):
        """Script should track pageview with subdomain property."""
        result = extra_body_script(None)
        script = result["script"]
        # Should call umami.track for pageview
        assert "pageview" in script.lower()
        assert "subdomain" in script

    def test_script_patches_umami_track(self):
        """Script should patch umami.track to auto-include subdomain."""
        result = extra_body_script(None)
        script = result["script"]
        # Should modify umami.track function
        assert "umami.track" in script
