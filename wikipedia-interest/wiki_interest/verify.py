"""`verify`: is the conclusion of an analyze run stable under different ways of measuring?

Five independent checks per (topic, lang) row — devices, bots, window sensitivity, a fresh
spot-check against the API, and the project baseline — folded into robust | mixed | fragile.
"""
from __future__ import annotations

import calendar
import json
import random
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np

from .api import NoData, WikiClient
from .run import load_run
from .series import Series, Window, fetch_project_totals, fetch_series, make_window
from .stats import compute_metrics

THRESHOLDS = {
    "device_gap_alert_pts": 15, "device_gap_warn_pts": 10,
    "bot_share_alert_pct": 50, "bot_share_warn_pct": 35,   # Wikipedia articles typically see 20-30 % spider traffic
    "flat_band_pts": 5,  # |growth| below this is "flat": sign flips there are noise, not fragility
    "window_trim": 3,
}


def verify_run(client: WikiClient, run_dir: Path, today: date) -> dict:
    run = load_run(Path(run_dir))
    w = run["window"]
    window = make_window(None, w["start"], w["end"], w["granularity"], today)
    opts = run.get("options", {}) or {}
    spike_z = opts.get("spike_z")
    rows: dict[str, dict] = {}
    for s in run["series"]:
        if s["status"] != "ok":
            continue
        key = f"{s['topic']}|{s['lang']}"
        base = Series(**s)
        checks = {
            "devices": _devices(client, base, window, today, spike_z),
            "bots": _bots(client, base, window, today),
            "window": _window_sensitivity(base, spike_z),
            "spot_check": _spot_check(client, base, window),
            "baseline": _baseline(base),
        }
        verdict, reasons = _verdict(checks)
        rows[key] = {"title": s["title"], "checks": checks, "verdict": verdict, "reasons": reasons}
    return {"run": str(run_dir), "window": w, "rows": rows,
            "note": "verify measures stability of the trend, not its direction: a robust decline is still a decline."}


# ---- checks ----------------------------------------------------------------
def _growth(series: Series, spike_z) -> float | None:
    return compute_metrics(series, spike_z=spike_z).growth_clipped_pct_per_year


def _devices(client, base: Series, window: Window, today, spike_z) -> dict:
    out = {"status": "ok"}
    growths = {}
    for access in ("desktop", "mobile-web"):
        try:
            totals = fetch_project_totals(client, base.lang, window, today, access=access)
            s = fetch_series(client, base.topic, base.lang, base.title, window, totals, today, access=access)
            growths[access] = _growth(s, spike_z) if s.status == "ok" else None
        except (NoData, ValueError) as exc:
            growths[access] = None
            out["note"] = f"{access}: {exc}"
    out.update({"growth_desktop": growths.get("desktop"), "growth_mobile_web": growths.get("mobile-web")})
    d, m = growths.get("desktop"), growths.get("mobile-web")
    if d is None or m is None:
        out["status"] = "warn"
        out["detail"] = "one device series unavailable"
        return out
    gap = abs(d - m)
    same_sign = (d >= 0) == (m >= 0)
    if not same_sign and gap > THRESHOLDS["device_gap_warn_pts"] or gap > THRESHOLDS["device_gap_alert_pts"]:
        out["status"] = "alert"
    elif gap > THRESHOLDS["device_gap_warn_pts"]:
        out["status"] = "warn"
    out["detail"] = f"desktop {d:+.1f}%/yr vs mobile-web {m:+.1f}%/yr (gap {gap:.1f} pts)"
    return out


def _bots(client, base: Series, window: Window, today) -> dict:
    try:
        s_all = fetch_series(client, base.topic, base.lang, base.title, window, base.project_views, today, agent="all-agents")
    except (NoData, ValueError) as exc:
        return {"status": "warn", "detail": f"all-agents series unavailable: {exc}", "bot_share_pct": None}
    total_all = sum(s_all.views)
    total_user = sum(base.views)
    if total_all <= 0:
        return {"status": "warn", "detail": "no all-agents data", "bot_share_pct": None}
    share = round(100.0 * max(0, total_all - total_user) / total_all, 1)
    status = "alert" if share > THRESHOLDS["bot_share_alert_pct"] else "warn" if share > THRESHOLDS["bot_share_warn_pct"] else "ok"
    return {"status": status, "bot_share_pct": share,
            "detail": f"{share}% of all traffic to this article is non-human (spiders/automated)"}


