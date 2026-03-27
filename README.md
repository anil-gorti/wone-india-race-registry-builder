# India Race Registry

> A scraper toolkit that builds a canonical historical race registry from India's five major endurance sports timing platforms — covering 2017 to present.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Playwright](https://img.shields.io/badge/powered%20by-Playwright-45ba4b)](https://playwright.dev/)

---

## What This Does

Indian endurance events — marathons, triathlons, trail runs — are distributed across five independent timing companies with no unified directory. This tool scrapes each platform to produce a single, structured CSV registry:

- Race name, date, city, and distance categories
- Participant / finisher counts
- Source timing company and API provenance URL

**Supported timing platforms:**

| Platform | URL | Architecture | Status |
|---|---|---|---|
| SportTimingSolutions | sportstimingsolutions.in | Vue.js SPA | API discovery required |
| iFinish | ifinish.in | React SPA | API discovery required |
| MySamay | mysamay.in | SPA (Bootstrap) | API discovery required |
| TimingIndia | timingindia.com | Static site → results on ifinish.in | Slug enumeration built-in |
| MyRaceIndia | myraceindia.com | SPA (JS-rendered) | API discovery required |

---

## Architecture

The scraper operates in three progressive modes:

```
[--discover]       Opens a headed browser. You interact with dropdowns.
                   Every XHR/fetch call matching race data prints to stdout.
                   Run once per site to find the backend endpoint pattern.

[--mode=direct]    Calls the discovered API endpoint directly per year.
                   No browser overhead. Full 2017–2025 run completes in ~2 min.

[--mode=playwright] Full headless browser scrape. Fallback when API is
                    authenticated or obfuscated. Slower but resilient.
```

TimingIndia is special: its results live on ifinish.in under known URL slugs. The scraper enumerates slug × year combinations via HTTP HEAD requests — no API setup required.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/anil-gorti/india-race-registry.git
cd india-race-registry

# 2. Install dependencies
pip install -r requirements.txt
playwight install chromium

# 3. Discover API endpoints (opens a visible browser — interact with dropdowns)
python scrapers/race_registry_scraper.py --discover

# 4. Fill in discovered API URLs at the top of race_registry_scraper.py
# See docs/api_discovery_guide.md for step-by-step instructions

# 5. Bulk fetch all years
python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025

# Output is in ./output/
```

---

## Three Scraping Modes

### `--discover` (run first)

Opens a visible browser. Interact with year/race dropdowns on the platform. Every API call is printed to stdout with the URL, method, and response shape. Run once per site to find the backend endpoint.

```bash
python scrapers/race_registry_scraper.py --discover
```

### `--mode=direct` (fast, after discovery)

Calls the backend API directly for each year. No browser overhead.

```bash
# All platforms, all years
python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025

# Single platform only
python scrapers/race_registry_scraper.py --mode=direct --site=timingindia --years=2017-2025
```

> **TimingIndia** works out of the box with no API setup — it enumerates known event slugs directly on ifinish.in.

### `--mode=playwright` (fallback)

Full browser scrape for sites where the API is authenticated or obfuscated. Slower but more resilient.

```bash
python scrapers/race_registry_scraper.py --mode=playwright --years=2017-2025
```

---

## Output Schema

Each row in the output CSV:

| Field | Description | Example |
|---|---|---|
| `race_name` | Official race name | Bengaluru Marathon 2024 |
| `race_date` | Race date | 2024-10-20 |
| `city` | City / venue | Bengaluru |
| `distances` | Distance categories offered | 5K, 10K, 21K, FM |
| `participant_count` | Total finishers / registrants | 4200 |
| `timing_company` | Source platform | STS |
| `source_url` | Provenance URL of the API call | https://... |

---

## Project Structure

```
india-race-registry/
├── README.md
├── requirements.txt
├── .gitignore
├── scrapers/
│   ├── race_registry_scraper.py  # Main scraper (all 5 platforms)
│   └── normalizer.py             # Event record normalization utilities
├── docs/
│   ├── api_discovery_guide.md    # How to find API endpoints via DevTools
│   ├── site_map.md               # Architecture notes per timing platform
│   └── data_schema.md            # Output schema documentation
├── tests/
│   └── test_normalizer.py        # Unit tests for normalize_events()
└── output/                       # Generated CSVs (gitignored)
    ├── race_registry_sts.csv
    ├── race_registry_ifinish.csv
    ├── race_registry_mysamay.csv
    ├── race_registry_timingindia.csv
    ├── race_registry_myraceindia.csv
    └── race_registry_combined.csv
```

---

## Deduplication

The combined registry may contain the same event from multiple timing companies (organizer switching vendors, or dual timing arrangements). The dedup pass handles this:

- **High confidence:** exact `race_name` match + same `year` → keep first occurrence
- **Probable:** fuzzy name match (>85% similarity) + same `city` + date within 7 days
- **Manual review:** everything else flagged for inspection

```bash
python scrapers/race_registry_scraper.py --dedup
```

Outputs `race_registry_combined_deduped.csv`.

---

## Adding More Timing Platforms

To extend the scraper to a new timing company, follow the pattern in `docs/site_map.md`:

1. Add `PLATFORM_EVENTS_API`, `PLATFORM_AUTH_HEADER`, `PLATFORM_YEAR_PARAM` constants
2. Add an entry to `SITE_CONFIGS` with `discover_urls`
3. Wire it into the `direct` and `playwright` mode dispatch blocks
4. Run `--discover` on the new site to find the endpoint
5. Add normalization key fallbacks in `scrapers/normalizer.py` if field names differ
6. Document the architecture in `docs/site_map.md`

---

## What Broke Along the Way

Iterating on this surfaced several real-world SPA scraping challenges:

| Problem | What happened | How it was resolved |
|---|---|---|
| SPAs fire XHR before DOM is ready | `networkidle` timeout too short on slow connections | Added `asyncio.sleep(3)` + scroll triggers after load |
| API responses use inconsistent field names | `event_name` vs `name` vs `EventName` vs `title` | Built `_first()` fallback key resolver in `normalizer.py` |
| TimingIndia has no public API | Results live on ifinish.in under opaque slugs | Enumerated known slug × year combinations via HTTP HEAD |
| Duplicate events across platforms | Same marathon timed by two companies in different years | Two-pass dedup: exact match then fuzzy name + city + date window |
| Auth-gated APIs block direct calls | Some platforms require a session cookie or bearer token | Playwright mode captures session state and replays interactions |

---

## Requirements

```
requests>=2.28.0
playwright>=1.40.0
pandas>=2.0.0        # optional, required for --dedup
```

---

## License

MIT
