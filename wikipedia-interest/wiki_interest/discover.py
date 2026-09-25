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
from .series import DATA_FLOOR, MONTH_LOAD_GRACE_DAYS, _shift_month, _ym, fetch_project_totals, fetch_series, make_window
from .stats import compute_metrics

DEFAULT_LIMIT = 20
MAX_LINES = 40
JUNK = re.compile(r"\.(php|phtml|html?|js|css|xml)$|^-$|^\W+$")  # technical leftovers that appear in top lists


def default_month(today: date) -> str:
    """Last closed month, or the one before it during the first days of a month (Wikimedia load lag)."""
    last_closed = _shift_month(today.strftime("%Y-%m"), -1)
    return last_closed if today.day >= MONTH_LOAD_GRACE_DAYS else _shift_month(last_closed, -1)


def discover(client: WikiClient, lang: str, month: str | None, today: date, limit: int = DEFAULT_LIMIT,
             include: str | None = None, exclude: str | None = None, min_views: int = 1000,
             sustained: bool = False) -> dict:
    last_closed = _shift_month(today.strftime("%Y-%m"), -1)
    month = month or default_month(today)
    _ym(month)
    if month > last_closed:
        raise ValueError(f"--month must be a closed month (latest {last_closed}), got {month}")
    if month < _shift_month(DATA_FLOOR, 12):
        raise ValueError(f"need a year of history before {month}; data starts {DATA_FLOOR}")
    year_ago = _shift_month(month, -12)
    project = f"{lang}.wikipedia"
    prev = _shift_month(month, -1)
    try:
        inc = re.compile(include, re.I) if include else None
        exc = re.compile(exclude, re.I) if exclude else None
    except re.error as err:
        raise ValueError(f"bad regular expression in --include/--exclude: {err}") from err

    try:
        now_top = client.top_articles(project, *_ym(month))
    except NoData as err:
        if month == last_closed:
            raise ValueError(f"top list for {project} {month} is not published yet; use --month {prev}") from err
        raise ValueError(f"no top list for {project} in {month} ({err}); check the language code "
                         f"(Czech is cs, Ukrainian is uk)") from err
    try:
        ago_top = {a["article"]: a["views"] for a in client.top_articles(project, *_ym(year_ago))}
    except NoData as err:
        raise ValueError(f"no top list for {project} in {year_ago} ({err})") from err
    totals = {m: _project_total(client, lang, m, today) for m in (month, year_ago)}
    if not totals[month]:
        raise ValueError(f"project totals for {project} {month} are not published yet; use --month {prev}")
    if not totals[year_ago]:
        raise ValueError(f"no project totals for {project} {year_ago}; cannot normalize")
    prefixes = tuple(f"{ns}:" for ns in client.namespaces(lang))

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
    skipped_new = 0
    fetch_cap = limit * 3  # bound the extra per-article calls for articles that were not in last year's top list
    for a in candidates:
        title = a["article"]
        ago_views = ago_top.get(title)
        new_in_top = ago_views is None
        note = None
        if new_in_top:
            if fetched >= fetch_cap:
                skipped_new += 1
                note = f"year-ago not fetched (cap of {fetch_cap} extra lookups reached; raise --limit or narrow --include)"
            else:
                fetched += 1
                ago_views = _single_month_views(client, project, title, year_ago)
        pm_now = _pm(a["views"], totals[month])
        pm_ago = _pm(ago_views, totals[year_ago])
        growth = None if pm_ago in (None, 0) else round((pm_now / pm_ago - 1) * 100, 1)
        if new_in_top and ago_views == 0:
            note = "no views a year ago: new article"
        rows.append({"title": title, "views_now": a["views"], "views_year_ago": ago_views, "pm_now": pm_now,
                     "pm_year_ago": pm_ago, "growth_pct": growth, "new_in_top": new_in_top, "rank_now": a["rank"], "note": note})
    all_new = [r for r in rows if r["new_in_top"]]
    rows.sort(key=lambda r: (r["growth_pct"] is None, -(r["growth_pct"] or 0), -r["views_now"]))
    rows = rows[:limit]
    if sustained:
        _attach_trends(client, lang, month, today, rows)
        rows.sort(key=lambda r: (r["growth_clipped_pct_per_year"] is None, -(r["growth_clipped_pct_per_year"] or 0)))
    return {"lang": lang, "month": month, "year_ago": year_ago, "project_views": totals, "rows": rows, "sustained": sustained,
            "skipped_new": skipped_new, "all_new_candidates": all_new,
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
    if d.get("skipped_new"):
        lines.append(f"{d['skipped_new']} further articles new to the top list were not checked against last year "
                     f"(lookup cap); narrow --include or raise --limit to see them.")
    lines.append(f"Note: {d['note']}" + ("" if sus else " Add --sustained to attach the 24-month clipped trend and confidence per candidate."))
    if d["rows"]:
        picks = ",".join(f"{d['lang']}={r['title']}" for r in d["rows"][:1])
        lines.append(f"Next: `uv run scripts/wiki_interest.py analyze --topic \"<name it>\" --langs {d['lang']} --titles {picks} --months 24 --out runs/<slug>`")
    return "\n".join(lines) + "\n"  # rows are already capped by --limit


def write_discover(d: dict, out_dir: Path) -> str:
    text = render_discover(d)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "discover.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "discover.md").write_text(text, encoding="utf-8")
    return text


def _project_total(client: WikiClient, lang: str, month: str, today: date) -> int:
    """Project views for one month via the same permanence/eviction rules as analyze (no permanent zeros)."""
    window = make_window(None, month, month, "monthly", today)
    return fetch_project_totals(client, lang, window, today)[0]


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
