"""Live API checks. Run with: uv run pytest -m network"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.network


def _cli():
    spec = importlib.util.spec_from_file_location("wiki_interest_cli", ROOT / "scripts" / "wiki_interest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_intermittent_fasting_pl_cs(tmp_path, capsys):
    rc = _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "pl,cs", "--months", "24", "--out", str(tmp_path / "if")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Přerušovaný půst" in out
    assert (tmp_path / "if" / "chart.png").exists()


def test_astronomy_uk_confidence_present(tmp_path, capsys):
    rc = _cli().main(["analyze", "--topic", "астрономія", "--langs", "uk", "--months", "24", "--out", str(tmp_path / "astro")])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Астрономія" in out and "| uk |" in out


def test_english_multi_lang_report(tmp_path, capsys):
    cli = _cli()
    assert cli.main(["analyze", "--topic", "English language", "--langs", "pl,cs,uk", "--months", "12", "--out", str(tmp_path / "en")]) == 0
    assert cli.main(["report", "--run", str(tmp_path / "en"), "--notes", "Test run.", "--lang", "uk"]) == 0
    assert (tmp_path / "en" / "report.pdf").exists()
