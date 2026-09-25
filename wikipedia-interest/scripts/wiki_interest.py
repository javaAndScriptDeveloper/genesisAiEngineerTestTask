#!/usr/bin/env python3
"""wikipedia-interest CLI: resolve | analyze | report.

Run from the skill root:  uv run scripts/wiki_interest.py <command> ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from wiki_interest.api import ApiError, WikiClient, validate_access_agent  # noqa: E402
from wiki_interest.cache import Cache  # noqa: E402
from wiki_interest.charts import render_chart  # noqa: E402
from wiki_interest.pdf import render_pdf  # noqa: E402
from wiki_interest.resolve import resolve_topic  # noqa: E402
from wiki_interest.run import run_analysis, write_run  # noqa: E402
from wiki_interest.summary import render_summary  # noqa: E402
from wiki_interest.verify import verify_run, write_verify  # noqa: E402
from wiki_interest.compare import compare_runs, write_compare  # noqa: E402
from wiki_interest.discover import discover, write_discover  # noqa: E402

EXIT_OK, EXIT_NO_DATA, EXIT_BAD_ARGS = 0, 2, 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki_interest.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--topic", help="topic in any language, e.g. 'intermittent fasting' or 'астрономія'")
        sp.add_argument("--topics", help="several topics separated by ';' (analyze only)")
        sp.add_argument("--topics-file", help="file with one topic per line ('#' comments allowed) for batch matrices")
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
    a.add_argument("--access", default="all-access", help="all-access (default) | desktop | mobile-web | mobile-app")
    a.add_argument("--agent", default="user", help="user (default, humans) | all-agents | spider | automated")
    a.add_argument("--spike-z", type=float, default=None, help="robust z above which a period counts as a spike (default 3.5)")
    a.add_argument("--out", help="output directory (default runs/<slug>)")

    vf = sub.add_parser("verify", help="stress-test an analyze run: devices, bots, window, fresh spot-check, baseline")
    vf.add_argument("--run", required=True, help="directory written by analyze")
    vf.add_argument("--no-cache", action="store_true")

    cp = sub.add_parser("compare", help="what changed between two analyze runs (follow-ups, changed assumptions)")
    cp.add_argument("--runs", nargs=2, required=True, metavar=("A", "B"), help="two run directories: earlier, later")
    cp.add_argument("--out", help="directory for compare.md/json (default: run B)")

    dc = sub.add_parser("discover", help="rising articles in a language edition (monthly top list vs a year earlier)")
    dc.add_argument("--lang", required=True, help="one language code, e.g. uk")
    dc.add_argument("--month", help="YYYY-MM closed month (default: last closed month)")
    dc.add_argument("--limit", type=int, default=20)
    dc.add_argument("--include", help="regex the title must match, e.g. 'астроном|космос'")
    dc.add_argument("--exclude", help="regex to drop titles, e.g. 'фільм|серіал'")
    dc.add_argument("--min-views", type=int, default=1000)
    dc.add_argument("--sustained", action="store_true", help="also fetch each candidate's 24-month trend + confidence (≈2 calls per candidate)")
    dc.add_argument("--out", help="output directory (default runs/discover-<lang>-<month>)")
    dc.add_argument("--no-cache", action="store_true")

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
    return WikiClient(cache=Cache(cache_path, bypass_reads=no_cache))


def warn(msg: str) -> None:
    print(f"WARNING: {msg}", file=sys.stderr)


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
        out[k.strip().lower()] = unquote(v.strip())  # accept URL-encoded titles copied from a browser
    return out


def _topics(args) -> list[str]:
    raw: list[str] = []
    if getattr(args, "topics_file", None):
        path = Path(args.topics_file)
        if not path.exists():
            raise ValueError(f"--topics-file {path} not found")
        raw += [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")]
    if args.topics:
        raw += [t.strip() for t in args.topics.split(";") if t.strip()]
    if args.topic:
        raw.append(args.topic.strip())
    seen: set[str] = set()
    topics = [t for t in raw if not (t in seen or seen.add(t))]
    if not topics:
        raise ValueError("no topics: pass --topic, --topics 'a;b' or --topics-file <file> (one per line)")
    return topics


def _warn_ignored(args, topics: list[str], langs: list[str], titles: dict[str, str]) -> None:
    extra = sorted(set(titles) - set(langs))
    if extra:
        warn(f"--titles for {', '.join(extra)} ignored: not in --langs {','.join(langs)}")
    if args.qid and len(topics) > 1:
        warn("--qid ignored: it applies to a single --topic, you passed several topics")


def cmd_resolve(args) -> int:
    topics = _topics(args)
    topic = topics[0]
    if len(topics) > 1:
        warn(f"resolve handles one topic; using {topic!r} and ignoring the rest")
    langs = _langs(args.langs)
    _warn_ignored(args, [topic], langs, _titles(args.titles))
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
    _warn_ignored(args, topics, langs, titles)
    validate_access_agent(args.access, args.agent)
    if args.spike_z is not None and args.spike_z <= 0:
        raise ValueError("--spike-z must be positive")
    out_dir = Path(args.out) if args.out else SKILL_ROOT / "runs" / _slug(topics, langs, args)
    client = make_client(args.no_cache)
    run = run_analysis(client, topics, langs, args.months, args.start, args.end, args.granularity, args.rank_by,
                       titles, args.qid, args.lang_hint, date.today(), out_dir,
                       access=args.access, agent=args.agent, spike_z=args.spike_z)
    summary = render_summary(run, out_dir)
    write_run(run, out_dir, summary)
    render_chart(run, out_dir / "chart.png")
    print(summary)
    if not run.usable():
        print("ERROR: no usable series — every requested language is missing or has no pageview data. "
              "Check the Resolved line, try `resolve` with --lang-hint, or pass --titles.", file=sys.stderr)
        return EXIT_NO_DATA
    return EXIT_OK


def cmd_verify(args) -> int:
    run_dir = Path(args.run)
    client = make_client(args.no_cache)
    v = verify_run(client, run_dir, date.today())
    print(write_verify(v, run_dir), end="")
    return EXIT_OK


def cmd_compare(args) -> int:
    a, b = Path(args.runs[0]), Path(args.runs[1])
    c = compare_runs(a, b)
    print(write_compare(c, Path(args.out) if args.out else b), end="")
    return EXIT_OK


def cmd_discover(args) -> int:
    lang = _langs(args.lang)[0]
    client = make_client(args.no_cache)
    d = discover(client, lang, args.month, date.today(), limit=args.limit, include=args.include,
                 exclude=args.exclude, min_views=args.min_views, sustained=args.sustained)
    out_dir = Path(args.out) if args.out else SKILL_ROOT / "runs" / f"discover-{lang}-{d['month']}"
    print(write_discover(d, out_dir), end="")
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
    if not t:  # scripts outside Latin/Cyrillic: keep the slug readable and unique
        t = "topic-" + hashlib.sha1(";".join(topics).encode("utf-8")).hexdigest()[:8]
    span = f"{args.start}_{args.end}" if args.start else f"{args.months or 24}m"
    extra = "" if (args.access, args.agent) == ("all-access", "user") else f"-{args.access}-{args.agent}"
    return f"{t}-{'-'.join(langs)}-{span}{extra}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return {"resolve": cmd_resolve, "analyze": cmd_analyze, "report": cmd_report, "verify": cmd_verify, "compare": cmd_compare, "discover": cmd_discover}[args.cmd](args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_BAD_ARGS
    except ApiError as exc:
        print(f"ERROR: API failure: {exc}\nHint: retry in a minute; check network access to wikimedia.org.",
              file=sys.stderr)
        return EXIT_NO_DATA


if __name__ == "__main__":
    sys.exit(main())
