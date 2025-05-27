from datasette import hookimpl
from datasette.utils.asgi import Response


async def robots_txt(datasette, request):
    disallow = []
    for database_name in datasette.databases:
        if database_name != "_internal":
            disallow.append(datasette.urls.database(database_name))
    lines = []
    user_agents_to_block = [
        "User-agent: Google-Extended",
        "User-agent: GPTBot",
        "User-agent: Applebot",
        "User-agent: Applebot-Extended",
        "User-Agent: ChatGPT-User",
        "User-Agent: CCBot",
        "User-agent: PerplexityBot",
        "User-agent: anthropic-ai",
        "User-agent: Claude-Web",
        "User-agent: ClaudeBot",
        "User-agent: Amazonbot",
        "User-Agent: FacebookBot",
        "User-agent: Omgilibot",
        "User-agent: Omgili",
        "User-agent: Diffbot",
        "User-agent: Bytespider",
        "User-agent: ImagesiftBot",
        "User-agent: cohere-ai",
        "User-agent: SplitSignalBot",
        "User-agent: SemrushBot",
        "User-agent: SemrushBot-OCOB",
        "User-agent: SemrushBot-FT",
        "User-agent: SemrushBot-SWA",
        "User-agent: Meta-ExternalFetcher",
        "User-agent: OAI-SearchBot",
        "User-agent: YouBot",
        "User-agent: Meta-ExternalAgent",
        "User-agent: Ai2Bot",
        "User-agent: Ai2Bot-Dolma",
    ]
    for user_agent in user_agents_to_block:
        lines += [user_agent]
        lines += ["Disallow: {}".format(item) for item in disallow]
        lines += ["\n"]
    return Response.text("\n".join(lines))


@hookimpl
def register_routes():
    return [
        (r"^/robots\.txt$", robots_txt),
    ]
