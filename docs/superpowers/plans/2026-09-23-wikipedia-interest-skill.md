# Wikipedia Interest Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `wikipedia-interest` Agent Skill: a Python CLI (`resolve` / `analyze` / `report`) that turns Wikipedia pageview data into cross-language interest comparisons with a confidence rating, a chart and a one-page PDF, plus an eval harness proving it works on Claude Haiku 4.5.

**Architecture:** One `uv`-managed Python package inside the skill directory. Thin HTTP layer with SQLite cache → resolver (Wikidata) → series fetch/normalize → pure-numpy stats → deterministic `summary.md` + `result.json` + `chart.png` → reportlab PDF. A single argparse entrypoint wires it so an agent needs 1–3 tool calls per question. An OpenRouter tool-calling harness at repo root runs the task's example prompts against Haiku 4.5.

**Tech Stack:** Python ≥3.12, uv, httpx, numpy, matplotlib, reportlab; dev: pytest, respx, pypdf. `skills-ref` (uvx) for validation.

**Spec:** `docs/superpowers/specs/2026-09-23-wikipedia-interest-skill-design.md`

## Global Constraints

- Skill root is `wikipedia-interest/` at repo root; frontmatter `name: wikipedia-interest` (spec §3, §8).
- All skill code, references, assets and tests live inside `wikipedia-interest/`; eval harness lives in repo-root `eval/` (spec §9).
- No compiled binaries committed; deps pinned by `uv.lock` (task requirement).
- `SKILL.md` body ≤ 150 lines; `summary.md` ≤ 40 lines (spec §3, §7).
- Pageviews always `access=all-access`, `agent=user`; current month excluded; default window 24 full months (spec §2).
- PDF is exactly one A4 page, pure Python (reportlab + matplotlib DejaVuSans) (spec §4.3).
- Confidence thresholds exactly as spec §6: low if `coverage_pct < 70` or `spike_share_pct > 30` or `p > 0.10` or `|growth − growth_clipped| > 25` or `views_total < 1000`; medium if `coverage_pct < 90` or `spike_share_pct > 10` or `p > 0.05` or `N < 24`; else high.
- Rank weights: high 1.0, medium 0.6, low 0.25 (spec §6).
- Exit codes: 0 ok/partial, 2 no usable series, 3 bad args (spec §4.2).
- Cache: closed-month windows permanent, everything else TTL 7 days (spec §5.2).
- All commands run from skill root via `uv run scripts/wiki_interest.py …`; tests via `uv run pytest`.
- Commit after every task; message subject ≤ 72 chars, imperative, body says why, ends with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.

## Review Focus

1. **Title with slash or non-ASCII** (e.g. `AC/DC`, `Přerušovaný půst`): must be percent-encoded with `safe=""` so the pageviews URL has no raw `/`. Test pinned in Task 3.
2. **Window shorter than 12 months**: `yoy_pct`, `pm_year_ago`, `seasonality_amp` must be `None`, not crash or divide by zero. Test pinned in Task 6.
3. **All requested languages missing**: `analyze` exits 2 with a stderr hint, still writes `summary.md` listing missing langs. Test pinned in Task 10.
4. **Very long `--notes`** (thousands of chars): PDF stays one page (font shrink then truncation). Test pinned in Task 9.
5. **Series with all zeros / MAD = 0** (dead article): no spikes, growth 0, confidence low with `views_total < 1000` reason, no NaN in JSON. Test pinned in Task 6.

---

### Task 1: Scaffold skill directory, uv project, valid SKILL.md, test runner

**Files:**
- Create: `wikipedia-interest/pyproject.toml`
- Create: `wikipedia-interest/.python-version`
- Create: `wikipedia-interest/SKILL.md` (minimal, replaced fully in Task 11)
- Create: `wikipedia-interest/wiki_interest/__init__.py`
- Create: `wikipedia-interest/tests/__init__.py` (empty)
- Create: `wikipedia-interest/tests/test_smoke.py`
- Create: `wikipedia-interest/scripts/.gitkeep`

**Interfaces:**
- Produces: `wiki_interest.__version__ = "0.1.0"`; pytest config with `pythonpath = ["."]` so `import wiki_interest` works from tests.

- [ ] **Step 1: Write pyproject and python-version**

`wikipedia-interest/pyproject.toml`:
```toml
[project]
name = "wikipedia-interest"
version = "0.1.0"
description = "Agent skill: compare audience interest across Wikipedia language editions using pageview data"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27",
  "numpy>=1.26",
  "matplotlib>=3.9",
  "reportlab>=4.2",
]

[dependency-groups]
dev = ["pytest>=8", "pypdf>=5", "respx>=0.21"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
markers = ["network: hits live Wikimedia APIs (deselected by default)"]
addopts = "-m 'not network'"
```

`wikipedia-interest/.python-version`:
```
3.12
```

- [ ] **Step 2: Write minimal SKILL.md with valid frontmatter**

```markdown
---
name: wikipedia-interest
description: Analyze Wikipedia pageview trends to compare audience interest in topics across language editions, rate how trustworthy the growth is, plot charts and build a one-page PDF report. Use when a user asks which topics or languages/markets to invest in, whether interest in a subject is growing, or wants Wikipedia/Wikimedia pageview statistics compared between languages.
license: MIT
compatibility: Requires Python 3.12+, uv, and internet access to wikimedia.org and wikidata.org
metadata:
  author: vampir
  version: "0.1.0"
---

# Wikipedia Interest

Placeholder body; replaced in Task 11.
```

- [ ] **Step 3: Write package init and smoke test**

`wikipedia-interest/wiki_interest/__init__.py`:
```python
"""Wikipedia interest analysis skill package."""

__version__ = "0.1.0"
```

`wikipedia-interest/tests/test_smoke.py`:
```python
import wiki_interest


def test_version():
    assert wiki_interest.__version__ == "0.1.0"
```

- [ ] **Step 4: Sync env, run test, validate skill**

Run (from `wikipedia-interest/`):
```bash
uv sync
uv run pytest -q
uvx skills-ref validate .
```
Expected: `1 passed`; validator prints success / no errors.

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest .gitignore
git commit -m "Scaffold wikipedia-interest skill with uv project and validator

Locks the Agent Skills frontmatter and the reproducible environment first
so every later task can be validated with skills-ref and pytest."
```
(Append the Co-Authored-By line as in Global Constraints.)

---

### Task 2: SQLite response cache

**Files:**
- Create: `wikipedia-interest/wiki_interest/cache.py`
- Test: `wikipedia-interest/tests/test_cache.py`

**Interfaces:**
- Produces:
  ```python
  class Cache:
      def __init__(self, path: Path) -> None
      def get(self, url: str, now: datetime | None = None) -> str | None
      def put(self, url: str, body: str, ttl_seconds: int | None, now: datetime | None = None) -> None
      hits: int; misses: int
  PERMANENT = None  # ttl sentinel
  ```

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_cache.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cache.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.cache'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/cache.py`:
```python
"""SQLite cache for raw API responses.

Closed-month pageview windows never change, so they are stored permanently.
Everything else (current month, Wikidata, MediaWiki lookups) gets a TTL.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
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
        now = now or datetime.utcnow()
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
        now = now or datetime.utcnow()
        ttl_until = None
        if ttl_seconds is not None:
            ttl_until = (now + timedelta(seconds=ttl_seconds)).isoformat()
        self._conn.execute(
            "INSERT OR REPLACE INTO responses(url, body, fetched_at, ttl_until) VALUES (?, ?, ?, ?)",
            (url, body, now.isoformat(), ttl_until),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_cache.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/cache.py wikipedia-interest/tests/test_cache.py
git commit -m "Add SQLite response cache with TTL and permanent entries

Follow-up questions re-fetch the same windows; closed months never change,
so caching them permanently makes repeated and related queries near-free."
```

---

### Task 3: HTTP clients for Pageviews, Wikidata and MediaWiki

**Files:**
- Create: `wikipedia-interest/wiki_interest/api.py`
- Test: `wikipedia-interest/tests/test_api.py`

**Interfaces:**
- Consumes: `Cache` from Task 2.
- Produces:
  ```python
  REPO_URL = "https://github.com/vampir/genesisAiEngineerCourse"  # update when remote exists
  def user_agent() -> str
  class NoData(Exception)          # 404 from pageviews
  class ApiError(Exception)        # non-retryable failure
  def encode_title(title: str) -> str
  class WikiClient:
      def __init__(self, cache: Cache | None = None, transport=None, max_retries: int = 3, sleep=time.sleep) -> None
      def get_json(self, url: str, ttl_seconds: int | None) -> dict
      def per_article(self, project: str, title: str, granularity: str, start: str, end: str, permanent: bool) -> list[dict]
      def aggregate(self, project: str, granularity: str, start: str, end: str, permanent: bool) -> list[dict]
      def wd_search(self, text: str, language: str, limit: int = 5) -> list[dict]   # [{id,label,description}]
      def wd_entities(self, qids: list[str]) -> dict[str, dict]                     # qid -> {"sitelinks": {...}, "labels": {...}}
      def mw_resolve_title(self, lang: str, title: str) -> str | None
      def mw_search(self, lang: str, text: str, limit: int = 3) -> list[str]
  ```
  `project` is like `uk.wikipedia`; `start`/`end` are already API-formatted strings.

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_api.py`:
```python
import json

import httpx
import pytest
import respx

from wiki_interest.api import ApiError, NoData, WikiClient, encode_title, user_agent
from wiki_interest.cache import Cache

PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews"


def test_encode_title_slash_and_unicode():
    assert encode_title("AC/DC") == "AC%2FDC"
    assert encode_title("Přerušovaný půst") == "P%C5%99eru%C5%A1ovan%C3%BD_p%C5%AFst"
    assert encode_title("Intermittent fasting") == "Intermittent_fasting"


def test_user_agent_mentions_skill():
    assert user_agent().startswith("wikipedia-interest-skill/0.1.0")


@respx.mock
def test_per_article_ok_and_cached(tmp_path):
    url = f"{PV}/per-article/uk.wikipedia/all-access/user/%D0%90/monthly/20240101/20240131"
    route = respx.get(url).mock(return_value=httpx.Response(200, json={"items": [{"views": 5, "timestamp": "2024010100"}]}))
    c = WikiClient(cache=Cache(tmp_path / "c.sqlite"))
    assert c.per_article("uk.wikipedia", "А", "monthly", "20240101", "20240131", permanent=True)[0]["views"] == 5
    assert c.per_article("uk.wikipedia", "А", "monthly", "20240101", "20240131", permanent=True)[0]["views"] == 5
    assert route.call_count == 1


@respx.mock
def test_per_article_404_raises_nodata(tmp_path):
    respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))
    c = WikiClient(cache=None)
    with pytest.raises(NoData):
        c.per_article("uk.wikipedia", "X", "monthly", "20240101", "20240131", permanent=True)


@respx.mock
def test_retry_on_503_then_success():
    route = respx.get(url__regex=r".*/aggregate/.*").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json={"items": [{"views": 1}]})]
    )
    c = WikiClient(cache=None, sleep=lambda s: None)
    assert c.aggregate("uk.wikipedia", "monthly", "2024010100", "2024010100", permanent=True) == [{"views": 1}]
    assert route.call_count == 2


@respx.mock
def test_gives_up_after_retries():
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(503))
    c = WikiClient(cache=None, sleep=lambda s: None, max_retries=2)
    with pytest.raises(ApiError):
        c.aggregate("uk.wikipedia", "monthly", "2024010100", "2024010100", permanent=True)


@respx.mock
def test_wd_search_and_entities():
    respx.get(url__regex=r".*wikidata.*wbsearchentities.*").mock(
        return_value=httpx.Response(200, json={"search": [{"id": "Q1", "label": "astronomy", "description": "science"}]})
    )
    respx.get(url__regex=r".*wikidata.*wbgetentities.*").mock(
        return_value=httpx.Response(200, json={"entities": {"Q1": {"sitelinks": {"ukwiki": {"title": "Астрономія"}}, "labels": {"uk": {"value": "астрономія"}}}}})
    )
    c = WikiClient(cache=None)
    assert c.wd_search("astronomy", "en")[0] == {"id": "Q1", "label": "astronomy", "description": "science"}
    ents = c.wd_entities(["Q1"])
    assert ents["Q1"]["sitelinks"]["ukwiki"]["title"] == "Астрономія"


@respx.mock
def test_mw_resolve_title_redirect_and_missing():
    respx.get(url__regex=r".*en\.wikipedia.*redirects=1.*").mock(
        side_effect=[
            httpx.Response(200, json={"query": {"redirects": [{"from": "IF", "to": "Intermittent fasting"}], "pages": {"1": {"title": "Intermittent fasting"}}}}),
            httpx.Response(200, json={"query": {"pages": {"-1": {"title": "Nope", "missing": ""}}}}),
        ]
    )
    c = WikiClient(cache=None)
    assert c.mw_resolve_title("en", "IF") == "Intermittent fasting"
    assert c.mw_resolve_title("en", "Nope") is None


