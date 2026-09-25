#!/usr/bin/env python3
"""wikipedia-interest CLI: resolve | analyze | report.

Run from the skill root:  uv run scripts/wiki_interest.py <command> ...
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from wiki_interest.api import ApiError, WikiClient  # noqa: E402
from wiki_interest.cache import Cache  # noqa: E402
from wiki_interest.charts import render_chart  # noqa: E402
from wiki_interest.pdf import render_pdf  # noqa: E402
from wiki_interest.resolve import resolve_topic  # noqa: E402
from wiki_interest.run import run_analysis, write_run  # noqa: E402
from wiki_interest.summary import render_summary  # noqa: E402

EXIT_OK, EXIT_NO_DATA, EXIT_BAD_ARGS = 0, 2, 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki_interest.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--topic", help="topic in any language, e.g. 'intermittent fasting' or 'астрономія'")
        sp.add_argument("--topics", help="several topics separated by ';' (analyze only)")
        sp.add_argument("--langs", required=True, help="comma-separated Wikipedia language codes, e.g. uk,pl,cs")
        sp.add_argument("--lang-hint", help="language the topic text is written in (default: auto)")
        sp.add_argument("--qid", help="force a Wikidata item, e.g. Q1666254")
        sp.add_argument("--titles", help="override titles: pl=Post_przerywany,cs=Přerušovaný_půst")
        sp.add_argument("--no-cache", action="store_true", help="ignore cached responses (still writes cache)")

    r = sub.add_parser("resolve", help="preview which article each language maps to (cheap)")
    common(r)
    r.add_argument("--json", action="store_true")

    a = sub.add_parser("analyze", help="fetch, normalize, compute trends/confidence, write summary+chart")
    common(a)
    a.add_argument("--months", type=int, default=None, help="last N full months (default 24)")
    a.add_argument("--start", help="YYYY-MM (with --end)")
    a.add_argument("--end", help="YYYY-MM (with --start); clamped to last closed month")
    a.add_argument("--granularity", choices=["monthly", "daily"], default="monthly")
    a.add_argument("--rank-by", choices=["score", "growth", "volume"], default="score")
    a.add_argument("--out", help="output directory (default runs/<slug>)")

    rp = sub.add_parser("report", help="build one-page PDF from an analyze run")
    rp.add_argument("--run", required=True, help="directory written by analyze")
    rp.add_argument("--title")
    rp.add_argument("--notes", default="", help="your recommendation: paragraphs and '- ' bullets")
    rp.add_argument("--notes-file", help="read --notes from a file")
    rp.add_argument("--lang", choices=["en", "uk"], default="en")
    rp.add_argument("--out", help="PDF path (default <run>/report.pdf)")
    return p


def make_client(no_cache: bool) -> WikiClient:
    cache_path = Path(os.environ.get("WIKI_INTEREST_CACHE", SKILL_ROOT / ".cache" / "cache.sqlite"))
    cache = Cache(cache_path)
    if no_cache:
        cache.get = lambda url, now=None: None  # type: ignore[method-assign]
    return WikiClient(cache=cache)


def _langs(s: str) -> list[str]:
    langs = [x.strip().lower() for x in s.split(",") if x.strip()]
    if not langs:
        raise ValueError("--langs must list at least one language code")
    return langs


def _titles(s: str | None) -> dict[str, str]:
    if not s:
        return {}
    out = {}
    for pair in s.split(","):
        if "=" not in pair:
            raise ValueError(f"--titles entries must look like lang=Title, got {pair!r}")
        k, v = pair.split("=", 1)
        out[k.strip().lower()] = v.strip()
    return out


def _topics(args) -> list[str]:
    if args.topics:
        return [t.strip() for t in args.topics.split(";") if t.strip()]
    if args.topic:
        return [args.topic.strip()]
    raise ValueError("--topic or --topics is required")


def cmd_resolve(args) -> int:
    topic = _topics(args)[0]
    langs = _langs(args.langs)
    client = make_client(args.no_cache)
    res = resolve_topic(client, topic, langs, hint=args.lang_hint, qid=args.qid, overrides=_titles(args.titles))
    if args.json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"topic: {res.topic}  →  {res.qid or '(no Wikidata item)'} «{res.label or ''}»")
    print("| lang | status | title | note |")
    print("|---|---|---|---|")
    for lang, lr in res.per_lang.items():
        cand = f" candidates: {', '.join(lr.candidates)}" if lr.candidates else ""
        print(f"| {lang} | {lr.status} | {lr.title or ''} | {lr.note}{cand} |")
    if res.alternatives:
        print("other Wikidata candidates: " + "; ".join(
            f"{a['qid']} «{a['label']}» ({a['description']})" for a in res.alternatives))
        print("(use --qid to pick one)")
    return EXIT_OK


def cmd_analyze(args) -> int:
    topics = _topics(args)
    langs = _langs(args.langs)
    titles = _titles(args.titles)
    out_dir = Path(args.out) if args.out else SKILL_ROOT / "runs" / _slug(topics, langs, args)
    client = make_client(args.no_cache)
    run = run_analysis(client, topics, langs, args.months, args.start, args.end, args.granularity, args.rank_by,
                       titles, args.qid, args.lang_hint, date.today(), out_dir)
    summary = render_summary(run, out_dir)
    write_run(run, out_dir, summary)
    render_chart(run, out_dir / "chart.png")
    print(summary)
    if not run.usable():
        print("ERROR: no usable series — every requested language is missing or has no pageview data. "
              "Check the Resolved line, try `resolve` with --lang-hint, or pass --titles.", file=sys.stderr)
        return EXIT_NO_DATA
    return EXIT_OK


def cmd_report(args) -> int:
    run_dir = Path(args.run)
    notes = args.notes
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    out = Path(args.out) if args.out else run_dir / "report.pdf"
    if args.out and (out.is_dir() or out.suffix.lower() != ".pdf"):
        out = out / "report.pdf"  # a directory (or a name without .pdf) means "put report.pdf in there"
    path = render_pdf(run_dir, out, args.title, notes, args.lang)
    print(f"wrote {path.resolve()}")
    return EXIT_OK


def _slug(topics, langs, args) -> str:
    t = re.sub(r"[^a-z0-9Ѐ-ӿ]+", "-", ";".join(topics).lower()).strip("-")[:40]
    span = f"{args.start}_{args.end}" if args.start else f"{args.months or 24}m"
    return f"{t}-{'-'.join(langs)}-{span}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return {"resolve": cmd_resolve, "analyze": cmd_analyze, "report": cmd_report}[args.cmd](args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_BAD_ARGS
    except ApiError as exc:
        print(f"ERROR: API failure: {exc}\nHint: retry in a minute; check network access to wikimedia.org.",
              file=sys.stderr)
        return EXIT_NO_DATA


if __name__ == "__main__":
    sys.exit(main())
