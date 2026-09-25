"""Orchestrate one analysis: resolve → fetch → metrics → rank → files."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from .api import WikiClient
from .resolve import TopicResolution, resolve_topic
from .series import Series, Window, fetch_project_totals, fetch_series, make_window
from .stats import THRESHOLDS, Metrics, compute_metrics, rank

SEASONALITY_NOTE_AMP = 1.0  # (max - min month-of-year mean) / overall mean above which we warn

FIXED_ASSUMPTIONS = [
    "Pageviews filtered to agent=user (human traffic as classified by Wikimedia) and all access methods.",
    "Interest is measured as views per million of the whole language edition's views in the same period.",
    "The current (incomplete) month is excluded.",
    "Growth figures are annualized log-linear trends with spike periods clipped (see references/methodology.md).",
]
FIXED_LIMITATIONS = [
    "Wikipedia interest is not willingness to pay; validate promising directions with real user research.",
    "Views depend on article existence and quality; a missing or poor article hides real interest.",
    "Bot filtering is imperfect; spikes can be automated traffic or news events.",
    "A language edition is not a country: readers of one language live in many markets.",
]


def key(topic: str, lang: str) -> str:
    return f"{topic}|{lang}"


@dataclass
class RunResult:
    topics: list[str]
    langs: list[str]
    window: Window
    rank_by: str
    resolutions: dict[str, TopicResolution]
    series: list[Series]
    metrics: dict[str, Metrics]
    ranking: list[tuple[str, float]]
    checks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    generated_at: str = ""
    options: dict = field(default_factory=lambda: {"access": "all-access", "agent": "user", "spike_z": None})

    def usable(self) -> list[Series]:
        return [s for s in self.series if s.status == "ok"]

    def to_dict(self) -> dict:
        return {
            "topics": self.topics, "langs": self.langs, "window": self.window.to_dict(), "rank_by": self.rank_by,
            "resolutions": {t: r.to_dict() for t, r in self.resolutions.items()},
            "series": [s.to_dict() for s in self.series],
            "metrics": {k: m.to_dict() for k, m in self.metrics.items()},
            "ranking": [{"key": k, "score": s} for k, s in self.ranking],
            "checks": self.checks, "assumptions": self.assumptions, "limitations": self.limitations,
            "follow_ups": self.follow_ups, "generated_at": self.generated_at, "options": self.options,
        }


def build_assumptions(access: str, agent: str, spike_z: float | None) -> list[str]:
    """FIXED_ASSUMPTIONS with the first and last lines rewritten when the user changed the defaults."""
    out = list(FIXED_ASSUMPTIONS)
    if access != "all-access" or agent != "user":
        agent_txt = {"user": "human traffic as classified by Wikimedia", "all-agents": "ALL traffic including bots and spiders",
                     "spider": "search-engine crawlers only", "automated": "automated/bot traffic only"}[agent]
        access_txt = {"all-access": "all access methods", "desktop": "desktop only", "mobile-web": "mobile web only",
                      "mobile-app": "mobile apps only"}[access]
        out[0] = f"Pageviews filtered to agent={agent} ({agent_txt}) and access={access} ({access_txt}) — user-chosen, not the default."
    if spike_z is not None:
        out[3] = (f"Growth figures are annualized log-linear trends with spike periods clipped at a user-chosen robust z of "
                  f"{spike_z} (default {THRESHOLDS['spike_z']}); see references/methodology.md.")
    return out


def run_analysis(client: WikiClient, topics: list[str], langs: list[str], months: int | None, start: str | None,
                 end: str | None, granularity: str, rank_by: str, titles: dict[str, str], qid: str | None,
                 hint: str | None, today: date, out_dir: Path, access: str = "all-access", agent: str = "user",
                 spike_z: float | None = None) -> RunResult:
    window = make_window(months, start, end, granularity, today)
    checks: list[str] = []
    limitations = list(FIXED_LIMITATIONS)

    totals = {lang: fetch_project_totals(client, lang, window, today, access, agent) for lang in langs}
    resolutions: dict[str, TopicResolution] = {}
    series: list[Series] = []
    metrics: dict[str, Metrics] = {}
    for topic in topics:
        res = resolve_topic(client, topic, langs, hint=hint, qid=qid if len(topics) == 1 else None, overrides=titles)
        resolutions[topic] = res
        for lang in langs:
            lr = res.per_lang[lang]
            s = fetch_series(client, topic, lang, lr.title, window, totals[lang], today, access, agent)
            series.append(s)
            if s.status == "missing":
                checks.append(f"{topic} / {lang}: MISSING article ({lr.note})")
                if lr.candidates:
                    limitations.append(f"{lang}: no article for '{topic}'; search suggests {', '.join(lr.candidates)} — "
                                       f"pass --titles {lang}=<title> only if one of them is the same topic.")
                else:
                    limitations.append(f"{lang}: no article for '{topic}' — absence of an article is not absence of interest.")
                continue
            if s.status == "no_data":
                checks.append(f"{topic} / {lang}: no pageview data for «{s.title}» ({s.note})")
                continue
            metrics[key(topic, lang)] = compute_metrics(s, spike_z=spike_z)
            zero = sum(1 for v in s.views if v == 0)
            if zero:
                checks.append(f"{topic} / {lang}: {zero} of {len(s.views)} periods have zero views")
        if res.alternatives:
            alts = "; ".join(f"{a['qid']} «{a['label']}» ({a['description']})" for a in res.alternatives)
            checks.append(f"{topic}: resolved to {res.qid} «{res.label}»; other candidates: {alts}. Use --qid to switch.")

    entries = [(k, m) for k, m in metrics.items()]
    if rank_by == "score" and entries and all((m.growth_clipped_pct_per_year or 0.0) < 0 for _, m in entries):
        rank_by = "volume"
        checks.append("every row is declining → ranked by volume (current attention share) instead of score; "
                      "a score ranking would only order declines and favour low-confidence ones. "
                      "Use --rank-by growth to see which declines slowest.")
    ranking = rank(entries, by=rank_by)
    for lang in langs:
        for i, p in enumerate(window.periods):
            if totals[lang][i] == 0:
                checks.append(f"{lang}: project totals for {p} not loaded yet (0 project views) — Wikimedia publishes "
                              f"a month a few days after it ends; that period counts as no data")
    checks.append(f"window {window.start}..{window.end} ({len(window.periods)} {granularity} periods); current month excluded")
    if client.cache is not None:
        checks.append(f"cache: {client.cache.hits} hits, {client.cache.misses} misses")
    for k, m in metrics.items():
        if m.seasonality_amp is not None and m.seasonality_amp > SEASONALITY_NOTE_AMP:
            checks.append(f"{k}: strongly seasonal (amplitude {m.seasonality_amp}× the mean) — compare the same months "
                          f"across years, not adjacent months; 'pm latest' vs 'pm year ago' already does that")
        if m.spike_periods:
            limitations.append(f"{k}: spikes in {', '.join(m.spike_periods[:6])} carry {m.spike_share_pct}% of views.")
        if m.coverage_pct < 100:
            limitations.append(f"{k}: data covers {m.coverage_pct}% of the window (first seen {m.first_seen}).")

    follow_ups = _follow_ups(out_dir, topics, langs, window, metrics)
    return RunResult(topics, langs, window, rank_by, resolutions, series, metrics, ranking, checks,
                     build_assumptions(access, agent, spike_z), limitations, follow_ups,
                     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                     options={"access": access, "agent": agent, "spike_z": spike_z})


def write_run(run: RunResult, out_dir: Path, summary: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    with (out_dir / "data.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["topic", "lang", "title", "period", "views", "project_views", "per_million"])
        for s in run.series:
            for p, v, pv, pm in zip(s.periods, s.views, s.project_views, s.per_million):
                w.writerow([s.topic, s.lang, s.title or "", p, v, pv, pm])


def load_run(out_dir: Path) -> dict:
    path = Path(out_dir) / "result.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run `analyze --out {out_dir}` first")
    return json.loads(path.read_text(encoding="utf-8"))


def _follow_ups(out_dir: Path, topics, langs, window: Window, metrics: dict[str, Metrics]) -> list[str]:
    cli = "uv run scripts/wiki_interest.py"
    t = f'--topics "{";".join(topics)}"' if len(topics) > 1 else f'--topic "{topics[0]}"'
    out: list[str] = []
    spiky = [(k, m) for k, m in metrics.items() if m.spike_periods and window.granularity == "monthly"]
    if spiky:
        k, m = spiky[0]
        p = m.spike_periods[0]
        out.append(f'{cli} analyze {t} --langs {k.split("|")[1]} --granularity daily --start {p} --end {p} '
                   f'--out {out_dir}-daily-{p}   # inspect the {p} spike day by day')
    if window.granularity == "monthly" and len(window.periods) < 36:
        out.append(f'{cli} analyze {t} --langs {",".join(langs)} --months 48 --out {out_dir}-48m   # longer history')
    out.append(f'{cli} report --run {out_dir} --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF')
    return out