@respx.mock
def test_mw_search():
    respx.get(url__regex=r".*pl\.wikipedia.*list=search.*").mock(
        return_value=httpx.Response(200, json={"query": {"search": [{"title": "Post przerywany"}, {"title": "Post"}]}})
    )
    c = WikiClient(cache=None)
    assert c.mw_search("pl", "intermittent fasting", limit=2) == ["Post przerywany", "Post"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_api.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.api'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/api.py`:
```python
"""HTTP clients for the Wikimedia Pageviews API, Wikidata and MediaWiki.

One small class, synchronous httpx, retries with backoff, optional SQLite
cache. Every request carries a descriptive User-Agent as Wikimedia asks.
"""
from __future__ import annotations

import json
import os
import time
from urllib.parse import quote, urlencode

import httpx

from . import __version__
from .cache import DEFAULT_TTL_SECONDS, PERMANENT, Cache

PAGEVIEWS_BASE = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
REPO_URL = "https://github.com/vampir/genesisAiEngineerCourse"
RETRY_STATUSES = {429, 500, 502, 503, 504}


class NoData(Exception):
    """Pageviews API returned 404: no data for this article/window."""


class ApiError(Exception):
    """Non-recoverable API failure."""


def user_agent() -> str:
    contact = os.environ.get("WIKI_INTEREST_CONTACT")
    tail = f"{REPO_URL}; {contact}" if contact else REPO_URL
    return f"wikipedia-interest-skill/{__version__} (+{tail})"


def encode_title(title: str) -> str:
    return quote(title.strip().replace(" ", "_"), safe="")


class WikiClient:
    def __init__(self, cache: Cache | None = None, transport=None, max_retries: int = 3, sleep=time.sleep) -> None:
        self.cache = cache
        self.max_retries = max_retries
        self._sleep = sleep
        self._http = httpx.Client(headers={"User-Agent": user_agent()}, timeout=30.0, transport=transport)

    # ---- generic ---------------------------------------------------------
    def get_json(self, url: str, ttl_seconds: int | None) -> dict:
        if self.cache is not None:
            body = self.cache.get(url)
            if body is not None:
                return json.loads(body)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.get(url)
            except httpx.HTTPError as exc:  # network / timeout
                last_error = exc
                self._sleep(2 ** attempt)
                continue
            if resp.status_code == 404:
                raise NoData(_detail(resp))
            if resp.status_code in RETRY_STATUSES:
                last_error = ApiError(f"HTTP {resp.status_code} for {url}")
                self._sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                raise ApiError(f"HTTP {resp.status_code} for {url}: {_detail(resp)}")
            if self.cache is not None:
                self.cache.put(url, resp.text, ttl_seconds)
            return resp.json()
        raise ApiError(f"Giving up after {self.max_retries + 1} attempts: {last_error}")

    # ---- pageviews -------------------------------------------------------
    def per_article(self, project: str, title: str, granularity: str, start: str, end: str, permanent: bool) -> list[dict]:
        url = f"{PAGEVIEWS_BASE}/per-article/{project}/all-access/user/{encode_title(title)}/{granularity}/{start}/{end}"
        return self.get_json(url, PERMANENT if permanent else DEFAULT_TTL_SECONDS).get("items", [])

    def aggregate(self, project: str, granularity: str, start: str, end: str, permanent: bool) -> list[dict]:
        url = f"{PAGEVIEWS_BASE}/aggregate/{project}/all-access/user/{granularity}/{start}/{end}"
        return self.get_json(url, PERMANENT if permanent else DEFAULT_TTL_SECONDS).get("items", [])

    # ---- wikidata --------------------------------------------------------
    def wd_search(self, text: str, language: str, limit: int = 5) -> list[dict]:
        url = WIKIDATA_API + "?" + urlencode({
            "action": "wbsearchentities", "search": text, "language": language,
            "uselang": language, "type": "item", "limit": limit, "format": "json",
        })
        data = self.get_json(url, DEFAULT_TTL_SECONDS)
        return [{"id": s["id"], "label": s.get("label", ""), "description": s.get("description", "")} for s in data.get("search", [])]

    def wd_entities(self, qids: list[str]) -> dict[str, dict]:
        url = WIKIDATA_API + "?" + urlencode({
            "action": "wbgetentities", "ids": "|".join(qids),
            "props": "sitelinks|labels|descriptions", "format": "json",
        })
        return self.get_json(url, DEFAULT_TTL_SECONDS).get("entities", {})

    # ---- mediawiki -------------------------------------------------------
    def mw_resolve_title(self, lang: str, title: str) -> str | None:
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urlencode({
            "action": "query", "titles": title, "redirects": 1, "format": "json",
        })
        pages = self.get_json(url, DEFAULT_TTL_SECONDS).get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1" or "missing" in page:
                return None
            return page["title"]
        return None

    def mw_search(self, lang: str, text: str, limit: int = 3) -> list[str]:
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urlencode({
            "action": "query", "list": "search", "srsearch": text, "srlimit": limit, "format": "json",
        })
        return [s["title"] for s in self.get_json(url, DEFAULT_TTL_SECONDS).get("query", {}).get("search", [])]


def _detail(resp: httpx.Response) -> str:
    try:
        return resp.json().get("detail", resp.text[:200])
    except ValueError:
        return resp.text[:200]
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api.py -q`
Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/api.py wikipedia-interest/tests/test_api.py
git commit -m "Add Wikimedia, Wikidata and MediaWiki HTTP client with retries

Single client with cache, backoff and a descriptive User-Agent keeps the
rest of the skill free of HTTP details and makes 404 a typed NoData."
```

---

### Task 4: Topic → per-language title resolution

**Files:**
- Create: `wikipedia-interest/wiki_interest/resolve.py`
- Create: `wikipedia-interest/tests/fixtures/wd_search_if.json`, `wikipedia-interest/tests/fixtures/wd_entities_if.json`
- Test: `wikipedia-interest/tests/test_resolve.py`

**Interfaces:**
- Consumes: `WikiClient.wd_search`, `wd_entities`, `mw_resolve_title`, `mw_search`.
- Produces:
  ```python
  @dataclass
  class LangResolution:
      lang: str
      status: str            # "found" | "missing"
      title: str | None
      note: str = ""
      candidates: list[str] = field(default_factory=list)   # search fallback suggestions when missing
  @dataclass
  class TopicResolution:
      topic: str
      qid: str | None
      label: str | None
      per_lang: dict[str, LangResolution]
      alternatives: list[dict]   # [{qid,label,description}] other plausible Wikidata items
      def to_dict(self) -> dict
  def search_languages(topic: str, langs: list[str], hint: str | None) -> list[str]
  def resolve_topic(client, topic: str, langs: list[str], hint: str | None = None, qid: str | None = None, overrides: dict[str, str] | None = None) -> TopicResolution
  ```

- [ ] **Step 1: Write fixtures and failing tests**

`wikipedia-interest/tests/fixtures/wd_search_if.json`:
```json
{"search": [
  {"id": "Q1666254", "label": "intermittent fasting", "description": "a diet that cycles between fasting and non-fasting"},
  {"id": "Q112575736", "label": "Intermittent Fasting", "description": "2022 film"}
]}
```

`wikipedia-interest/tests/fixtures/wd_entities_if.json`:
```json
{"entities": {
  "Q1666254": {"sitelinks": {"cswiki": {"title": "Přerušovaný půst"}, "enwiki": {"title": "Intermittent fasting"}, "ukwiki": {"title": "Інтервальне голодування"}},
                "labels": {"en": {"value": "intermittent fasting"}, "pl": {"value": "post przerywany"}}},
  "Q112575736": {"sitelinks": {"enwiki": {"title": "Intermittent Fasting (film)"}}, "labels": {"en": {"value": "Intermittent Fasting"}}}
}}
```

`wikipedia-interest/tests/test_resolve.py`:
```python
import json
from pathlib import Path

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.resolve import resolve_topic, search_languages

FIX = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIX / name).read_text())


def test_search_languages_latin_defaults_to_en_then_requested():
    assert search_languages("astronomy", ["uk", "pl"], None) == ["en", "uk", "pl"]


def test_search_languages_cyrillic_prefers_uk_ru():
    assert search_languages("астрономія", ["pl"], None) == ["uk", "ru", "pl", "en"]


def test_search_languages_hint_first():
    assert search_languages("astronomie", ["uk"], "cs") == ["cs", "en", "uk"]


@respx.mock
def test_resolve_found_and_missing_with_fallback():
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=_load("wd_search_if.json")))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=_load("wd_entities_if.json")))
    respx.get(url__regex=r".*pl\.wikipedia.*list=search.*").mock(
        return_value=httpx.Response(200, json={"query": {"search": [{"title": "Post przerywany"}]}})
    )
    r = resolve_topic(WikiClient(), "intermittent fasting", ["pl", "cs", "uk"])
    assert r.qid == "Q1666254"
    assert r.per_lang["cs"].status == "found" and r.per_lang["cs"].title == "Přerušovaný půst"
    assert r.per_lang["uk"].title == "Інтервальне голодування"
    assert r.per_lang["pl"].status == "missing"
    assert r.per_lang["pl"].candidates == ["Post przerywany"]
    assert "post przerywany" in r.per_lang["pl"].note  # used the pl label for the search
    assert r.alternatives == [{"qid": "Q112575736", "label": "Intermittent Fasting", "description": "2022 film"}]


@respx.mock
def test_resolve_overrides_skip_wikidata_and_follow_redirect():
    respx.get(url__regex=r".*pl\.wikipedia.*redirects=1.*").mock(
        return_value=httpx.Response(200, json={"query": {"pages": {"7": {"title": "Post przerywany"}}}})
    )
    r = resolve_topic(WikiClient(), "whatever", ["pl"], overrides={"pl": "Post_Przerywany"})
    assert r.per_lang["pl"].status == "found"
    assert r.per_lang["pl"].title == "Post przerywany"
    assert r.qid is None


@respx.mock
def test_resolve_no_wikidata_hits():
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json={"search": []}))
    respx.get(url__regex=r".*wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": []}}))
    r = resolve_topic(WikiClient(), "zzzqqq", ["uk"])
    assert r.qid is None
    assert r.per_lang["uk"].status == "missing"


@respx.mock
def test_resolve_with_explicit_qid():
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=_load("wd_entities_if.json")))
    r = resolve_topic(WikiClient(), "x", ["uk"], qid="Q1666254")
    assert r.per_lang["uk"].title == "Інтервальне голодування"
    assert r.label == "intermittent fasting"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_resolve.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.resolve'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/resolve.py`:
```python
"""Map a free-text topic to article titles in several Wikipedia languages.

Strategy: Wikidata search in a sensible language order → take the first item
that has a sitelink in at least one requested language → sitelinks give
canonical titles. Languages without a sitelink are reported as missing with
MediaWiki search suggestions (never auto-used: a suggestion is not the topic).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .api import WikiClient

CYRILLIC = re.compile(r"[Ѐ-ӿ]")


@dataclass
class LangResolution:
    lang: str
    status: str  # "found" | "missing"
    title: str | None
    note: str = ""
    candidates: list[str] = field(default_factory=list)


@dataclass
class TopicResolution:
    topic: str
    qid: str | None
    label: str | None
    per_lang: dict[str, LangResolution]
    alternatives: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic, "qid": self.qid, "label": self.label,
            "per_lang": {k: asdict(v) for k, v in self.per_lang.items()},
            "alternatives": self.alternatives,
        }

    def found_langs(self) -> list[str]:
        return [l for l, r in self.per_lang.items() if r.status == "found"]


def search_languages(topic: str, langs: list[str], hint: str | None) -> list[str]:
    order: list[str] = []
    if hint:
        order.append(hint)
    if CYRILLIC.search(topic):
        order += ["uk", "ru"]
    else:
        order.append("en")
    order += langs
    order.append("en")
    seen: set[str] = set()
    return [l for l in order if not (l in seen or seen.add(l))]


def resolve_topic(client: WikiClient, topic: str, langs: list[str], hint: str | None = None,
                  qid: str | None = None, overrides: dict[str, str] | None = None) -> TopicResolution:
    overrides = overrides or {}
    per_lang: dict[str, LangResolution] = {}
    label: str | None = None
    alternatives: list[dict] = []
    entity: dict = {}

    need_wikidata = [l for l in langs if l not in overrides]
    if need_wikidata:
        if qid is None:
            qid, entity, alternatives = _pick_item(client, topic, langs, hint)
        else:
            entity = client.wd_entities([qid]).get(qid, {})
        if entity:
            label = _label(entity, ["en", hint or "en"]) or topic

    for lang in langs:
        if lang in overrides:
            title = client.mw_resolve_title(lang, overrides[lang].replace("_", " "))
            per_lang[lang] = (LangResolution(lang, "found", title, "user-supplied title")
                              if title else LangResolution(lang, "missing", None, f"user-supplied title '{overrides[lang]}' does not exist"))
            continue
        sitelink = entity.get("sitelinks", {}).get(f"{lang}wiki") if entity else None
        if sitelink:
            per_lang[lang] = LangResolution(lang, "found", sitelink["title"], f"Wikidata sitelink of {qid}")
            continue
        query = _label(entity, [lang]) or topic if entity else topic
        candidates = client.mw_search(lang, query, limit=3)
        note = (f"no {lang}wiki article linked to {qid}; searched {lang}.wikipedia for '{query}'"
                if qid else f"no Wikidata item found; searched {lang}.wikipedia for '{query}'")
        per_lang[lang] = LangResolution(lang, "missing", None, note, candidates)

    return TopicResolution(topic, qid, label, per_lang, alternatives)


def _pick_item(client: WikiClient, topic: str, langs: list[str], hint: str | None):
    for search_lang in search_languages(topic, langs, hint):
        hits = client.wd_search(topic, search_lang, limit=5)
        if not hits:
            continue
        entities = client.wd_entities([h["id"] for h in hits])
        wanted = {f"{l}wiki" for l in langs}
        usable = [h for h in hits if wanted & set(entities.get(h["id"], {}).get("sitelinks", {}))]
        if not usable:
            usable = hits[:1]
        chosen = usable[0]
        alternatives = [{"qid": h["id"], "label": h["label"], "description": h["description"]}
                        for h in hits if h["id"] != chosen["id"]][:3]
        return chosen["id"], entities.get(chosen["id"], {}), alternatives
    return None, {}, []


def _label(entity: dict, langs: list[str]) -> str | None:
    labels = entity.get("labels", {})
    for l in langs:
        if l in labels:
            return labels[l]["value"]
    return None
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_resolve.py -q`
Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/resolve.py wikipedia-interest/tests/test_resolve.py wikipedia-interest/tests/fixtures
git commit -m "Resolve topics to per-language titles through Wikidata sitelinks

