# Wikipedia Interest Skill — Design Spec

Date: 2026-09-23
Status: approved in brainstorming, pending written review

## 1. Purpose

Task: <https://gist.github.com/edugenesis/84f332ba58642cf12110b196775a8b72> (Genesis AI Engineer course, test task 1).

Build a self-contained Agent Skill (per <https://agentskills.io/specification>) that lets an AI agent
help B2C product founders decide **which topics to develop** and **which language markets to enter**,
using Wikipedia pageview statistics. The skill must:

- analyze Wikimedia Pageviews API data across topics and language editions;
- produce charts and a shareable one-page PDF report;
- make conclusions that are data-backed, with explicit assumptions, limitations and a confidence rating;
- be efficient for a cheap, fast tool-using model (Claude Haiku 4.5 class): few tool calls, short outputs;
- handle follow-up and related queries cheaply (caching);
- ship real code, reproducible dependencies, no compiled binaries, everything inside the skill directory;
- come with an explanation of how to iterate it toward larger research and larger data volumes.

Success criterion: reviewer can run `skills-ref validate`, run the three example queries from the task
end-to-end on a Haiku-class model, and see numbers, chart, PDF and an honest verdict.

## 2. Assumptions (not stated in the task)

- Default period: last 24 full months. Current (partial) month is excluded from statistics.
- Default filters: `agent=user` (excludes spiders/automated), `access=all-access`.
- Default granularity: monthly. Daily is used when the window is ≤ 6 months or the user asks for spike detail.
- Topic → article title mapping goes through Wikidata (search → sitelinks), with MediaWiki search fallback.
- PDF is produced by pure-Python libraries (reportlab + matplotlib). No browser, no Cairo, no system fonts.
- SKILL.md and references are in English (better instruction-following on small models).
  Repo README is Ukrainian with an English mirror.
- Runtime: Python 3.12, `uv` for env/lock. Network access to `wikimedia.org` and `wikidata.org` required.

## 3. Directory layout

```
wikipedia-interest/                ← skill root; frontmatter `name: wikipedia-interest`
├── SKILL.md                       ← ≤150 lines: when to use, 3 commands, how to read results
├── pyproject.toml                 ← deps: httpx, matplotlib, reportlab; dev: pytest, pypdf
├── uv.lock
├── scripts/
│   └── wiki_interest.py           ← single CLI entrypoint (argparse), subcommands below
├── wiki_interest/                 ← package with the real logic
│   ├── api.py                     ← Pageviews + Wikidata + MediaWiki HTTP clients, retries, UA
│   ├── cache.py                   ← SQLite response cache
│   ├── resolve.py                 ← topic → per-language title resolution
│   ├── series.py                  ← fetch + align + normalize time series
│   ├── stats.py                   ← trend, spikes, coverage, confidence, ranking
│   ├── summary.py                 ← summary.md renderer (deterministic text)
│   ├── charts.py                  ← chart.png
│   └── pdf.py                     ← report.pdf (one page)
├── references/
│   ├── methodology.md             ← formulas, thresholds, confidence rules, limitations
│   ├── api-notes.md               ← endpoints, quirks (404 = no data, redirects, 2015-07 floor, rate limits)
│   └── examples.md                ← the 3 task prompts → command sequences → expected outputs
├── assets/
│   └── report_notes_template.md   ← wording skeleton for the agent's narrative in the PDF
├── tests/                         ← pytest; offline fixtures in tests/fixtures/*.json
└── .cache/                        ← created at runtime, gitignored
```

Invocation: `uv run scripts/wiki_interest.py <subcommand> ...` from the skill root. `uv` creates the
venv from `uv.lock` on first run. No global install.

## 4. CLI contract

All subcommands print human-readable text to stdout and write files under `--out`. JSON details go
to files, not stdout, to keep the agent's context small. Errors go to stderr with actionable hints.

### 4.1 `resolve`

```
resolve --topic "<text>" --langs uk,pl,cs [--lang-hint <lang>] [--json]
```

- Searches Wikidata (`wbsearchentities`, language = `--lang-hint` or auto: `en` unless topic contains
  non-Latin script, then try `uk`, `ru`, then `en`). Takes top candidates, fetches `sitelinks`.
- For each requested language: `found` (title), `missing` (no sitelink; MediaWiki `list=search` fallback
  proposes up to 3 candidates flagged `fallback`), `ambiguous` (several Wikidata items with sitelinks;
  lists candidates with descriptions).
- Follows redirects (`action=query&redirects=1`) so the pageviews title is canonical.
- Output table: `lang | status | title | qid | note`. `--json` prints JSON instead.
- Purpose: cheap preview so the agent can confirm titles with the user before heavier calls.

### 4.2 `analyze`

```
analyze --topic "<text>" [--topics "a;b;c"] --langs uk,pl,cs
        [--titles pl=Post_przerywany,cs=...] [--qid Q1666254]
        [--months 24 | --start YYYY-MM --end YYYY-MM]
        [--granularity monthly|daily] [--rank-by score|growth|volume]
        [--out runs/<slug>]
```

- Resolves titles (unless `--titles` given), fetches per-article series and per-project aggregate
  series, normalizes, computes stats, ranks, writes:
  - `result.json` — full numbers, series, checks, assumptions, limitations, resolved titles;
  - `summary.md` — ≤ 40 lines; printed to stdout;
  - `chart.png`;
  - `data.csv` — long format `topic,lang,title,month,views,project_views,per_million`.
- Exit codes: `0` success (including partial: some languages missing); `2` no usable series at all;
  `3` invalid arguments. Never crash on a single 404.
- `--out` default: `runs/<topic-slug>-<langs>-<months>m`. Re-running with same args overwrites.

### 4.3 `report`

```
report --run runs/<slug> [--title "<text>"] [--notes "<markdown-lite>"] [--notes-file path]
       [--lang en|uk] [--out runs/<slug>/report.pdf]
```

- Produces exactly one A4 page: title; subtitle (period, source, generation date); key-numbers table
  (one row per topic×language: per-million latest, per-million 12 months earlier, YoY %, growth/yr
  (clipped), spike share, coverage, confidence); chart; verdict box (ranking + confidence badges);
  narrative from `--notes` (paragraphs and `-` bullets only); footer with assumptions, limitations and
  data source line.
- Overflow strategy: shrink narrative font in steps down to 7 pt, then truncate narrative with "…".
  Never produce page 2.
- `--lang uk` switches fixed labels to Ukrainian; numbers and narrative unchanged.

## 5. Data layer

### 5.1 Endpoints

- Per-article: `/metrics/pageviews/per-article/{project}/all-access/user/{title}/{granularity}/{start}/{end}`
- Aggregate: `/metrics/pageviews/aggregate/{project}/all-access/user/{granularity}/{start}/{end}`
- Wikidata: `wbsearchentities`, `wbgetentities&props=sitelinks|labels|descriptions`
- MediaWiki per wiki: `action=query&redirects=1`, `list=search` fallback
- `User-Agent: wikipedia-interest-skill/<version> (+<repo URL>; contact email)`. Repo URL is a constant in `api.py`, set to the GitHub remote once it exists.
  Contact email read from env `WIKI_INTEREST_CONTACT` if set, otherwise a fixed repo URL only.

### 5.2 Cache

- SQLite at `<skill>/.cache/cache.sqlite`, table `responses(url PRIMARY KEY, body, fetched_at, ttl_until)`.
- Closed months: stored permanently, except that the most recent closed month counts as final only from
  the 4th day of the following month (Wikimedia load lag); an aggregate response with a missing period is
  evicted (amended after review).
- Windows touching the current month, Wikidata and MediaWiki lookups: TTL 7 days.
- `--no-cache` flag bypasses read (still writes).
- Cache hits are counted and reported in `checks`.

### 5.3 Fetching

- httpx client, timeout 30 s, up to 4 concurrent requests (threads), retry 3× with exponential backoff
  on 429/5xx/network errors. Respect Wikimedia guidance (≤ 100 req/s, well below).
- 404 from per-article → series marked `no_data` with the API message; not an exception.
- Series aligned to a full month index across the requested window; missing months → 0 views with a
  `months_missing` count in checks.
- Coverage: `coverage_pct = months with views > 0 / months in window`. First month with views > 0 is
  reported as `first_seen` (proxy for article age).

## 6. Analytics

Per (topic, lang) series `v[t]` over N months, with project totals `P[t]`:

- `per_million[t] = v[t] / P[t] * 1e6` — the primary comparable metric.
- `views_total = Σ v[t]`, `pm_latest` = mean of last 3 months, `pm_year_ago` = mean of the same 3 months
  12 months earlier (if available).
- `yoy_pct = (mean last 12 / mean prior 12 − 1) * 100` (requires N ≥ 24, else null).
- Trend: OLS on `log(per_million[t] + ε)` vs month index → `growth_pct_per_year = (exp(12·slope) − 1)·100`.
  `ε = max(0.001, 0.01·median(positive per_million))`; zero periods are excluded from the fit (amended after
  review: a fixed ε of 1 damped growth for low-traffic rows).
- Spikes: robust z-score using median and MAD on `log(per_million+ε)`; month is a spike if |z| > 3.5.
  `spike_share_pct = Σ v[spike months] / views_total · 100`.
- Clipped series: spike months replaced by rolling median (window 5). Trend recomputed →
  `growth_clipped_pct_per_year`. This is the headline growth figure.
- Monotonicity: Spearman rho between month index and clipped per_million, with p-value
  (t-approximation). Reported as `rho`, `p`.
- Seasonality amplitude: for N ≥ 24, `seasonality_amp = (max − min of month-of-year means) / overall mean`.
- Confidence:
  - `low` if any hard flag: `coverage_pct < 70`, `spike_share_pct > 30`, `p > 0.10`,
    `|growth − growth_clipped| > 25` points, or `views_total < 1000`.
  - `medium` if any soft flag: `coverage_pct < 90`, `spike_share_pct > 10`, `p > 0.05`, N < 24.
  - `high` otherwise. `reasons[]` always lists the triggered flags.
- Ranking (`--rank-by score` default): `score = growth_clipped_pct_per_year · w(confidence)` with
  weights high 1.0, medium 0.6, low 0.25; ties broken by `pm_latest`. `growth` and `volume` rank by
  the raw metric. The rule is printed in summary so the agent can explain it. Amended after review:
  when every row's clipped growth is negative, `score` degrades to `volume` automatically with a Check
  line, because shrinking negative numbers toward zero would rank low-confidence declines first.
- The summary prints a `Reasons` line for every non-high row (amended after review: the cheap model
  otherwise invents reasons).
- Fixed limitations text (always present): interest ≠ willingness to pay; article views depend on
  article quality/existence; bot filtering imperfect; Wikipedia audience skews; language edition ≠
  country. Dynamic limitations appended per run (missing languages, partial coverage, spikes).

Thresholds live in one place (`stats.py` constants) and are documented in `references/methodology.md`.

## 7. Outputs read by the agent

`summary.md` structure (deterministic, no LLM):

```
# <topic(s)> — <langs> — <start>..<end> (N months)
Resolved: uk → «Астрономія» (Q333) · pl → «Astronomia» · cs → MISSING
| topic | lang | pm latest | pm year ago | YoY % | growth/yr % (clipped) | spikes % | coverage % | confidence |
Ranking (score): 1. uk (…), 2. pl (…)
## Checks
- cache hits 5/6 · current month excluded · cs: no article (Wikidata has no sitelink; search fallback found «…», not used)
## Limitations
- … (fixed + dynamic)
## Suggested follow-ups
- `analyze … --granularity daily --start … --end …` to inspect the 2025-03 spike
- `report --run … --notes "…"` to produce the PDF
```

## 8. SKILL.md

Frontmatter:

```yaml
name: wikipedia-interest
description: Analyze Wikipedia pageview trends to compare audience interest in topics across language editions, rate how trustworthy the growth is, plot charts and build a one-page PDF report. Use when a user asks which topics or languages/markets to invest in, whether interest in a subject is growing, or wants Wikipedia/Wikimedia pageview statistics compared between languages.
license: MIT
compatibility: Requires Python 3.12+, uv, and internet access to wikimedia.org and wikidata.org
metadata:
  author: vampir
  version: "0.1.0"
```

Body sections (target ≤ 150 lines, ≤ 3000 tokens):

1. **Use / don't use** — yes: topic interest, language market comparison, trend trust; no: revenue,
   search-engine demand, page edits, anything before 2015-07.
2. **Setup** — `cd <skill>` then `uv run scripts/wiki_interest.py --help`; first run installs deps.
3. **Workflow** — (a) if topic is ambiguous or non-English, `resolve` first and confirm with the user;
   (b) `analyze`; (c) read the printed summary — confidence and Checks first; (d) answer with per-million
   numbers, growth (clipped), confidence and the limitations that apply; (e) `report` only when the user
   wants a shareable file, passing your narrative via `--notes`.
4. **Interpretation rules** — compare languages by per-million, not raw views; missing article ≠ no
   interest; spike-driven growth must be called out; never state growth without confidence; current
   month is excluded; always list assumptions.
5. **Follow-ups** — re-run `analyze` with changed flags; the cache makes it cheap; keep `--out` slugs
   related so runs can be compared; multi-topic via `--topics`.
6. **Command table** — three rows with the most-used flags.
7. **Read more** — links to `references/methodology.md`, `references/api-notes.md`, `references/examples.md`.

## 9. Testing

- **Unit (offline, pytest)**:
  - `stats`: synthetic exponential series → growth within tolerance; injected spike → detected and
    clipped; coverage math; confidence rule table; ranking order.
  - `resolve`: recorded Wikidata/MediaWiki JSON fixtures → found/missing/ambiguous paths; redirect
    normalization.
  - `cache`: miss → fetch → hit; TTL expiry; permanent for closed months.
  - `summary`: renders ≤ 40 lines, contains required sections.
  - `pdf`: generated file has exactly 1 page (pypdf), long notes still 1 page.
  - `cli`: `analyze` with mocked API produces the four files; exit codes.
- **Integration (network, `-m network`, skipped in CI by default)**: the three task queries end-to-end.
- **Model eval (`eval/` at repo root, outside the skill)**: `run_eval.py` uses OpenRouter chat
  completions with tool calling; tools: `bash` limited to the skill directory, `read_file`. System
  prompt = SKILL.md body. Runs the three task prompts plus one follow-up ("now add Czech and shorten
  to 12 months") on `anthropic/claude-haiku-4.5` and one free model. Saves transcripts to
  `eval/transcripts/` and a rubric in `eval/RESULTS.md`: used resolve when needed, cited per-million,
  cited confidence, mentioned missing language honestly, produced PDF on request, total tool calls.
  API key from `.env` (`OPENROUTER_API_KEY`), never committed.

## 10. Repository

- Root `README.md` (UA first, EN mirror below): what and why; quickstart; architecture; methodology
  summary; how it was tested on Haiku 4.5 (links to transcripts and RESULTS.md); how AI-generated code
  was verified (tests, manual API cross-checks, model eval); roadmap.
- Roadmap content: monthly pageview dumps / Wikimedia Enterprise for bulk; topic expansion via Wikidata
  `P31`/`P279` and category graphs; related-topic discovery from `top` endpoints; Parquet + DuckDB local
  store; multi-page reports and per-country views (`top-per-country`); scheduled monitoring with
  breakout alerts; forecasting; evaluation set of labelled past cases.
- `.gitignore`: `.cache/`, `runs/`, `.env`, `.venv/`, `__pycache__/`, `eval/transcripts/*.raw.json`.
- Commit history follows the plan; each task = tests first, then implementation.

## 11. Out of scope (v0.1)

- Country-level breakdowns, editor metrics, page edits.
- Forecasting.
- Multi-page reports, HTML dashboards.
- Any hosted service; the skill runs locally inside the agent's sandbox.
