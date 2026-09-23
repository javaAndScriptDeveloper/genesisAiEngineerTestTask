import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_skill_md_short_and_links_exist():
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    body = text.split("---", 2)[2]
    assert len(body.strip().splitlines()) <= 150
    for rel in re.findall(r"\((references/[^)]+|assets/[^)]+|scripts/[^)]+)\)", text):
        assert (ROOT / rel).exists(), rel
    assert "uv run scripts/wiki_interest.py" in text
    for word in ("resolve", "analyze", "report", "confidence", "per million"):
        assert word in text


def test_methodology_mentions_thresholds():
    from wiki_interest.stats import THRESHOLDS
    text = (ROOT / "references" / "methodology.md").read_text(encoding="utf-8")
    for k in ("low_coverage_pct", "low_spike_pct", "low_p", "spike_z"):
        assert str(THRESHOLDS[k]) in text, k
