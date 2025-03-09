from datasette import hookimpl


@hookimpl
def extra_template_vars(datasette):
    async def metadata():
        return {
            "instance_metadata": await datasette.get_instance_metadata(),
            "subdomain": datasette.plugin_config("umami").get("subdomain"),
        }

    return metadata
