# Site Map: Indian Timing Platforms

Architecture notes and scraping strategy per timing company.
Updated as new platforms are added.

---

## 1. SportTimingSolutions (STS)

| Attribute | Details |
|---|---|
| URL | https://sportstimingsolutions.in |
| Results page | /results |
| Architecture | Vue.js SPA (built by Acetrot) |
| Backend | Likely Laravel or CodeIgniter REST API |
| Data access | XHR/fetch API calls from browser |
| Year filter | Dropdown on /results page (custom Vue component) |
| Race filter | Second dropdown, populated after year selection |
| Auth | Unknown - possibly unauthenticated |
| Rate limiting | "Too Many Requests" message observed |
| Historical depth | Unknown - use `--discover` to check oldest available year |

**Scraping approach:**
1. Run `--discover` mode and click year dropdown
2. Capture the API call that fires (e.g. `GET /api/events?year=2024`)
3. Fill `STS_EVENTS_API` in scraper, run `--mode=direct`

**Known endpoint patterns (to verify):**
```
GET /api/events?year=YYYY
GET /api/v1/event/list?year=YYYY
POST /api/get-events  {"year": YYYY}
```

**Notes:**
- STS also has a "Runner Profile" feature where athletes claim results
- Their backend has a structured event + participant graph
- Consider emailing them for a data partnership before full scraping

---

## 2. iFinish

| Attribute | Details |
|---|---|
| URL | https://ifinish.in |
| Results page | /eventresult |
| Calendar page | / (homepage has marathon calendar) |
| Architecture | React SPA |
| Backend | Unknown - likely Node.js or Python |
| Data access | fetch API calls from browser |
| Year filter | Unknown - check via `--discover` |
| Auth | Unknown |
| Historical depth | Launched 2011 |

**Scraping approach:**
1. Run `--discover` on both `/eventresult` and `/` (homepage)
2. Homepage calendar may expose a more convenient events API
3. Fill `IFINISH_EVENTS_API` in scraper, run `--mode=direct`

**Notes:**
- iFinish also handles event registration (not just timing)
- Has a blog with event announcements: ifinishevents.blogspot.com
- Partners with "Timing Technologies" for some events

---

## 3. MySamay

| Attribute | Details |
|---|---|
| URL | https://mysamay.in |
| Architecture | SPA (JS-rendered) — Bootstrap + custom CSS, dark theme |
| Analytics | Google Tag Manager (GTM-MX2G4NTP), Facebook Pixel |
| Results page | /results |
| Events page | /events |
| Data access | Dynamic — XHR/fetch calls from browser (not visible in static HTML) |
| Year filter | Unknown — check via `--discover` |
| Auth | Unknown |
| Status | Config vars added; API endpoint pending `--discover` |

**Scraping approach:**
1. Run `--discover` mode — browser opens mysamay.in/results and mysamay.in/events
2. Interact with dropdowns; capture XHR calls in terminal output
3. Fill `MYSAMAY_EVENTS_API` in scraper, run `--mode=direct --site=mysamay`

**Known endpoint patterns (to verify):**
```
GET /api/events?year=YYYY
GET /api/v1/races?year=YYYY
POST /api/event/list  {"year": YYYY}
```

---

## 4. TimingIndia

| Attribute | Details |
|---|---|
| URL | https://www.timingindia.com |
| Architecture | Static HTML site (Bootstrap) — NOT a SPA |
| Backend | **Results hosted on ifinish.in** (301 redirect: ifinish.co.in → ifinish.in) |
| Result URL pattern | `https://ifinish.in/eventresult/result-{EventSlug}-{Year}` |
| Confirmed redirect | `timingindia.com` → `ifinish.in/eventresult/result-Whitathon-Vijayawada-2025` |
| Status | Implemented via slug enumeration fallback |

**Known events (confirmed slugs on ifinish.in):**
- NMDC-Marathon
- Hyderabad-Half-Marathon
- Telangana-Marathon
- SKF-Goa-River-Marathon
- Sandhya-Vizag-River-Marathon
- GMR-Airport-Run
- Tuffman
- Herculean-Triathlon
- Hyderabad-Triathlon
- Ironman-Goa
- Whitathon-Vijayawada

**Scraping approach (two options):**

Option A — Slug enumeration (default fallback):
```
python scrapers/race_registry_scraper.py --mode=direct --site=timingindia --years=2017-2025
```
Probes `ifinish.in/eventresult/result-{slug}-{year}` for all known slugs × years via HTTP HEAD.

Option B — API discovery via ifinish.in:
1. Run `--discover` mode; browser opens ifinish.in/eventresult
2. Interact with the event dropdown to trigger API calls
3. Look for an organizer/filter param (e.g. `?organizer=timingindia`)
4. Fill `TIMINGINDIA_EVENTS_API` in scraper

**Notes:**
- Add new event slugs to `TIMINGINDIA_KNOWN_SLUGS` in scraper as they are discovered
- Consider reaching out to TimingIndia directly — they may share a full event list

---

## 5. MyRaceIndia

| Attribute | Details |
|---|---|
| URL | https://www.myraceindia.com |
| Architecture | SPA (JS-rendered) — minimal static footprint |
| Results page | /results (returns minimal HTML — JS-rendered) |
| Events page | /events |
| Data access | Dynamic — XHR/fetch calls from browser |
| Year filter | Unknown — check via `--discover` |
| Auth | Unknown |
| Status | Config vars added; API endpoint pending `--discover` |

**Scraping approach:**
1. Run `--discover` mode — browser opens myraceindia.com/results and /events
2. Interact with event/year selectors; capture XHR calls in terminal output
3. Fill `MYRACEINDIA_EVENTS_API` in scraper, run `--mode=direct --site=myraceindia`

**Known endpoint patterns (to verify):**
```
GET /api/events?year=YYYY
GET /api/races/list?year=YYYY
```

---

## 7. RaceResult (planned)

| Attribute | Details |
|---|---|
| URL | https://my.raceresult.com |
| Architecture | Public REST API available |
| API docs | https://www.raceresult.com/en-us/home/api |
| Status | Has documented public API - easiest to integrate |

---

## Adding a New Platform

1. Manual recon: load the site, open DevTools > Network > XHR
2. Document architecture in this file
3. Add `PLATFORM_EVENTS_API` config var in scraper
4. Add to `SITE_CONFIGS` dict in scraper
5. Verify `normalize_events()` handles the response shape; add key fallbacks if needed
6. Update this doc
