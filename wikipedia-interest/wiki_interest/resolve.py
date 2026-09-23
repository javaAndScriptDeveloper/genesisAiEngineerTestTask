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
        return [lang for lang, r in self.per_lang.items() if r.status == "found"]


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
    return [lang for lang in order if not (lang in seen or seen.add(lang))]


def resolve_topic(client: WikiClient, topic: str, langs: list[str], hint: str | None = None,
                  qid: str | None = None, overrides: dict[str, str] | None = None) -> TopicResolution:
    overrides = overrides or {}
    per_lang: dict[str, LangResolution] = {}
    label: str | None = None
    alternatives: list[dict] = []
    entity: dict = {}

    need_wikidata = [lang for lang in langs if lang not in overrides]
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
            if title:
                per_lang[lang] = LangResolution(lang, "found", title, "user-supplied title")
            else:
                per_lang[lang] = LangResolution(lang, "missing", None,
                                                f"user-supplied title '{overrides[lang]}' does not exist")
            continue
        sitelink = entity.get("sitelinks", {}).get(f"{lang}wiki") if entity else None
        if sitelink:
            per_lang[lang] = LangResolution(lang, "found", sitelink["title"], f"Wikidata sitelink of {qid}")
            continue
        query = (_label(entity, [lang]) or topic) if entity else topic
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
        wanted = {f"{lang}wiki" for lang in langs}
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
    for lang in langs:
        if lang in labels:
            return labels[lang]["value"]
    return None
