# Methodology

Source: Wikimedia Pageviews API, `access=all-access`, `agent=user`. Monthly granularity by default.

## Per (topic, language) series
- `per_million[t] = views[t] / project_views[t] × 1e6` — share of the edition's attention. This is
  what makes uk (≈100M views/month) comparable with en (≈8B views/month).
- The summary prints `Reasons <key> (<confidence>): …` for every row that is not `high`; quote them.
- `pm_latest` = mean of the last 3 months (7 days when daily); `pm_year_ago` = same 3 months, 12 months earlier.
- `yoy_pct` = mean of last 12 months vs the 12 before, needs ≥ 24 months.
- `growth_pct_per_year` = OLS slope of `log(per_million + ε)` against time, annualized:
  `(exp(slope × 12) − 1) × 100` (× 365 for daily). `ε = max(0.001, 0.01 × median of the positive
  values)`, so the offset is tiny relative to the series and rows with 0.5 or 100 views per million get the
  same growth for the same relative change. Periods with zero views are excluded from the fit (they are
  reported through `coverage_pct`), so a missing or not-yet-loaded month cannot drag the trend.
- Spikes: robust z-score `0.6745 × (x − median) / MAD` on the log series; a period is a spike when z > 3.5
  (`spike_z`). If MAD is 0 (flat series) the mean absolute deviation is used instead.
  `spike_share_pct` = share of total views that fall in spike periods.
- Clipped series: spike periods replaced by the median of non-spike neighbours (window 5). The
  headline `growth_clipped_pct_per_year` is computed on it.
- Monotonicity: Spearman rho between time and the clipped series; `p_value` from a 2000-permutation
  test (seeded, deterministic). Small p → consistent direction, not noise.
- `seasonality_amp` = (max − min of month-of-year means) / overall mean, needs ≥ 24 months.
- `coverage_pct` = periods with views > 0 / periods; `first_seen` = first such period (article age proxy).

## Confidence
`low` if any hard flag:
- coverage < 70 (`low_coverage_pct`), spike share > 30 (`low_spike_pct`), p > 0.1 (`low_p`),
  |growth − growth_clipped| > 25 points, or total views < 1000.
`medium` if any soft flag: coverage < 90, spike share > 10, p > 0.05, fewer than 24 months.
`high` otherwise. `reasons[]` always lists the triggered flags — quote them.

Confidence is about how much the *trend* can be trusted, not whether the trend is good news:
a clean, steady decline is `high` confidence too.

## Ranking
`score = growth_clipped × weight(confidence)`, weights high 1.0 / medium 0.6 / low 0.25; ties by `pm_latest`.
`--rank-by growth` uses clipped growth alone; `--rank-by volume` uses `pm_latest`. Say which rule you used.
With negative growth the weight would shrink the penalty and rank a noisy decline above a confident one,
so **when every row's clipped growth is negative the skill switches to `volume` automatically** and prints
a Check saying so; the ranking then means "largest current attention share". Use `--rank-by growth` to
see which decline is slowest.

## Fixed limitations (always true)
Interest ≠ willingness to pay · views depend on article existence/quality · bot filtering is imperfect ·
a language edition is not a country · Wikipedia readers skew toward certain demographics.

## Interpreting common shapes
- Rising clipped trend, low spikes, high confidence → organic growth; good candidate.
- Flat trend with big spikes → news-driven; not a durable audience signal.
- Low coverage → new article; compare only the covered months (`--start`).
- Missing in a language → no article; consider it an opportunity signal only after checking search candidates.
- Declining everywhere → the topic's peak is behind it on Wikipedia; still worth checking whether the
  decline is slower in one language (relative advantage).
