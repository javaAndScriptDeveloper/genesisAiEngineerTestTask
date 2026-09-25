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
REPO_URL = "https://github.com/javaAndScriptDeveloper/genesisAiEngineerTestTask"
RETRY_STATUSES = {429, 500, 502, 503, 504}
ACCESS_VALUES = ("all-access", "desktop", "mobile-web", "mobile-app")
AGENT_VALUES = ("user", "all-agents", "spider", "automated")


def validate_access_agent(access: str, agent: str) -> None:
    if access not in ACCESS_VALUES:
        raise ValueError(f"--access must be one of {', '.join(ACCESS_VALUES)}, got {access!r}")
    if agent not in AGENT_VALUES:
        raise ValueError(f"--agent must be one of {', '.join(AGENT_VALUES)}, got {agent!r}")


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
    def get_json(self, url: str, ttl_seconds: int | None, fresh: bool = False) -> dict:
        if self.cache is not None and not fresh:
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
            try:
                data = resp.json()
            except ValueError as exc:
                raise ApiError(f"non-JSON response from {url}: {resp.text[:120]!r}") from exc
            if self.cache is not None:
                self.cache.put(url, resp.text, ttl_seconds)
            return data
        raise ApiError(f"Giving up after {self.max_retries + 1} attempts: {last_error}")

    # ---- pageviews -------------------------------------------------------
    def per_article_url(self, project: str, title: str, granularity: str, start: str, end: str,
                        access: str = "all-access", agent: str = "user") -> str:
        return f"{PAGEVIEWS_BASE}/per-article/{project}/{access}/{agent}/{encode_title(title)}/{granularity}/{start}/{end}"

    def per_article(self, project: str, title: str, granularity: str, start: str, end: str, permanent: bool,
                    access: str = "all-access", agent: str = "user", fresh: bool = False) -> list[dict]:
        url = self.per_article_url(project, title, granularity, start, end, access, agent)
        return self.get_json(url, PERMANENT if permanent else DEFAULT_TTL_SECONDS, fresh=fresh).get("items", [])

    def aggregate_url(self, project: str, granularity: str, start: str, end: str,
                      access: str = "all-access", agent: str = "user") -> str:
        return f"{PAGEVIEWS_BASE}/aggregate/{project}/{access}/{agent}/{granularity}/{start}/{end}"

    def aggregate(self, project: str, granularity: str, start: str, end: str, permanent: bool,
                  access: str = "all-access", agent: str = "user") -> list[dict]:
        url = self.aggregate_url(project, granularity, start, end, access, agent)
        return self.get_json(url, PERMANENT if permanent else DEFAULT_TTL_SECONDS).get("items", [])

    def forget(self, url: str) -> None:
        """Drop a cached response (used when a 'closed' window came back incomplete)."""
        if self.cache is not None:
            self.cache.delete(url)

    def top_articles(self, project: str, year: int, month: int, access: str = "all-access") -> list[dict]:
        """Top-1000 articles of a month: [{article, views, rank}]. Closed months are permanent."""
        url = f"{PAGEVIEWS_BASE}/top/{project}/{access}/{year:04d}/{month:02d}/all-days"
        items = self.get_json(url, PERMANENT).get("items", [])
        return items[0].get("articles", []) if items else []

    def namespaces(self, lang: str) -> list[str]:
        """Localized namespace prefixes (e.g. 'Спеціальна', 'Категорія') so top lists can be filtered to articles."""
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urlencode({
            "action": "query", "meta": "siteinfo", "siprop": "namespaces|namespacealiases", "format": "json"})
        q = self.get_json(url, DEFAULT_TTL_SECONDS).get("query", {})
        names: set[str] = {"Wikipedia", "Special", "Category", "Talk", "User", "File", "Template", "Help", "Portal", "Draft"}
        for k, v in q.get("namespaces", {}).items():
            if str(k) == "0":
                continue
            for field in ("*", "canonical"):
                if v.get(field):
                    names.add(v[field])
        for a in q.get("namespacealiases", []) or []:
            if a.get("*"):
                names.add(a["*"])
        return sorted(names)

    # ---- wikidata --------------------------------------------------------
    def wd_search(self, text: str, language: str, limit: int = 5) -> list[dict]:
        url = WIKIDATA_API + "?" + urlencode({
            "action": "wbsearchentities", "search": text, "language": language,
            "uselang": language, "type": "item", "limit": limit, "format": "json",
        })
        data = self.get_json(url, DEFAULT_TTL_SECONDS)
        return [{"id": s["id"], "label": s.get("label", ""), "description": s.get("description", "")}
                for s in data.get("search", [])]

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
