from datetime import date

import pypdf

from wiki_interest.charts import render_chart
from wiki_interest.pdf import render_pdf
from wiki_interest.resolve import LangResolution, TopicResolution
from wiki_interest.run import RunResult, key, write_run
from wiki_interest.series import Series, make_window
from wiki_interest.stats import compute_metrics
from wiki_interest.summary import render_summary

TODAY = date(2026, 9, 23)


def _prepare(tmp_path):
    w = make_window(24, None, None, "monthly", TODAY)
    pm = [10.0 + i for i in range(24)]
    s = Series("astronomy", "uk", "Астрономія", w.periods, [int(x * 100) for x in pm], [10_000_000] * 24, pm, "ok")
    res = {"astronomy": TopicResolution("astronomy", "Q333", "astronomy", {"uk": LangResolution("uk", "found", "Астрономія")})}
    run = RunResult(["astronomy"], ["uk"], w, "score", res, [s], {key("astronomy", "uk"): compute_metrics(s)},
                    [(key("astronomy", "uk"), 5.0)], ["window ok"], ["assumption A"], ["limitation L"], ["follow"])
    write_run(run, tmp_path, render_summary(run, tmp_path))
    render_chart(run, tmp_path / "chart.png")
    return run


def test_pdf_one_page_short_notes(tmp_path):
    _prepare(tmp_path)
    out = render_pdf(tmp_path, tmp_path / "report.pdf", "Астрономія в укр. Wikipedia", "Interest grows steadily.\n- bullet one\n- bullet two", "uk")
    r = pypdf.PdfReader(out)
    assert len(r.pages) == 1
    assert "Астрономія" in r.pages[0].extract_text()


def test_pdf_one_page_very_long_notes(tmp_path):
    _prepare(tmp_path)
    notes = "\n".join(f"Paragraph {i}: " + "word " * 60 for i in range(80))
    out = render_pdf(tmp_path, tmp_path / "report.pdf", None, notes, "en")
    assert len(pypdf.PdfReader(out).pages) == 1


def test_pdf_missing_chart_still_renders(tmp_path):
    _prepare(tmp_path)
    (tmp_path / "chart.png").unlink()
    out = render_pdf(tmp_path, tmp_path / "report.pdf", None, "", "en")
    assert len(pypdf.PdfReader(out).pages) == 1


def test_pdf_escapes_angle_brackets_in_limitations(tmp_path):
    run = _prepare(tmp_path)
    run.limitations.append("pl: no article; pass --titles pl=<title> only if it is the same topic & confirmed.")
    write_run(run, tmp_path, render_summary(run, tmp_path))
    out = render_pdf(tmp_path, tmp_path / "report.pdf", None, "Notes with <b>tags</b> & ampersand", "en")
    assert len(pypdf.PdfReader(out).pages) == 1
