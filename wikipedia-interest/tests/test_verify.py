import json
from datetime import date
from pathlib import Path

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.cache import Cache
from wiki_interest.run import run_analysis, write_run
from wiki_interest.summary import render_summary
from wiki_interest.verify import render_verify, verify_run

TODAY = date(2026, 9, 23)
FIX = Path(__file__).parent / "fixtures"
MONTHS = [f"{2024 + (i // 12):04d}{i % 12 + 1:02d}" for i in range(9, 9 + 24)]  # 2024-10 .. 2026-09 → clamp to 2026-08
MONTHS = [m for m in MONTHS if m <= "202608"]


def _items(values):
    return {"items": [{"timestamp": f"{m}0100", "views": v} for m, v in zip(MONTHS, values)]}


def _rising(base, factor=1.5):
    return [int(base * factor ** (i / 12)) for i in range(len(MONTHS))]


def _falling(base, factor=0.6):
    return [int(base * factor ** (i / 12)) for i in range(len(MONTHS))]


def _mock(user_all, desktop, mobile, all_agents, project=50_000_000):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json={"search": [{"id": "Q333", "label": "astronomy", "description": "science"}]}))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json={"entities": {"Q333": {"sitelinks": {"ukwiki": {"title": "Астрономія"}}, "labels": {"en": {"value": "astronomy"}}}}}))
    respx.get(url__regex=r".*/aggregate/uk\.wikipedia/[a-z-]+/[a-z-]+/monthly/.*").mock(return_value=httpx.Response(200, json=_items([project] * len(MONTHS))))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/user/.*/monthly/2024.*").mock(return_value=httpx.Response(200, json=_items(user_all)))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/desktop/user/.*").mock(return_value=httpx.Response(200, json=_items(desktop)))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/mobile-web/user/.*").mock(return_value=httpx.Response(200, json=_items(mobile)))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/all-agents/.*").mock(return_value=httpx.Response(200, json=_items(all_agents)))
    # spot check: single-month fresh fetch answers with the same series value
    def spot(request):
        ym = request.url.path.split("/")[-2][:6]
        i = MONTHS.index(ym)
        return httpx.Response(200, json={"items": [{"timestamp": f"{ym}0100", "views": user_all[i]}]})
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/user/.*/monthly/2026\d{4}/2026\d{4}").mock(side_effect=spot)
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/all-access/user/.*/monthly/2025\d{4}/2025\d{4}").mock(side_effect=spot)


def _run(tmp_path, cache=None):
    client = WikiClient(cache=cache)
    run = run_analysis(client, ["astronomy"], ["uk"], None, "2024-10", "2026-08", "monthly", "score", {}, None, None, TODAY, tmp_path)
    write_run(run, tmp_path, render_summary(run, tmp_path))
    return client


