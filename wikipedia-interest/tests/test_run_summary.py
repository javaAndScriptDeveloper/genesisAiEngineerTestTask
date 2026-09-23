import json
from datetime import date
from pathlib import Path

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.run import key, load_run, run_analysis, write_run
from wiki_interest.summary import render_summary

TODAY = date(2026, 9, 23)
FIX = Path(__file__).parent / "fixtures"


def _mock_world():
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*pl\.wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": [{"title": "Post przerywany"}]}}))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 50_000_000} for m in (6, 7, 8)]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 500}, {"timestamp": "2026070100", "views": 600}, {"timestamp": "2026080100", "views": 700}]}))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))


@respx.mock
def test_run_analysis_partial_success(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["pl", "cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    assert [s.status for s in run.series] == ["missing", "ok", "no_data"]
    assert key("intermittent fasting", "cs") in run.metrics
    assert run.ranking[0][0] == key("intermittent fasting", "cs")
    assert any("pl" in c and "missing" in c.lower() for c in run.checks)
    assert any("uk" in c and "no pageview data" in c.lower() for c in run.checks)
    assert any("current month" in c.lower() for c in run.checks)
    assert any("Post przerywany" in l for l in run.limitations)
    assert run.follow_ups and any("report" in f for f in run.follow_ups)


@respx.mock
def test_summary_is_short_and_complete(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["pl", "cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    text = render_summary(run, tmp_path)
    lines = text.splitlines()
    assert len(lines) <= 40
    assert lines[0].startswith("# ")
    for section in ("## Ranking", "## Checks", "## Limitations", "## Suggested follow-ups"):
        assert section in text
    assert "Přerušovaný půst" in text and "MISSING" in text and "NO DATA" in text
    assert "| topic | lang |" in text
    assert "confidence" in text


@respx.mock
def test_write_and_load_run(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    write_run(run, tmp_path, render_summary(run, tmp_path))
    assert (tmp_path / "result.json").exists() and (tmp_path / "summary.md").exists()
    raw = (tmp_path / "data.csv").read_bytes()
    assert b"\r" not in raw  # LF only, so git and pandas see the same file
    csv = raw.decode().splitlines()
    assert csv[0] == "topic,lang,title,period,views,project_views,per_million"
    assert len(csv) == 4
    d = load_run(tmp_path)
    assert d["metrics"][key("intermittent fasting", "cs")]["confidence"] in ("low", "medium", "high")
    assert d["window"]["start"] == "2026-06"


@respx.mock
def test_strong_seasonality_is_surfaced_in_checks(tmp_path):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json={"search": [{"id": "Q333", "label": "astronomy", "description": "science"}]}))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json={"entities": {"Q333": {"sitelinks": {"ukwiki": {"title": "Астрономія"}}, "labels": {"en": {"value": "astronomy"}}}}}))
    months = [f"{2024 + (i // 12):04d}{i % 12 + 1:02d}" for i in range(24)]  # 2024-01 .. 2025-12
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"{m}0100", "views": 100_000_000} for m in months]}))
    respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"{m}0100", "views": 5000 if m.endswith("09") else 1000} for m in months]}))
    run = run_analysis(WikiClient(), ["astronomy"], ["uk"], None, "2024-01", "2025-12", "monthly", "score", {}, None, None, TODAY, tmp_path)
    m = run.metrics[key("astronomy", "uk")]
    assert m.seasonality_amp is not None and m.seasonality_amp > 1
    assert any("seasonal" in c.lower() and "same months" in c.lower() for c in run.checks)
