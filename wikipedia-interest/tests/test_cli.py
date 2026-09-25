import importlib.util
import json
from pathlib import Path

import httpx
import respx

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"


def _cli():
    spec = importlib.util.spec_from_file_location("wiki_interest_cli", ROOT / "scripts" / "wiki_interest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_world(uk_ok=True):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": []}}))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 50_000_000} for m in (6, 7, 8)]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 500}, {"timestamp": "2026070100", "views": 600}, {"timestamp": "2026080100", "views": 700}]}))
    if uk_ok:
        respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
            {"timestamp": "2026060100", "views": 900}, {"timestamp": "2026070100", "views": 800}, {"timestamp": "2026080100", "views": 700}]}))
    else:
        respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))


@respx.mock
def test_resolve_prints_table(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["resolve", "--topic", "intermittent fasting", "--langs", "pl,cs"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "cs" in out and "Přerušovaný půst" in out and "missing" in out and "Q1666254" in out


@respx.mock
def test_analyze_writes_files_and_prints_summary(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run1"
    rc = _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "cs,uk", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    for f in ("result.json", "summary.md", "chart.png", "data.csv"):
        assert (out_dir / f).exists(), f
    assert out.startswith("# ") and "## Checks" in out


@respx.mock
def test_analyze_exit_2_when_nothing_usable(capsys, tmp_path, monkeypatch):
    _mock_world(uk_ok=False)
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run2"
    rc = _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "pl,uk", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "no usable" in captured.err.lower()
    assert (out_dir / "summary.md").exists()


def test_analyze_bad_args_exit_3(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["analyze", "--topic", "x", "--langs", "uk", "--start", "2026-08", "--end", "2026-01", "--out", str(tmp_path / "r")])
    assert rc == 3
    assert "after end" in capsys.readouterr().err


def test_analyze_requires_topic(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["analyze", "--langs", "uk", "--out", str(tmp_path / "r")])
    assert rc == 3


@respx.mock
def test_report_creates_pdf(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run3"
    assert _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "cs", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)]) == 0
    rc = _cli().main(["report", "--run", str(out_dir), "--title", "IF in Czech", "--notes", "Grows.\n- keep watching", "--lang", "uk"])
    assert rc == 0
    assert (out_dir / "report.pdf").exists()
    assert "report.pdf" in capsys.readouterr().out


def test_report_missing_run_exit_3(capsys, tmp_path):
    rc = _cli().main(["report", "--run", str(tmp_path / "nope")])
    assert rc == 3
    assert "analyze" in capsys.readouterr().err


@respx.mock
def test_analyze_unknown_language_exit_3_with_hint(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    respx.get(url__regex=r".*/aggregate/cz\.wikipedia.*").mock(return_value=httpx.Response(404, json={"detail": "not loaded"}))
    rc = _cli().main(["analyze", "--topic", "x", "--langs", "cz", "--start", "2026-06", "--end", "2026-08", "--out", str(tmp_path / "r")])
    err = capsys.readouterr().err
    assert rc == 3
    assert "cz.wikipedia" in err and "cs" in err


@respx.mock
def test_report_out_directory_gets_report_pdf_inside(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run4"
    assert _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "cs", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)]) == 0
    target = tmp_path / "reports"
    rc = _cli().main(["report", "--run", str(out_dir), "--out", str(target)])
    assert rc == 0
    assert (target / "report.pdf").exists(), "a --out without .pdf suffix is a directory"
    assert "report.pdf" in capsys.readouterr().out


def test_analyze_rejects_bad_access_value(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["analyze", "--topic", "x", "--langs", "uk", "--access", "mobile", "--out", str(tmp_path / "r")])
    assert rc == 3
    assert "--access" in capsys.readouterr().err


def test_verify_missing_run_exit_3(capsys, tmp_path):
    rc = _cli().main(["verify", "--run", str(tmp_path / "nope")])
    assert rc == 3
    assert "analyze" in capsys.readouterr().err


def test_compare_missing_run_exit_3(capsys, tmp_path):
    rc = _cli().main(["compare", "--runs", str(tmp_path / "a"), str(tmp_path / "b")])
    assert rc == 3
