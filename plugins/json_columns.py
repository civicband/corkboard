"""
JSON Column Display Plugin

Renders entities_json and votes_json columns with rich HTML formatting:
- Table view: Compact summary with counts/icons
- Row detail view: Full display with chips and vote boxes
"""

import json
from urllib.parse import quote

import markupsafe
from datasette import hookimpl

# CSS styles - injected once per column type per page via data attribute check
STYLES = """
<style>
.json-col-compact {
    font-size: 1.1em;
    white-space: nowrap;
    cursor: pointer;
}
.json-col-compact:hover {
    background: #f0f0f0;
    border-radius: 4px;
}
.json-col-compact a {
    text-decoration: none;
    color: inherit;
    display: block;
    padding: 0.25em 0.5em;
}
.json-col-compact a:hover {
    text-decoration: none;
}
.entity-section {
    display: block;
    margin-bottom: 0.3em;
    max-width: 350px;
}
.entity-section-label {
    font-weight: 600;
    font-size: 0.8em;
    color: #666;
    margin-right: 0.25em;
}
.entity-chips {
    display: inline;
}
.entity-chip {
    display: inline-block;
    padding: 0.15em 0.4em;
    border-radius: 3px;
    font-size: 0.8em;
    background: #e8f4f8;
    border: 1px solid #b8d4e3;
    margin-right: 0.2em;
    margin-bottom: 0.15em;
    text-decoration: none;
    color: inherit;
}
a.entity-chip:hover {
    filter: brightness(0.95);
    text-decoration: none;
}
.entity-chip.person {
    background: #e8f4e8;
    border-color: #b8d4b8;
}
.entity-chip.org {
    background: #f4e8f4;
    border-color: #d4b8d4;
}
.entity-chip.location {
    background: #f4f0e8;
    border-color: #d4c8b8;
}
.entity-chip.low-confidence {
    opacity: 0.6;
}
.vote-box {
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 0.75em;
    margin-bottom: 0.5em;
    background: #fafafa;
    max-width: 400px;
}
.vote-box.passed {
    border-left: 4px solid #28a745;
}
.vote-box.passed-contested {
    border-left: 4px solid #ffc107;
}
.vote-box.failed {
    border-left: 4px solid #dc3545;
}
.vote-header {
    font-weight: 600;
    font-size: 1.1em;
    margin-bottom: 0.5em;
}
.vote-detail {
    font-size: 0.9em;
    color: #555;
    margin: 0.2em 0;
}
.vote-individual {
    margin-top: 0.5em;
    padding-top: 0.5em;
    border-top: 1px solid #eee;
}
.vote-aye {
    color: #28a745;
}
.vote-nay {
    color: #dc3545;
}
.vote-abstain {
    color: #6c757d;
}
.json-raw {
    margin-top: 0.5em;
}
.json-raw summary {
    font-size: 0.75em;
    color: #888;
    cursor: pointer;
    user-select: none;
}
.json-raw summary:hover {
    color: #555;
}
.json-raw pre {
    font-size: 0.7em;
    background: #f5f5f5;
    padding: 0.5em;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 200px;
    margin-top: 0.25em;
}
</style>
"""


def _is_row_detail_view(request):
    """Check if we're on a row detail page vs table listing."""
    if not request:
        return False
    # Row detail URLs: /database/table/row_id
    # Table URLs: /database/table or /database/table?...
    path = request.url_vars
    # In Datasette, row detail pages have 'pks' in url_vars
    return "pks" in path if path else False


def _parse_json(value):
    """Safely parse JSON value."""
    if not value:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def _render_entities_compact(data, row_url=None):
    """Render compact entity summary for table view."""
    if not data:
        return ""

    persons = data.get("persons", [])
    orgs = data.get("orgs", [])
    locations = data.get("locations", [])

    parts = []
    if persons:
        parts.append(f"👤{len(persons)}")
    if orgs:
        parts.append(f"🏛{len(orgs)}")
    if locations:
        parts.append(f"📍{len(locations)}")

    if not parts:
        return ""

    content = " ".join(parts)
    if row_url:
        return (
            f'<span class="json-col-compact"><a href="{row_url}">{content}</a></span>'
        )
    return f'<span class="json-col-compact">{content}</span>'


