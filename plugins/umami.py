from datasette import hookimpl


@hookimpl
def extra_body_script(datasette):
    return {
        "script": '</script><script src="https://analytics.civic.band/sunshine" data-website-id="6250918b-6a0c-4c05-a6cb-ec8f86349e1a" data-auto-track="true">'
    }