@respx.mock
def test_consistent_signals_are_robust(tmp_path):
    user = _rising(1000)
    _mock(user, [v // 2 for v in user], [v // 2 for v in user], [int(v * 1.1) for v in user])
    client = _run(tmp_path)
    v = verify_run(client, tmp_path, TODAY)
    row = v["rows"]["astronomy|uk"]
    assert row["verdict"] == "robust", row
    assert row["checks"]["devices"]["status"] == "ok"
    assert row["checks"]["bots"]["status"] == "ok" and 5 < row["checks"]["bots"]["bot_share_pct"] < 15
    assert row["checks"]["window"]["status"] == "ok"
    assert row["checks"]["spot_check"]["status"] == "ok"
    assert "relative" in row["checks"]["baseline"]
    text = render_verify(v)
    assert "robust" in text and len(text.splitlines()) <= 30


@respx.mock
def test_device_disagreement_is_fragile(tmp_path):
    user = _rising(1000)
    _mock(user, _falling(800), _rising(200, 3.0), [int(v * 1.05) for v in user])
    client = _run(tmp_path)
    row = verify_run(client, tmp_path, TODAY)["rows"]["astronomy|uk"]
    assert row["checks"]["devices"]["status"] == "alert"
    assert row["verdict"] == "fragile" and any("desktop" in r for r in row["reasons"])


@respx.mock
def test_bot_heavy_traffic_is_fragile(tmp_path):
    user = _rising(1000)
    _mock(user, [v // 2 for v in user], [v // 2 for v in user], [int(v * 2.3) for v in user])  # ~57 % bots
    client = _run(tmp_path)
    row = verify_run(client, tmp_path, TODAY)["rows"]["astronomy|uk"]
    assert row["checks"]["bots"]["status"] == "alert" and row["checks"]["bots"]["bot_share_pct"] > 50
    assert row["verdict"] == "fragile"


@respx.mock
def test_spot_check_catches_a_poisoned_cache(tmp_path):
    user = _rising(1000)
    _mock(user, [v // 2 for v in user], [v // 2 for v in user], [int(v * 1.05) for v in user])
    cache = Cache(tmp_path / "c.sqlite")
    client = _run(tmp_path, cache=cache)
    # poison: rewrite result.json so one month's stored views differs from the API
    data = json.loads((tmp_path / "result.json").read_text())
    data["series"][0]["views"] = [v + 999 for v in data["series"][0]["views"]]
    (tmp_path / "result.json").write_text(json.dumps(data))
    row = verify_run(client, tmp_path, TODAY)["rows"]["astronomy|uk"]
    assert row["checks"]["spot_check"]["status"] == "alert"


@respx.mock
def test_window_sensitivity_flags_sign_flip(tmp_path):
    # rising for 21 months, then a crash in the last 3 → without the tail the trend is positive, with it it is not
    user = _rising(1000)[:21] + [50, 40, 30]
    _mock(user, [v // 2 for v in user], [v // 2 for v in user], [int(v * 1.05) for v in user])
    client = _run(tmp_path)
    row = verify_run(client, tmp_path, TODAY)["rows"]["astronomy|uk"]
    assert row["checks"]["window"]["status"] in ("warn", "alert")
    assert row["verdict"] in ("mixed", "fragile")


def test_flat_trend_sign_flip_is_not_fragile():
    from wiki_interest.series import Series
    from wiki_interest.verify import _window_sensitivity
    periods = [f"{2024 + (i // 12):04d}-{i % 12 + 1:02d}" for i in range(24)]
    pm = [100 + (1 if i % 2 else -1) * 0.5 + (0.8 if i > 20 else 0) for i in range(24)]  # essentially flat
    s = Series("t", "uk", "T", periods, [int(x * 1000) for x in pm], [1_000_000] * 24, pm, "ok")
    assert _window_sensitivity(s, None)["status"] == "ok"


@respx.mock
def test_verify_honours_run_access_and_agent(tmp_path):
    # run measured on desktop only: bots must compare all-agents vs user *on desktop*, spot check must re-fetch desktop
    user = _rising(1000)
    def spot_desktop(request):  # registered first: respx matches routes in insertion order
        ym = request.url.path.split("/")[-2][:6]
        return httpx.Response(200, json={"items": [{"timestamp": f"{ym}0100", "views": user[MONTHS.index(ym)]}]})
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/desktop/user/.*/monthly/(2025|2026)\d{4}/(2025|2026)\d{4}$").mock(side_effect=spot_desktop)
    _mock(user, [v for v in user], [v // 2 for v in user], [int(v * 1.1) for v in user])
    respx.get(url__regex=r".*/per-article/uk\.wikipedia/desktop/all-agents/.*").mock(return_value=httpx.Response(200, json=_items([int(v * 1.1) for v in user])))
    client = WikiClient()
    run = run_analysis(client, ["astronomy"], ["uk"], None, "2024-10", "2026-08", "monthly", "score", {}, None, None, TODAY, tmp_path, access="desktop")
    write_run(run, tmp_path, render_summary(run, tmp_path))
    row = verify_run(client, tmp_path, TODAY)["rows"]["astronomy|uk"]
    assert row["checks"]["bots"]["status"] == "ok" and 5 < row["checks"]["bots"]["bot_share_pct"] < 15
    assert row["checks"]["spot_check"]["status"] == "ok"
    assert row["checks"]["devices"]["status"] == "ok" and "n/a" in row["checks"]["devices"]["detail"]
    assert row["verdict"] == "robust"


def test_user_above_all_agents_is_a_warning():
    from wiki_interest.verify import _bots_from_totals
    assert _bots_from_totals(total_all=100, total_user=120)["status"] == "warn"


def test_daily_window_check_is_not_applicable():
    from wiki_interest.series import Series
    from wiki_interest.verify import _window_sensitivity
    periods = [f"2026-08-{d:02d}" for d in range(1, 32)]
    pm = [10.0 + d for d in range(31)]
    s = Series("t", "uk", "T", periods, [int(x * 100) for x in pm], [1_000_000] * 31, pm, "ok", "", "daily")
    r = _window_sensitivity(s, None)
    assert r["status"] == "ok" and "daily" in r["detail"]
