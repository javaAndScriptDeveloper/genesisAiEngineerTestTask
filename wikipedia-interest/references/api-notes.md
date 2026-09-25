# API notes

## Endpoints used
- Per-article: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/{title}/{monthly|daily}/{YYYYMMDD}/{YYYYMMDD}`
- Aggregate (project totals for normalization): `…/aggregate/{lang}.wikipedia/all-access/user/{monthly|daily}/{YYYYMMDDHH}/{YYYYMMDDHH}`
- Wikidata: `wbsearchentities` (topic → items), `wbgetentities&props=sitelinks|labels` (item → titles per language)
- MediaWiki per edition: `action=query&redirects=1` (canonical title), `list=search` (candidates when missing)

## Quirks
- Data starts 2015-07-01. Requests before that fail validation (exit 3).
- 404 means "no data for this article/window" (article missing, renamed, or zero traffic), not a network error.
  The skill records it as `no_data` and continues with the other languages.
- Titles are percent-encoded with `/` escaped; spaces become underscores. Redirect targets are resolved
  so the canonical page is counted.
- The current month is incomplete and excluded; windows are clamped to the last closed month. Wikimedia
  publishes a month's totals during the first days of the next month, so until the 4th the most recent
  closed month is cached with a 7-day TTL, not permanently, and a period that comes back without project
  totals is flagged in Checks and evicted from the cache.
- Unknown language codes (`cz`, `ua`) make the aggregate endpoint return 404 → exit 3 with a hint
  (Czech is `cs`, Ukrainian is `uk`).
- Per-article monthly rows only exist for months with ≥ 1 view; missing months are aligned to 0.
- Wikidata search picks the first item that has an article in at least one requested language; other hits
  are listed as "other candidates" (often papers or films with the same name) — switch with `--qid`.
- When a language has no sitelink, the skill searches that edition with the item's label in that language
  (or the original topic text) and lists up to 3 candidates. They are suggestions, never used automatically.
- Rate limit guidance: stay well under 100 req/s. The client uses sequential requests, retries
  429/5xx three times with exponential backoff, and identifies itself with a descriptive User-Agent
  (set `WIKI_INTEREST_CONTACT=you@example.com` to add contact info).

## Cache
- SQLite at `.cache/cache.sqlite` (override with `WIKI_INTEREST_CACHE`). Closed-month windows are
  permanent; everything else expires after 7 days. `--no-cache` forces refetch.
- Cache hit/miss counts are printed under `## Checks`.

## Exit codes
- 0 — success (possibly partial: some languages missing, listed in Checks)
- 2 — no usable series at all, or API unavailable after retries
- 3 — invalid arguments or missing run directory (message says what to fix)
- argparse itself exits 2 on unknown flags; read the usage text it prints.
