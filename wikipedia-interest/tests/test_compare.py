import json
from datetime import date
from pathlib import Path

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.compare import compare_runs, render_compare
from wiki_interest.run import run_analysis, write_run
from wiki_interest.summary import render_summary

TODAY = date(2026, 9, 23)
FIX = Path(__file__).parent / "fixtures"


def _mock(cs_a, uk_a, months):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*pl\.wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": []}}))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [{"timestamp": f"{m}0100", "views": 50_000_000} for m in months]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [{"timestamp": f"{m}0100", "views": v} for m, v in zip(months, cs_a)]}))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [{"timestamp": f"{m}0100", "views": v} for m, v in zip(months, uk_a)]}))


def _make(tmp_path, name, langs, start, end, months, cs, uk):
    out = tmp_path / name
    run = run_analysis(WikiClient(), ["intermittent fasting"], langs, None, start, end, "monthly", "score", {}, None, None, TODAY, out)
    write_run(run, out, render_summary(run, out))
    return out


@respx.mock
def test_compare_reports_added_rows_and_metric_deltas(tmp_path):
    months = [f"2026{m:02d}" for m in range(3, 9)]  # 2026-03..2026-08
    _mock([500, 550, 600, 650, 700, 750], [900, 850, 800, 750, 700, 650], months)
    a = _make(tmp_path, "a", ["cs"], "2026-03", "2026-08", months, None, None)
    b = _make(tmp_path, "b", ["cs", "uk"], "2026-06", "2026-08", months, None, None)
    c = compare_runs(a, b)
    assert c["added_rows"] == ["intermittent fasting|uk"] and c["removed_rows"] == []
    assert c["window"]["a"]["start"] == "2026-03" and c["window"]["b"]["start"] == "2026-06"
    row = c["rows"]["intermittent fasting|cs"]
    assert set(row) >= {"pm_latest", "growth_clipped_pct_per_year", "confidence"}
    assert row["pm_latest"]["a"] != row["pm_latest"]["b"] or row["growth_clipped_pct_per_year"]["a"] != row["growth_clipped_pct_per_year"]["b"]
    text = render_compare(c)
    assert "added" in text.lower() and "intermittent fasting|uk" in text
    assert "| metric |" in text or "| row |" in text
    assert len(text.splitlines()) <= 40


@respx.mock
def test_compare_notes_changed_options(tmp_path):
    months = [f"2026{m:02d}" for m in range(6, 9)]
    _mock([500, 600, 700], [900, 800, 700], months)
    a = _make(tmp_path, "a", ["cs"], "2026-06", "2026-08", months, None, None)
    out_b = tmp_path / "b"
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs"], None, "2026-06", "2026-08", "monthly", "score", {}, None, None, TODAY, out_b, agent="all-agents")
    write_run(run, out_b, render_summary(run, out_b))
    c = compare_runs(a, out_b)
    assert c["options_changed"] == {"agent": {"a": "user", "b": "all-agents"}}
    assert "agent" in render_compare(c)
