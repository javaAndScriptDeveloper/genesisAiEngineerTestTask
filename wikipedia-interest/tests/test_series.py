from datetime import date

import httpx
import pytest
import respx

from wiki_interest.api import WikiClient
from wiki_interest.series import fetch_project_totals, fetch_series, make_window, period_key

TODAY = date(2026, 9, 23)


def test_make_window_default_24_months_excludes_current_month():
    w = make_window(24, None, None, "monthly", TODAY)
    assert (w.start, w.end) == ("2024-09", "2026-08")
    assert len(w.periods) == 24 and w.periods[0] == "2024-09" and w.periods[-1] == "2026-08"
    assert w.api_range_article() == ("20240901", "20260831")
    assert w.api_range_aggregate() == ("2024090100", "2026083100")


def test_make_window_explicit_start_end_clamped_to_last_closed_month():
    w = make_window(None, "2026-01", "2026-12", "monthly", TODAY)
    assert (w.start, w.end) == ("2026-01", "2026-08")


def test_make_window_daily_periods():
    w = make_window(None, "2026-07", "2026-08", "daily", TODAY)
    assert w.periods[0] == "2026-07-01" and w.periods[-1] == "2026-08-31" and len(w.periods) == 62
    assert w.api_range_article() == ("20260701", "20260831")
    assert w.api_range_aggregate() == ("2026070100", "2026083100")


def test_make_window_rejects_bad_input():
    with pytest.raises(ValueError):
        make_window(None, "2026-08", "2026-01", "monthly", TODAY)
    with pytest.raises(ValueError):
        make_window(None, "2015-01", "2015-12", "monthly", TODAY)  # before 2015-07 floor


def test_period_key():
    assert period_key("2024010100", "monthly") == "2024-01"
    assert period_key("2024011500", "daily") == "2024-01-15"


@respx.mock
def test_fetch_series_aligns_missing_months_to_zero():
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 1_000_000}, {"timestamp": "2026070100", "views": 2_000_000}, {"timestamp": "2026080100", "views": 1_000_000}]}))
    respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 10}, {"timestamp": "2026080100", "views": 30}]}))
    c = WikiClient()
    totals = fetch_project_totals(c, "uk", w, TODAY)
    s = fetch_series(c, "t", "uk", "X", w, totals, TODAY)
    assert s.views == [10, 0, 30]
    assert s.project_views == [1_000_000, 2_000_000, 1_000_000]
    assert s.per_million == [10.0, 0.0, 30.0]
    assert s.status == "ok"


@respx.mock
def test_fetch_series_no_data_404():
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))
    s = fetch_series(WikiClient(), "t", "uk", "X", w, [1, 1, 1], TODAY)
    assert s.status == "no_data" and s.views == [0, 0, 0]


def test_fetch_series_missing_title_short_circuits():
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    s = fetch_series(WikiClient(), "t", "pl", None, w, [1, 1, 1], TODAY)
    assert s.status == "missing" and s.per_million == [0.0, 0.0, 0.0]


def test_single_month_window_has_full_month_range():
    w = make_window(1, None, None, "monthly", TODAY)
    assert (w.start, w.end) == ("2026-08", "2026-08")
    assert w.api_range_aggregate() == ("2026080100", "2026083100")


def test_is_closed_waits_for_wikimedia_to_load_the_month():
    w = make_window(None, "2026-06", "2026-08", "monthly", date(2026, 9, 23))
    assert w.is_closed(date(2026, 9, 23)) is True      # well into the next month
    assert w.is_closed(date(2026, 9, 2)) is False      # first days: last month may not be loaded yet
    older = make_window(None, "2026-05", "2026-07", "monthly", date(2026, 9, 2))
    assert older.is_closed(date(2026, 9, 2)) is True   # ends two months back: safe


@respx.mock
def test_unknown_language_code_is_a_clear_value_error():
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    respx.get(url__regex=r".*/aggregate/cz\.wikipedia.*").mock(return_value=httpx.Response(404, json={"detail": "not loaded"}))
    with pytest.raises(ValueError) as exc:
        fetch_project_totals(WikiClient(), "cz", w, TODAY)
    assert "cz.wikipedia" in str(exc.value) and "language code" in str(exc.value)


@respx.mock
def test_incomplete_aggregate_is_not_kept_in_cache(tmp_path):
    from wiki_interest.cache import Cache
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 1}, {"timestamp": "2026070100", "views": 1}]}))  # August missing
    c = WikiClient(cache=Cache(tmp_path / "c.sqlite"))
    totals = fetch_project_totals(c, "uk", w, TODAY)
    assert totals == [1, 1, 0]
    assert c.cache.get(c.aggregate_url("uk.wikipedia", "monthly", *w.api_range_aggregate())) is None


@respx.mock
def test_fetch_series_and_totals_pass_access_and_agent_into_urls():
    w = make_window(None, "2026-06", "2026-08", "monthly", TODAY)
    agg = respx.get(url__regex=r".*/aggregate/uk\.wikipedia/mobile-web/all-agents/monthly/.*").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": f"2026{m:02d}0100", "views": 1_000_000} for m in (6, 7, 8)]}))
    art = respx.get(url__regex=r".*/per-article/uk\.wikipedia/mobile-web/all-agents/X/monthly/.*").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": "2026060100", "views": 10}]}))
    c = WikiClient()
    totals = fetch_project_totals(c, "uk", w, TODAY, access="mobile-web", agent="all-agents")
    s = fetch_series(c, "t", "uk", "X", w, totals, TODAY, access="mobile-web", agent="all-agents")
    assert agg.called and art.called and s.views == [10, 0, 0]