Users phrase topics in any language; Wikidata gives canonical titles in
every edition and makes a missing article an explicit, reported fact
rather than a silent zero."
```

---

### Task 5: Time windows, series fetch, alignment and normalization

**Files:**
- Create: `wikipedia-interest/wiki_interest/series.py`
- Test: `wikipedia-interest/tests/test_series.py`

**Interfaces:**
- Consumes: `WikiClient.per_article`, `WikiClient.aggregate`, `NoData`.
- Produces:
  ```python
  @dataclass
  class Window:
      start: str; end: str; granularity: str   # "YYYY-MM" bounds inclusive, granularity "monthly"|"daily"
      periods: list[str]                        # "YYYY-MM" or "YYYY-MM-DD"
      def api_range_article(self) -> tuple[str, str]     # ("20240901","20260831") monthly or daily
      def api_range_aggregate(self) -> tuple[str, str]   # ("2024090100","2026080100") monthly; daily ("2024090100","2026083100")
      def is_closed(self, today: date) -> bool
  def make_window(months: int | None, start: str | None, end: str | None, granularity: str, today: date) -> Window
  @dataclass
  class Series:
      topic: str; lang: str; title: str | None
      periods: list[str]; views: list[int]; project_views: list[int]; per_million: list[float]
      status: str  # "ok" | "no_data" | "missing"
      note: str = ""
      granularity: str = "monthly"
  def fetch_project_totals(client, lang, window, today) -> list[int]
  def fetch_series(client, topic, lang, title, window, project_views, today) -> Series
  def period_key(timestamp: str, granularity: str) -> str
  ```

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_series.py`:
```python
from datetime import date

import httpx
import pytest
import respx

from wiki_interest.api import WikiClient
from wiki_interest.series import Window, fetch_project_totals, fetch_series, make_window, period_key

TODAY = date(2026, 9, 23)


def test_make_window_default_24_months_excludes_current_month():
    w = make_window(24, None, None, "monthly", TODAY)
    assert (w.start, w.end) == ("2024-09", "2026-08")
    assert len(w.periods) == 24 and w.periods[0] == "2024-09" and w.periods[-1] == "2026-08"
    assert w.api_range_article() == ("20240901", "20260831")
    assert w.api_range_aggregate() == ("2024090100", "2026080100")


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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_series.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.series'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/series.py`:
```python
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
        _ym(start); _ym(end)
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
        y, m = s.split("-")
        y, m = int(y), int(m)
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
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_series.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/series.py wikipedia-interest/tests/test_series.py
git commit -m "Fetch aligned pageview series normalized per million project views

Raw views across editions are not comparable; aligning to a fixed period
index and dividing by project totals makes languages and gaps explicit."
```

---

### Task 6: Statistics, spikes, confidence and ranking

**Files:**
- Create: `wikipedia-interest/wiki_interest/stats.py`
- Test: `wikipedia-interest/tests/test_stats.py`

**Interfaces:**
- Consumes: `Series` from Task 5.
- Produces:
  ```python
  THRESHOLDS = {...}  # single source of truth, documented in references/methodology.md
  @dataclass
  class Metrics:
      views_total: int; pm_latest: float | None; pm_year_ago: float | None; yoy_pct: float | None
      growth_pct_per_year: float | None; growth_clipped_pct_per_year: float | None
      spike_periods: list[str]; spike_share_pct: float
      rho: float | None; p_value: float | None; seasonality_amp: float | None
      coverage_pct: float; first_seen: str | None; n_periods: int
      confidence: str; reasons: list[str]
      def to_dict(self) -> dict
  def compute_metrics(series: Series) -> Metrics
  def rank(entries: list[tuple[str, Metrics]], by: str = "score") -> list[tuple[str, float]]   # key, score, sorted desc
  ```

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_stats.py`:
```python
import math

import numpy as np
import pytest

from wiki_interest.series import Series
from wiki_interest.stats import Metrics, compute_metrics, rank


def _series(pm, granularity="monthly", views=None):
    n = len(pm)
    periods = [f"{2024 + (i // 12):04d}-{i % 12 + 1:02d}" for i in range(n)] if granularity == "monthly" \
        else [f"2026-07-{i + 1:02d}" for i in range(n)]
    views = views if views is not None else [int(round(x * 100)) for x in pm]
    return Series("t", "uk", "T", periods, views, [100_000_000] * n, list(map(float, pm)), "ok", "", granularity)


def test_clean_exponential_growth_high_confidence():
    pm = [100 * (1.5 ** (i / 12)) for i in range(24)]  # +50 %/yr
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert abs(m.growth_pct_per_year - 50) < 2
    assert abs(m.growth_clipped_pct_per_year - 50) < 2
    assert m.spike_periods == [] and m.spike_share_pct == 0
    assert m.p_value is not None and m.p_value < 0.01
    assert m.coverage_pct == 100 and m.first_seen == "2024-01"
    assert m.yoy_pct is not None and m.yoy_pct > 30
    assert m.confidence == "high" and m.reasons == []


def test_single_spike_detected_and_clipped():
    pm = [100.0] * 24
    pm[10] = 5000.0
    views = [int(x * 1000) for x in pm]
    m = compute_metrics(_series(pm, views=views))
    assert m.spike_periods == ["2024-11"]
    assert m.spike_share_pct > 60
    assert abs(m.growth_clipped_pct_per_year) < 1
    assert m.confidence == "low" and any("spike" in r for r in m.reasons)


def test_short_window_no_yoy_no_seasonality():
    pm = [100.0 + i for i in range(6)]
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.yoy_pct is None and m.pm_year_ago is None and m.seasonality_amp is None
    assert m.n_periods == 6
    assert m.confidence in ("medium", "low")
    assert any("24" in r for r in m.reasons)


def test_all_zero_series_no_nan():
    m = compute_metrics(_series([0.0] * 24, views=[0] * 24))
    d = m.to_dict()
    assert all(not (isinstance(v, float) and math.isnan(v)) for v in d.values())
    assert m.spike_periods == [] and m.growth_clipped_pct_per_year == 0
    assert m.coverage_pct == 0 and m.first_seen is None
    assert m.confidence == "low" and any("1000" in r for r in m.reasons)


def test_low_coverage_flagged():
    pm = [0.0] * 12 + [100.0] * 12
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.coverage_pct == 50 and m.first_seen == "2025-01"
    assert m.confidence == "low" and any("coverage" in r for r in m.reasons)


def test_medium_when_only_soft_flag():
    rng = np.random.default_rng(1)
    pm = [100 * (1.3 ** (i / 12)) * (1 + 0.05 * rng.standard_normal()) for i in range(24)]
    pm[5] = pm[6] = pm[7] = 0.0  # three zero months → coverage 21/24 = 87.5 % (< 90 soft, ≥ 70 not hard)
    m = compute_metrics(_series(pm, views=[int(x * 1000) for x in pm]))
    assert m.coverage_pct == 87.5
    assert m.confidence == "medium"
    assert any("coverage" in r for r in m.reasons)


def test_daily_growth_annualized():
    pm = [100 * (2 ** (i / 365)) for i in range(31)]  # doubling per year
    m = compute_metrics(_series(pm, granularity="daily", views=[int(x * 1000) for x in pm]))
    assert abs(m.growth_pct_per_year - 100) < 5
    assert m.yoy_pct is None


def _metrics(growth, conf, pm_latest=10.0):
    return Metrics(10_000, pm_latest, None, None, growth, growth, [], 0.0, None, None, None, 100.0, "2024-01", 24, conf, [])


def test_rank_score_weights_confidence():
    entries = [("a", _metrics(40, "low")), ("b", _metrics(20, "high")), ("c", _metrics(30, "medium"))]
    assert [k for k, _ in rank(entries)] == ["b", "c", "a"]  # 20*1.0 > 30*0.6 > 40*0.25


def test_rank_by_volume_and_growth():
    entries = [("a", _metrics(40, "low", pm_latest=1)), ("b", _metrics(20, "high", pm_latest=5))]
    assert [k for k, _ in rank(entries, by="volume")] == ["b", "a"]
    assert [k for k, _ in rank(entries, by="growth")] == ["a", "b"]


def test_rank_rejects_unknown():
    with pytest.raises(ValueError):
        rank([], by="magic")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_stats.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.stats'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/stats.py`:
```python
"""Trend, robustness and confidence metrics for one pageview series.

All thresholds live in THRESHOLDS and are mirrored in references/methodology.md.
Pure numpy; the p-value is a permutation test on Spearman's rho so no SciPy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .series import Series

THRESHOLDS = {
    "spike_z": 3.5,               # robust z (MAD) above which a period is a spike
    "clip_window": 5,             # rolling median window used to replace spikes
    "permutations": 2000,         # for the Spearman p-value
    "low_coverage_pct": 70, "medium_coverage_pct": 90,
    "low_spike_pct": 30, "medium_spike_pct": 10,
    "low_p": 0.10, "medium_p": 0.05,
    "low_growth_gap_pts": 25,
    "low_min_views": 1000,
    "medium_min_periods": 24,
}
RANK_WEIGHTS = {"high": 1.0, "medium": 0.6, "low": 0.25}
PERIODS_PER_YEAR = {"monthly": 12, "daily": 365}


@dataclass
class Metrics:
    views_total: int
    pm_latest: float | None
    pm_year_ago: float | None
    yoy_pct: float | None
    growth_pct_per_year: float | None
    growth_clipped_pct_per_year: float | None
    spike_periods: list[str]
    spike_share_pct: float
    rho: float | None
    p_value: float | None
    seasonality_amp: float | None
    coverage_pct: float
    first_seen: str | None
    n_periods: int
    confidence: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def compute_metrics(series: Series) -> Metrics:
    pm = np.asarray(series.per_million, dtype=float)
    views = np.asarray(series.views, dtype=float)
    n = len(pm)
    ppy = PERIODS_PER_YEAR[series.granularity]
    monthly = series.granularity == "monthly"

    views_total = int(views.sum())
    nonzero = np.flatnonzero(views > 0)
    coverage_pct = round(100.0 * len(nonzero) / n, 1) if n else 0.0
    first_seen = series.periods[int(nonzero[0])] if len(nonzero) else None

    tail = 3 if monthly else 7
    pm_latest = _r(pm[-tail:].mean()) if n >= tail else _r(pm.mean()) if n else None
    pm_year_ago = _r(pm[-ppy - tail:-ppy].mean()) if monthly and n >= ppy + tail else None
    yoy_pct = None
    if monthly and n >= 24:
        prev, last = pm[-24:-12].mean(), pm[-12:].mean()
        yoy_pct = _r((last / prev - 1) * 100) if prev > 0 else None

    logs = np.log1p(pm)
    growth = _growth(logs, ppy)
    spikes = _spike_mask(logs)
    spike_periods = [series.periods[i] for i in np.flatnonzero(spikes)]
    spike_share_pct = _r(100.0 * views[spikes].sum() / views_total) if views_total else 0.0
    clipped = _clip(logs, spikes)
    growth_clipped = _growth(clipped, ppy)
    rho, p_value = _spearman_perm(clipped)

    seasonality_amp = None
    if monthly and n >= 24:
        moy = np.array([int(p[5:7]) for p in series.periods])
        means = np.array([pm[moy == k].mean() for k in range(1, 13)])
        seasonality_amp = _r((means.max() - means.min()) / pm.mean()) if pm.mean() > 0 else None

    confidence, reasons = _confidence(coverage_pct, spike_share_pct, p_value, growth, growth_clipped, views_total, n, monthly)
    return Metrics(views_total, pm_latest, pm_year_ago, yoy_pct, growth, growth_clipped, spike_periods,
                   spike_share_pct, rho, p_value, seasonality_amp, coverage_pct, first_seen, n, confidence, reasons)


def rank(entries: list[tuple[str, Metrics]], by: str = "score") -> list[tuple[str, float]]:
    if by not in ("score", "growth", "volume"):
        raise ValueError(f"--rank-by must be score, growth or volume, got {by}")

    def key(m: Metrics) -> float:
        g = m.growth_clipped_pct_per_year or 0.0
        if by == "growth":
            return g
        if by == "volume":
            return m.pm_latest or 0.0
        return g * RANK_WEIGHTS[m.confidence]

    scored = [(k, _r(key(m)), m.pm_latest or 0.0) for k, m in entries]
    scored.sort(key=lambda t: (t[1], t[2]), reverse=True)
    return [(k, s) for k, s, _ in scored]


# ---- internals -----------------------------------------------------------
def _r(x) -> float | None:
    if x is None or not np.isfinite(x):
        return None
    return round(float(x), 2)


def _growth(logs: np.ndarray, ppy: int) -> float | None:
    n = len(logs)
    if n < 3 or np.allclose(logs, logs[0]):
        return 0.0 if n else None
    slope = np.polyfit(np.arange(n), logs, 1)[0]
    return _r((np.exp(slope * ppy) - 1) * 100)


def _spike_mask(logs: np.ndarray) -> np.ndarray:
    med = np.median(logs)
    dev = np.abs(logs - med)
    mad = np.median(dev)
    if mad == 0:
        # Mostly-constant series (e.g. flat with one outlier): fall back to mean absolute deviation.
        mad = dev.mean()
    if mad == 0:
        return np.zeros(len(logs), dtype=bool)
    z = 0.6745 * (logs - med) / mad
    return z > THRESHOLDS["spike_z"]


def _clip(logs: np.ndarray, spikes: np.ndarray) -> np.ndarray:
    out = logs.copy()
    w = THRESHOLDS["clip_window"] // 2
    n = len(logs)
    for i in np.flatnonzero(spikes):
        lo, hi = max(0, i - w), min(n, i + w + 1)
        neighbours = [logs[j] for j in range(lo, hi) if not spikes[j]]
        out[i] = np.median(neighbours) if neighbours else np.median(logs[~spikes]) if (~spikes).any() else logs[i]
    return out


def _spearman_perm(x: np.ndarray) -> tuple[float | None, float | None]:
    n = len(x)
    if n < 4 or np.allclose(x, x[0]):
        return None, None
    idx = np.arange(n)
    rx = _ranks(x)
    rho = float(np.corrcoef(idx, rx)[0, 1])
    rng = np.random.default_rng(0)
    perms = THRESHOLDS["permutations"]
    count = 0
    for _ in range(perms):
        r = float(np.corrcoef(idx, rng.permutation(rx))[0, 1])
        if abs(r) >= abs(rho):
            count += 1
    return _r(rho), _r((count + 1) / (perms + 1))


def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(1, len(x) + 1)
    # average ties
    for v in np.unique(x):
        mask = x == v
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def _confidence(coverage, spike_share, p, growth, growth_clipped, views_total, n, monthly):
    T = THRESHOLDS
    hard, soft = [], []
    if coverage < T["low_coverage_pct"]:
        hard.append(f"coverage {coverage}% < {T['low_coverage_pct']}% (article young or absent for part of window)")
    elif coverage < T["medium_coverage_pct"]:
        soft.append(f"coverage {coverage}% < {T['medium_coverage_pct']}%")
    if spike_share > T["low_spike_pct"]:
        hard.append(f"spike share {spike_share}% > {T['low_spike_pct']}% (news-driven traffic)")
    elif spike_share > T["medium_spike_pct"]:
        soft.append(f"spike share {spike_share}% > {T['medium_spike_pct']}%")
    if p is None or p > T["low_p"]:
        hard.append(f"trend not monotonic (p={p})")
    elif p > T["medium_p"]:
        soft.append(f"weak monotonic trend (p={p})")
    if growth is not None and growth_clipped is not None and abs(growth - growth_clipped) > T["low_growth_gap_pts"]:
        hard.append(f"growth changes by {abs(growth - growth_clipped):.0f} pts when spikes are clipped")
    if views_total < T["low_min_views"]:
        hard.append(f"total views {views_total} < {T['low_min_views']}")
    if monthly and n < T["medium_min_periods"]:
        soft.append(f"only {n} months (< {T['medium_min_periods']}): no year-over-year check")
    if hard:
        return "low", hard + soft
    if soft:
        return "medium", soft
    return "high", []
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_stats.py -q`
Expected: `10 passed`. If `test_clean_exponential_growth_high_confidence` fails on `p_value`, the permutation test is fine (rho=1 gives p≈0.0005); check `_confidence` ordering instead.

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/stats.py wikipedia-interest/tests/test_stats.py
git commit -m "Compute growth, spike-robust trend and confidence rating

