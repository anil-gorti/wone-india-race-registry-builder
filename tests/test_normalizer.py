"""
tests/test_normalizer.py
========================
Unit tests for the normalize_events() and dedup_events() utilities.

Run:
  python -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Allow importing from scrapers/
sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapers.normalizer import normalize_events, dedup_events, _extract_items


# ─────────────────────────────────────────────────────────────────────────────
# normalize_events tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeEvents:

    def test_list_at_root(self):
        raw = [
            {"name": "Bengaluru Marathon 2024", "date": "2024-10-20", "city": "Bengaluru"},
            {"name": "Mumbai Half Marathon 2024", "date": "2024-01-15", "city": "Mumbai"},
        ]
        events = normalize_events(raw, source="STS", source_url="https://example.com/api")
        assert len(events) == 2
        assert events[0]["race_name"] == "Bengaluru Marathon 2024"
        assert events[0]["race_date"] == "2024-10-20"
        assert events[0]["timing_company"] == "STS"

    def test_nested_under_events_key(self):
        raw = {
            "status": "ok",
            "events": [
                {"event_name": "Hyderabad 10K 2023", "event_date": "2023-12-03"}
            ]
        }
        events = normalize_events(raw, source="iFinish", source_url="https://ifinish.in/api")
        assert len(events) == 1
        assert events[0]["race_name"] == "Hyderabad 10K 2023"
        assert events[0]["timing_company"] == "iFinish"

    def test_nested_under_data_key(self):
        raw = {
            "data": [
                {"title": "Pune Half Marathon", "start_date": "2024-02-18", "location": "Pune"}
            ]
        }
        events = normalize_events(raw, source="STS", source_url="https://example.com")
        assert len(events) == 1
        assert events[0]["race_name"] == "Pune Half Marathon"
        assert events[0]["city"] == "Pune"

    def test_single_event_dict(self):
        raw = {"event_name": "Chennai Trail Run", "race_date": "2024-03-10"}
        events = normalize_events(raw, source="MySamay", source_url="https://example.com")
        assert len(events) == 1
        assert events[0]["race_name"] == "Chennai Trail Run"

    def test_empty_response(self):
        assert normalize_events({}, source="STS", source_url="") == []
        assert normalize_events([], source="STS", source_url="") == []
        assert normalize_events(None, source="STS", source_url="") == []

    def test_skips_items_without_name(self):
        raw = [
            {"date": "2024-01-01", "city": "Delhi"},  # no name
            {"name": "Delhi Marathon", "date": "2024-01-01"},
        ]
        events = normalize_events(raw, source="STS", source_url="")
        assert len(events) == 1
        assert events[0]["race_name"] == "Delhi Marathon"

    def test_key_fallbacks_camelCase(self):
        raw = [{"eventName": "Jaipur Marathon", "eventDate": "2024-11-24"}]
        events = normalize_events(raw, source="iFinish", source_url="")
        assert events[0]["race_name"] == "Jaipur Marathon"
        assert events[0]["race_date"] == "2024-11-24"

    def test_key_fallbacks_PascalCase(self):
        raw = [{"EventName": "Kolkata Run", "EventDate": "2024-06-02", "City": "Kolkata"}]
        events = normalize_events(raw, source="STS", source_url="")
        assert events[0]["race_name"] == "Kolkata Run"
        assert events[0]["city"] == "Kolkata"

    def test_participant_count_extracted(self):
        raw = [{"name": "Goa Marathon", "total_runners": 3200}]
        events = normalize_events(raw, source="STS", source_url="")
        assert events[0]["participant_count"] == "3200"

    def test_distances_extracted(self):
        raw = [{"name": "Ahmedabad Marathon", "categories": "5K, 10K, 21K, FM"}]
        events = normalize_events(raw, source="STS", source_url="")
        assert events[0]["distances"] == "5K, 10K, 21K, FM"

    def test_source_url_preserved(self):
        raw = [{"name": "Test Race"}]
        url = "https://sportstimingsolutions.in/api/events?year=2024"
        events = normalize_events(raw, source="STS", source_url=url)
        assert events[0]["source_url"] == url


# ─────────────────────────────────────────────────────────────────────────────
# dedup_events tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDedupEvents:

    def test_removes_exact_duplicates(self):
        events = [
            {"race_name": "Bengaluru Marathon", "race_date": "2024-10-20", "timing_company": "STS"},
            {"race_name": "Bengaluru Marathon", "race_date": "2024-10-20", "timing_company": "STS"},
        ]
        unique, dups = dedup_events(events)
        assert len(unique) == 1
        assert len(dups) == 1

    def test_different_years_not_duplicates(self):
        events = [
            {"race_name": "Bengaluru Marathon", "race_date": "2024-10-20"},
            {"race_name": "Bengaluru Marathon", "race_date": "2023-10-15"},
        ]
        unique, dups = dedup_events(events)
        assert len(unique) == 2
        assert len(dups) == 0

    def test_case_insensitive_dedup(self):
        events = [
            {"race_name": "bengaluru marathon", "race_date": "2024-10-20"},
            {"race_name": "Bengaluru Marathon", "race_date": "2024-10-20"},
        ]
        unique, dups = dedup_events(events)
        assert len(unique) == 1

    def test_empty_input(self):
        unique, dups = dedup_events([])
        assert unique == []
        assert dups == []

    def test_preserves_order(self):
        events = [
            {"race_name": "Race A", "race_date": "2024-01-01"},
            {"race_name": "Race B", "race_date": "2024-02-01"},
            {"race_name": "Race C", "race_date": "2024-03-01"},
        ]
        unique, _ = dedup_events(events)
        assert [e["race_name"] for e in unique] == ["Race A", "Race B", "Race C"]


# ─────────────────────────────────────────────────────────────────────────────
# _extract_items tests
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractItems:

    def test_list_passthrough(self):
        data = [{"name": "A"}, {"name": "B"}]
        assert _extract_items(data) == data

    def test_extracts_from_events_key(self):
        data = {"events": [{"name": "A"}], "total": 1}
        assert _extract_items(data) == [{"name": "A"}]

    def test_extracts_from_data_key(self):
        data = {"data": [{"name": "A"}]}
        assert _extract_items(data) == [{"name": "A"}]

    def test_single_event_wrapped(self):
        data = {"name": "Solo Race", "date": "2024-01-01"}
        result = _extract_items(data)
        assert len(result) == 1
        assert result[0]["name"] == "Solo Race"

    def test_empty_returns_empty(self):
        assert _extract_items({}) == []
        assert _extract_items([]) == []
        assert _extract_items(None) == []
