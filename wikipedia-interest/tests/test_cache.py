from datetime import datetime, timedelta
from pathlib import Path

from wiki_interest.cache import Cache


def test_miss_then_hit(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite")
    assert c.get("u1") is None
    c.put("u1", "{}", ttl_seconds=None)
    assert c.get("u1") == "{}"
    assert c.hits == 1 and c.misses == 1


def test_ttl_expiry(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite")
    t0 = datetime(2026, 1, 1)
    c.put("u", "a", ttl_seconds=60, now=t0)
    assert c.get("u", now=t0 + timedelta(seconds=59)) == "a"
    assert c.get("u", now=t0 + timedelta(seconds=61)) is None


def test_permanent_never_expires(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite")
    t0 = datetime(2026, 1, 1)
    c.put("u", "a", ttl_seconds=None, now=t0)
    assert c.get("u", now=t0 + timedelta(days=3650)) == "a"


def test_put_overwrites(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite")
    c.put("u", "a", None)
    c.put("u", "b", None)
    assert c.get("u") == "b"


def test_creates_parent_dir(tmp_path: Path):
    c = Cache(tmp_path / "deep" / "dir" / "c.sqlite")
    c.put("u", "a", None)
    assert (tmp_path / "deep" / "dir" / "c.sqlite").exists()


def test_cache_uses_wal_and_busy_timeout(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite")
    assert c._conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert c._conn.execute("PRAGMA busy_timeout").fetchone()[0] >= 10000


def test_cache_bypass_reads_counts_misses(tmp_path: Path):
    c = Cache(tmp_path / "c.sqlite", bypass_reads=True)
    c.put("u", "a", None)
    assert c.get("u") is None and c.misses == 1 and c.bypass_reads is True
