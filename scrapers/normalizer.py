"""
normalizer.py
=============
Standalone event normalization utilities for the WONE race registry.

Extracted from race_registry_scraper.py so it can be imported by
other WONE pipeline components (profile engine, dedup, etc.)
"""

from typing import Any


# Output schema for all normalized events
SCHEMA = {
    "race_name":         str,   # Official race name
    "race_date":         str,   # ISO date string (YYYY-MM-DD) when available
    "city":              str,   # City / venue
    "distances":         str,   # Distance categories (5K, 10K, 21K, FM)
    "participant_count": str,   # Total finishers / registered
    "event_id":          str,   # Source platform's internal ID
    "timing_company":    str,   # STS | iFinish | MySamay | etc.
    "source_url":        str,   # API URL this record came from
}


def normalize_events(raw: Any, source: str, source_url: str) -> list[dict]:
    """
    Normalize any timing platform API response into standard WONE event records.

    Handles:
      - List at root:             [{"name": ...}, ...]
      - Nested under common keys: {"events": [...], "data": [...], ...}
      - Single event dict:        {"name": ..., "date": ...}

    Args:
        raw:        Parsed JSON response (dict or list)
        source:     Timing company identifier (e.g. "STS", "iFinish")
        source_url: URL the response came from

    Returns:
        List of normalized event dicts matching SCHEMA
    """
    items = _extract_items(raw)
    return [_normalize_item(item, source, source_url) for item in items if _is_event(item)]


def _extract_items(raw: Any) -> list:
    """Extract the list of event items from any response shape."""
    if isinstance(raw, list):
        return raw

    if isinstance(raw, dict):
        # Try common envelope keys
        for key in ["events", "data", "results", "races", "items", "list", "eventList", "Events", "Data"]:
            if key in raw and isinstance(raw[key], list):
                return raw[key]

        # Check if the dict itself looks like a single event
        if any(k in raw for k in ["name", "event_name", "race_name", "title", "EventName"]):
            return [raw]

    return []


def _is_event(item: Any) -> bool:
    """Return True if item has at least a name field (minimal valid event)."""
    if not isinstance(item, dict):
        return False
    name = _first(item, ["event_name", "name", "race_name", "title", "EventName", "eventName"])
    return bool(name and str(name).strip())


def _normalize_item(item: dict, source: str, source_url: str) -> dict:
    """Map raw item fields to WONE schema."""
    return {
        "race_name": _clean(_first(item, [
            "event_name", "name", "race_name", "title",
            "EventName", "eventName", "RaceName", "event"
        ])),
        "race_date": _clean(_first(item, [
            "race_date", "date", "event_date", "start_date",
            "EventDate", "eventDate", "RaceDate", "scheduled_date"
        ])),
        "city": _clean(_first(item, [
            "city", "location", "venue", "place",
            "City", "Location", "Venue", "Place"
        ])),
        "distances": _clean(_first(item, [
            "categories", "distances", "race_types",
            "Categories", "Distances", "race_categories"
        ])),
        "participant_count": _clean(_first(item, [
            "participant_count", "participants", "total_participants",
            "count", "total_runners", "finishers", "ParticipantCount"
        ])),
        "event_id": _clean(_first(item, [
            "id", "event_id", "race_id", "EventId", "Id"
        ])),
        "timing_company": source,
        "source_url": source_url,
    }


def _first(d: dict, keys: list) -> Any:
    """Return the first non-None, non-empty value from a list of dict keys."""
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip():
            return v
    return None


def _clean(value: Any) -> str:
    """Safely convert a value to a clean string."""
    if value is None:
        return ""
    return str(value).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Dedup utilities
# ─────────────────────────────────────────────────────────────────────────────

def dedup_events(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Deduplicate a list of normalized events.

    Strategy:
    1. Exact: normalized race_name + year -> keep first occurrence
    2. Returns (unique_events, duplicate_events) for audit trail

    Args:
        events: List of normalized event dicts

    Returns:
        (unique, duplicates)
    """
    seen: set[tuple] = set()
    unique: list[dict] = []
    duplicates: list[dict] = []

    for event in events:
        key = _dedup_key(event)
        if key in seen:
            duplicates.append(event)
        else:
            seen.add(key)
            unique.append(event)

    return unique, duplicates


def _dedup_key(event: dict) -> tuple:
    """Generate a deduplication key for an event."""
    name_norm = (
        event.get("race_name", "")
        .lower()
        .strip()
        .replace("  ", " ")
    )
    # Extract year from date string
    date_str = event.get("race_date", "")
    year = date_str[:4] if len(date_str) >= 4 else event.get("year", "")
    return (name_norm, str(year))
