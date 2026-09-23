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
