from datasette import hookimpl


@hookimpl
def extra_template_vars(template, datasette, request):
    if template != "index.html":
        return {
            "site_name": datasette.plugin_config("corkboard").get("site_name"),
            "subdomain": datasette.plugin_config("corkboard").get("subdomain"),
            "site_title": datasette.plugin_config("corkboard").get("site_title"),
            "site_description_html": datasette.plugin_config("corkboard").get(
                "site_description_html"
            ),
        }

    # For index.html, add recent content data
    async def inner():
        base_vars = {
            "site_name": datasette.plugin_config("corkboard").get("site_name"),
            "subdomain": datasette.plugin_config("corkboard").get("subdomain"),
            "site_title": datasette.plugin_config("corkboard").get("site_title"),
            "site_description_html": datasette.plugin_config("corkboard").get(
                "site_description_html"
            ),
        }

        # Get recent content data
        recent_content = await get_recent_content(datasette, request)
        base_vars.update(recent_content)

        return base_vars

    return inner


async def get_recent_content(datasette, request):
    """Get recent agendas and minutes for the index page"""
    del request  # Not used in this function
    try:
        # Get the main database (assume 'meetings' is the database name)
        db = datasette.get_database("meetings")

        # Query for upcoming agendas
        upcoming_agendas_sql = """
            SELECT meeting, date, count(page) as pages 
            FROM agendas 
            WHERE date >= date('now') 
            GROUP BY date, meeting 
            ORDER BY date ASC 
            LIMIT 5
        """

        # Query for recent minutes
        recent_minutes_sql = """
            SELECT meeting, date, count(page) as pages,
                   substr(group_concat(text, ' '), 1, 200) as preview
            FROM minutes 
            WHERE date >= date('now', '-14 days')
            GROUP BY date, meeting 
            ORDER BY date DESC 
            LIMIT 5
        """

        # Query for recent activity summary
        recent_activity_sql = """
            SELECT 
                'agenda' as type,
                meeting,
                date,
                count(page) as pages,
                substr(group_concat(text, ' '), 1, 150) as preview
            FROM agendas 
            WHERE date >= date('now', '-7 days')
            GROUP BY date, meeting
            
            UNION ALL
            
            SELECT 
                'minutes' as type,
                meeting,
                date,
                count(page) as pages,
                substr(group_concat(text, ' '), 1, 150) as preview
            FROM minutes 
            WHERE date >= date('now', '-7 days')
            GROUP BY date, meeting
            
            ORDER BY date DESC
            LIMIT 10
        """

        upcoming_agendas = []
        recent_minutes = []
        recent_activity = []

        # Execute queries
        try:
            upcoming_result = await db.execute(upcoming_agendas_sql)
            upcoming_agendas = [dict(row) for row in upcoming_result.rows]
        except Exception:
            pass  # Table might not exist or other error

        try:
            minutes_result = await db.execute(recent_minutes_sql)
            recent_minutes = [dict(row) for row in minutes_result.rows]
        except Exception:
            pass

        try:
            activity_result = await db.execute(recent_activity_sql)
            recent_activity = [dict(row) for row in activity_result.rows]
        except Exception:
            pass

        return {
            "upcoming_agendas": upcoming_agendas,
            "recent_minutes": recent_minutes,
            "recent_activity": recent_activity,
        }

    except Exception:
        # Return empty data if there's any error
        return {
            "upcoming_agendas": [],
            "recent_minutes": [],
            "recent_activity": [],
        }
