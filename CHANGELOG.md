# Changelog

All notable changes to the `wikipedia-interest` skill. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [SemVer](https://semver.org/).

## [0.1.0] — 2026-09-27

First release for the Genesis AI Engineer test task.

### Added
- `resolve` — topic → article title per language edition via Wikidata sitelinks; missing articles reported, never guessed.
- `analyze` — pageviews normalized per million project views, spike-clipped annualized growth, YoY, seasonality,
  coverage, confidence (high/medium/low) with reasons, ranking, ≤40-line summary, `result.json`, `data.csv`, `chart.png`.
- `verify` — stability of a conclusion: desktop vs mobile, bot share, window sensitivity, fresh API spot-check, project baseline.
- `compare` — per-row deltas between two runs for follow-up questions and changed assumptions.
- `discover` — rising articles of an edition from monthly top lists, namespace-filtered, with `--sustained` 24-month trend.
- `report` — one-page A4 PDF (reportlab + bundled DejaVu font), Ukrainian or English labels.
- Assumption overrides `--access`, `--agent`, `--spike-z`; batch mode `--topics-file`.
- SQLite response cache (closed months permanent, month-load grace of 4 days), retries with backoff, typed `NoData`.
- Eval harness with two runners (OpenRouter tool calling; local `claude -p`), six scenarios, transcripts and rubric.
- 114 offline tests, 3 live tests, Agent Skills validator, CI (GitHub Actions + GitLab mirror).

### Fixed (during review)
- Unknown language codes crashed with a traceback → exit 3 with a hint.
- Incomplete month roll-ups could be cached permanently → grace period and eviction.
- `log1p` understated growth for low-traffic rows → `log(pm + ε)` with ε proportional to the series.
- `verify` ignored a run's `--access/--agent` → measures at the run's options.
- Ranking under all-negative growth favoured low-confidence rows → automatic switch to volume with a Check line.

[0.1.0]: https://github.com/javaAndScriptDeveloper/genesisAiEngineerTestTask/releases/tag/v0.1.0
