"""SQLite cache for raw API responses.

Closed-month pageview windows never change, so they are stored permanently.
Everything else (current month, Wikidata, MediaWiki lookups) gets a TTL.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

PERMANENT = None
DEFAULT_TTL_SECONDS = 7 * 24 * 3600


class Cache:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses ("
            "url TEXT PRIMARY KEY, body TEXT NOT NULL, "
            "fetched_at TEXT NOT NULL, ttl_until TEXT)"
        )
        self._conn.commit()
        self.hits = 0
        self.misses = 0

    def get(self, url: str, now: datetime | None = None) -> str | None:
        now = now or _utcnow()
        row = self._conn.execute(
            "SELECT body, ttl_until FROM responses WHERE url = ?", (url,)
        ).fetchone()
        if row is None:
            self.misses += 1
            return None
        body, ttl_until = row
        if ttl_until is not None and datetime.fromisoformat(ttl_until) < now:
            self.misses += 1
            return None
        self.hits += 1
        return body

    def put(self, url: str, body: str, ttl_seconds: int | None, now: datetime | None = None) -> None:
        now = now or _utcnow()
        ttl_until = None
        if ttl_seconds is not None:
            ttl_until = (now + timedelta(seconds=ttl_seconds)).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO responses(url, body, fetched_at, ttl_until) VALUES (?, ?, ?, ?)",
            (url, body, now.isoformat(), ttl_until),
        )
        self._conn.commit()

    def delete(self, url: str) -> None:
        self._conn.execute("DELETE FROM responses WHERE url = ?", (url,))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def _utcnow() -> datetime:
    """Naive UTC timestamp (callers may pass naive datetimes for testing)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