def _render_entities_full(data, database=None, table=None):
    """Render full entity display with inline chips that link to search."""
    if not data:
        return ""

    html_parts = []
    base_url = f"/{database}/{table}" if database and table else ""

    # People
    persons = data.get("persons", [])
    if persons:
        chips = []
        for p in persons:
            text = p.get("text", "") if isinstance(p, dict) else str(p)
            confidence = p.get("confidence", 1.0) if isinstance(p, dict) else 1.0
            css_class = "entity-chip person"
            if confidence < 0.8:
                css_class += " low-confidence"
            search_url = f"{base_url}?_search={quote(text)}" if base_url else ""
            if search_url:
                chips.append(
                    f'<a href="{search_url}" class="{css_class}">'
                    f"{markupsafe.escape(text)}</a>"
                )
            else:
                chips.append(
                    f'<span class="{css_class}">{markupsafe.escape(text)}</span>'
                )
        html_parts.append(
            f'<div class="entity-section">'
            f'<span class="entity-section-label">👤</span>'
            f'<span class="entity-chips">{"".join(chips)}</span>'
            f"</div>"
        )

    # Organizations
    orgs = data.get("orgs", [])
    if orgs:
        chips = []
        for o in orgs:
            text = o.get("text", "") if isinstance(o, dict) else str(o)
            confidence = o.get("confidence", 1.0) if isinstance(o, dict) else 1.0
            css_class = "entity-chip org"
            if confidence < 0.8:
                css_class += " low-confidence"
            search_url = f"{base_url}?_search={quote(text)}" if base_url else ""
            if search_url:
                chips.append(
                    f'<a href="{search_url}" class="{css_class}">'
                    f"{markupsafe.escape(text)}</a>"
                )
            else:
                chips.append(
                    f'<span class="{css_class}">{markupsafe.escape(text)}</span>'
                )
        html_parts.append(
            f'<div class="entity-section">'
            f'<span class="entity-section-label">🏛</span>'
            f'<span class="entity-chips">{"".join(chips)}</span>'
            f"</div>"
        )

    # Locations
    locations = data.get("locations", [])
    if locations:
        chips = []
        for loc in locations:
            text = loc.get("text", "") if isinstance(loc, dict) else str(loc)
            confidence = loc.get("confidence", 1.0) if isinstance(loc, dict) else 1.0
            css_class = "entity-chip location"
            if confidence < 0.8:
                css_class += " low-confidence"
            search_url = f"{base_url}?_search={quote(text)}" if base_url else ""
            if search_url:
                chips.append(
                    f'<a href="{search_url}" class="{css_class}">'
                    f"{markupsafe.escape(text)}</a>"
                )
            else:
                chips.append(
                    f'<span class="{css_class}">{markupsafe.escape(text)}</span>'
                )
        html_parts.append(
            f'<div class="entity-section">'
            f'<span class="entity-section-label">📍</span>'
            f'<span class="entity-chips">{"".join(chips)}</span>'
            f"</div>"
        )

    if not html_parts:
        return ""

    return "".join(html_parts)


def _render_votes_compact(data, row_url=None):
    """Render compact vote summary for table view."""
    if not data:
        return None  # Return None to hide column entirely

    votes = data.get("votes", [])
    if not votes:
        if row_url:
            return f'<span class="json-col-compact" style="color: #999;"><a href="{row_url}" style="color: #999;">—</a></span>'
        return '<span class="json-col-compact" style="color: #999;">—</span>'

    parts = []
    for vote in votes:
        tally = vote.get("tally", {})
        ayes = tally.get("ayes", 0) or 0
        nays = tally.get("nays", 0) or 0
        result = vote.get("result", "").lower()

        if result == "failed" or nays > ayes:
            emoji = "❌"
        elif nays > 0:
            emoji = "⚠️"
        else:
            emoji = "✅"

        parts.append(f"{emoji}{ayes}-{nays}")

    content = " ".join(parts)
    if row_url:
        return (
            f'<span class="json-col-compact"><a href="{row_url}">{content}</a></span>'
        )
    return f'<span class="json-col-compact">{content}</span>'


