# Data Schema

Output schema for all normalized race registry records.

---

## Event Record

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `race_name` | string | yes | Official race name as on timing platform | Bengaluru Marathon 2024 |
| `race_date` | string | no | ISO date (YYYY-MM-DD) when available | 2024-10-20 |
| `city` | string | no | City or venue | Bengaluru |
| `distances` | string | no | Distance categories offered | 5K, 10K, 21K, FM |
| `participant_count` | string | no | Total finishers or registered count | 4200 |
| `event_id` | string | no | Source platform's internal event ID | 1042 |
| `timing_company` | string | yes | Source platform identifier | STS |
| `source_url` | string | yes | API URL the record came from | https://... |

---

## Timing Company Identifiers

| Value | Platform |
|---|---|
| `STS` | SportTimingSolutions (sportstimingsolutions.in) |
| `iFinish` | iFinish (ifinish.in) |
| `MySamay` | MySamay (mysamay.com) |
| `TimingIndia` | TimingIndia (timingindia.com) |
| `RaceResult` | RaceResult (my.raceresult.com) |

---

## Output Files

| File | Contents |
|---|---|
| `output/race_registry_sts.csv` | STS events only |
| `output/race_registry_ifinish.csv` | iFinish events only |
| `output/race_registry_combined.csv` | All platforms merged |
| `output/race_registry_combined_deduped.csv` | Combined after dedup pass |

---

## Deduplication Logic

Two events are considered duplicates when:
- `race_name` matches (case-insensitive, whitespace-normalized)
- `year` extracted from `race_date` matches

When duplicates are found, the first occurrence (by source order) is kept.
The full duplicate list is printed during the `--dedup` run for audit.

---

## Downstream Usage in WONE

This registry feeds:

1. **Athlete profile enrichment** — given an athlete's city and active years, find races they likely ran
2. **Result verification** — cross-reference against scraped timing results for a specific athlete
3. **Club participation mapping** — which races does a club's cohort consistently attend?
4. **Organizer relationship graph** — which timing companies does an organizer use?