Founders need to know how much to trust a growth number. Clipping spikes,
checking monotonicity and coverage, and turning the flags into an explicit
confidence level with reasons makes that trust auditable."
```

---

### Task 7: Run model, orchestration and summary.md renderer

**Files:**
- Create: `wikipedia-interest/wiki_interest/run.py`
- Create: `wikipedia-interest/wiki_interest/summary.py`
- Test: `wikipedia-interest/tests/test_run_summary.py`

**Interfaces:**
- Consumes: `resolve_topic`, `make_window`, `fetch_project_totals`, `fetch_series`, `compute_metrics`, `rank`.
- Produces:
  ```python
  FIXED_LIMITATIONS: list[str]; FIXED_ASSUMPTIONS: list[str]
  @dataclass
  class RunResult:
      topics: list[str]; langs: list[str]; window: Window; rank_by: str
      resolutions: dict[str, TopicResolution]            # by topic
      series: list[Series]
      metrics: dict[str, Metrics]                        # key "topic|lang"
      ranking: list[tuple[str, float]]
      checks: list[str]; assumptions: list[str]; limitations: list[str]; follow_ups: list[str]
      generated_at: str
      def to_dict(self) -> dict
      def usable(self) -> list[Series]                  # status == "ok"
  def key(topic, lang) -> str
  def run_analysis(client, topics, langs, months, start, end, granularity, rank_by, titles: dict[str,str], qid, hint, today, out_dir: Path) -> RunResult
  def write_run(run: RunResult, out_dir: Path, summary: str) -> None   # result.json + data.csv + summary.md
  def load_run(out_dir: Path) -> dict                                  # result.json back
  def render_summary(run: RunResult, out_dir: Path) -> str            # ≤ 40 lines
  ```

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_run_summary.py`:
```python
import json
from datetime import date
from pathlib import Path

import httpx
import respx

from wiki_interest.api import WikiClient
from wiki_interest.run import key, load_run, run_analysis, write_run
from wiki_interest.summary import render_summary

TODAY = date(2026, 9, 23)
FIX = Path(__file__).parent / "fixtures"


def _mock_world():
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*pl\.wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": [{"title": "Post przerywany"}]}}))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 50_000_000} for m in (6, 7, 8)]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 500}, {"timestamp": "2026070100", "views": 600}, {"timestamp": "2026080100", "views": 700}]}))
    respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))


@respx.mock
def test_run_analysis_partial_success(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["pl", "cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    assert [s.status for s in run.series] == ["missing", "ok", "no_data"]
    assert key("intermittent fasting", "cs") in run.metrics
    assert run.ranking[0][0] == key("intermittent fasting", "cs")
    assert any("pl" in c and "missing" in c.lower() for c in run.checks)
    assert any("uk" in c and "no pageview data" in c.lower() for c in run.checks)
    assert any("current month" in c.lower() for c in run.checks)
    assert any("Post przerywany" in l for l in run.limitations)
    assert run.follow_ups and any("report" in f for f in run.follow_ups)


@respx.mock
def test_summary_is_short_and_complete(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["pl", "cs", "uk"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    text = render_summary(run, tmp_path)
    lines = text.splitlines()
    assert len(lines) <= 40
    assert lines[0].startswith("# ")
    for section in ("## Ranking", "## Checks", "## Limitations", "## Suggested follow-ups"):
        assert section in text
    assert "Přerušovaný půst" in text and "MISSING" in text and "NO DATA" in text
    assert "| topic | lang |" in text
    assert "confidence" in text


@respx.mock
def test_write_and_load_run(tmp_path):
    _mock_world()
    run = run_analysis(WikiClient(), ["intermittent fasting"], ["cs"], None, "2026-06", "2026-08",
                       "monthly", "score", {}, None, None, TODAY, tmp_path)
    write_run(run, tmp_path, render_summary(run, tmp_path))
    assert (tmp_path / "result.json").exists() and (tmp_path / "summary.md").exists()
    csv = (tmp_path / "data.csv").read_text().splitlines()
    assert csv[0] == "topic,lang,title,period,views,project_views,per_million"
    assert len(csv) == 4
    d = load_run(tmp_path)
    assert d["metrics"][key("intermittent fasting", "cs")]["confidence"] in ("low", "medium", "high")
    assert d["window"]["start"] == "2026-06"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_run_summary.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.run'`

- [ ] **Step 3: Implement run.py**

`wikipedia-interest/wiki_interest/run.py`:
```python
"""Orchestrate one analysis: resolve → fetch → metrics → rank → files."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from .api import WikiClient
from .resolve import TopicResolution, resolve_topic
from .series import Series, Window, fetch_project_totals, fetch_series, make_window
from .stats import Metrics, compute_metrics, rank

FIXED_ASSUMPTIONS = [
    "Pageviews filtered to agent=user (human traffic as classified by Wikimedia) and all access methods.",
    "Interest is measured as views per million of the whole language edition's views in the same period.",
    "The current (incomplete) month is excluded.",
    "Growth figures are annualized log-linear trends with spike periods clipped (see references/methodology.md).",
]
FIXED_LIMITATIONS = [
    "Wikipedia interest is not willingness to pay; validate promising directions with real user research.",
    "Views depend on article existence and quality; a missing or poor article hides real interest.",
    "Bot filtering is imperfect; spikes can be automated traffic or news events.",
    "A language edition is not a country: readers of one language live in many markets.",
]


def key(topic: str, lang: str) -> str:
    return f"{topic}|{lang}"


@dataclass
class RunResult:
    topics: list[str]
    langs: list[str]
    window: Window
    rank_by: str
    resolutions: dict[str, TopicResolution]
    series: list[Series]
    metrics: dict[str, Metrics]
    ranking: list[tuple[str, float]]
    checks: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    generated_at: str = ""

    def usable(self) -> list[Series]:
        return [s for s in self.series if s.status == "ok"]

    def to_dict(self) -> dict:
        return {
            "topics": self.topics, "langs": self.langs, "window": self.window.to_dict(), "rank_by": self.rank_by,
            "resolutions": {t: r.to_dict() for t, r in self.resolutions.items()},
            "series": [s.to_dict() for s in self.series],
            "metrics": {k: m.to_dict() for k, m in self.metrics.items()},
            "ranking": [{"key": k, "score": s} for k, s in self.ranking],
            "checks": self.checks, "assumptions": self.assumptions, "limitations": self.limitations,
            "follow_ups": self.follow_ups, "generated_at": self.generated_at,
        }


def run_analysis(client: WikiClient, topics: list[str], langs: list[str], months: int | None, start: str | None,
                 end: str | None, granularity: str, rank_by: str, titles: dict[str, str], qid: str | None,
                 hint: str | None, today: date, out_dir: Path) -> RunResult:
    window = make_window(months, start, end, granularity, today)
    checks: list[str] = []
    limitations = list(FIXED_LIMITATIONS)

    totals = {lang: fetch_project_totals(client, lang, window, today) for lang in langs}
    resolutions: dict[str, TopicResolution] = {}
    series: list[Series] = []
    metrics: dict[str, Metrics] = {}
    for topic in topics:
        res = resolve_topic(client, topic, langs, hint=hint, qid=qid if len(topics) == 1 else None, overrides=titles)
        resolutions[topic] = res
        for lang in langs:
            lr = res.per_lang[lang]
            s = fetch_series(client, topic, lang, lr.title, window, totals[lang], today)
            series.append(s)
            if s.status == "missing":
                checks.append(f"{topic} / {lang}: MISSING article ({lr.note})")
                if lr.candidates:
                    limitations.append(f"{lang}: no article for '{topic}'; search suggests {', '.join(lr.candidates)} — "
                                       f"pass --titles {lang}=<title> only if one of them is the same topic.")
                else:
                    limitations.append(f"{lang}: no article for '{topic}' — absence of an article is not absence of interest.")
                continue
            if s.status == "no_data":
                checks.append(f"{topic} / {lang}: no pageview data for «{s.title}» ({s.note})")
                continue
            metrics[key(topic, lang)] = compute_metrics(s)
            zero = sum(1 for v in s.views if v == 0)
            if zero:
                checks.append(f"{topic} / {lang}: {zero} of {len(s.views)} periods have zero views")
        if res.alternatives:
            alts = "; ".join(f"{a['qid']} «{a['label']}» ({a['description']})" for a in res.alternatives)
            checks.append(f"{topic}: resolved to {res.qid} «{res.label}»; other candidates: {alts}. Use --qid to switch.")

    ranking = rank([(k, m) for k, m in metrics.items()], by=rank_by)
    checks.append(f"window {window.start}..{window.end} ({len(window.periods)} {granularity} periods); current month excluded")
    if client.cache is not None:
        checks.append(f"cache: {client.cache.hits} hits, {client.cache.misses} misses")
    for k, m in metrics.items():
        if m.spike_periods:
            limitations.append(f"{k}: spikes in {', '.join(m.spike_periods[:6])} carry {m.spike_share_pct}% of views.")
        if m.coverage_pct < 100:
            limitations.append(f"{k}: data covers {m.coverage_pct}% of the window (first seen {m.first_seen}).")

    follow_ups = _follow_ups(out_dir, topics, langs, window, metrics)
    return RunResult(topics, langs, window, rank_by, resolutions, series, metrics, ranking, checks,
                     list(FIXED_ASSUMPTIONS), limitations, follow_ups,
                     datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


def write_run(run: RunResult, out_dir: Path, summary: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(run.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    with (out_dir / "data.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["topic", "lang", "title", "period", "views", "project_views", "per_million"])
        for s in run.series:
            for p, v, pv, pm in zip(s.periods, s.views, s.project_views, s.per_million):
                w.writerow([s.topic, s.lang, s.title or "", p, v, pv, pm])


def load_run(out_dir: Path) -> dict:
    path = Path(out_dir) / "result.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run `analyze --out {out_dir}` first")
    return json.loads(path.read_text(encoding="utf-8"))


def _follow_ups(out_dir: Path, topics, langs, window: Window, metrics: dict[str, Metrics]) -> list[str]:
    cli = "uv run scripts/wiki_interest.py"
    t = f'--topics "{";".join(topics)}"' if len(topics) > 1 else f'--topic "{topics[0]}"'
    out: list[str] = []
    spiky = [(k, m) for k, m in metrics.items() if m.spike_periods and window.granularity == "monthly"]
    if spiky:
        k, m = spiky[0]
        p = m.spike_periods[0]
        out.append(f'{cli} analyze {t} --langs {k.split("|")[1]} --granularity daily --start {p} --end {p} '
                   f'--out {out_dir}-daily-{p}   # inspect the {p} spike day by day')
    if window.granularity == "monthly" and len(window.periods) < 36:
        out.append(f'{cli} analyze {t} --langs {",".join(langs)} --months 48 --out {out_dir}-48m   # longer history')
    out.append(f'{cli} report --run {out_dir} --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF')
    return out
```

- [ ] **Step 4: Implement summary.py**

