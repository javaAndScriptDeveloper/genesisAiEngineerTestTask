import json
from datetime import date

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.discover import discover, render_discover

TODAY = date(2026, 9, 23)


def _top(articles):
    return {"items": [{"project": "uk.wikipedia", "access": "all-access", "year": "2026", "month": "08", "day": "all-days",
                       "articles": [{"article": a, "views": v, "rank": i + 1} for i, (a, v) in enumerate(articles)]}]}


def _mock():
    respx.get(url__regex=r".*/top/uk\.wikipedia/all-access/2026/08/all-days").mock(return_value=httpx.Response(200, json=_top([
        ("Головна_сторінка", 300000), ("Спеціальна:Пошук", 100000), ("Астрономія", 5000), ("Марс", 4000), ("Погода", 3000), ("Категорія:Наука", 2500)])))
    respx.get(url__regex=r".*/top/uk\.wikipedia/all-access/2025/08/all-days").mock(return_value=httpx.Response(200, json=_top([
        ("Головна_сторінка", 320000), ("Астрономія", 2000), ("Погода", 3000)])))
    respx.get(url__regex=r".*/aggregate/uk\.wikipedia/all-access/user/monthly/2026080100/2026083100").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": "2026080100", "views": 50_000_000}]}))
    respx.get(url__regex=r".*/aggregate/uk\.wikipedia/all-access/user/monthly/2025080100/2025083100").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": "2025080100", "views": 100_000_000}]}))
    respx.get(url__regex=r".*uk\.wikipedia.*meta=siteinfo.*").mock(return_value=httpx.Response(200, json={"query": {"namespaces": {
        "0": {"id": 0, "*": ""}, "-1": {"id": -1, "*": "Спеціальна"}, "14": {"id": 14, "*": "Категорія"}}}}))
    # Марс is new to the top list: its year-ago views come from per-article
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/user/%D0%9C%D0%B0%D1%80%D1%81/monthly/20250801/20250831").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": "2025080100", "views": 500}]}))


@respx.mock
def test_discover_ranks_rising_articles_and_filters_namespaces():
    _mock()
    d = discover(WikiClient(), "uk", "2026-08", TODAY, limit=10)
    titles = [r["title"] for r in d["rows"]]
    assert "Головна_сторінка" not in titles and "Спеціальна:Пошук" not in titles and "Категорія:Наука" not in titles
    assert titles[0] == "Марс"          # 500 → 4000 views, per-million 5 → 80: biggest rise
    assert titles[1] == "Астрономія"    # 2000 → 5000 with project halving: per-million 20 → 100
    mars = d["rows"][0]
    assert mars["new_in_top"] is True and mars["pm_now"] == 80.0 and mars["pm_year_ago"] == 5.0
    assert d["rows"][-1]["title"] == "Погода" and d["rows"][-1]["growth_pct"] > 0  # flat views, project halved → pm doubled
    text = render_discover(d)
    assert "Марс" in text and "--titles" in text and len(text.splitlines()) <= 40


@respx.mock
def test_discover_filter_and_exclude_regex():
    _mock()
    d = discover(WikiClient(), "uk", "2026-08", TODAY, limit=10, include=r"Астр|Марс", exclude=r"Марс")
    assert [r["title"] for r in d["rows"]] == ["Астрономія"]


@respx.mock
def test_discover_rejects_current_or_future_month():
    _mock()
    import pytest
    with pytest.raises(ValueError):
        discover(WikiClient(), "uk", "2026-09", TODAY)


@respx.mock
def test_discover_sustained_adds_trend_and_confidence_and_drops_junk():
    _mock()
    # add a junk title to the current top list
    respx.get(url__regex=r".*/top/uk\.wikipedia/all-access/2026/08/all-days").mock(return_value=httpx.Response(200, json=_top([
        ("Головна_сторінка", 300000), ("wiki.phtml", 20000), ("Астрономія", 5000), ("Марс", 4000)])))
    months = [f"{2024 + (i // 12):04d}{i % 12 + 1:02d}" for i in range(8, 8 + 24)]  # 2024-09..2026-08
    respx.get(url__regex=r".*/aggregate/uk\.wikipedia/all-access/user/monthly/2024090100/2026083100").mock(
        return_value=httpx.Response(200, json={"items": [{"timestamp": f"{m}0100", "views": 50_000_000} for m in months]}))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/user/.*/monthly/20240901/20260831").mock(
        side_effect=lambda req: httpx.Response(200, json={"items": [
            {"timestamp": f"{m}0100", "views": (1000 + 100 * i) if "%D0%90%D1%81" in str(req.url) else 4000} for i, m in enumerate(months)]}))
    d = discover(WikiClient(), "uk", "2026-08", TODAY, limit=10, sustained=True)
    titles = [r["title"] for r in d["rows"]]
    assert "wiki.phtml" not in titles
    astro = next(r for r in d["rows"] if r["title"] == "Астрономія")
    assert astro["growth_clipped_pct_per_year"] is not None and astro["growth_clipped_pct_per_year"] > 30
    assert astro["confidence"] in ("high", "medium", "low")
    mars = next(r for r in d["rows"] if r["title"] == "Марс")
    assert abs(mars["growth_clipped_pct_per_year"]) < 1  # flat 24-month series: attention spike, not a trend
    text = render_discover(d)
    assert "growth/yr" in text and "confidence" in text
