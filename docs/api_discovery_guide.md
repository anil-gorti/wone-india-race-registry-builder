# API Discovery Guide: STS + iFinish
## Find the backend API endpoints in 10 minutes

---

## Why This Matters

Both sites are JavaScript SPAs. The race list comes from API calls, not HTML.
Once you have the API URL, you can call it directly for any year — no browser needed.

---

## SportTimingSolutions (sportstimingsolutions.in)

### Step 1: Open the results page
```
https://sportstimingsolutions.in/results
```

### Step 2: Open DevTools
- Chrome/Edge: `F12` or `Cmd+Option+I`
- Go to **Network** tab
- Check **Preserve log** checkbox
- Filter by: `Fetch/XHR`

### Step 3: Trigger the year dropdown
- Click the year selector on the page (e.g., select "2024")
- Watch the Network tab — you'll see a new request appear

### Step 4: Click that request
Look for something like:
```
GET /api/events?year=2024
POST /api/get-events     {"year": 2024}
GET /api/v1/race-list?year=2024
```

### Step 5: Copy the full URL + headers
In the request detail, go to:
- **Headers** tab → copy Request URL and any auth headers
- **Response** tab → confirm it's JSON with event names

### Step 6: Also trigger the race dropdown
After selecting a year, click "Select Race" to see if a second API call fires.
This will show you the races-by-year endpoint — which is exactly what you want.

---

## iFinish (ifinish.in)

### Step 1: Open the event result page
```
https://ifinish.in/eventresult
```

### Step 2: Same DevTools process
Open Network > Fetch/XHR > watch requests as page loads

### Step 3: Also check the homepage
```
https://ifinish.in
```
The marathon calendar on the homepage likely calls a structured events API.

### Step 4: Look for these patterns
iFinish is React + likely Node.js backend. Common patterns:
```
GET /api/events
GET /api/v1/events?page=1&limit=100
GET /api/marathon-calendar
GET /api/results/events
```

### Step 5: Check for pagination
If the response has fields like `page`, `total_pages`, `next`, `has_more` — 
the API is paginated and you'll need to loop through pages.

---

## After Discovery: Fill in the Scraper

Once you have the URLs, update `race_registry_scraper.py`:

```python
# Line ~70: Replace with actual STS endpoint
STS_EVENTS_API = "https://sportstimingsolutions.in/api/events"

# Line ~120: Replace with actual iFinish endpoint
IFINISH_EVENTS_API = "https://ifinish.in/api/events"
```

Then run:
```bash
python race_registry_scraper.py --mode=direct
```

---

## What to Look For in the Response

A good event list response will have fields like:

| Field | Common key names |
|---|---|
| Race name | `event_name`, `name`, `race_name`, `title` |
| Date | `race_date`, `date`, `event_date`, `start_date` |
| City | `city`, `location`, `venue`, `place` |
| Distances | `categories`, `distances`, `race_types` |
| Participant count | `participants`, `total_runners`, `count` |
| Event ID | `id`, `event_id`, `race_id` |

---

## If There Are Auth Headers

Some timing platforms pass a Bearer token. Check the Request Headers for:
```
Authorization: Bearer <token>
X-API-Key: <key>
```

If the token is in the request, it's likely tied to your browser session.
You can either:
1. Copy it and include it in your scraper (will expire)
2. Use Playwright to maintain a session and make authenticated calls

---

## Backup: Playwright Full DOM Scrape

If the API is fully locked down, run the Playwright scraper:
```bash
python race_registry_scraper.py --mode=playwright
```

This loads each page in a real browser, interacts with dropdowns,
and extracts event names from the rendered DOM.
Slower (5-10 seconds per page) but works on any site.
