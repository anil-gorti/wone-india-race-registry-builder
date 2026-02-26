# WONE Race Registry Scraper

Builds a historical race registry from India's endurance sports timing platforms.
Part of the [WONE](https://wone.in) coordination infrastructure for the Indian endurance sports ecosystem.

## What This Does

Scrapes race history (2017-present) from Indian timing companies to build a canonical race registry:
- Race name, date, city, distances
- Participant counts
- Source timing company

**Supported timing platforms:**
| Platform | URL | Architecture |
|---|---|---|
| SportTimingSolutions | sportstimingsolutions.in | Vue.js SPA |
| iFinish | ifinish.in | React SPA |

The registry feeds WONE's athlete profile engine — enabling retroactive verification of race results, club participation pattern discovery, and race organizer relationship mapping.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/YOUR_ORG/wone-race-registry.git
cd wone-race-registry

# 2. Install
pip install -r requirements.txt
playwright install chromium

# 3. Discover API endpoints (opens a browser — interact with dropdowns)
python scrapers/race_registry_scraper.py --discover

# 4. Fill in discovered API URLs at top of scraper file, then bulk fetch
python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025

# 5. Output is in ./output/
```

---

## Project Structure

```
wone-race-registry/
├── README.md
├── requirements.txt
├── .gitignore
├── scrapers/
│   ├── race_registry_scraper.py     # Main scraper (STS + iFinish)
│   └── normalizer.py                # Event record normalization utilities
├── docs/
│   ├── api_discovery_guide.md       # How to find API endpoints via DevTools
│   ├── site_map.md                  # Architecture notes per timing platform
│   └── data_schema.md               # Output schema documentation
├── tests/
│   └── test_normalizer.py           # Unit tests for normalize_events()
└── output/                          # Generated CSVs (gitignored)
    ├── race_registry_sts.csv
    ├── race_registry_ifinish.csv
    └── race_registry_combined.csv
```

---

## Three Modes

### `--discover` (run first)
Opens a visible browser. You interact with year/race dropdowns. Every API call is printed to stdout. Run once per site to find the backend endpoint pattern.

```bash
python scrapers/race_registry_scraper.py --discover
```

### `--mode=direct` (fast, after discovery)
Calls the API directly for each year. No browser overhead. 2017-2025 runs in under 2 minutes.

```bash
# After filling in STS_EVENTS_API and IFINISH_EVENTS_API in the scraper:
python scrapers/race_registry_scraper.py --mode=direct --years=2017-2025
```

### `--mode=playwright` (fallback)
Full browser scrape for sites where the API is authenticated or obfuscated. Slower but resilient.

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
| `participant_count` | Total finishers | 4200 |
| `timing_company` | Source platform | STS |
| `source_url` | URL of the API call | https://... |

---

## Adding More Timing Platforms

To add another Indian timing company (MySamay, TimingIndia, etc.):

1. Add a new section in `scrapers/race_registry_scraper.py` following the STS pattern
2. Run `--discover` on the new site
3. Add normalization handling in `scrapers/normalizer.py` if the response shape is unusual
4. Document the site architecture in `docs/site_map.md`

---

## Deduplication

The combined registry may contain duplicate events (same race timed by two companies in different years, or organizer switching vendors). Dedup logic:

- **High confidence:** exact `race_name` match + same `year`
- **Probable:** fuzzy name match (>85% similarity) + same `city` + date within 7 days
- **Manual review:** everything else

Run dedup pass after collecting all sources:
```bash
python scrapers/race_registry_scraper.py --dedup
```

---

## Context

This scraper is Phase 1 of WONE's data acquisition strategy:

- **Phase 1 (this repo):** Build historical race registry without organizer dependency, via scraping
- **Phase 2:** Club-triggered, athlete-facing workflows that embed in existing processes
- **Phase 3:** Organizers as direct data partners

The output feeds WONE's three-agent AI pipeline (Detective → Pattern Reader → Storyteller) for athlete profile generation.

---

## License

MIT
