"""Deterministic, ≤40-line Markdown summary the agent reads instead of JSON."""
from __future__ import annotations

from pathlib import Path

from .run import RunResult, key

MAX_LINES = 40


def render_summary(run: RunResult, out_dir: Path) -> str:
    w = run.window
    lines: list[str] = []
    lines.append(f"# {', '.join(run.topics)} — {','.join(run.langs)} — {w.start}..{w.end} ({len(w.periods)} {w.granularity})")
    for topic, res in run.resolutions.items():
        parts = []
        for lang in run.langs:
            lr = res.per_lang[lang]
            s = next(s for s in run.series if s.topic == topic and s.lang == lang)
            if s.status == "ok":
                parts.append(f"{lang} → «{lr.title}»")
            elif s.status == "no_data":
                parts.append(f"{lang} → «{lr.title}» NO DATA")
            else:
                parts.append(f"{lang} → MISSING")
        qid = f" ({res.qid})" if res.qid else ""
        lines.append(f"Resolved{qid if len(run.topics) == 1 else ''} {topic}: " + " · ".join(parts))
    lines.append("")
    lines.append("| topic | lang | pm latest | pm year ago | YoY % | growth/yr % (clipped) | spikes % | coverage % | confidence |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for topic in run.topics:
        for lang in run.langs:
            m = run.metrics.get(key(topic, lang))
            if m is None:
                continue
            lines.append(f"| {topic} | {lang} | {_f(m.pm_latest)} | {_f(m.pm_year_ago)} | {_f(m.yoy_pct)} | "
                         f"{_f(m.growth_clipped_pct_per_year)} | {_f(m.spike_share_pct)} | {_f(m.coverage_pct)} | {m.confidence} |")
    lines.append("")
    lines.append(f"## Ranking (by {run.rank_by}; score = clipped growth × confidence weight high 1.0 / medium 0.6 / low 0.25)")
    if run.ranking:
        lines.append("; ".join(f"{i + 1}. {k} ({s})" for i, (k, s) in enumerate(run.ranking)))
    else:
        lines.append("No usable series — nothing to rank.")
    lines.append("## Checks")
    lines += [f"- {c}" for c in run.checks]
    lines.append("## Limitations")
    lines += [f"- {lim}" for lim in run.limitations]
    lines.append("## Suggested follow-ups")
    lines += [f"- `{f}`" for f in run.follow_ups]
    lines.append(f"Files: {out_dir}/result.json, data.csv, chart.png")
    return "\n".join(_trim(lines)) + "\n"


def _f(x) -> str:
    return "–" if x is None else f"{x:g}"


def _trim(lines: list[str]) -> list[str]:
    if len(lines) <= MAX_LINES:
        return lines
    # Drop bullets from the end of bullet runs until it fits; keep headers and the final Files line.
    keep_tail = lines[-1]
    body = lines[:-1]
    while len(body) + 1 > MAX_LINES:
        for i in range(len(body) - 1, 0, -1):
            if body[i].startswith("- ") and body[i - 1].startswith("- "):
                del body[i]
                break
        else:
            break
    if len(body) + 1 > MAX_LINES:
        body = body[:MAX_LINES - 2] + ["- … (see result.json for the full list)"]
    return body + [keep_tail]
