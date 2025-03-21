from datasette import hookimpl


@hookimpl
def extra_template_vars(datasette):
    return {
        "site_name": datasette.plugin_config("corkboard").get("site_name"),
        "subdomain": datasette.plugin_config("corkboard").get("subdomain"),
        "site_title": datasette.plugin_config("corkboard").get("site_title"),
        "site_description_html": datasette.plugin_config("corkboard").get(
            "site_description_html"
        ),
    }
