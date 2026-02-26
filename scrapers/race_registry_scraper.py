"""
WONE Race Registry Builder
===========================
Scrapes race history from Indian endurance sports timing platforms.

Supported:
  - SportTimingSolutions (sportstimingsolutions.in)
  - iFinish (ifinish.in)

Usage:
  # Step 1: Install deps
  pip install -r requirements.txt
  playwright install chromium

  # Step 2: Discover API endpoints (run once — opens visible browser)
  python scrapers/race_registry_scraper.py --discover

  # Step 3: Fill in API URLs below, then bulk fetch all years
  python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025

  # Fallback: full Playwright DOM scrape if API is locked down
  python scrapers/race_registry_scraper.py --mode=playwright --years=2017-2025

  # Dedup combined output
  python scrapers/race_registry_scraper.py --dedup
"""

import asyncio
import json
import csv
import sys
import argparse
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# Fill these in after running --discover mode.
# See docs/api_discovery_guide.md for instructions.
# ─────────────────────────────────────────────────────────────────────────────
STS_EVENTS_API       = None   # e.g. "https://sportstimingsolutions.in/api/events"
STS_AUTH_HEADER      = None   # e.g. {"Authorization": "Bearer xyz"} if needed
STS_YEAR_PARAM       = "year" # query param name for year filter

IFINISH_EVENTS_API   = None   # e.g. "https://ifinish.in/api/v1/events"
IFINISH_AUTH_HEADER  = None
IFINISH_YEAR_PARAM   = "year"
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_YEARS = list(range(2017, 2026))
OUTPUT_DIR    = Path("./output")

