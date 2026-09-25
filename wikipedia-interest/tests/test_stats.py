import math

import numpy as np
import pytest

from wiki_interest.series import Series
from wiki_interest.stats import Metrics, compute_metrics, rank


def _series(pm, granularity="monthly", views=None):
    n = len(pm)
    periods = [f"{2024 + (i // 12):04d}-{i % 12 + 1:02d}" for i in range(n)] if granularity == "monthly" \
        else [f"2026-07-{i + 1:02d}" for i in range(n)]
    views = views if views is not None else [int(round(x * 100)) for x in pm]
    return Series("t", "uk", "T", periods, views, [100_000_000] * n, list(map(float, pm)), "ok", "", granularity)


def test_clean_exponential_growth_high_confidence():
    pm = [100 * (1.5 ** (i / 12)) for i in range(24)]  # +50 %/yr
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert abs(m.growth_pct_per_year - 50) < 2
    assert abs(m.growth_clipped_pct_per_year - 50) < 2
    assert m.spike_periods == [] and m.spike_share_pct == 0
    assert m.p_value is not None and m.p_value < 0.01
    assert m.coverage_pct == 100 and m.first_seen == "2024-01"
    assert m.yoy_pct is not None and m.yoy_pct > 30
    assert m.confidence == "high" and m.reasons == []


def test_single_spike_detected_and_clipped():
    pm = [100.0] * 24
    pm[10] = 5000.0
    views = [int(x * 1000) for x in pm]
    m = compute_metrics(_series(pm, views=views))
    assert m.spike_periods == ["2024-11"]
    assert m.spike_share_pct > 60
    assert abs(m.growth_clipped_pct_per_year) < 1
    assert m.confidence == "low" and any("spike" in r for r in m.reasons)


def test_short_window_no_yoy_no_seasonality():
    pm = [100.0 + i for i in range(6)]
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.yoy_pct is None and m.pm_year_ago is None and m.seasonality_amp is None
    assert m.n_periods == 6
    assert m.confidence in ("medium", "low")
    assert any("24" in r for r in m.reasons)


def test_all_zero_series_no_nan():
    m = compute_metrics(_series([0.0] * 24, views=[0] * 24))
    d = m.to_dict()
    assert all(not (isinstance(v, float) and math.isnan(v)) for v in d.values())
    assert m.spike_periods == [] and m.growth_clipped_pct_per_year == 0
    assert m.coverage_pct == 0 and m.first_seen is None
    assert m.confidence == "low" and any("1000" in r for r in m.reasons)


def test_low_coverage_flagged():
    pm = [0.0] * 12 + [100.0] * 12
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.coverage_pct == 50 and m.first_seen == "2025-01"
    assert m.confidence == "low" and any("coverage" in r for r in m.reasons)


def test_medium_when_only_soft_flag():
    rng = np.random.default_rng(1)
    pm = [100 * (1.3 ** (i / 12)) * (1 + 0.05 * rng.standard_normal()) for i in range(24)]
    pm[5] = pm[6] = pm[7] = 0.0  # three zero months → coverage 21/24 = 87.5 % (< 90 soft, ≥ 70 not hard)
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.coverage_pct == 87.5
    assert m.confidence == "medium"
    assert any("coverage" in r for r in m.reasons)


def test_daily_growth_annualized():
    pm = [100 * (2 ** (i / 365)) for i in range(31)]  # doubling per year
    m = compute_metrics(_series(pm, granularity="daily", views=[int(x * 1000) for x in pm]))
    assert abs(m.growth_pct_per_year - 100) < 5
    assert m.yoy_pct is None


def _metrics(growth, conf, pm_latest=10.0):
    return Metrics(10_000, pm_latest, None, None, growth, growth, [], 0.0, None, None, None, 100.0, "2024-01", 24, conf, [])


def test_rank_score_weights_confidence():
    entries = [("a", _metrics(40, "low")), ("b", _metrics(20, "high")), ("c", _metrics(30, "medium"))]
    assert [k for k, _ in rank(entries)] == ["b", "c", "a"]  # 20*1.0 > 30*0.6 > 40*0.25


def test_rank_by_volume_and_growth():
    entries = [("a", _metrics(40, "low", pm_latest=1)), ("b", _metrics(20, "high", pm_latest=5))]
    assert [k for k, _ in rank(entries, by="volume")] == ["b", "a"]
    assert [k for k, _ in rank(entries, by="growth")] == ["a", "b"]


def test_rank_rejects_unknown():
    with pytest.raises(ValueError):
        rank([], by="magic")


def test_growth_is_not_damped_for_low_traffic_rows():
    for base in (100.0, 2.0, 0.5):
        pm = [base * (0.5 ** (i / 12)) for i in range(24)]  # true -50 %/yr at every level
        m = compute_metrics(_series(pm, views=[max(1, int(x * 1000)) for x in pm]))
        assert abs(m.growth_pct_per_year - (-50)) < 3, (base, m.growth_pct_per_year)


def test_zero_months_are_excluded_from_the_trend_fit():
    pm = [100 * (1.3 ** (i / 12)) for i in range(24)]
    pm[5] = pm[6] = 0.0
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert abs(m.growth_pct_per_year - 30) < 3


def test_spike_threshold_can_be_overridden():
    pm = [100.0 + 5 * math.sin(i) for i in range(24)]  # gentle noise so MAD > 0
    pm[10] = 112.0  # mild bump: below z=3.5, above z=1.0
    views = [int(x * 1000) for x in pm]
    assert compute_metrics(_series(pm, views=views)).spike_periods == []
    assert "2024-11" in compute_metrics(_series(pm, views=views), spike_z=1.0).spike_periods
