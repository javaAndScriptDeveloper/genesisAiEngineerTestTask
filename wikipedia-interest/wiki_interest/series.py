"""Time windows and per-topic/language pageview series.

Views are normalized to per-million of the whole project's user pageviews in
the same period, which is the only fair way to compare a 2M-article English
wiki with a 1M-article Ukrainian one.
"""
from __future__ import annotations

import calendar
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from .api import NoData, WikiClient

DATA_FLOOR = "2015-07"  # Pageviews API starts 2015-07-01


@dataclass
class Window:
    start: str
    end: str
    granularity: str
    periods: list[str] = field(default_factory=list)

    def api_range_article(self) -> tuple[str, str]:
        y, m = _ym(self.start)
        y2, m2 = _ym(self.end)
        return f"{y:04d}{m:02d}01", f"{y2:04d}{m2:02d}{calendar.monthrange(y2, m2)[1]:02d}"

    def api_range_aggregate(self) -> tuple[str, str]:
        y, m = _ym(self.start)
        y2, m2 = _ym(self.end)
        if self.granularity == "daily":
            return f"{y:04d}{m:02d}0100", f"{y2:04d}{m2:02d}{calendar.monthrange(y2, m2)[1]:02d}00"
        return f"{y:04d}{m:02d}0100", f"{y2:04d}{m2:02d}0100"

    def is_closed(self, today: date) -> bool:
        return self.end < today.strftime("%Y-%m")

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "granularity": self.granularity, "n_periods": len(self.periods)}


@dataclass
class Series:
    topic: str
    lang: str
    title: str | None
    periods: list[str]
    views: list[int]
    project_views: list[int]
    per_million: list[float]
    status: str
    note: str = ""
    granularity: str = "monthly"

    def to_dict(self) -> dict:
        return asdict(self)


def make_window(months: int | None, start: str | None, end: str | None, granularity: str, today: date) -> Window:
    if granularity not in ("monthly", "daily"):
        raise ValueError(f"granularity must be monthly or daily, got {granularity}")
    last_closed = _shift_month(today.strftime("%Y-%m"), -1)
    if start or end:
        if not (start and end):
            raise ValueError("--start and --end must be given together (YYYY-MM)")
        _ym(start)
        _ym(end)
        if end > last_closed:
            end = last_closed
    else:
        months = months or 24
        if months < 1:
            raise ValueError("--months must be >= 1")
        end = last_closed
        start = _shift_month(end, -(months - 1))
    if start > end:
        raise ValueError(f"window start {start} is after end {end} (end is clamped to last closed month {last_closed})")
    if start < DATA_FLOOR:
        raise ValueError(f"Pageviews data starts {DATA_FLOOR}; requested start {start}")
    periods = _month_list(start, end) if granularity == "monthly" else _day_list(start, end)
    return Window(start, end, granularity, periods)


def period_key(timestamp: str, granularity: str) -> str:
    if granularity == "daily":
        return f"{timestamp[0:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
    return f"{timestamp[0:4]}-{timestamp[4:6]}"


def fetch_project_totals(client: WikiClient, lang: str, window: Window, today: date) -> list[int]:
    start, end = window.api_range_aggregate()
    items = client.aggregate(f"{lang}.wikipedia", window.granularity, start, end, permanent=window.is_closed(today))
    return _align(items, window)


def fetch_series(client: WikiClient, topic: str, lang: str, title: str | None, window: Window,
                 project_views: list[int], today: date) -> Series:
    zeros = [0] * len(window.periods)
    if title is None:
        return Series(topic, lang, None, window.periods, zeros, project_views, [0.0] * len(zeros),
                      "missing", "no article in this language", window.granularity)
    start, end = window.api_range_article()
    try:
        items = client.per_article(f"{lang}.wikipedia", title, window.granularity, start, end,
                                   permanent=window.is_closed(today))
    except NoData as exc:
        return Series(topic, lang, title, window.periods, zeros, project_views, [0.0] * len(zeros),
                      "no_data", f"API has no pageview data: {exc}", window.granularity)
    views = _align(items, window)
    pm = [round(v / p * 1e6, 4) if p else 0.0 for v, p in zip(views, project_views)]
    return Series(topic, lang, title, window.periods, views, project_views, pm, "ok", "", window.granularity)


# ---- helpers -------------------------------------------------------------
def _ym(s: str) -> tuple[int, int]:
    try:
        y_s, m_s = s.split("-")
        y, m = int(y_s), int(m_s)
    except ValueError as exc:
        raise ValueError(f"expected YYYY-MM, got {s!r}") from exc
    if not 1 <= m <= 12:
        raise ValueError(f"month out of range in {s!r}")
    return y, m


def _shift_month(ym: str, delta: int) -> str:
    y, m = _ym(ym)
    idx = y * 12 + (m - 1) + delta
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def _month_list(start: str, end: str) -> list[str]:
    out, cur = [], start
    while cur <= end:
        out.append(cur)
        cur = _shift_month(cur, 1)
    return out


def _day_list(start: str, end: str) -> list[str]:
    y, m = _ym(start)
    y2, m2 = _ym(end)
    d = date(y, m, 1)
    last = date(y2, m2, calendar.monthrange(y2, m2)[1])
    out = []
    while d <= last:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _align(items: list[dict], window: Window) -> list[int]:
    by_key = {period_key(i["timestamp"], window.granularity): int(i.get("views", 0)) for i in items}
    return [by_key.get(p, 0) for p in window.periods]
