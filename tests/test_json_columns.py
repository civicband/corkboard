"""Tests for JSON column display plugin."""

import json

# Import the plugin module - need to add plugins to path
import sys
from pathlib import Path
from unittest.mock import MagicMock

import markupsafe

sys.path.insert(0, str(Path(__file__).parent.parent / "plugins"))

from json_columns import (
    _get_row_url,
    _is_row_detail_view,
    _parse_json,
    _render_entities_compact,
    _render_entities_full,
    _render_votes_compact,
    _render_votes_full,
    render_cell,
)


class TestIsRowDetailView:
    """Test row detail view detection."""

    def test_no_request_returns_false(self):
        assert _is_row_detail_view(None) is False

    def test_table_view_no_pks(self):
        request = MagicMock()
        request.url_vars = {"database": "meetings", "table": "minutes"}
        assert _is_row_detail_view(request) is False

    def test_row_detail_with_pks(self):
        request = MagicMock()
        request.url_vars = {"database": "meetings", "table": "minutes", "pks": "123"}
        assert _is_row_detail_view(request) is True

    def test_empty_url_vars(self):
        request = MagicMock()
        request.url_vars = {}
        assert _is_row_detail_view(request) is False

    def test_none_url_vars(self):
        request = MagicMock()
        request.url_vars = None
        assert _is_row_detail_view(request) is False


class TestParseJson:
    """Test JSON parsing helper."""

    def test_parse_valid_json_string(self):
        result = _parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_dict_passthrough(self):
        data = {"already": "parsed"}
        result = _parse_json(data)
        assert result == data

    def test_parse_none_returns_none(self):
        assert _parse_json(None) is None

    def test_parse_empty_string_returns_none(self):
        assert _parse_json("") is None

    def test_parse_invalid_json_returns_none(self):
        assert _parse_json("not valid json") is None

    def test_parse_complex_entities_json(self):
        entities = {
            "persons": [{"text": "John Doe", "confidence": 0.95}],
            "orgs": [{"text": "City Council", "confidence": 0.85}],
            "locations": [{"text": "City Hall", "confidence": 0.90}],
        }
        result = _parse_json(json.dumps(entities))
        assert result == entities


class TestRenderEntitiesCompact:
    """Test compact entity rendering."""

    def test_empty_data_returns_empty(self):
        assert _render_entities_compact(None) == ""
        assert _render_entities_compact({}) == ""

    def test_persons_only(self):
        data = {"persons": [{"text": "Alice"}, {"text": "Bob"}]}
        result = _render_entities_compact(data)
        assert "👤2" in result
        assert "json-col-compact" in result

    def test_orgs_only(self):
        data = {"orgs": [{"text": "City Council"}]}
        result = _render_entities_compact(data)
        assert "🏛1" in result

    def test_locations_only(self):
        data = {"locations": [{"text": "City Hall"}, {"text": "Library"}]}
        result = _render_entities_compact(data)
        assert "📍2" in result

    def test_all_entity_types(self):
        data = {
            "persons": [{"text": "Alice"}],
            "orgs": [{"text": "Council"}, {"text": "Board"}],
            "locations": [{"text": "Hall"}],
        }
        result = _render_entities_compact(data)
        assert "👤1" in result
        assert "🏛2" in result
        assert "📍1" in result

    def test_with_row_url(self):
        data = {"persons": [{"text": "Alice"}]}
        result = _render_entities_compact(data, row_url="/db/table/1")
        assert 'href="/db/table/1"' in result

    def test_empty_arrays_returns_empty(self):
        data = {"persons": [], "orgs": [], "locations": []}
        assert _render_entities_compact(data) == ""


