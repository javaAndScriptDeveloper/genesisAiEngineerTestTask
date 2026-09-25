"""Trend, robustness and confidence metrics for one pageview series.

All thresholds live in THRESHOLDS and are mirrored in references/methodology.md.
Pure numpy; the p-value is a permutation test on Spearman's rho so no SciPy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .series import Series

THRESHOLDS = {
    "spike_z": 3.5,               # robust z (MAD) above which a period is a spike
    "clip_window": 5,             # rolling median window used to replace spikes
    "permutations": 2000,         # for the Spearman p-value
    "low_coverage_pct": 70, "medium_coverage_pct": 90,
    "low_spike_pct": 30, "medium_spike_pct": 10,
    "low_p": 0.10, "medium_p": 0.05,
    "low_growth_gap_pts": 25,
    "low_min_views": 1000,
    "medium_min_periods": 24,
}
RANK_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.25}
PERIODS_PER_YEAR = {"monthly": 12, "daily": 365}


@dataclass
class Metrics:
    views_total: int
    pm_latest: float | None
    pm_year_ago: float | None
    yoy_pct: float | None
    growth_pct_per_year: float | None
    growth_clipped_pct_per_year: float | None
    spike_periods: list[str]
    spike_share_pct: float
    rho: float | None
    p_value: float | None
    seasonality_amp: float | None
    coverage_pct: float
    first_seen: str | None
    n_periods: int
    confidence: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(series: Series, spike_z: float | None = None) -> Metrics:
    pm = np.asarray(series.per_million, dtype=float)
    views = np.asarray(series.views, dtype=float)
    n = len(pm)
    ppy = PERIODS_PER_YEAR[series.granularity]
    monthly = series.granularity == "monthly"

    views_total = int(views.sum())
    nonzero = np.flatnonzero(views > 0)
    coverage_pct = round(100.0 * len(nonzero) / n, 1) if n else 0.0
    first_seen = series.periods[int(nonzero[0])] if len(nonzero) else None

    tail = 3 if monthly else 7
    pm_latest = _r(pm[-tail:].mean()) if n >= tail else (_r(pm.mean()) if n else None)
    pm_year_ago = _r(pm[-ppy - tail:-ppy].mean()) if monthly and n >= ppy + tail else None
    yoy_pct = None
    if monthly and n >= 24:
        prev, last = pm[-24:-12].mean(), pm[-12:].mean()
        yoy_pct = _r((last / prev - 1) * 100) if prev > 0 else None

    positive = pm > 0  # zero periods (article absent / not loaded) are reported via coverage, not fitted
    logs = _log(pm)
    growth = _growth(logs, positive, ppy)
    spikes = _spike_mask(logs, positive, spike_z or THRESHOLDS["spike_z"])
    spike_periods = [series.periods[i] for i in np.flatnonzero(spikes)]
    spike_share_pct = _r(100.0 * views[spikes].sum() / views_total) if views_total else 0.0
    clipped = _clip(logs, spikes, positive)
    growth_clipped = _growth(clipped, positive, ppy)
    rho, p_value = _spearman_perm(clipped, positive)

    seasonality_amp = None
    if monthly and n >= 24:
        moy = np.array([int(p[5:7]) for p in series.periods])
        means = np.array([pm[moy == k].mean() for k in range(1, 13)])
        seasonality_amp = _r((means.max() - means.min()) / pm.mean()) if pm.mean() > 0 else None

    confidence, reasons = _confidence(coverage_pct, spike_share_pct, p_value, growth, growth_clipped,
                                      views_total, n, monthly)
    return Metrics(views_total, pm_latest, pm_year_ago, yoy_pct, growth, growth_clipped, spike_periods,
                   spike_share_pct, rho, p_value, seasonality_amp, coverage_pct, first_seen, n, confidence, reasons)


def rank(entries: list[tuple[str, Metrics]], by: str = "score") -> list[tuple[str, float]]:
    if by not in ("score", "growth", "volume"):
        raise ValueError(f"--rank-by must be score, growth or volume, got {by}")

    def key(m: Metrics) -> float:
        g = m.growth_clipped_pct_per_year or 0.0
        if by == "growth":
            return g
        if by == "volume":
            return m.pm_latest or 0.0
        return g * RANK_WEIGHTS[m.confidence]

    scored = [(k, _r(key(m)), m.pm_latest or 0.0) for k, m in entries]
    scored.sort(key=lambda t: (t[1], t[2]), reverse=True)
    return [(k, s) for k, s, _ in scored]


# ---- internals -----------------------------------------------------------
def _r(x) -> float | None:
    if x is None or not np.isfinite(x):
        return None
    return round(float(x), 2)


def _log(pm: np.ndarray) -> np.ndarray:
    """log(pm + eps) with eps tiny relative to the series, so low-traffic rows are not damped.

    (log1p would add a constant 1 per-million and understate growth for rows below ~5 per million.)
    """
    positive = pm[pm > 0]
    eps = max(1e-3, 0.01 * float(np.median(positive))) if positive.size else 1e-3
    return np.log(pm + eps)


def _growth(logs: np.ndarray, use: np.ndarray, ppy: int) -> float | None:
    n = len(logs)
    if n == 0:
        return None
    idx = np.flatnonzero(use)
    if len(idx) < 3 or np.allclose(logs[idx], logs[idx][0]):
        return 0.0
    slope = np.polyfit(idx, logs[idx], 1)[0]
    return _r((np.exp(slope * ppy) - 1) * 100)


def _spike_mask(logs: np.ndarray, use: np.ndarray, spike_z: float) -> np.ndarray:
    out = np.zeros(len(logs), dtype=bool)
    idx = np.flatnonzero(use)
    if len(idx) < 3:
        return out
    vals = logs[idx]
    med = np.median(vals)
    dev = np.abs(vals - med)
    mad = np.median(dev)
    if mad == 0:
        # Mostly-constant series (e.g. flat with one outlier): fall back to mean absolute deviation.
        mad = dev.mean()
    if mad == 0:
        return out
    z = 0.6745 * (vals - med) / mad
    out[idx[z > spike_z]] = True
    return out


def _clip(logs: np.ndarray, spikes: np.ndarray, use: np.ndarray) -> np.ndarray:
    out = logs.copy()
    w = THRESHOLDS["clip_window"] // 2
    n = len(logs)
    good = use & ~spikes
    for i in np.flatnonzero(spikes):
        lo, hi = max(0, i - w), min(n, i + w + 1)
        neighbours = [logs[j] for j in range(lo, hi) if good[j]]
        if neighbours:
            out[i] = np.median(neighbours)
        elif good.any():
            out[i] = np.median(logs[good])
    return out


def _spearman_perm(x_full: np.ndarray, use: np.ndarray) -> tuple[float | None, float | None]:
    idx = np.flatnonzero(use)
    x = x_full[idx]
    n = len(x)
    if n < 4 or np.allclose(x, x[0]):
        return None, None
    rx = _ranks(x)
    rho = float(np.corrcoef(idx, rx)[0, 1])
    rng = np.random.default_rng(0)
    perms = THRESHOLDS["permutations"]
    count = 0
    for _ in range(perms):
        r = float(np.corrcoef(idx, rng.permutation(rx))[0, 1])
        if abs(r) >= abs(rho):
            count += 1
    return _r(rho), _r((count + 1) / (perms + 1))


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1)
    for v in np.unique(x):  # average ties
        mask = x == v
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def _confidence(coverage, spike_share, p, growth, growth_clipped, views_total, n, monthly):
    T = THRESHOLDS
    hard, soft = [], []
    if coverage < T["low_coverage_pct"]:
        hard.append(f"coverage {coverage}% < {T['low_coverage_pct']}% (article young or absent for part of window)")
    elif coverage < T["medium_coverage_pct"]:
        soft.append(f"coverage {coverage}% < {T['medium_coverage_pct']}%")
    if spike_share > T["low_spike_pct"]:
        hard.append(f"spike share {spike_share}% > {T['low_spike_pct']}% (news-driven traffic)")
    elif spike_share > T["medium_spike_pct"]:
        soft.append(f"spike share {spike_share}% > {T['medium_spike_pct']}%")
    if p is None or p > T["low_p"]:
        hard.append(f"trend not monotonic (p={p})")
    elif p > T["medium_p"]:
        soft.append(f"weak monotonic trend (p={p})")
    if growth is not None and growth_clipped is not None and abs(growth - growth_clipped) > T["low_growth_gap_pts"]:
        hard.append(f"growth changes by {abs(growth - growth_clipped):.0f} pts when spikes are clipped")
    if views_total < T["low_min_views"]:
        hard.append(f"total views {views_total} < {T['low_min_views']}")
    if monthly and n < T["medium_min_periods"]:
        soft.append(f"only {n} months (< {T['medium_min_periods']}): no year-over-year check")
    if hard:
        return "low", hard + soft
    if soft:
        return "medium", soft
    return "high", []
