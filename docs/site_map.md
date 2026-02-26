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

## 3. MySamay (planned)

| Attribute | Details |
|---|---|
| URL | https://mysamay.com |
| Architecture | TBD |
| Status | Not yet implemented |

---

## 4. TimingIndia (planned)

| Attribute | Details |
|---|---|
| URL | https://timingindia.com |
| Architecture | TBD |
| Notable events | NMDC Marathon, Hyderabad Half Marathon, Telangana Marathon |
| Status | Not yet implemented |

---

## 5. RaceResult (planned)

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
