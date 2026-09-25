"""`discover`: which articles in a language edition are rising, year over year, from the monthly top lists.

The user did not name these topics; this is how the skill proposes candidates for "what to develop next".
"""
from __future__ import annotations

import calendar
import json
import re
from datetime import date
from pathlib import Path

from .api import NoData, WikiClient
from .series import DATA_FLOOR, _shift_month, _ym, fetch_project_totals, fetch_series, make_window
from .stats import compute_metrics

DEFAULT_LIMIT = 20
MAX_LINES = 40
JUNK = re.compile(r"\.(php|phtml|html?|js|css|xml)$|^-$|^\W+$")  # technical leftovers that appear in top lists


def discover(client: WikiClient, lang: str, month: str | None, today: date, limit: int = DEFAULT_LIMIT,
             include: str | None = None, exclude: str | None = None, min_views: int = 1000,
             sustained: bool = False) -> dict:
    last_closed = _shift_month(today.strftime("%Y-%m"), -1)
    month = month or last_closed
    _ym(month)
    if month > last_closed:
        raise ValueError(f"--month must be a closed month (latest {last_closed}), got {month}")
    if month < _shift_month(DATA_FLOOR, 12):
        raise ValueError(f"need a year of history before {month}; data starts {DATA_FLOOR}")
    year_ago = _shift_month(month, -12)
    project = f"{lang}.wikipedia"

    now_top = client.top_articles(project, *_ym(month))
    ago_top = {a["article"]: a["views"] for a in client.top_articles(project, *_ym(year_ago))}
    totals = {m: _project_total(client, lang, m) for m in (month, year_ago)}
    prefixes = tuple(f"{ns}:" for ns in client.namespaces(lang))
    inc = re.compile(include, re.I) if include else None
    exc = re.compile(exclude, re.I) if exclude else None

    candidates = []
    for a in now_top:
        title = a["article"]
        if title.startswith(prefixes) or title in MAIN_PAGES or a["views"] < min_views or JUNK.search(title):
            continue
        if inc and not inc.search(title.replace("_", " ")):
            continue
        if exc and exc.search(title.replace("_", " ")):
            continue
        candidates.append(a)

    rows = []
    fetched = 0
    for a in candidates:
        title = a["article"]
        ago_views = ago_top.get(title)
        new_in_top = ago_views is None
        if new_in_top:
            if fetched >= limit * 3:  # bound the extra per-article calls
                continue
            fetched += 1
            ago_views = _single_month_views(client, project, title, year_ago)
        pm_now = _pm(a["views"], totals[month])
        pm_ago = _pm(ago_views, totals[year_ago])
        growth = None if pm_ago in (None, 0) else round((pm_now / pm_ago - 1) * 100, 1)
        rows.append({"title": title, "views_now": a["views"], "views_year_ago": ago_views, "pm_now": pm_now,
                     "pm_year_ago": pm_ago, "growth_pct": growth, "new_in_top": new_in_top, "rank_now": a["rank"]})
    rows.sort(key=lambda r: (r["growth_pct"] is None, -(r["growth_pct"] or 0)))
    rows = rows[:limit]
    if sustained:
        _attach_trends(client, lang, month, today, rows)
        rows.sort(key=lambda r: (r["growth_clipped_pct_per_year"] is None, -(r["growth_clipped_pct_per_year"] or 0)))
    return {"lang": lang, "month": month, "year_ago": year_ago, "project_views": totals, "rows": rows, "sustained": sustained,
            "filters": {"include": include, "exclude": exclude, "min_views": min_views},
            "note": ("Top lists count all readers of the month; a rise here is attention, not durable interest — "
                     "run analyze --titles on the candidates you care about to get a 24-month trend with confidence.")}