`wikipedia-interest/wiki_interest/summary.py`:
```python
"""Deterministic, ≤40-line Markdown summary the agent reads instead of JSON."""
from __future__ import annotations

from pathlib import Path

from .run import RunResult, key

MAX_LINES = 40


def render_summary(run: RunResult, out_dir: Path) -> str:
    w = run.window
    lines: list[str] = []
    lines.append(f"# {', '.join(run.topics)} — {','.join(run.langs)} — {w.start}..{w.end} ({len(w.periods)} {w.granularity})")
    for topic, res in run.resolutions.items():
        parts = []
        for lang in run.langs:
            lr = res.per_lang[lang]
            s = next(s for s in run.series if s.topic == topic and s.lang == lang)
            if s.status == "ok":
                parts.append(f"{lang} → «{lr.title}»")
            elif s.status == "no_data":
                parts.append(f"{lang} → «{lr.title}» NO DATA")
            else:
                parts.append(f"{lang} → MISSING")
        qid = f" ({res.qid})" if res.qid else ""
        lines.append(f"Resolved{qid if len(run.topics) == 1 else ''} {topic}: " + " · ".join(parts))
    lines.append("")
    lines.append("| topic | lang | pm latest | pm year ago | YoY % | growth/yr % (clipped) | spikes % | coverage % | confidence |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for topic in run.topics:
        for lang in run.langs:
            m = run.metrics.get(key(topic, lang))
            if m is None:
                continue
            lines.append(f"| {topic} | {lang} | {_f(m.pm_latest)} | {_f(m.pm_year_ago)} | {_f(m.yoy_pct)} | "
                         f"{_f(m.growth_clipped_pct_per_year)} | {_f(m.spike_share_pct)} | {_f(m.coverage_pct)} | {m.confidence} |")
    lines.append("")
    lines.append(f"## Ranking (by {run.rank_by}; score = clipped growth × confidence weight high 1.0 / medium 0.6 / low 0.25)")
    if run.ranking:
        lines.append("; ".join(f"{i + 1}. {k} ({s})" for i, (k, s) in enumerate(run.ranking)))
    else:
        lines.append("No usable series — nothing to rank.")
    lines.append("## Checks")
    lines += [f"- {c}" for c in run.checks]
    lines.append("## Limitations")
    lines += [f"- {l}" for l in run.limitations]
    lines.append("## Suggested follow-ups")
    lines += [f"- `{f}`" for f in run.follow_ups]
    lines.append(f"Files: {out_dir}/result.json, data.csv, chart.png")
    return "\n".join(_trim(lines)) + "\n"


def _f(x) -> str:
    return "–" if x is None else f"{x:g}"


def _trim(lines: list[str]) -> list[str]:
    if len(lines) <= MAX_LINES:
        return lines
    # Drop limitation/check bullets from the end of those sections until it fits, keep headers and last line.
    keep_tail = lines[-1]
    body = lines[:-1]
    while len(body) + 1 > MAX_LINES:
        for i in range(len(body) - 1, 0, -1):
            if body[i].startswith("- ") and body[i - 1].startswith("- "):
                del body[i]
                break
        else:
            break
    if len(body) + 1 > MAX_LINES:
        body = body[:MAX_LINES - 2] + ["- … (see result.json for the full list)"]
    return body + [keep_tail]
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_run_summary.py -q`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add wikipedia-interest/wiki_interest/run.py wikipedia-interest/wiki_interest/summary.py wikipedia-interest/tests/test_run_summary.py
git commit -m "Orchestrate analysis runs and render a 40-line agent summary

The agent should read one short, deterministic summary with checks and
limitations up front, not raw JSON, so a small model can answer in one
tool call and cannot skip the caveats."
```

---

### Task 8: Chart rendering

**Files:**
- Create: `wikipedia-interest/wiki_interest/charts.py`
- Test: `wikipedia-interest/tests/test_charts.py`

**Interfaces:**
- Consumes: `RunResult`.
- Produces: `def render_chart(run: RunResult, path: Path) -> Path` (PNG, 1600×900 px at 150 dpi).

- [ ] **Step 1: Write failing test**

`wikipedia-interest/tests/test_charts.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_charts.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.charts'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/charts.py`:
```python
"""Chart: per-million views per language, spike markers, dashed clipped trend."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .run import RunResult, key  # noqa: E402

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf"]


def render_chart(run: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(run.topics)
    cols = 1 if n == 1 else 2
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(10.67, 6 if n == 1 else 4 * rows), dpi=150, squeeze=False)
    for ax, topic in zip(axes.flat, run.topics):
        _plot_topic(ax, run, topic)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(f"Wikipedia interest, views per million project views · {run.window.start}..{run.window.end} · agent=user",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _plot_topic(ax, run: RunResult, topic: str) -> None:
    x_labels = run.window.periods
    x = np.arange(len(x_labels))
    plotted = 0
    for i, lang in enumerate(run.langs):
        s = next(s for s in run.series if s.topic == topic and s.lang == lang)
        m = run.metrics.get(key(topic, lang))
        color = COLORS[i % len(COLORS)]
        if s.status != "ok" or m is None:
            ax.plot([], [], color=color, label=f"{lang}: {s.status.upper()}")
            continue
        y = np.asarray(s.per_million)
        ax.plot(x, y, color=color, lw=1.6, label=f"{lang}: {s.title} ({m.confidence})")
        if m.spike_periods:
            idx = [x_labels.index(p) for p in m.spike_periods if p in x_labels]
            ax.scatter(idx, y[idx], color=color, marker="^", s=40, zorder=3)
        if m.growth_clipped_pct_per_year is not None and len(y) >= 3:
            logs = np.log1p(y)
            spikes = np.zeros(len(y), dtype=bool)
            for p in m.spike_periods:
                if p in x_labels:
                    spikes[x_labels.index(p)] = True
            fit_x = x[~spikes]
            if len(fit_x) >= 3:
                slope, intercept = np.polyfit(fit_x, logs[~spikes], 1)
                ax.plot(x, np.expm1(intercept + slope * x), color=color, lw=1, ls="--", alpha=0.7)
        plotted += 1
    ax.set_title(topic, fontsize=10)
    ax.set_ylabel("views per million")
    step = max(1, len(x_labels) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], rotation=45, ha="right", fontsize=7)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left")
    if plotted == 0:
        ax.text(0.5, 0.5, "no usable data", ha="center", va="center", transform=ax.transAxes)
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_charts.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/charts.py wikipedia-interest/tests/test_charts.py
git commit -m "Render per-million interest chart with spike markers and trend

A picture of spikes versus the clipped trend line is the fastest way for
a founder to see whether growth is organic or news-driven."
```

---

### Task 9: One-page PDF report

**Files:**
- Create: `wikipedia-interest/wiki_interest/pdf.py`
- Test: `wikipedia-interest/tests/test_pdf.py`

**Interfaces:**
- Consumes: `load_run` dict shape (result.json), `chart.png` next to it.
- Produces: `def render_pdf(run_dir: Path, out: Path, title: str | None, notes: str, lang: str = "en") -> Path`; `LABELS = {"en": {...}, "uk": {...}}`.

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_pdf.py`:
```python
import json
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_pdf.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'wiki_interest.pdf'`

- [ ] **Step 3: Implement**

`wikipedia-interest/wiki_interest/pdf.py`:
```python
"""One-page A4 PDF report built with reportlab and matplotlib's bundled DejaVu font."""
from __future__ import annotations

import os
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle

from .run import load_run

FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"
LABELS = {
    "en": {"subtitle": "Wikipedia pageviews (agent=user), views per million project views · {start}..{end} · generated {gen}",
           "table": ["topic", "lang", "title", "pm latest", "pm year ago", "YoY %", "growth/yr % (clipped)", "spikes %", "coverage %", "confidence"],
           "ranking": "Ranking", "notes": "Recommendation", "assumptions": "Assumptions", "limitations": "Limitations",
           "source": "Source: Wikimedia Pageviews API (wikimedia.org/api/rest_v1), Wikidata sitelinks. Built with the wikipedia-interest skill."},
    "uk": {"subtitle": "Перегляди Wikipedia (agent=user), переглядів на мільйон переглядів розділу · {start}..{end} · створено {gen}",
           "table": ["тема", "мова", "стаття", "на млн зараз", "на млн рік тому", "YoY %", "ріст/рік % (без піків)", "піки %", "покриття %", "довіра"],
           "ranking": "Рейтинг", "notes": "Рекомендація", "assumptions": "Припущення", "limitations": "Обмеження",
           "source": "Джерело: Wikimedia Pageviews API (wikimedia.org/api/rest_v1), Wikidata. Побудовано навичкою wikipedia-interest."},
}
CONF_COLORS = {"high": colors.HexColor("#2e7d32"), "medium": colors.HexColor("#ef6c00"), "low": colors.HexColor("#c62828")}


