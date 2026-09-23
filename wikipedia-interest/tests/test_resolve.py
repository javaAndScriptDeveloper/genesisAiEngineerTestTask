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