def _attach_trends(client: WikiClient, lang: str, month: str, today: date, rows: list[dict]) -> None:
    """24-month clipped growth + confidence for each candidate: separates durable interest from one-month attention."""
    window = make_window(None, _shift_month(month, -23), month, "monthly", today)
    totals = fetch_project_totals(client, lang, window, today)
    for r in rows:
        s = fetch_series(client, r["title"], lang, r["title"], window, totals, today)
        if s.status != "ok":
            r.update({"growth_clipped_pct_per_year": None, "confidence": None, "coverage_pct": None})
            continue
        m = compute_metrics(s)
        r.update({"growth_clipped_pct_per_year": m.growth_clipped_pct_per_year, "confidence": m.confidence,
                  "coverage_pct": m.coverage_pct, "spike_share_pct": m.spike_share_pct})


MAIN_PAGES = {"Main_Page", "Головна_сторінка", "Strona_główna", "Hlavní_strana", "Wikipedia:Hauptseite",
              "Wikipedia:Portada", "Заглавная_страница", "Wikipédia:Accueil_principal"}


def render_discover(d: dict) -> str:
    lines = [f"# discover — {d['lang']}.wikipedia — {d['month']} vs {d['year_ago']} (per million of project views)"]
    f = d["filters"]
    if f.get("include") or f.get("exclude"):
        lines.append(f"filters: include={f.get('include')!r} exclude={f.get('exclude')!r}")
    sus = d.get("sustained")
    head = "| # | article | pm now | pm year ago | month-on-year % | views now | new in top? |"
    if sus:
        head += " growth/yr % (clipped, 24m) | confidence | spikes % |"
    lines.append(head)
    lines.append("|" + "---|" * (head.count("|") - 1))
    for i, r in enumerate(d["rows"], 1):
        line = (f"| {i} | {r['title'].replace('_', ' ')} | {_f(r['pm_now'])} | {_f(r['pm_year_ago'])} | {_f(r['growth_pct'])} | "
                f"{r['views_now']} | {'yes' if r['new_in_top'] else ''} |")
        if sus:
            line += f" {_f(r.get('growth_clipped_pct_per_year'))} | {r.get('confidence') or '–'} | {_f(r.get('spike_share_pct'))} |"
        lines.append(line)
    if not d["rows"]:
        lines.append("| – | no articles matched the filters |" + " |" * (head.count("|") - 3))
    lines.append(f"Note: {d['note']}" + ("" if sus else " Add --sustained to attach the 24-month clipped trend and confidence per candidate."))
    if d["rows"]:
        picks = ",".join(f"{d['lang']}={r['title']}" for r in d["rows"][:1])
        lines.append(f"Next: `uv run scripts/wiki_interest.py analyze --topic \"<name it>\" --langs {d['lang']} --titles {picks} --months 24 --out runs/<slug>`")
    return "\n".join(lines[:MAX_LINES]) + "\n"


def write_discover(d: dict, out_dir: Path) -> str:
    text = render_discover(d)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "discover.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "discover.md").write_text(text, encoding="utf-8")
    return text


def _project_total(client: WikiClient, lang: str, month: str) -> int:
    y, m = _ym(month)
    start, end = f"{y:04d}{m:02d}0100", f"{y:04d}{m:02d}{calendar.monthrange(y, m)[1]:02d}00"
    try:
        items = client.aggregate(f"{lang}.wikipedia", "monthly", start, end, permanent=True)
    except NoData as exc:
        raise ValueError(f"no project totals for {lang}.wikipedia {month} ({exc}); check the language code") from exc
    return int(items[0]["views"]) if items else 0


def _single_month_views(client: WikiClient, project: str, title: str, month: str) -> int:
    y, m = _ym(month)
    start, end = f"{y:04d}{m:02d}01", f"{y:04d}{m:02d}{calendar.monthrange(y, m)[1]:02d}"
    try:
        items = client.per_article(project, title, "monthly", start, end, permanent=True)
    except NoData:
        return 0
    return int(items[0]["views"]) if items else 0


def _pm(views: int | None, total: int) -> float | None:
    if views is None or not total:
        return None
    return round(views / total * 1e6, 2)


def _f(x) -> str:
    return "–" if x is None else f"{x:g}"
