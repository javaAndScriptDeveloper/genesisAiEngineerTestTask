# Transcript — 1-if-pl-cs
usage: {'prompt_tokens': 96419, 'completion_tokens': 1749}
score: {'matched': 3, 'expected': 3, 'tool_calls': 3, 'used_resolve': True, 'used_analyze': True, 'used_report': False, 'final_chars': 1332}

## user
Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia за останні два роки.

## assistant
I'll analyze Wikipedia pageview trends for intermittent fasting in Polish and Czech editions over the last two years.

## assistant → Skill
```
{"skill": "wikipedia-interest", "args": "intermittent fasting, Polish (pl), Czech (cs), 2 years"}
```

## tool result
```
Launching skill: wikipedia-interest
```

## assistant
I'll compare intermittent fasting interest in Polish and Czech Wikipedia. Starting by resolving the article titles.

## assistant → bash
```
cd /home/vampir/petProjects/genesisAiEngineerCourse/wikipedia-interest && uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
```

## tool result
```
topic: intermittent fasting  →  Q1666254 «intermittent fasting»
| lang | status | title | note |
|---|---|---|---|
| pl | missing |  | no plwiki article linked to Q1666254; searched pl.wikipedia for 'intermittent fasting' candidates: Stres oksydacyjny, Głodówka lecznicza, Paleolityczny styl życia |
| cs | found | Přerušovaný půst | Wikidata sitelink of Q1666254 |
other Wikidata candidates: Q112575736 «Intermittent Fasting Can Make Us Healthier» (Article published in Scientific European on 15 January 2019); Q63574657 «Intermittent Fasting Versus Daily Caloric Restriction for Weight Loss» (clinical trial); Q79110871 «Intermittent Fasting as a Means to Lose Fluid Overload and Weight in Complicated Obesity» (clinical trial)
(use --qid to pick one)
```

## assistant
Now analyzing the data. Czech has the article "Přerušovaný půst" but Polish doesn't have a dedicated article on intermittent fasting.

## assistant → bash
```
uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs cs --months 24 --out runs/intermittent-fasting-cs
```

## tool result
```
# intermittent fasting — cs — 2024-09..2026-08 (24 monthly)
Resolved (Q1666254) intermittent fasting: cs → «Přerušovaný půst»

| topic | lang | pm latest (3-mo avg) | pm year ago (3-mo avg) | YoY % (12m vs prior 12m) | growth/yr % (clipped) | spikes % | coverage % of window | confidence |
|---|---|---|---|---|---|---|---|---|
| intermittent fasting | cs | 2.06 | 4.5 | -47.69 | -45.32 | 0 | 100 | high |

## Ranking (by volume: pm latest, i.e. current attention share)
1. intermittent fasting|cs (2.06)
## Checks
- intermittent fasting: resolved to Q1666254 «intermittent fasting»; other candidates: Q112575736 «Intermittent Fasting Can Make Us Healthier» (Article published in Scientific European on 15 January 2019); Q63574657 «Intermittent Fasting Versus Daily Caloric Restriction for Weight Loss» (clinical trial); Q79110871 «Intermittent Fasting as a Means to Lose Fluid Overload and Weight in Complicated Obesity» (clinical trial). Use --qid to switch.
- every row is declining → ranked by volume (current attention share) instead of score; a score ranking would only order declines and favour low-confidence ones. Use --rank-by growth to see which declines slowest.
- window 2024-09..2026-08 (24 monthly periods); current month excluded
- cache: 4 hits, 0 misses
- intermittent fasting|cs: strongly seasonal (amplitude 1.41× the mean) — compare the same months across years, not adjacent months; 'pm latest' vs 'pm year ago' already does that
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article existence and quality; a missing or poor article hides real interest.
- Bot filtering is imperfect; spikes can be automated traffic or news events.
- A language edition is not a country: readers of one language live in many markets.
## Suggested follow-ups
- `uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs cs --months 48 --out runs/intermittent-fasting-cs-48m   # longer history`
- `uv run scripts/wiki_interest.py report --run runs/intermittent-fasting-cs --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF`
Files: runs/intermittent-fasting-cs/result.json, data.csv, chart.png
```

## assistant
## Результати порівняння

**Вивід: Порівняти безпосередньо неможливо.**

- **Польська Wikipedia (pl)**: Немає окремої статті про інтервальне голодування. Система знайшла пов'язані теми (наприклад, "Głodówka lecznicza" — терапевтичне голодування), але не точний топік.

- **Чеська Wikipedia (cs)**: Статтю знайдено — "Přerušovaný půst"

### Дані по Чеській Wikipedia за останні 2 роки (вересень 2024 — серпень 2026):

| Метрика | Значення |
|---|---|
| **Останні 3 місяці** (на мільйон переглядів) | 2.06 |
| **3 місяці рік тому** | 4.5 |
| **Річне падіння (YoY)** | **−47.69%** |
| **Темп падіння (клипований)** | −45.32% на рік |
| **Впевненість** | Висока |

### Ключові висновки:

1. **Інтерес в Чехії демонструє стійке падіння** — майже половину за рік. Це не новинна коливання, а реальний тренд (0% спайків).

2. **Сезонність**: Статтю читають неоднаково протягом року — коливання близько 1.41× від середнього. Це означає, що певні місяці мають значно більше переглядів.

3. **Польська мова**: Без статті на польській Wikipedia не можна порівнювати. Якщо хочете дослідити інтерес у польськомовній аудиторії, потрібно шукати альтернативні статті (як "лікувальне голодування") або перевірити, чи розглядалась стаття до видалення.

Чеські дані дають сигнал: інтерес до інтервального голодування там **скорочується**, а не зростає.
