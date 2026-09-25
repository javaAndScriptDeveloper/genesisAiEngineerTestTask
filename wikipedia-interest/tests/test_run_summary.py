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


def _mock_two_langs(cs_views, uk_views, months=("2026060100", "2026070100", "2026080100"), project=50_000_000):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": m, "views": project} for m in months]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": m, "views": v} for m, v in zip(months, cs_views)]}))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": m, "views": v} for m, v in zip(months, uk_views)]}))


@respx.mock
def test_summary_lists_confidence_reasons_for_non_high_rows(tmp_path):
    _mock_two_langs([500, 600, 700], [900, 800, 700])
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    text = render_summary(run, tmp_path)
    m = run.metrics[key("intermittent fasting", "cs")]
    assert m.confidence != "high" and m.reasons
    assert "Reasons" in text and m.reasons[0].split(" (")[0] in text


@respx.mock
def test_all_negative_growth_switches_ranking_to_volume_with_a_check(tmp_path):
    _mock_two_langs([900, 800, 700], [90, 80, 70])
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    assert all((m.growth_clipped_pct_per_year or 0) < 0 for m in run.metrics.values())
    assert run.rank_by == "volume"
    assert run.ranking[0][0] == key("intermittent fasting", "cs")
    assert any("declin" in c.lower() and "volume" in c.lower() for c in run.checks)


@respx.mock
def test_zero_project_views_in_last_period_is_flagged(tmp_path):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 50_000_000}, {"timestamp": "2026070100", "views": 50_000_000}]}))  # August not loaded
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 500}, {"timestamp": "2026070100", "views": 600}]}))
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    assert any("2026-08" in c and "project" in c.lower() and "not loaded" in c.lower() for c in run.checks)


@respx.mock
def test_assumptions_reflect_access_agent_and_spike_overrides(tmp_path):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*/aggregate/cs\.wikipedia/desktop/all-agents/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 50_000_000} for m in (6, 7, 8)]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia/desktop/all-agents/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 500} for m in (6, 7, 8)]}))
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path, access="desktop", agent="all-agents", spike_z=2.0)
    joined = " ".join(run.assumptions)
    assert "desktop" in joined and "all-agents" in joined and "2.0" in joined
    assert "agent=user" not in joined
    assert run.to_dict()["options"] == {"access": "desktop", "agent": "all-agents", "spike_z": 2.0}