def _register_fonts() -> None:
    if FONT in pdfmetrics.getRegisteredFontNames():
        return
    ttf_dir = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
    pdfmetrics.registerFont(TTFont(FONT, os.path.join(ttf_dir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(ttf_dir, "DejaVuSans-Bold.ttf")))


def render_pdf(run_dir: Path, out: Path, title: str | None, notes: str, lang: str = "en") -> Path:
    _register_fonts()
    run = load_run(Path(run_dir))
    L = LABELS.get(lang, LABELS["en"])
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    W, H = A4
    margin = 14 * mm
    c = canvas.Canvas(str(out), pagesize=A4)
    c.setTitle(title or ", ".join(run["topics"]))
    y = H - margin

    # Title + subtitle
    c.setFont(FONT_BOLD, 15)
    c.drawString(margin, y, _fit(c, title or f"{', '.join(run['topics'])} — {', '.join(run['langs'])}", FONT_BOLD, 15, W - 2 * margin))
    y -= 7 * mm
    c.setFont(FONT, 8)
    c.drawString(margin, y, L["subtitle"].format(start=run["window"]["start"], end=run["window"]["end"], gen=run["generated_at"]))
    y -= 6 * mm

    # Key numbers table
    rows = [L["table"]]
    for k, m in run["metrics"].items():
        topic, lg = k.split("|", 1)
        title_ = run["resolutions"][topic]["per_lang"][lg]["title"] or ""
        rows.append([topic[:28], lg, title_[:26], _f(m["pm_latest"]), _f(m["pm_year_ago"]), _f(m["yoy_pct"]),
                     _f(m["growth_clipped_pct_per_year"]), _f(m["spike_share_pct"]), _f(m["coverage_pct"]), m["confidence"]])
    tbl = Table(rows, colWidths=[30 * mm, 9 * mm, 34 * mm, 15 * mm, 17 * mm, 13 * mm, 22 * mm, 13 * mm, 16 * mm, 14 * mm])
    style = [("FONT", (0, 0), (-1, -1), FONT, 6.5), ("FONT", (0, 0), (-1, 0), FONT_BOLD, 6.5),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    for i, row in enumerate(rows[1:], start=1):
        style.append(("TEXTCOLOR", (-1, i), (-1, i), CONF_COLORS.get(row[-1], colors.black)))
    tbl.setStyle(TableStyle(style))
    tw, th = tbl.wrapOn(c, W - 2 * margin, H)
    tbl.drawOn(c, margin, y - th)
    y -= th + 5 * mm

    # Chart
    chart = Path(run_dir) / "chart.png"
    chart_h = 78 * mm
    if chart.exists():
        c.drawImage(str(chart), margin, y - chart_h, width=W - 2 * margin, height=chart_h, preserveAspectRatio=True, anchor="n")
    else:
        c.setFont(FONT, 8)
        c.drawString(margin, y - 5 * mm, "(chart.png not found)")
    y -= chart_h + 4 * mm

    # Ranking line
    c.setFont(FONT_BOLD, 9)
    c.drawString(margin, y, L["ranking"] + ":")
    c.setFont(FONT, 8)
    ranking = "; ".join(f"{i + 1}. {r['key']} ({r['score']})" for i, r in enumerate(run["ranking"])) or "—"
    c.drawString(margin + 22 * mm, y, _fit(c, ranking, FONT, 8, W - 2 * margin - 22 * mm))
    y -= 6 * mm

    # Footer block (fixed height) then notes fill what remains
    footer_top = margin + 30 * mm
    _draw_footer(c, run, L, margin, W, footer_top)
    avail_h = y - footer_top - 3 * mm
    _draw_notes(c, notes, L["notes"], margin, y, W - 2 * margin, avail_h)

    c.showPage()
    c.save()
    return out


def _draw_notes(c, notes: str, heading: str, x: float, top: float, width: float, avail_h: float) -> None:
    c.setFont(FONT_BOLD, 9)
    c.drawString(x, top, heading)
    top -= 4 * mm
    avail_h -= 4 * mm
    if not notes.strip() or avail_h < 10 * mm:
        return  # nothing to draw, or the table was so tall that no room is left above the footer
    html = _notes_to_html(notes)
    for size in (9, 8.5, 8, 7.5, 7):
        para = Paragraph(html, ParagraphStyle("n", fontName=FONT, fontSize=size, leading=size * 1.25))
        _, h = para.wrap(width, avail_h)
        if h <= avail_h:
            para.drawOn(c, x, top - h)
            return
    # Truncate at 7 pt until it fits
    words = html.split(" ")
    while words:
        words = words[: max(1, int(len(words) * 0.85))]
        para = Paragraph(" ".join(words) + " …", ParagraphStyle("n", fontName=FONT, fontSize=7, leading=8.75))
        _, h = para.wrap(width, avail_h)
        if h <= avail_h:
            para.drawOn(c, x, top - h)
            return
        if len(words) == 1:
            return


def _draw_footer(c, run: dict, L: dict, margin: float, W: float, top: float) -> None:
    width = W - 2 * margin
    text = f"<b>{L['assumptions']}:</b> " + " ".join(run["assumptions"][:4]) + \
           f"<br/><b>{L['limitations']}:</b> " + " ".join(run["limitations"][:6]) + \
           f"<br/>{L['source']}"
    for size in (7, 6.5, 6, 5.5):
        para = Paragraph(text, ParagraphStyle("f", fontName=FONT, fontSize=size, leading=size * 1.2, textColor=colors.HexColor("#444444")))
        _, h = para.wrap(width, top - margin)
        if h <= top - margin:
            para.drawOn(c, margin, top - h)
            return
    para = Paragraph(text[:1500] + " …", ParagraphStyle("f", fontName=FONT, fontSize=5.5, leading=6.6))
    _, h = para.wrap(width, top - margin)
    para.drawOn(c, margin, max(margin, top - h))


def _notes_to_html(notes: str) -> str:
    out = []
    for line in notes.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith(("- ", "* ")):
            out.append("&bull; " + line[2:])
        else:
            out.append(line)
    return "<br/>".join(out)


def _fit(c, text: str, font: str, size: float, width: float) -> str:
    while text and pdfmetrics.stringWidth(text, font, size) > width:
        text = text[:-2] + "…"
    return text


def _f(x) -> str:
    return "–" if x is None else f"{x:g}"
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_pdf.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add wikipedia-interest/wiki_interest/pdf.py wikipedia-interest/tests/test_pdf.py
git commit -m "Build one-page PDF report with table, chart, verdict and caveats

A shareable page must always fit: the narrative shrinks and truncates
before the assumptions and limitations footer ever gets pushed out."
```

---

### Task 10: CLI entrypoint with resolve / analyze / report

**Files:**
- Create: `wikipedia-interest/scripts/wiki_interest.py`
- Delete: `wikipedia-interest/scripts/.gitkeep`
- Test: `wikipedia-interest/tests/test_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `main(argv: list[str] | None = None) -> int` (exit code), subcommands per spec §4.

- [ ] **Step 1: Write failing tests**

`wikipedia-interest/tests/test_cli.py`:
```python
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

ROOT = Path(__file__).resolve().parents[1]
FIX = Path(__file__).parent / "fixtures"


def _cli():
    spec = importlib.util.spec_from_file_location("wiki_interest_cli", ROOT / "scripts" / "wiki_interest.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mock_world(uk_ok=True):
    respx.get(url__regex=r".*wbsearchentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_search_if.json").read_text())))
    respx.get(url__regex=r".*wbgetentities.*").mock(return_value=httpx.Response(200, json=json.loads((FIX / "wd_entities_if.json").read_text())))
    respx.get(url__regex=r".*wikipedia.*list=search.*").mock(return_value=httpx.Response(200, json={"query": {"search": []}}))
    respx.get(url__regex=r".*/aggregate/.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": f"2026{m:02d}0100", "views": 50_000_000} for m in (6, 7, 8)]}))
    respx.get(url__regex=r".*/per-article/cs\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
        {"timestamp": "2026060100", "views": 500}, {"timestamp": "2026070100", "views": 600}, {"timestamp": "2026080100", "views": 700}]}))
    if uk_ok:
        respx.get(url__regex=r".*/per-article/uk\.wikipedia.*").mock(return_value=httpx.Response(200, json={"items": [
            {"timestamp": "2026060100", "views": 900}, {"timestamp": "2026070100", "views": 800}, {"timestamp": "2026080100", "views": 700}]}))
    else:
        respx.get(url__regex=r".*/per-article/.*").mock(return_value=httpx.Response(404, json={"detail": "no data"}))


@respx.mock
def test_resolve_prints_table(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["resolve", "--topic", "intermittent fasting", "--langs", "pl,cs"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "cs" in out and "Přerušovaný půst" in out and "missing" in out and "Q1666254" in out


@respx.mock
def test_analyze_writes_files_and_prints_summary(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run1"
    rc = _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "cs,uk", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)])
    out = capsys.readouterr().out
    assert rc == 0
    for f in ("result.json", "summary.md", "chart.png", "data.csv"):
        assert (out_dir / f).exists(), f
    assert out.startswith("# ") and "## Checks" in out


@respx.mock
def test_analyze_exit_2_when_nothing_usable(capsys, tmp_path, monkeypatch):
    _mock_world(uk_ok=False)
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run2"
    rc = _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "pl,uk", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "no usable" in captured.err.lower()
    assert (out_dir / "summary.md").exists()


def test_analyze_bad_args_exit_3(capsys, tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    rc = _cli().main(["analyze", "--topic", "x", "--langs", "uk", "--start", "2026-08", "--end", "2026-01", "--out", str(tmp_path / "r")])
    assert rc == 3
    assert "after end" in capsys.readouterr().err


def test_analyze_requires_topic(capsys, tmp_path):
    rc = _cli().main(["analyze", "--langs", "uk", "--out", str(tmp_path / "r")])
    assert rc == 3


@respx.mock
def test_report_creates_pdf(capsys, tmp_path, monkeypatch):
    _mock_world()
    monkeypatch.setenv("WIKI_INTEREST_CACHE", str(tmp_path / "c.sqlite"))
    out_dir = tmp_path / "run3"
    assert _cli().main(["analyze", "--topic", "intermittent fasting", "--langs", "cs", "--start", "2026-06", "--end", "2026-08", "--out", str(out_dir)]) == 0
    rc = _cli().main(["report", "--run", str(out_dir), "--title", "IF in Czech", "--notes", "Grows.\n- keep watching", "--lang", "uk"])
    assert rc == 0
    assert (out_dir / "report.pdf").exists()
    assert "report.pdf" in capsys.readouterr().out


def test_report_missing_run_exit_3(capsys, tmp_path):
    rc = _cli().main(["report", "--run", str(tmp_path / "nope")])
    assert rc == 3
    assert "analyze" in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_cli.py -q`
Expected: FAIL with `FileNotFoundError` / `AttributeError: module has no attribute 'main'`

- [ ] **Step 3: Implement**

`wikipedia-interest/scripts/wiki_interest.py`:
```python
#!/usr/bin/env python3
"""wikipedia-interest CLI: resolve | analyze | report.

Run from the skill root:  uv run scripts/wiki_interest.py <command> ...
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from wiki_interest.api import ApiError, WikiClient  # noqa: E402
from wiki_interest.cache import Cache  # noqa: E402
from wiki_interest.charts import render_chart  # noqa: E402
from wiki_interest.pdf import render_pdf  # noqa: E402
from wiki_interest.resolve import resolve_topic  # noqa: E402
from wiki_interest.run import run_analysis, write_run  # noqa: E402
from wiki_interest.summary import render_summary  # noqa: E402

EXIT_OK, EXIT_NO_DATA, EXIT_BAD_ARGS = 0, 2, 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="wiki_interest.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--topic", help="topic in any language, e.g. 'intermittent fasting' or 'астрономія'")
        sp.add_argument("--topics", help="several topics separated by ';' (analyze only)")
        sp.add_argument("--langs", required=True, help="comma-separated Wikipedia language codes, e.g. uk,pl,cs")
        sp.add_argument("--lang-hint", help="language the topic text is written in (default: auto)")
        sp.add_argument("--qid", help="force a Wikidata item, e.g. Q1666254")
        sp.add_argument("--titles", help="override titles: pl=Post_przerywany,cs=Přerušovaný_půst")
        sp.add_argument("--no-cache", action="store_true", help="ignore cached responses (still writes cache)")

    r = sub.add_parser("resolve", help="preview which article each language maps to (cheap)")
    common(r)
    r.add_argument("--json", action="store_true")

    a = sub.add_parser("analyze", help="fetch, normalize, compute trends/confidence, write summary+chart")
    common(a)
    a.add_argument("--months", type=int, default=None, help="last N full months (default 24)")
    a.add_argument("--start", help="YYYY-MM (with --end)")
    a.add_argument("--end", help="YYYY-MM (with --start); clamped to last closed month")
    a.add_argument("--granularity", choices=["monthly", "daily"], default="monthly")
    a.add_argument("--rank-by", choices=["score", "growth", "volume"], default="score")
    a.add_argument("--out", help="output directory (default runs/<slug>)")

    rp = sub.add_parser("report", help="build one-page PDF from an analyze run")
    rp.add_argument("--run", required=True, help="directory written by analyze")
    rp.add_argument("--title")
    rp.add_argument("--notes", default="", help="your recommendation: paragraphs and '- ' bullets")
    rp.add_argument("--notes-file", help="read --notes from a file")
    rp.add_argument("--lang", choices=["en", "uk"], default="en")
    rp.add_argument("--out", help="PDF path (default <run>/report.pdf)")
    return p


def make_client(no_cache: bool) -> WikiClient:
    cache_path = Path(os.environ.get("WIKI_INTEREST_CACHE", SKILL_ROOT / ".cache" / "cache.sqlite"))
    cache = Cache(cache_path)
    if no_cache:
        cache.get = lambda url, now=None: None  # type: ignore[assignment]
    return WikiClient(cache=cache)


def _langs(s: str) -> list[str]:
    langs = [x.strip().lower() for x in s.split(",") if x.strip()]
    if not langs:
        raise ValueError("--langs must list at least one language code")
    return langs


def _titles(s: str | None) -> dict[str, str]:
    if not s:
        return {}
    out = {}
    for pair in s.split(","):
        if "=" not in pair:
            raise ValueError(f"--titles entries must look like lang=Title, got {pair!r}")
        k, v = pair.split("=", 1)
        out[k.strip().lower()] = v.strip()
    return out


def _topics(args) -> list[str]:
    if args.topics:
        return [t.strip() for t in args.topics.split(";") if t.strip()]
    if args.topic:
        return [args.topic.strip()]
    raise ValueError("--topic or --topics is required")


def cmd_resolve(args) -> int:
    client = make_client(args.no_cache)
    res = resolve_topic(client, _topics(args)[0], _langs(args.langs), hint=args.lang_hint, qid=args.qid, overrides=_titles(args.titles))
    if args.json:
        import json
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"topic: {res.topic}  →  {res.qid or '(no Wikidata item)'} «{res.label or ''}»")
    print("| lang | status | title | note |")
    print("|---|---|---|---|")
    for lang, lr in res.per_lang.items():
        cand = f" candidates: {', '.join(lr.candidates)}" if lr.candidates else ""
        print(f"| {lang} | {lr.status} | {lr.title or ''} | {lr.note}{cand} |")
    if res.alternatives:
        print("other Wikidata candidates: " + "; ".join(f"{a['qid']} «{a['label']}» ({a['description']})" for a in res.alternatives))
        print("(use --qid to pick one)")
    return EXIT_OK


def cmd_analyze(args) -> int:
    topics = _topics(args)
    langs = _langs(args.langs)
    out_dir = Path(args.out) if args.out else SKILL_ROOT / "runs" / _slug(topics, langs, args)
    client = make_client(args.no_cache)
    run = run_analysis(client, topics, langs, args.months, args.start, args.end, args.granularity, args.rank_by,
                       _titles(args.titles), args.qid, args.lang_hint, date.today(), out_dir)
    summary = render_summary(run, out_dir)
    write_run(run, out_dir, summary)
    render_chart(run, out_dir / "chart.png")
    print(summary)
    if not run.usable():
        print("ERROR: no usable series — every requested language is missing or has no pageview data. "
              "Check the Resolved line, try `resolve` with --lang-hint, or pass --titles.", file=sys.stderr)
        return EXIT_NO_DATA
    return EXIT_OK


def cmd_report(args) -> int:
    run_dir = Path(args.run)
    notes = args.notes
    if args.notes_file:
        notes = Path(args.notes_file).read_text(encoding="utf-8")
    out = Path(args.out) if args.out else run_dir / "report.pdf"
    path = render_pdf(run_dir, out, args.title, notes, args.lang)
    print(f"wrote {path}")
    return EXIT_OK


def _slug(topics, langs, args) -> str:
    import re
    t = re.sub(r"[^a-z0-9Ѐ-ӿ]+", "-", ";".join(topics).lower()).strip("-")[:40]
    span = f"{args.start}_{args.end}" if args.start else f"{args.months or 24}m"
    return f"{t}-{'-'.join(langs)}-{span}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return {"resolve": cmd_resolve, "analyze": cmd_analyze, "report": cmd_report}[args.cmd](args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_BAD_ARGS
    except ApiError as exc:
        print(f"ERROR: API failure: {exc}\nHint: retry in a minute; check network access to wikimedia.org.", file=sys.stderr)
        return EXIT_NO_DATA


if __name__ == "__main__":
    sys.exit(main())
```

Note: argparse exits with code 2 on its own for unknown flags; that is acceptable (documented in api-notes).

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: all pass (≈ 47 tests).

- [ ] **Step 5: Manual smoke against live API**

Run (from `wikipedia-interest/`):
```bash
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs,uk
uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs pl,cs,uk --months 24 --out runs/if-demo
uv run scripts/wiki_interest.py report --run runs/if-demo --title "Intermittent fasting: PL vs CS" --notes "Czech interest is higher per reader.\n- Polish has no article" --lang en
```
Expected: table shows pl missing with candidates, cs and uk found; summary printed ≤ 40 lines; `runs/if-demo/report.pdf` opens as one page. Second `analyze` run should report cache hits.

- [ ] **Step 6: Commit**

```bash
git rm -q wikipedia-interest/scripts/.gitkeep
git add wikipedia-interest/scripts/wiki_interest.py wikipedia-interest/tests/test_cli.py
git commit -m "Add resolve/analyze/report CLI entrypoint

One command per agent step, summary on stdout, files on disk, and
distinct exit codes so a small model can branch on failure without
parsing JSON."
```

---

### Task 11: SKILL.md body, references and assets

**Files:**
- Modify: `wikipedia-interest/SKILL.md` (replace body)
- Create: `wikipedia-interest/references/methodology.md`
- Create: `wikipedia-interest/references/api-notes.md`
- Create: `wikipedia-interest/references/examples.md`
- Create: `wikipedia-interest/assets/report_notes_template.md`
- Test: `wikipedia-interest/tests/test_skill_docs.py`

**Interfaces:** none (documentation), but `SKILL.md` line count ≤ 150 and every referenced path must exist.

- [ ] **Step 1: Write failing test**

`wikipedia-interest/tests/test_skill_docs.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_skill_docs.py -q`
Expected: FAIL (`references/methodology.md` missing; body placeholder lacks words).

- [ ] **Step 3: Write SKILL.md**

Replace `wikipedia-interest/SKILL.md` (keep the frontmatter from Task 1 verbatim) with this body:
```markdown
# Wikipedia Interest

Compare how much readers of different Wikipedia language editions care about a topic, whether that
interest is growing, and how much to trust the growth. Built for B2C founders choosing which topics
to develop and which languages/markets to launch next.

## Use it when
- "Is interest in X growing in <language> Wikipedia?" / "Can we trust that growth?"
- "Compare X across pl/cs/uk…" / "Which of these languages/topics should we explore next?"
- The user wants a chart or a one-page PDF to share.

## Not for
Revenue or willingness to pay, search-engine demand, article edits, anything before 2015-07,
country-level data (a language edition is not a country).

## Setup (once per machine)
Run every command from this skill's directory. `uv` installs pinned dependencies on first run.

```bash
uv run scripts/wiki_interest.py --help
```

## Workflow
1. **Resolve titles first when the topic is ambiguous, non-English, or the user named specific articles.**
   `resolve` is cheap (Wikidata only). Show the user the table if any language is `missing` or if
   "other Wikidata candidates" appear, and confirm before analyzing.
   ```bash
   uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
   ```
2. **Analyze.** One call fetches, normalizes and scores everything, prints a ≤40-line summary and
   writes `result.json`, `data.csv`, `chart.png` under `--out`.
   ```bash
   uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 24 --out runs/astro-uk
   uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl,cs,uk,de --out runs/eng
   ```
   Useful flags: `--months N` (default 24 full months) or `--start YYYY-MM --end YYYY-MM`;
   `--titles pl=Post_przerywany` to force a title; `--qid Q…` to pick a Wikidata item;
   `--granularity daily` for short windows; `--rank-by score|growth|volume`.
3. **Read the summary before answering.** In this order: `Resolved` line (which languages actually
   have data), the `confidence` column, `## Checks`, `## Limitations`, then the numbers.
4. **Answer** with: per-million values (not raw views) for each language, clipped growth per year,
   YoY %, the confidence level with its reasons, and the limitations that apply. Quote the ranking
   rule when you rank. Mention missing languages explicitly.
5. **Report** only when the user wants a shareable file. Write 3–6 sentences of recommendation
   yourself (template: [assets/report_notes_template.md](assets/report_notes_template.md)) and pass
   them via `--notes`; `--lang uk` switches labels to Ukrainian.
   ```bash
   uv run scripts/wiki_interest.py report --run runs/astro-uk --title "Astronomy in Ukrainian Wikipedia" --notes "..." --lang uk
   ```

## Interpretation rules (do not skip)
- Compare languages by **views per million project views**; raw views favour big editions.
- **Missing article ≠ no interest.** Say the article does not exist; suggest `--titles` only if a
  search candidate is clearly the same topic.
- Headline growth is the **clipped** figure (spikes removed). If `spikes %` is high, say growth is
  news-driven; offer the daily follow-up command printed in the summary.
- Never state a growth number without its **confidence** (high / medium / low) and at least one
  reason from `result.json` → `metrics.<key>.reasons`.
- `coverage %` < 100 means the article did not exist for part of the window; growth is inflated.
- The current month is excluded; data starts 2015-07.
- Always list the assumptions that matter (filters, normalization, window).

## Follow-ups and related questions
- Re-run `analyze` with changed flags; responses are cached in `.cache/`, so adding a language or
  changing the window costs seconds. Keep related runs in sibling `--out` directories.
- "Which audiences next?" → one `analyze` with all candidate `--langs`, then rank; explain the
  score rule and show the confidence of each row.
- "How trustworthy?" → read `reasons`, `spike_share_pct`, `coverage_pct`, `p_value` from
  `result.json`; the summary's Limitations already lists the important ones.
- Exit code 2 = nothing usable (check titles); 3 = bad arguments (message says what to fix).

## Commands
| command | purpose | key flags |
|---|---|---|
| `resolve` | map topic → article per language, cheap preview | `--topic --langs --lang-hint --qid --titles --json` |
| `analyze` | fetch + normalize + trend + confidence + chart | `--topic/--topics --langs --months/--start/--end --granularity --rank-by --titles --out` |
| `report` | one-page PDF from a run | `--run --title --notes/--notes-file --lang --out` |

## Read more
- [references/methodology.md](references/methodology.md) — metrics, thresholds, confidence rules, ranking.
- [references/api-notes.md](references/api-notes.md) — endpoints, quirks, cache, error codes.
- [references/examples.md](references/examples.md) — the three canonical requests worked end to end.
```

- [ ] **Step 4: Write references/methodology.md**

`wikipedia-interest/references/methodology.md`:
```markdown
# Methodology

Source: Wikimedia Pageviews API, `access=all-access`, `agent=user`. Monthly granularity by default.

## Per (topic, language) series
- `per_million[t] = views[t] / project_views[t] × 1e6` — share of the edition's attention. This is
  what makes uk (≈100M views/month) comparable with en (≈8B views/month).
- `pm_latest` = mean of the last 3 months (7 days when daily); `pm_year_ago` = same 3 months, 12 months earlier.
- `yoy_pct` = mean of last 12 months vs the 12 before, needs ≥ 24 months.
- `growth_pct_per_year` = OLS slope of `log1p(per_million)` against time, annualized:
  `(exp(slope × 12) − 1) × 100` (× 365 for daily).
- Spikes: robust z-score `0.6745 × (x − median) / MAD` on the log series; a period is a spike when z > 3.5
  (`spike_z`). `spike_share_pct` = share of total views that fall in spike periods.
- Clipped series: spike periods replaced by the median of non-spike neighbours (window 5). The
  headline `growth_clipped_pct_per_year` is computed on it.
- Monotonicity: Spearman rho between time and the clipped series; `p_value` from a 2000-permutation
  test (seeded, deterministic). Small p → consistent direction, not noise.
- `seasonality_amp` = (max − min of month-of-year means) / overall mean, needs ≥ 24 months.
- `coverage_pct` = periods with views > 0 / periods; `first_seen` = first such period (article age proxy).

## Confidence
`low` if any hard flag:
- coverage < 70 (`low_coverage_pct`), spike share > 30 (`low_spike_pct`), p > 0.1 (`low_p`),
  |growth − growth_clipped| > 25 points, or total views < 1000.
`medium` if any soft flag: coverage < 90, spike share > 10, p > 0.05, fewer than 24 months.
`high` otherwise. `reasons[]` always lists the triggered flags — quote them.

## Ranking
`score = growth_clipped × weight(confidence)`, weights high 1.0 / medium 0.6 / low 0.25; ties by `pm_latest`.
`--rank-by growth` uses clipped growth alone; `--rank-by volume` uses `pm_latest`. Say which rule you used.

## Fixed limitations (always true)
Interest ≠ willingness to pay · views depend on article existence/quality · bot filtering is imperfect ·
a language edition is not a country · Wikipedia readers skew toward certain demographics.

## Interpreting common shapes
- Rising clipped trend, low spikes, high confidence → organic growth; good candidate.
- Flat trend with big spikes → news-driven; not a durable audience signal.
- Low coverage → new article; compare only the covered months (`--start`).
- Missing in a language → no article; consider it an opportunity signal only after checking search candidates.
```

- [ ] **Step 5: Write references/api-notes.md**

`wikipedia-interest/references/api-notes.md`:
```markdown
# API notes

## Endpoints used
- Per-article: `https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/{title}/{monthly|daily}/{YYYYMMDD}/{YYYYMMDD}`
- Aggregate (project totals for normalization): `…/aggregate/{lang}.wikipedia/all-access/user/{monthly|daily}/{YYYYMMDDHH}/{YYYYMMDDHH}`
- Wikidata: `wbsearchentities` (topic → items), `wbgetentities&props=sitelinks|labels` (item → titles per language)
- MediaWiki per edition: `action=query&redirects=1` (canonical title), `list=search` (candidates when missing)

## Quirks
- Data starts 2015-07-01. Requests before that fail validation (exit 3).
- 404 means "no data for this article/window" (article missing, renamed, or zero traffic), not a network error.
  The skill records it as `no_data` and continues with the other languages.
- Titles are percent-encoded with `/` escaped; spaces become underscores. Redirect targets are resolved
  so the canonical page is counted.
- The current month is incomplete and excluded; windows are clamped to the last closed month.
- Per-article monthly rows only exist for months with ≥ 1 view; missing months are aligned to 0.
- Rate limit guidance: stay well under 100 req/s. The client uses sequential requests, retries
  429/5xx three times with exponential backoff, and identifies itself with a descriptive User-Agent
  (set `WIKI_INTEREST_CONTACT=you@example.com` to add contact info).

## Cache
- SQLite at `.cache/cache.sqlite` (override with `WIKI_INTEREST_CACHE`). Closed-month windows are
  permanent; everything else expires after 7 days. `--no-cache` forces refetch.
- Cache hit/miss counts are printed under `## Checks`.

## Exit codes
- 0 — success (possibly partial: some languages missing, listed in Checks)
- 2 — no usable series at all, or API unavailable after retries
- 3 — invalid arguments or missing run directory (message says what to fix)
```

- [ ] **Step 6: Write references/examples.md**

`wikipedia-interest/references/examples.md`:
```markdown
# Worked examples

## 1. "Compare growth of interest in intermittent fasting in Polish and Czech Wikipedia over two years"
```bash
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
# pl → missing (no plwiki article linked to Q1666254; search candidates listed), cs → «Přerušovaný půst»
uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs pl,cs --months 24 --out runs/if-pl-cs
```
Answer shape: "Czech: X per million now vs Y a year ago, clipped growth Z %/yr, confidence …
because …; Polish Wikipedia has no article on the topic, so there is no signal — that is not
evidence of no interest. If the user confirms `Post przerywany` is the same topic, re-run with
`--titles pl=Post_przerywany`."

## 2. "Is interest in astronomy growing in Ukrainian Wikipedia, and how much can we trust it?"
```bash
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --months 36 --out runs/astro-uk
```
Answer shape: growth (clipped) and YoY, confidence with its reasons (coverage, spikes, p-value),
seasonality note if `seasonality_amp` is large (school year), limitations. Offer the daily
follow-up command from the summary if a spike dominates.

## 3. "We build a language-learning app. Compare interest in learning English across our language editions and say which audiences to research next"
```bash
uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl,cs,uk,de,es --months 24 --rank-by score --out runs/english
uv run scripts/wiki_interest.py report --run runs/english --title "Interest in English across editions" --notes "<3–6 sentences>" --lang en
```
Answer shape: table of per-million and clipped growth per language, the ranking with the rule
stated, which rows have low confidence and why, and the recommendation: research the top 2 by
score, note that per-million interest in a topic is a proxy for audience curiosity, not demand.

## Follow-up: "now add Czech and only the last 12 months"
```bash
uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk,cs --months 12 --out runs/astro-uk-cs-12m
```
Cached responses make this take seconds. Note that with 12 months YoY is unavailable and confidence
is at most medium.
```

- [ ] **Step 7: Write assets/report_notes_template.md**

`wikipedia-interest/assets/report_notes_template.md`:
```markdown
Recommendation template for `report --notes` (replace the angle-bracket parts, keep it to 3–6 sentences):

<Headline verdict: which topic/language shows the strongest, most trustworthy growth and why.>
<Key numbers: per-million now vs a year ago and clipped growth per year for the top 1–2 rows; confidence level with one reason.>
<What weakens the signal: spikes, coverage, missing languages — one sentence.>
- Next step 1: <e.g. run user interviews in the leading language>
- Next step 2: <e.g. re-check in 3 months / inspect the spike month daily>
```

- [ ] **Step 8: Run tests and validator**

Run:
```bash
uv run pytest tests/test_skill_docs.py -q
uvx skills-ref validate .
```
Expected: `2 passed`; validator OK.

- [ ] **Step 9: Commit**

```bash
git add wikipedia-interest/SKILL.md wikipedia-interest/references wikipedia-interest/assets wikipedia-interest/tests/test_skill_docs.py
git commit -m "Write SKILL.md workflow, methodology and API references

The instructions put confidence and checks before numbers and keep the
main file short so a Haiku-class model follows the workflow instead of
improvising; details load on demand from references."
```

---

### Task 12: Live integration tests and recorded example runs

**Files:**
- Create: `wikipedia-interest/tests/test_network.py`
- Create: `examples/` at repo root with the three example runs' `summary.md`, `chart.png`, `report.pdf` (small, committed as evidence)

**Interfaces:** none new.

- [ ] **Step 1: Write network tests**

`wikipedia-interest/tests/test_network.py`:
```python
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
```

- [ ] **Step 2: Run them**

Run (from `wikipedia-interest/`): `uv run pytest -m network -q`
Expected: `3 passed` (needs internet; takes < 1 min thanks to cache after first run).

- [ ] **Step 3: Produce and commit example outputs**

Run from `wikipedia-interest/`:
```bash
uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs pl,cs --months 24 --out ../examples/01-intermittent-fasting-pl-cs
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --months 36 --out ../examples/02-astronomy-uk
uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl,cs,uk,de,es --months 24 --out ../examples/03-english-multi
uv run scripts/wiki_interest.py report --run ../examples/03-english-multi --title "Interest in English across Wikipedia editions" --notes-file ../examples/03-notes.md --lang en
```
Write `examples/03-notes.md` by hand from the actual summary (3–6 sentences following the template).
Read each `summary.md`; confirm the numbers, confidence and limitations read sensibly. Then commit
`examples/*/summary.md`, `chart.png`, `report.pdf`, `data.csv` (not `result.json` if > 200 KB).

- [ ] **Step 4: Commit**

```bash
git add wikipedia-interest/tests/test_network.py examples
git commit -m "Add live API tests and recorded example runs

Reviewers can see real outputs for the three canonical requests without
running anything, and the network suite proves the pipeline end to end."
```

---

### Task 13: OpenRouter eval harness on Haiku 4.5

**Files:**
- Create: `eval/pyproject.toml`
- Create: `eval/run_eval.py`
- Create: `eval/prompts.json`
- Create: `eval/RESULTS.md` (generated + hand-edited)
- Create: `.env.example`
- Test: `eval/test_run_eval.py` (offline: tool sandboxing and rubric logic)

**Interfaces:**
- Produces: `python run_eval.py --model anthropic/claude-haiku-4.5 [--prompt-id 1] [--max-turns 15]`; writes `eval/transcripts/<model>/<id>.md` and `.raw.json`, appends rubric rows to `eval/RESULTS.md`.
- Tools exposed to the model (OpenAI function format): `bash(command)` executed with `cwd=wikipedia-interest/`, timeout 240 s, output truncated to 8000 chars; `read_file(path)` restricted to the skill dir.
- System prompt: "You are a helpful analyst agent. A skill is installed:" + full `SKILL.md` + note that the tools run in the skill directory.

- [ ] **Step 1: Write eval config**

`eval/pyproject.toml`:
```toml
[project]
name = "wikipedia-interest-eval"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "python-dotenv>=1.0"]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["."]
```

`eval/prompts.json`:
```json
[
  {"id": "1-if-pl-cs", "prompt": "Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за останні два роки.",
   "expect": ["per million|на мільйон|per-million", "confidence|довір|впевнен", "Polish|польськ|pl.*(missing|відсут|немає)"]},
  {"id": "2-astro-uk", "prompt": "Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню можна довіряти?",
   "expect": ["growth|зрост|ріст", "confidence|довір|впевнен", "%"]},
  {"id": "3-english-multi", "prompt": "Ми створюємо застосунок для вивчення мов. Порівняй інтерес до вивчення англійської у польському, чеському, українському та німецькому розділах Wikipedia та підготуй короткий PDF-звіт: які аудиторії варто дослідити наступними й чому?",
   "expect": ["report.pdf|PDF|pdf", "rank|рейтинг|перш", "confidence|довір|впевнен"]},
  {"id": "4-followup", "prompt": "Тепер додай іспанський розділ і візьми лише останні 12 місяців. Що змінилось?",
   "after": "3-english-multi",
   "expect": ["es|іспан", "12"]}
]
```

`.env.example` (repo root):
```
OPENROUTER_API_KEY=sk-or-...
WIKI_INTEREST_CONTACT=you@example.com
```

- [ ] **Step 2: Write failing offline test**

`eval/test_run_eval.py`:
```python
from pathlib import Path

from run_eval import run_tool, score


def test_bash_runs_in_skill_dir():
    out = run_tool("bash", {"command": "ls SKILL.md"})
    assert out.strip() == "SKILL.md"


def test_read_file_blocks_escape():
    out = run_tool("read_file", {"path": "../../etc/passwd"})
    assert out.startswith("ERROR")


def test_read_file_reads_skill_file():
    assert "wikipedia-interest" in run_tool("read_file", {"path": "SKILL.md"})


def test_score_counts_expectations_and_tool_calls():
    transcript = [{"role": "assistant", "tool_calls": [{"function": {"name": "bash", "arguments": '{"command": "uv run scripts/wiki_interest.py analyze --topic x --langs pl"}'}}]},
                  {"role": "assistant", "content": "Czech per million grew; confidence medium. Polish is missing."}]
    s = score(transcript, ["per million", "confidence", "Polish.*missing"])
    assert s["matched"] == 3 and s["tool_calls"] == 1 and s["used_analyze"] is True
```

Run: `cd eval && uv run pytest -q` → Expected: FAIL `ModuleNotFoundError: No module named 'run_eval'`

- [ ] **Step 3: Implement run_eval.py**

`eval/run_eval.py`:
```python
#!/usr/bin/env python3
"""Run the task's example prompts against a cheap model via OpenRouter with the skill installed.

Usage: uv run run_eval.py --model anthropic/claude-haiku-4.5 [--prompt-id 1-if-pl-cs] [--max-turns 15]
Writes transcripts to eval/transcripts/<model>/ and appends a rubric row to eval/RESULTS.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SKILL_DIR = REPO / "wikipedia-interest"
load_dotenv(REPO / ".env")

TOOLS = [
    {"type": "function", "function": {"name": "bash", "description": "Run a shell command inside the skill directory (cwd = skill root). Output truncated to 8000 chars.",
                                       "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read a text file inside the skill directory by relative path.",
                                       "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]


def system_prompt() -> str:
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    return ("You are an analyst agent helping a B2C product founder. Answer in the user's language. "
            "You have two tools: bash (runs in the skill directory) and read_file. The following skill is installed "
            "and its working directory is your bash cwd:\n\n" + skill)


def run_tool(name: str, args: dict) -> str:
    if name == "bash":
        try:
            p = subprocess.run(args["command"], shell=True, cwd=SKILL_DIR, capture_output=True, text=True, timeout=240)
        except subprocess.TimeoutExpired:
            return "ERROR: command timed out after 240 s"
        out = (p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr.strip() else "")).strip()
        out = out or f"(no output, exit {p.returncode})"
        return out[:8000] + ("\n…[truncated]" if len(out) > 8000 else "")
    if name == "read_file":
        target = (SKILL_DIR / args["path"]).resolve()
        if SKILL_DIR not in target.parents and target != SKILL_DIR:
            return "ERROR: path escapes the skill directory"
        if not target.exists():
            return f"ERROR: {args['path']} not found"
        text = target.read_text(encoding="utf-8", errors="replace")
        return text[:12000] + ("\n…[truncated]" if len(text) > 12000 else "")
    return f"ERROR: unknown tool {name}"


def chat(model: str, messages: list[dict], api_key: str) -> dict:
    for attempt in range(4):
        r = httpx.post("https://openrouter.ai/api/v1/chat/completions",
                       headers={"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://github.com/vampir/genesisAiEngineerCourse",
                                "X-Title": "wikipedia-interest skill eval"},
                       json={"model": model, "messages": messages, "tools": TOOLS, "temperature": 0}, timeout=180)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"OpenRouter kept failing: {r.status_code} {r.text[:300]}")


def run_prompt(model: str, prompt: dict, prior: list[dict] | None, max_turns: int, api_key: str) -> tuple[list[dict], str, dict]:
    messages = prior[:] if prior else [{"role": "system", "content": system_prompt()}]
    messages.append({"role": "user", "content": prompt["prompt"]})
    usage_total = {"prompt_tokens": 0, "completion_tokens": 0}
    final = ""
    for _ in range(max_turns):
        resp = chat(model, messages, api_key)
        usage = resp.get("usage", {})
        for k in usage_total:
            usage_total[k] += usage.get(k, 0)
        msg = resp["choices"][0]["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            final = msg.get("content") or ""
            break
        for call in calls:
            fn = call["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(fn["name"], args)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    return messages, final, usage_total


def score(messages: list[dict], expectations: list[str]) -> dict:
    final = next((m.get("content") or "" for m in reversed(messages) if m.get("role") == "assistant" and not m.get("tool_calls")), "")
    calls = [c for m in messages if m.get("role") == "assistant" for c in (m.get("tool_calls") or [])]
    cmds = [json.loads(c["function"]["arguments"]).get("command", "") for c in calls if c["function"]["name"] == "bash"]
    matched = sum(1 for e in expectations if re.search(e, final, re.I | re.S))
    return {
        "matched": matched, "expected": len(expectations), "tool_calls": len(calls),
        "used_resolve": any(" resolve " in c for c in cmds),
        "used_analyze": any(" analyze " in c for c in cmds),
        "used_report": any(" report " in c for c in cmds),
        "final_chars": len(final),
    }


def write_transcript(path: Path, messages: list[dict], usage: dict, sc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".raw.json").write_text(json.dumps(messages, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# Transcript — {path.stem}", f"usage: {usage}", f"score: {sc}", ""]
    for m in messages:
        role = m.get("role")
        if role == "system":
            lines.append("## system\n(SKILL.md as system prompt — omitted)\n")
        elif role == "user":
            lines.append(f"## user\n{m['content']}\n")
        elif role == "assistant":
            if m.get("tool_calls"):
                for c in m["tool_calls"]:
                    lines.append(f"## assistant → {c['function']['name']}\n```\n{json.loads(c['function']['arguments']).get('command') or c['function']['arguments']}\n```\n")
            if m.get("content"):
                lines.append(f"## assistant\n{m['content']}\n")
        elif role == "tool":
            lines.append(f"## tool result\n```\n{m['content'][:3000]}\n```\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompt-id")
    ap.add_argument("--max-turns", type=int, default=15)
    args = ap.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY missing (put it in .env at repo root)")
        return 3
    prompts = json.loads((HERE / "prompts.json").read_text(encoding="utf-8"))
    if args.prompt_id:
        prompts = [p for p in prompts if p["id"] == args.prompt_id or p.get("after") == args.prompt_id]
    histories: dict[str, list[dict]] = {}
    rows = []
    for p in prompts:
        prior = histories.get(p["after"]) if p.get("after") else None
        t0 = time.time()
        messages, final, usage = run_prompt(args.model, p, prior, args.max_turns, api_key)
        histories[p["id"]] = messages
        sc = score(messages, p["expect"])
        slug = re.sub(r"[^a-z0-9]+", "-", args.model.lower())
        write_transcript(HERE / "transcripts" / slug / f"{p['id']}.md", messages, usage, sc)
        rows.append(f"| {datetime.now(timezone.utc):%Y-%m-%d} | `{args.model}` | {p['id']} | {sc['matched']}/{sc['expected']} | {sc['tool_calls']} | "
                    f"{'✓' if sc['used_resolve'] else '–'} | {'✓' if sc['used_analyze'] else '–'} | {'✓' if sc['used_report'] else '–'} | "
                    f"{usage['prompt_tokens']}+{usage['completion_tokens']} | {time.time() - t0:.0f}s |")
        print(rows[-1])
    results = HERE / "RESULTS.md"
    if not results.exists():
        results.write_text("# Eval results\n\n| date | model | prompt | expectations | tool calls | resolve | analyze | report | tokens in+out | wall |\n|---|---|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    with results.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run offline tests**

Run: `cd eval && uv run pytest -q` → Expected: `4 passed`

- [ ] **Step 5: Run the eval for real**

Prerequisite: the user has put `OPENROUTER_API_KEY` into `.env` at the repo root (copy `.env.example`). Confirm `.env` is gitignored (`git check-ignore .env` prints `.env`).

Pick a free tool-capable model: `curl -s https://openrouter.ai/api/v1/models | python3 -c "import sys,json;[print(m['id']) for m in json.load(sys.stdin)['data'] if m['id'].endswith(':free') and 'tools' in m.get('supported_parameters',[])]"` and choose one (e.g. the first Qwen/DeepSeek listed).

Run from `eval/`:
```bash
uv run run_eval.py --model anthropic/claude-haiku-4.5
uv run run_eval.py --model <free-model-id>
```
Read every transcript in `eval/transcripts/`. For each, note in `RESULTS.md` under a "## Observations" heading: did the model follow the workflow, quote confidence, handle the missing Polish article honestly, produce the PDF on prompt 3, reuse the run on the follow-up. If Haiku misuses a flag or skips a rule, fix SKILL.md wording (Task 11 file) and re-run that prompt; record the change in Observations. Stop iterating when all four prompts hit every expectation on Haiku.

- [ ] **Step 6: Commit**

```bash
git add eval .env.example
git commit -m "Add OpenRouter eval harness and Haiku 4.5 transcripts

The task demands proof that a cheap tool-using model can drive the skill;
the harness makes that check reproducible and the transcripts show it."
```
(Raw JSON transcripts are gitignored; the Markdown ones are committed.)

---

### Task 14: README (UA + EN), roadmap, final validation

**Files:**
- Create: `README.md` (repo root)
- Create: `LICENSE` (MIT, repo root; referenced by SKILL.md `license: MIT`)
- Modify: `wikipedia-interest/wiki_interest/api.py` (`REPO_URL` to the real remote once known)

- [ ] **Step 1: Write README.md**

Structure (write full prose, Ukrainian first, English mirror after a `---`):
1. **Що це** — one paragraph: skill for agents, what question it answers, link to the task gist.
2. **Швидкий старт** — install uv, `cd wikipedia-interest`, three commands with the example from `references/examples.md`, where outputs land.
3. **Як користуватись з агентом** — copy the skill dir into the agent's skills folder (Claude Code: `~/.claude/skills/wikipedia-interest`), example prompt, what the agent will do (resolve → analyze → answer → report).
4. **Архітектура** — tree from spec §3 with one line per module; data flow sentence; why one pipeline command (Haiku budget: 1–3 tool calls).
5. **Методологія коротко** — per-million, clipped growth, confidence rule, ranking rule; link to methodology.md.
6. **Як перевірено** — unit tests (`uv run pytest`, count), network tests, `skills-ref validate`, model eval table copied from `eval/RESULTS.md` with links to transcripts; what went wrong on Haiku and which SKILL.md wording fixed it.
7. **Як я перевіряв результати AI-інструментів** — code written with Claude Code under a spec+plan; every module was TDD'd with the failing test first; numbers cross-checked by hand against raw API calls (`curl`) for one series; PDF opened and inspected; transcripts read line by line; thresholds sanity-checked on synthetic series.
8. **Обмеження** — the fixed limitations list.
9. **Roadmap: як розвивати далі** — ordered:
   1. Topic expansion: Wikidata `P31`/`P279` + category members → topic clusters instead of single articles; sum per-million across the cluster.
   2. Discovery mode: `top` endpoints per edition, filter by category, find rising articles the user did not name.
   3. Bulk data: monthly pageview dumps / Wikimedia Enterprise into Parquet + DuckDB so a 50-topic × 20-language matrix is one local query; cache becomes a columnar store.
   4. Per-country views (`top-per-country`) to separate markets from languages.
   5. Change-point detection and simple forecasting (Prophet-free STL + linear extrapolation) with prediction intervals.
   6. Multi-page report and HTML dashboard; scheduled monitoring with breakout alerts.
   7. Evaluation set: labelled past cases (topics that did/didn't become products) to calibrate the confidence thresholds; eval harness extended with rubric grading by a stronger model.
   8. Cost/latency: async fetching, batched Wikidata calls, streaming summaries for large matrices.
10. **Ліцензія** — MIT.

- [ ] **Step 2: Write LICENSE** — standard MIT text, year 2026, holder = the user's name.

- [ ] **Step 3: Set REPO_URL** — after the user creates the GitHub remote, replace the `REPO_URL` constant in `wikipedia-interest/wiki_interest/api.py` and the `HTTP-Referer` in `eval/run_eval.py`; run `uv run pytest -q` again.

- [ ] **Step 4: Final validation**

Run from `wikipedia-interest/`:
```bash
uv run pytest -q
uv run pytest -m network -q
uvx skills-ref validate .
git status --short   # must show no untracked runtime files (.cache, runs, .env)
```
Expected: all green; `git status` clean apart from intended files.

- [ ] **Step 5: Commit**

```bash
git add README.md LICENSE wikipedia-interest/wiki_interest/api.py eval/run_eval.py
git commit -m "Document the skill: quickstart, verification story and roadmap

Reviewers need to see how the skill was tested on a cheap model, how
AI-generated code was checked, and how the skill grows toward larger
research; the README carries that in Ukrainian and English."
```