class TestRenderEntitiesFull:
    """Test full entity rendering with chips."""

    def test_empty_data_returns_empty(self):
        assert _render_entities_full(None) == ""
        assert _render_entities_full({}) == ""

    def test_persons_rendered_as_chips(self):
        data = {"persons": [{"text": "Mary Knight", "confidence": 0.95}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "entity-chip person" in result
        assert "Mary Knight" in result
        assert "👤" in result

    def test_orgs_rendered_as_chips(self):
        data = {"orgs": [{"text": "Planning Commission", "confidence": 0.90}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "entity-chip org" in result
        assert "Planning Commission" in result
        assert "🏛" in result

    def test_locations_rendered_as_chips(self):
        data = {"locations": [{"text": "City Hall", "confidence": 0.85}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "entity-chip location" in result
        assert "City Hall" in result
        assert "📍" in result

    def test_low_confidence_adds_class(self):
        data = {"persons": [{"text": "Someone", "confidence": 0.5}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "low-confidence" in result

    def test_high_confidence_no_low_class(self):
        data = {"persons": [{"text": "Someone", "confidence": 0.9}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "low-confidence" not in result

    def test_chips_link_to_search(self):
        data = {"persons": [{"text": "John Doe", "confidence": 0.95}]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert 'href="/meetings/minutes?_search=John%20Doe"' in result

    def test_no_database_table_no_links(self):
        data = {"persons": [{"text": "John Doe", "confidence": 0.95}]}
        result = _render_entities_full(data)
        assert "<span" in result
        assert 'href="' not in result

    def test_string_entity_format(self):
        """Test handling entities as plain strings instead of dicts."""
        data = {"persons": ["Alice", "Bob"]}
        result = _render_entities_full(data, "meetings", "minutes")
        assert "Alice" in result
        assert "Bob" in result

    def test_html_escaping(self):
        """Test that entity text is properly escaped."""
        data = {
            "persons": [{"text": "<script>alert('xss')</script>", "confidence": 1.0}]
        }
        result = _render_entities_full(data, "meetings", "minutes")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestRenderVotesCompact:
    """Test compact vote rendering."""

    def test_none_data_returns_none(self):
        assert _render_votes_compact(None) is None

    def test_empty_votes_returns_dash(self):
        data = {"votes": []}
        result = _render_votes_compact(data)
        assert "—" in result
        assert "color: #999" in result

    def test_passed_unanimously(self):
        data = {"votes": [{"tally": {"ayes": 5, "nays": 0}, "result": "passed"}]}
        result = _render_votes_compact(data)
        assert "✅" in result
        assert "5-0" in result

    def test_passed_contested(self):
        data = {"votes": [{"tally": {"ayes": 4, "nays": 1}, "result": "passed"}]}
        result = _render_votes_compact(data)
        assert "⚠️" in result
        assert "4-1" in result

    def test_failed_vote(self):
        data = {"votes": [{"tally": {"ayes": 2, "nays": 3}, "result": "failed"}]}
        result = _render_votes_compact(data)
        assert "❌" in result
        assert "2-3" in result

    def test_multiple_votes(self):
        data = {
            "votes": [
                {"tally": {"ayes": 5, "nays": 0}, "result": "passed"},
                {"tally": {"ayes": 3, "nays": 2}, "result": "passed"},
            ]
        }
        result = _render_votes_compact(data)
        assert "✅5-0" in result
        assert "⚠️3-2" in result

    def test_with_row_url(self):
        data = {"votes": [{"tally": {"ayes": 5, "nays": 0}, "result": "passed"}]}
        result = _render_votes_compact(data, row_url="/db/table/1")
        assert 'href="/db/table/1"' in result

    def test_empty_votes_with_row_url(self):
        data = {"votes": []}
        result = _render_votes_compact(data, row_url="/db/table/1")
        assert 'href="/db/table/1"' in result
        assert "—" in result


class TestRenderVotesFull:
    """Test full vote rendering."""

    def test_none_data_returns_none(self):
        assert _render_votes_full(None) is None

    def test_empty_votes_returns_message(self):
        data = {"votes": []}
        result = _render_votes_full(data)
        assert "No votes recorded" in result

    def test_passed_vote_box(self):
        data = {
            "votes": [
                {
                    "tally": {"ayes": 5, "nays": 0, "abstain": 0, "absent": 0},
                    "result": "passed",
                    "motion_by": "Commissioner Smith",
                    "seconded_by": "Commissioner Jones",
                }
            ]
        }
        result = _render_votes_full(data)
        assert "vote-box passed" in result
        assert "✅" in result
        assert "Passed" in result
        assert "5-0" in result
        assert "Commissioner Smith" in result
        assert "Commissioner Jones" in result

    def test_contested_vote_box(self):
        data = {"votes": [{"tally": {"ayes": 4, "nays": 1}, "result": "passed"}]}
        result = _render_votes_full(data)
        assert "vote-box passed-contested" in result
        assert "⚠️" in result

    def test_failed_vote_box(self):
        data = {"votes": [{"tally": {"ayes": 2, "nays": 3}, "result": "failed"}]}
        result = _render_votes_full(data)
        assert "vote-box failed" in result
        assert "❌" in result
        assert "Failed" in result

    def test_abstain_shown(self):
        data = {
            "votes": [
                {"tally": {"ayes": 4, "nays": 0, "abstain": 1}, "result": "passed"}
            ]
        }
        result = _render_votes_full(data)
        assert "1 abstain" in result

    def test_absent_shown(self):
        data = {
            "votes": [
                {"tally": {"ayes": 4, "nays": 0, "absent": 2}, "result": "passed"}
            ]
        }
        result = _render_votes_full(data)
        assert "2 absent" in result

    def test_individual_votes_aye(self):
        data = {
            "votes": [
                {
                    "tally": {"ayes": 2, "nays": 0},
                    "result": "passed",
                    "individual_votes": [
                        {"name": "Smith", "vote": "aye"},
                        {"name": "Jones", "vote": "yes"},
                    ],
                }
            ]
        }
        result = _render_votes_full(data)
        assert "vote-aye" in result
        assert "✓ Smith" in result
        assert "✓ Jones" in result

    def test_individual_votes_nay(self):
        data = {
            "votes": [
                {
                    "tally": {"ayes": 1, "nays": 1},
                    "result": "failed",
                    "individual_votes": [{"name": "Smith", "vote": "nay"}],
                }
            ]
        }
        result = _render_votes_full(data)
        assert "vote-nay" in result
        assert "✗ Smith" in result

    def test_individual_votes_abstain(self):
        data = {
            "votes": [
                {
                    "tally": {"ayes": 1, "nays": 0, "abstain": 1},
                    "result": "passed",
                    "individual_votes": [{"name": "Smith", "vote": "abstain"}],
                }
            ]
        }
        result = _render_votes_full(data)
        assert "vote-abstain" in result
        assert "○ Smith" in result

    def test_null_motion_by_not_shown(self):
        data = {"votes": [{"tally": {"ayes": 5, "nays": 0}, "motion_by": "null"}]}
        result = _render_votes_full(data)
        assert "Motion:" not in result

    def test_html_escaping_motion_by(self):
        data = {
            "votes": [
                {
                    "tally": {"ayes": 5, "nays": 0},
                    "motion_by": "<script>alert('xss')</script>",
                }
            ]
        }
        result = _render_votes_full(data)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestGetRowUrl:
    """Test row URL building."""

    def test_with_id_column(self):
        row = {"id": 123, "title": "Meeting"}
        result = _get_row_url(row, "meetings", "minutes")
        assert result == "/meetings/minutes/123"

    def test_with_rowid_column(self):
        row = {"rowid": 456, "title": "Meeting"}
        result = _get_row_url(row, "meetings", "minutes")
        assert result == "/meetings/minutes/456"

    def test_with_pk_column(self):
        row = {"pk": 789, "title": "Meeting"}
        result = _get_row_url(row, "meetings", "minutes")
        assert result == "/meetings/minutes/789"

    def test_no_pk_column_returns_none(self):
        row = {"title": "Meeting", "date": "2024-01-01"}
        result = _get_row_url(row, "meetings", "minutes")
        assert result is None

    def test_none_pk_value_skipped(self):
        row = {"id": None, "rowid": 123}
        result = _get_row_url(row, "meetings", "minutes")
        assert result == "/meetings/minutes/123"

    def test_url_encoding(self):
        row = {"id": "abc def"}
        result = _get_row_url(row, "meetings", "minutes")
        assert result == "/meetings/minutes/abc%20def"


class TestRenderCell:
    """Test the main render_cell hook."""

    def test_wrong_column_returns_none(self):
        result = render_cell(
            row={},
            value="{}",
            column="other_column",
            table="minutes",
            database="meetings",
            datasette=None,
            request=None,
        )
        assert result is None

    def test_empty_value_returns_none(self):
        result = render_cell(
            row={},
            value=None,
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=None,
        )
        assert result is None

    def test_invalid_json_returns_none(self):
        result = render_cell(
            row={},
            value="not json",
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=None,
        )
        assert result is None

    def test_entities_json_renders_chips(self):
        value = json.dumps(
            {
                "persons": [{"text": "John Doe", "confidence": 0.95}],
                "orgs": [],
                "locations": [],
            }
        )
        request = MagicMock()
        request.url_vars = {"database": "meetings", "table": "minutes"}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "John Doe" in str(result)
        assert "entity-chip" in str(result)
        assert "View JSON" in str(result)

    def test_votes_json_renders_vote_display(self):
        value = json.dumps(
            {"votes": [{"tally": {"ayes": 5, "nays": 0}, "result": "passed"}]}
        )
        request = MagicMock()
        request.url_vars = {"database": "meetings", "table": "minutes"}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="votes_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "✅" in str(result)
        assert "5-0" in str(result)
        assert "View JSON" in str(result)

    def test_row_detail_uses_full_vote_view(self):
        value = json.dumps(
            {
                "votes": [
                    {
                        "tally": {"ayes": 5, "nays": 0},
                        "result": "passed",
                        "motion_by": "Commissioner Smith",
                    }
                ]
            }
        )
        request = MagicMock()
        request.url_vars = {"database": "meetings", "table": "minutes", "pks": "1"}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="votes_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        assert isinstance(result, markupsafe.Markup)
        assert "vote-box" in str(result)
        assert "Commissioner Smith" in str(result)

    def test_includes_css_styles(self):
        value = json.dumps({"persons": [{"text": "Alice", "confidence": 0.95}]})
        request = MagicMock()
        request.url_vars = {}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        assert "<style>" in str(result)
        assert ".entity-chip" in str(result)

    def test_includes_raw_json_disclosure(self):
        value = json.dumps({"persons": [{"text": "Alice", "confidence": 0.95}]})
        request = MagicMock()
        request.url_vars = {}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        assert "<details" in str(result)
        assert "View JSON" in str(result)
        assert "<pre>" in str(result)

    def test_empty_entities_returns_none(self):
        value = json.dumps({"persons": [], "orgs": [], "locations": []})
        request = MagicMock()
        request.url_vars = {}

        result = render_cell(
            row={"id": 1},
            value=value,
            column="entities_json",
            table="minutes",
            database="meetings",
            datasette=None,
            request=request,
        )

        # Empty entities should still return None
        assert result is None