def _window_sensitivity(base: Series, spike_z) -> dict:
    k = THRESHOLDS["window_trim"]
    full = _growth(base, spike_z)
    if len(base.periods) < 2 * k + 6:
        return {"status": "warn", "detail": "window too short to test sensitivity", "growth_full": full}
    no_tail = _growth(_slice(base, 0, len(base.periods) - k), spike_z)
    no_head = _growth(_slice(base, k, len(base.periods)), spike_z)
    vals = [v for v in (full, no_tail, no_head) if v is not None]
    status = "ok"
    flat = all(abs(v) < THRESHOLDS["flat_band_pts"] for v in vals)
    if len(vals) == 3 and not flat and not (all(v >= 0 for v in vals) or all(v < 0 for v in vals)):
        status = "alert"
    elif len(vals) == 3 and max(vals) - min(vals) > 25:
        status = "warn"
    return {"status": status, "growth_full": full, "growth_without_last_3": no_tail, "growth_without_first_3": no_head,
            "detail": f"full {_f(full)} · without last {k} {_f(no_tail)} · without first {k} {_f(no_head)}"
                      + (" (flat: within ±5 pts, sign changes ignored)" if flat else "")}


def _spot_check(client, base: Series, window: Window) -> dict:
    candidates = [i for i, v in enumerate(base.views) if v > 0]
    if not candidates:
        return {"status": "warn", "detail": "no non-zero period to re-fetch"}
    i = random.Random(base.title).choice(candidates)
    period = base.periods[i]
    if window.granularity == "monthly":
        y, m = int(period[:4]), int(period[5:7])
        start, end = f"{y:04d}{m:02d}01", f"{y:04d}{m:02d}{calendar.monthrange(y, m)[1]:02d}"
    else:
        start = end = period.replace("-", "")
    try:
        items = client.per_article(f"{base.lang}.wikipedia", base.title, window.granularity, start, end,
                                   permanent=False, fresh=True)
    except (NoData, ValueError) as exc:
        return {"status": "warn", "detail": f"re-fetch failed: {exc}", "period": period}
    fresh = int(items[0]["views"]) if items else 0
    stored = int(base.views[i])
    ok = fresh == stored
    return {"status": "ok" if ok else "alert", "period": period, "stored": stored, "fresh": fresh,
            "detail": f"{period}: stored {stored} vs API now {fresh}" + ("" if ok else " — MISMATCH, re-run with --no-cache")}


def _baseline(base: Series) -> dict:
    ppy = 12 if base.granularity == "monthly" else 365
    art = _raw_growth(base.views, ppy)
    proj = _raw_growth(base.project_views, ppy)
    rel = None if art is None or proj is None else round(art - proj, 1)
    return {"status": "ok", "article_raw_growth": art, "project_growth": proj, "relative": rel,
            "detail": f"raw article views {_f(art)}, whole {base.lang}.wikipedia {_f(proj)} → relative {_f(rel)}"}


# ---- verdict & rendering ----------------------------------------------------
def _verdict(checks: dict) -> tuple[str, list[str]]:
    reasons = []
    alerts = [n for n, c in checks.items() if c.get("status") == "alert"]
    warns = [n for n, c in checks.items() if c.get("status") == "warn"]
    for n in alerts + warns:
        reasons.append(f"{n}: {checks[n].get('detail', '')}")
    if alerts:
        return "fragile", reasons
    if warns:
        return "mixed", reasons
    return "robust", reasons


def render_verify(v: dict) -> str:
    lines = [f"# verify — {v['run']} — {v['window']['start']}..{v['window']['end']}"]
    for key, row in v["rows"].items():
        c = row["checks"]
        lines.append(f"## {key} «{row['title']}» → **{row['verdict'].upper()}**")
        lines.append(f"- devices [{c['devices']['status']}]: {c['devices'].get('detail', c['devices'].get('note', ''))}")
        lines.append(f"- bots [{c['bots']['status']}]: {c['bots'].get('detail', '')}")
        lines.append(f"- window [{c['window']['status']}]: {c['window'].get('detail', '')}")
        lines.append(f"- spot check [{c['spot_check']['status']}]: {c['spot_check'].get('detail', '')}")
        lines.append(f"- baseline: {c['baseline'].get('detail', '')}")
    if not v["rows"]:
        lines.append("No usable rows in this run.")
    lines.append(f"Note: {v['note']}")
    lines.append("Verdict rule: alert on devices/bots/window/spot check → fragile; only warnings → mixed; else robust.")
    cap = max(30, 6 * len(v["rows"]) + 4)
    return "\n".join(lines[:cap]) + "\n"


# ---- helpers ------------------------------------------------------------------
def _slice(s: Series, a: int, b: int) -> Series:
    return replace(s, periods=s.periods[a:b], views=s.views[a:b], project_views=s.project_views[a:b],
                   per_million=s.per_million[a:b])


def _raw_growth(values: list[int], ppy: int) -> float | None:
    v = np.asarray(values, dtype=float)
    idx = np.flatnonzero(v > 0)
    if len(idx) < 3:
        return None
    slope = np.polyfit(idx, np.log(v[idx]), 1)[0]
    return round(float((np.exp(slope * ppy) - 1) * 100), 1)


def _f(x) -> str:
    return "n/a" if x is None else f"{x:+.1f}%/yr"


def write_verify(v: dict, run_dir: Path) -> str:
    text = render_verify(v)
    (Path(run_dir) / "verify.json").write_text(json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    (Path(run_dir) / "verify.md").write_text(text, encoding="utf-8")
    return text