SITE_CONFIGS = {
    "STS": {
        "label": "SportTimingSolutions",
        "discover_urls": [
            "https://sportstimingsolutions.in/results",
        ],
        "api_url_var": "STS_EVENTS_API",
    },
    "iFinish": {
        "label": "iFinish",
        "discover_urls": [
            "https://ifinish.in/eventresult",
            "https://ifinish.in",
        ],
        "api_url_var": "IFINISH_EVENTS_API",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# DISCOVER MODE
# Opens a visible browser. Interact with year/race dropdowns.
# Every API call with event-like data prints to stdout.
# ══════════════════════════════════════════════════════════════════════════════

async def discover_apis():
    if async_playwright is None:
        print("ERROR: playwright not installed.")
        print("  Run: pip install playwright && playwright install chromium")
        return

    async with async_playwright() as pw:
        print("Launching browser in headed mode...")
        browser = await pw.chromium.launch(headless=False)

        for site_key, config in SITE_CONFIGS.items():
            for url in config["discover_urls"]:
                print(f"\n{'='*60}")
                print(f"Site:  {config['label']}")
                print(f"URL:   {url}")
                print(f"Config var to fill: {config['api_url_var']}")
                print("=" * 60)
                print("ACTION: Interact with the year/race dropdowns on the page.")
                print("        API calls will print below as they fire.")
                print("        Press ENTER when done to move to next URL.\n")

                page = await browser.new_page()

                async def on_response(response, site=site_key):
                    if response.request.resource_type not in ("xhr", "fetch"):
                        return
                    try:
                        body = await response.json()
                        body_str = json.dumps(body).lower()
                        keywords = ["event", "race", "marathon", "run", "result", "timing"]
                        if any(k in body_str for k in keywords):
                            method = response.request.method
                            req_url = response.url
                            post_data = response.request.post_data

                            print(f"\n  [{site}] API CALL DETECTED")
                            print(f"  Method:   {method}")
                            print(f"  URL:      {req_url}")
                            if post_data:
                                print(f"  Body:     {post_data[:300]}")
                            print(f"  Response: {str(body)[:400]}")
                            print(f"  *** Copy this URL into {config['api_url_var']} ***\n")
                    except Exception:
                        pass

                page.on("response", on_response)

                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    print(f"  Load error (non-fatal): {e}")

                # Non-blocking wait for user input
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, input, "\nPress ENTER to continue to next URL...")
                await page.close()

        await browser.close()

    print("\n" + "=" * 60)
    print("DISCOVERY COMPLETE")
    print("Next step: fill in the API URL constants at the top of this file.")
    print("Then run: python scrapers/race_registry_scraper.py --mode=direct")


# ══════════════════════════════════════════════════════════════════════════════
# DIRECT MODE
# Calls the backend API for each year once URLs are known.
# Fast — no browser overhead. 2017-2025 typically completes in <2 min.
# ══════════════════════════════════════════════════════════════════════════════

def fetch_direct(api_url: str, year_param: str, years: list,
                 auth_header: dict = None, source: str = "") -> list:
    if requests is None:
        print("ERROR: requests not installed. Run: pip install requests")
        return []

    base_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
    }
    if auth_header:
        base_headers.update(auth_header)

    all_events = []

    for year in years:
        try:
            resp = requests.get(
                api_url,
                params={year_param: year},
                headers=base_headers,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                events = normalize_events(
                    data,
                    source=source,
                    source_url=f"{api_url}?{year_param}={year}"
                )
                for e in events:
                    if not e.get("year"):
                        e["year"] = year
                all_events.extend(events)
                print(f"  [{source}] {year}: {len(events)} events")
            else:
                print(f"  [{source}] {year}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"  [{source}] {year}: ERROR - {e}")

    return all_events


# ══════════════════════════════════════════════════════════════════════════════
# PLAYWRIGHT MODE
# Full browser scrape. Fallback when API is authenticated or obfuscated.
# ══════════════════════════════════════════════════════════════════════════════

async def scrape_playwright(site_key: str, urls: list, years: list) -> list:
    if async_playwright is None:
        print("ERROR: playwright not installed.")
        return []

    all_events = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        event_buffer = []

        async def on_response(response):
            if response.request.resource_type not in ("xhr", "fetch"):
                return
            try:
                body = await response.json()
                body_str = json.dumps(body).lower()
                if any(k in body_str for k in ["event", "race", "marathon", "result"]):
                    event_buffer.append({
                        "url": response.url,
                        "body": body,
                        "method": response.request.method,
                    })
            except Exception:
                pass

        page.on("response", on_response)

        for url in urls:
            print(f"  [{site_key}] Loading {url}...")
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(3)

                # Scroll to trigger lazy-loaded content
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1)

                # Try interacting with year dropdowns
                selects = await page.query_selector_all("select")
                for sel in selects:
                    options = await sel.query_selector_all("option")
                    for opt in options:
                        val = await opt.get_attribute("value")
                        text = await opt.text_content()
                        if text and text.strip().isdigit():
                            year = int(text.strip())
                            if year in years:
                                await sel.select_option(value=val)
                                await asyncio.sleep(2)

            except Exception as e:
                print(f"    Error: {e}")

        print(f"\n  [{site_key}] API responses captured: {len(event_buffer)}")
        for item in event_buffer:
            print(f"    {item['method']} {item['url']}")
            events = normalize_events(item["body"], source=site_key, source_url=item["url"])
            all_events.extend(events)

        # DOM fallback: extract option elements as race names
        try:
            options = await page.query_selector_all("option")
            for opt in options:
                text = await opt.text_content()
                val = await opt.get_attribute("value")
                text = text.strip() if text else ""
                # Skip year/number options; keep race name options
                if text and len(text) > 5 and not text.isdigit():
                    all_events.append({
                        "race_name": text,
                        "race_date": str(val) if val else "",
                        "city": "",
                        "distances": "",
                        "participant_count": "",
                        "timing_company": site_key,
                        "source_url": page.url,
                    })
        except Exception:
            pass

        await browser.close()

    # Deduplicate within single site
    seen = set()
    unique = []
    for e in all_events:
        key = e.get("race_name", "").lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(e)

    print(f"  [{site_key}] Total unique events: {len(unique)}")
    return unique


# ══════════════════════════════════════════════════════════════════════════════
# NORMALIZER
# Flattens any API response shape into standard WONE event records.
# ══════════════════════════════════════════════════════════════════════════════

def normalize_events(raw, source: str, source_url: str) -> list:
    """
    Accepts any API response shape and returns a list of normalized event dicts.

    Handles:
      - List at root: [{"name": ...}, ...]
      - Nested under common keys: {"events": [...], "data": [...], ...}
      - Single event dict

    Output schema:
      race_name, race_date, city, distances, participant_count,
      timing_company, source_url
    """
    items = []

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        for key in ["events", "data", "results", "races", "items", "list", "eventList", "Events"]:
            if key in raw and isinstance(raw[key], list):
                items = raw[key]
                break
        if not items and any(k in raw for k in ["name", "event_name", "race_name", "title"]):
            items = [raw]  # Single event dict

    events = []
    for item in items:
        if not isinstance(item, dict):
            continue

        # Field extraction with key fallbacks (camelCase, snake_case, PascalCase)
        name = _first(item, [
            "event_name", "name", "race_name", "title",
            "EventName", "eventName", "RaceName", "event"
        ])
        date = _first(item, [
            "race_date", "date", "event_date", "start_date",
            "EventDate", "eventDate", "RaceDate", "scheduled_date"
        ])
        city = _first(item, [
            "city", "location", "venue", "place", "City", "Location", "Venue"
        ])
        participants = _first(item, [
            "participant_count", "participants", "total_participants",
            "count", "total_runners", "finishers", "ParticipantCount"
        ])
        distances = _first(item, [
            "categories", "distances", "race_types", "events",
            "Categories", "Distances", "race_categories"
        ])
        event_id = _first(item, ["id", "event_id", "race_id", "EventId"])

        if name and str(name).strip():
            events.append({
                "race_name":        str(name).strip(),
                "race_date":        str(date).strip() if date else "",
                "city":             str(city).strip() if city else "",
                "distances":        str(distances).strip() if distances else "",
                "participant_count": str(participants).strip() if participants else "",
                "event_id":         str(event_id).strip() if event_id else "",
                "timing_company":   source,
                "source_url":       source_url,
            })

    return events


def _first(d: dict, keys: list):
    """Return the first non-None, non-empty value from a list of dict keys."""
    for k in keys:
        v = d.get(k)
        if v is not None and str(v).strip():
            return v
    return None


# ══════════════════════════════════════════════════════════════════════════════
# DEDUP
# ══════════════════════════════════════════════════════════════════════════════

def dedup_registry(events: list) -> list:
    """
    Removes duplicates from combined registry.

    Strategy:
    1. Exact match: race_name (normalized) + year -> keep first occurrence
    2. Flag probable duplicates for manual review (different sources, same name + year)
    """
    if not PANDAS_AVAILABLE:
        print("[Dedup] pandas not available. Skipping dedup.")
        return events

    df = pd.DataFrame(events)
    if df.empty:
        return events

    # Normalize race_name for comparison
    df["_name_norm"] = (
        df["race_name"]
        .str.lower()
        .str.strip()
        .str.replace(r'\s+', ' ', regex=True)
        .str.replace(r'[^\w\s]', '', regex=True)
    )

    # Extract year from race_date if not already present
    if "year" not in df.columns:
        df["year"] = pd.to_datetime(df["race_date"], errors="coerce").dt.year

    # Mark duplicates (keep first)
    df["_is_dup"] = df.duplicated(subset=["_name_norm", "year"], keep="first")

    dups = df[df["_is_dup"]]
    if not dups.empty:
        print(f"[Dedup] Removed {len(dups)} duplicates:")
        for _, row in dups.iterrows():
            print(f"  - {row['race_name']} ({row.get('year', '?')}) [{row['timing_company']}]")

    clean = df[~df["_is_dup"]].drop(columns=["_name_norm", "_is_dup"]).to_dict("records")
    print(f"[Dedup] {len(events)} → {len(clean)} events after dedup")
    return clean


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════════

FIELDNAMES = [
    "race_name", "race_date", "city", "distances",
    "participant_count", "timing_company", "source_url", "event_id"
]

def export_csv(events: list, filename: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / filename

    if not events:
        print(f"[Export] No data for {filename}")
        return path

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)

    print(f"[Export] {len(events):,} events → {path}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="WONE Race Registry Builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrapers/race_registry_scraper.py --discover
  python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025
  python scrapers/race_registry_scraper.py --mode=playwright --years=2023-2025
  python scrapers/race_registry_scraper.py --dedup
        """
    )
    parser.add_argument(
        "--mode",
        choices=["discover", "direct", "playwright"],
        default="discover",
        help="discover=find API endpoints | direct=call API | playwright=full browser scrape"
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Shorthand for --mode=discover"
    )
    parser.add_argument(
        "--dedup",
        action="store_true",
        help="Run dedup pass on existing combined CSV"
    )
    parser.add_argument(
        "--years",
        type=str,
        default="2017-2025",
        help="Year range (e.g. 2017-2025) or single year (e.g. 2024)"
    )
    args = parser.parse_args()

    # Determine mode
    mode = "discover" if args.discover else args.mode

    # Parse year range
    if "-" in args.years:
        start, end = args.years.split("-")
        years = list(range(int(start), int(end) + 1))
    else:
        years = [int(args.years)]

    print(f"\nWONE Race Registry Builder")
    print(f"Mode:  {mode}")
    print(f"Years: {years[0]}–{years[-1]}")
    print("=" * 60 + "\n")

    # ── Dedup only ─────────────────────────────────────────────────────────
    if args.dedup:
        combined_path = OUTPUT_DIR / "race_registry_combined.csv"
        if not combined_path.exists():
            print(f"ERROR: {combined_path} not found. Run --mode=direct first.")
            return
        if not PANDAS_AVAILABLE:
            print("ERROR: pandas required for dedup. Run: pip install pandas")
            return
        df = pd.read_csv(combined_path)
        events = df.to_dict("records")
        clean = dedup_registry(events)
        export_csv(clean, "race_registry_combined_deduped.csv")
        return

    # ── Discovery mode ─────────────────────────────────────────────────────
    if mode == "discover":
        await discover_apis()
        return

    # ── Direct mode ────────────────────────────────────────────────────────
    if mode == "direct":
        all_sts, all_ifinish = [], []

        if STS_EVENTS_API:
            print("Fetching STS events (direct API)...")
            all_sts = fetch_direct(
                STS_EVENTS_API, STS_YEAR_PARAM, years,
                auth_header=STS_AUTH_HEADER, source="STS"
            )
        else:
            print("STS_EVENTS_API is not set.")
            print("Run --discover first, then fill in the constant at top of this file.\n")

        if IFINISH_EVENTS_API:
            print("\nFetching iFinish events (direct API)...")
            all_ifinish = fetch_direct(
                IFINISH_EVENTS_API, IFINISH_YEAR_PARAM, years,
                auth_header=IFINISH_AUTH_HEADER, source="iFinish"
            )
        else:
            print("IFINISH_EVENTS_API is not set.")
            print("Run --discover first, then fill in the constant at top of this file.\n")

        export_csv(all_sts, "race_registry_sts.csv")
        export_csv(all_ifinish, "race_registry_ifinish.csv")
        export_csv(all_sts + all_ifinish, "race_registry_combined.csv")

    # ── Playwright mode ────────────────────────────────────────────────────
    elif mode == "playwright":
        sts_events = await scrape_playwright(
            "STS",
            SITE_CONFIGS["STS"]["discover_urls"],
            years
        )
        ifinish_events = await scrape_playwright(
            "iFinish",
            SITE_CONFIGS["iFinish"]["discover_urls"],
            years
        )
        export_csv(sts_events, "race_registry_sts.csv")
        export_csv(ifinish_events, "race_registry_ifinish.csv")
        export_csv(sts_events + ifinish_events, "race_registry_combined.csv")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
