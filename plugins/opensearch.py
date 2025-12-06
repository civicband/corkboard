"""OpenSearch plugin for researcher discovery and Zotero integration."""

from datasette import hookimpl
from datasette.utils.asgi import Response


async def opensearch_xml(datasette, request):
    """Generate OpenSearch description XML for the current subdomain."""
    config = datasette.plugin_config("corkboard") or {}
    subdomain = config.get("subdomain", "")
    site_name = config.get("site_name", "CivicBand")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
    <ShortName>{site_name}</ShortName>
    <Description>Search meeting minutes and agendas from {site_name}</Description>
    <Url type="text/html" template="https://{subdomain}.civic.band/meetings?_search={{searchTerms}}"/>
    <Url type="application/json" template="https://{subdomain}.civic.band/meetings.json?_search={{searchTerms}}"/>
    <Image height="16" width="16" type="image/x-icon">https://civic.band/favicon.ico</Image>
    <InputEncoding>UTF-8</InputEncoding>
    <OutputEncoding>UTF-8</OutputEncoding>
    <Contact>hello@civic.band</Contact>
    <LongName>{site_name} Civic Meeting Records</LongName>
    <Tags>civic government meetings minutes agendas {subdomain}</Tags>
    <Attribution>Data from {site_name} via CivicBand (https://civic.band)</Attribution>
</OpenSearchDescription>"""

    return Response.text(xml, content_type="application/opensearchdescription+xml")


@hookimpl
def register_routes():
    return [
        (r"^/opensearch\.xml$", opensearch_xml),
    ]
