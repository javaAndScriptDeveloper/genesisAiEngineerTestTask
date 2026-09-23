from datetime import date

from wiki_interest.charts import render_chart
from wiki_interest.resolve import LangResolution, TopicResolution
from wiki_interest.run import RunResult, key
from wiki_interest.series import Series, make_window
from wiki_interest.stats import compute_metrics

TODAY = date(2026, 9, 23)


def _run(n_topics=1):
    w = make_window(24, None, None, "monthly", TODAY)
    topics = [f"topic{i}" for i in range(n_topics)]
    series, metrics, res = [], {}, {}
    for t in topics:
        res[t] = TopicResolution(t, "Q1", t, {"uk": LangResolution("uk", "found", "T"), "pl": LangResolution("pl", "missing", None)})
        pm = [10.0 + i for i in range(24)]
        pm[7] = 400.0
        s = Series(t, "uk", "T", w.periods, [int(x * 100) for x in pm], [10_000_000] * 24, pm, "ok")
        series.append(s)
        series.append(Series(t, "pl", None, w.periods, [0] * 24, [1] * 24, [0.0] * 24, "missing"))
        metrics[key(t, "uk")] = compute_metrics(s)
    return RunResult(topics, ["uk", "pl"], w, "score", res, series, metrics, [(key(t, "uk"), 1.0) for t in topics])


def test_render_chart_png(tmp_path):
    p = render_chart(_run(), tmp_path / "chart.png")
    assert p.exists() and p.stat().st_size > 10_000
    assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_chart_multi_topic_small_multiples(tmp_path):
    p = render_chart(_run(3), tmp_path / "chart.png")
    assert p.exists() and p.stat().st_size > 10_000