def _render_votes_full(data):
    """Render full vote display for row detail view."""
    if not data:
        return None

    votes = data.get("votes", [])
    if not votes:
        return '<span style="color: #999; font-style: italic;">No votes recorded</span>'

    html_parts = []

    for vote in votes:
        tally = vote.get("tally", {})
        ayes = tally.get("ayes", 0) or 0
        nays = tally.get("nays", 0) or 0
        abstain = tally.get("abstain", 0) or 0
        absent = tally.get("absent", 0) or 0
        result = vote.get("result", "").lower()
        motion_by = vote.get("motion_by")
        seconded_by = vote.get("seconded_by")
        individual_votes = vote.get("individual_votes", [])

        # Determine status and emoji
        if result == "failed" or nays > ayes:
            emoji = "❌"
            status = "Failed"
            box_class = "vote-box failed"
        elif nays > 0:
            emoji = "⚠️"
            status = "Passed"
            box_class = "vote-box passed-contested"
        else:
            emoji = "✅"
            status = "Passed"
            box_class = "vote-box passed"

        # Build tally string
        tally_str = f"{ayes}-{nays}"
        if abstain:
            tally_str += f" ({abstain} abstain)"
        if absent:
            tally_str += f" ({absent} absent)"

        # Header
        header = f"{emoji} {status} {tally_str}"

        # Details
        details = []
        if motion_by and motion_by not in ("null", "by"):
            details.append(
                f'<div class="vote-detail">Motion: {markupsafe.escape(motion_by)}</div>'
            )
        if seconded_by and seconded_by not in ("null", "by"):
            details.append(
                f'<div class="vote-detail">Second: {markupsafe.escape(seconded_by)}</div>'
            )

        # Individual votes
        individual_html = ""
        if individual_votes:
            vote_parts = []
            for iv in individual_votes:
                name = iv.get("name", "Unknown")
                v = iv.get("vote", "").lower()
                if v in ("aye", "yes", "yea"):
                    vote_parts.append(
                        f'<span class="vote-aye">✓ {markupsafe.escape(name)}</span>'
                    )
                elif v in ("nay", "no"):
                    vote_parts.append(
                        f'<span class="vote-nay">✗ {markupsafe.escape(name)}</span>'
                    )
                elif v in ("abstain", "present"):
                    vote_parts.append(
                        f'<span class="vote-abstain">○ {markupsafe.escape(name)}</span>'
                    )
            if vote_parts:
                individual_html = (
                    f'<div class="vote-individual">{" &nbsp; ".join(vote_parts)}</div>'
                )

        html_parts.append(f'''
            <div class="{box_class}">
                <div class="vote-header">{header}</div>
                {"".join(details)}
                {individual_html}
            </div>
        ''')

    return "".join(html_parts)


def _get_row_url(row, database, table):
    """Build URL to the row detail page."""
    # Try common primary key column names
    pk_value = None
    for pk_col in ("id", "rowid", "pk", "_rowid"):
        try:
            pk_value = row[pk_col]
            if pk_value is not None:
                break
        except (KeyError, TypeError):
            continue

    if pk_value is None:
        return None

    # URL-encode the primary key value
    return f"/{database}/{table}/{quote(str(pk_value))}"


@hookimpl
def render_cell(row, value, column, table, database, datasette, request):
    """Render entities_json and votes_json columns with rich formatting."""
    if column not in ("entities_json", "votes_json"):
        return None

    if not value:
        return None

    data = _parse_json(value)
    if not data:
        return None

    is_detail = _is_row_detail_view(request)

    # Build row URL for compact view links
    row_url = None if is_detail else _get_row_url(row, database, table)

    if column == "entities_json":
        # Always use full chip view for entities with search links
        html = _render_entities_full(data, database, table)
    elif column == "votes_json":
        html = (
            _render_votes_full(data)
            if is_detail
            else _render_votes_compact(data, row_url)
        )
    else:
        return None

    if not html:
        return None

    # Add collapsible raw JSON for power users
    raw_json = json.dumps(data, indent=2)
    raw_html = (
        f'<details class="json-raw">'
        f"<summary>View JSON</summary>"
        f"<pre>{markupsafe.escape(raw_json)}</pre>"
        f"</details>"
    )

    # Include styles with each render - browser deduplicates identical style blocks
    return markupsafe.Markup(STYLES + html + raw_html)
