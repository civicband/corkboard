"""
Umami Analytics Plugin for Datasette

Injects Umami tracking script with:
- Manual pageview tracking with subdomain property
- Patched umami.track to auto-include subdomain on all custom events
"""

from datasette import hookimpl


@hookimpl
def extra_body_script(datasette):
    """Inject Umami tracking script with subdomain support."""

    # JavaScript that:
    # 1. Loads Umami without auto-track
    # 2. Extracts subdomain from hostname
    # 3. Tracks pageview with subdomain
    # 4. Patches umami.track to auto-include subdomain

    script = """</script>
<script src="https://analytics.civic.band/sunshine" data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a"></script>
<script>
(function() {
    // Extract subdomain from hostname (everything except last 2 parts)
    var parts = window.location.hostname.split('.');
    var subdomain = parts.length > 2 ? parts.slice(0, -2).join('.') : null;

    // Wait for Umami to load, then set up tracking
    function setupTracking() {
        if (typeof umami === 'undefined') {
            setTimeout(setupTracking, 50);
            return;
        }

        // Track pageview with subdomain
        if (subdomain) {
            umami.track('pageview', { subdomain: subdomain });
        } else {
            umami.track('pageview');
        }

        // Patch umami.track to auto-include subdomain
        var originalTrack = umami.track;
        umami.track = function(eventName, eventData) {
            if (subdomain && eventData && typeof eventData === 'object') {
                eventData.subdomain = subdomain;
            } else if (subdomain && !eventData) {
                eventData = { subdomain: subdomain };
            }
            return originalTrack.call(umami, eventName, eventData);
        };
    }

    setupTracking();
})();
</script>
<script>"""

    return {"script": script}
