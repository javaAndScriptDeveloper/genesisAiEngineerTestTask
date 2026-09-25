"""`compare`: what changed between two analyze runs (follow-up questions, changed assumptions)."""
from __future__ import annotations

import json
from pathlib import Path

from .run import load_run

METRICS = ("pm_latest", "pm_year_ago", "yoy_pct", "growth_clipped_pct_per_year", "spike_share_pct", "coverage_pct", "confidence")
MAX_LINES = 40


def compare_runs(a_dir: Path, b_dir: Path) -> dict:
    a, b = load_run(Path(a_dir)), load_run(Path(b_dir))
    rows_a, rows_b = a["metrics"], b["metrics"]
    common = [k for k in rows_a if k in rows_b]
    rows = {}
    for k in common:
        rows[k] = {}
        for m in METRICS:
            va, vb = rows_a[k].get(m), rows_b[k].get(m)
            entry = {"a": va, "b": vb}
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                entry["delta"] = round(vb - va, 2)
            rows[k][m] = entry
    opts_a, opts_b = a.get("options", {}) or {}, b.get("options", {}) or {}
    options_changed = {k: {"a": opts_a.get(k), "b": opts_b.get(k)} for k in set(opts_a) | set(opts_b) if opts_a.get(k) != opts_b.get(k)}
    return {
        "a": str(a_dir), "b": str(b_dir),
        "window": {"a": a["window"], "b": b["window"]},
        "options_changed": options_changed,
        "langs": {"a": a["langs"], "b": b["langs"]},
        "topics": {"a": a["topics"], "b": b["topics"]},
        "added_rows": [k for k in rows_b if k not in rows_a],
        "removed_rows": [k for k in rows_a if k not in rows_b],
        "rows": rows,
        "ranking": {"a": [r["key"] for r in a["ranking"]][:5], "b": [r["key"] for r in b["ranking"]][:5]},
        "rank_by": {"a": a["rank_by"], "b": b["rank_by"]},
    }


def render_compare(c: dict) -> str:
    wa, wb = c["window"]["a"], c["window"]["b"]
    lines = [f"# compare — A: {c['a']} ({wa['start']}..{wa['end']}) → B: {c['b']} ({wb['start']}..{wb['end']})"]
    if (wa["start"], wa["end"], wa["granularity"]) != (wb["start"], wb["end"], wb["granularity"]):
        lines.append(f"- window changed: {wa['start']}..{wa['end']} {wa['granularity']} → {wb['start']}..{wb['end']} {wb['granularity']}")
    for k, v in sorted(c["options_changed"].items()):
        lines.append(f"- option `{k}` changed: {v['a']} → {v['b']}")
    if c["added_rows"]:
        lines.append(f"- added rows: {', '.join(c['added_rows'])}")
    if c["removed_rows"]:
        lines.append(f"- removed rows: {', '.join(c['removed_rows'])}")
    if c["rank_by"]["a"] != c["rank_by"]["b"]:
        lines.append(f"- ranking rule: {c['rank_by']['a']} → {c['rank_by']['b']}")
    lines.append("")
    lines.append("| row | pm latest A→B | growth/yr % (clipped) A→B | YoY % A→B | spikes % A→B | confidence A→B |")
    lines.append("|---|---|---|---|---|---|")
    for k, r in c["rows"].items():
        lines.append(f"| {k} | {_ab(r['pm_latest'])} | {_ab(r['growth_clipped_pct_per_year'])} | {_ab(r['yoy_pct'])} | "
                     f"{_ab(r['spike_share_pct'])} | {r['confidence']['a']}→{r['confidence']['b']} |")
    if not c["rows"]:
        lines.append("| (no common rows) | | | | | |")
    lines.append("")
    lines.append(f"Ranking A (top): {', '.join(c['ranking']['a']) or '—'}")
    lines.append(f"Ranking B (top): {', '.join(c['ranking']['b']) or '—'}")
    lines.append("Read: growth deltas > 10 pts or a confidence change mean the conclusion depends on the changed "
                 "window/assumption — say so; small deltas mean the follow-up confirms the first answer.")
    return "\n".join(lines[:MAX_LINES]) + "\n"


def write_compare(c: dict, out_dir: Path) -> str:
    text = render_compare(c)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compare.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "compare.md").write_text(text, encoding="utf-8")
    return text


def _ab(e: dict) -> str:
    a, b = e.get("a"), e.get("b")
    fa, fb = ("–" if a is None else f"{a:g}"), ("–" if b is None else f"{b:g}")
    d = e.get("delta")
    return f"{fa}→{fb}" + (f" ({d:+g})" if d is not None and d != 0 else "")
