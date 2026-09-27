# Transcript — 3-english-multi
usage: {'prompt_tokens': 12745, 'completion_tokens': 2032}
score: {'matched': 3, 'expected': 3, 'tool_calls': 3, 'used_resolve': True, 'used_analyze': True, 'used_report': True, 'final_chars': 2749}

## system
(SKILL.md as system prompt — omitted)

## user
Ми створюємо застосунок для вивчення мов. Порівняй інтерес до вивчення англійської у польському, чеському, українському та німецькому розділах Wikipedia та підготуй короткий PDF-звіт: які аудиторії варто дослідити наступними й чому?

## assistant → bash
```
uv run scripts/wiki_interest.py resolve --topic "English language" --langs pl,cs,uk,de
```

## tool result
```
topic: English language  →  Q1860 «English»
| lang | status | title | note |
|---|---|---|---|
| pl | found | Język angielski | Wikidata sitelink of Q1860 |
| cs | found | Angličtina | Wikidata sitelink of Q1860 |
| uk | found | Англійська мова | Wikidata sitelink of Q1860 |
| de | found | Englische Sprache | Wikidata sitelink of Q1860 |
other Wikidata candidates: Q328 «English Wikipedia» (English-language edition of Wikipedia); Q27968 «English studies» (discipline that studies the English language and literature); Q186579 «English-language literature» (literary works written in the English language)
(use --qid to pick one)
```

## assistant → bash
```
uv run scripts/wiki_interest.py analyze --topic "English language" --langs pl,cs,uk,de --months 24 --out runs/english-comparison
```

## tool result
```
# English language — pl,cs,uk,de — 2024-09..2026-08 (24 monthly)
Resolved (Q1860) English language: pl → «Język angielski» · cs → «Angličtina» · uk → «Англійська мова» · de → «Englische Sprache»

| topic | lang | pm latest (3-mo avg) | pm year ago (3-mo avg) | YoY % (12m vs prior 12m) | growth/yr % (clipped) | spikes % | coverage % of window | confidence |
|---|---|---|---|---|---|---|---|---|
| English language | pl | 43.55 | 43.5 | -9.81 | -10.02 | 0 | 100 | high |
| English language | cs | 46.3 | 45.92 | -10.89 | -11.78 | 0 | 100 | high |
| English language | uk | 107.21 | 116.7 | -13.88 | -15.54 | 0 | 100 | high |
| English language | de | 32.09 | 33.27 | -0.81 | -0.67 | 0 | 100 | low |
Reasons English language|de (low): trend not monotonic (p=1.0)

## Ranking (by volume: pm latest, i.e. current attention share)
1. English language|uk (107.21); 2. English language|cs (46.3); 3. English language|pl (43.55); 4. English language|de (32.09)
## Checks
- English language: resolved to Q1860 «English»; other candidates: Q328 «English Wikipedia» (English-language edition of Wikipedia); Q27968 «English studies» (discipline that studies the English language and literature); Q186579 «English-language literature» (literary works written in the English language). Use --qid to switch.
- every row is declining → ranked by volume (current attention share) instead of score; a score ranking would only order declines and favour low-confidence ones. Use --rank-by growth to see which declines slowest.
- window 2024-09..2026-08 (24 monthly periods); current month excluded
- cache: 10 hits, 0 misses
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article existence and quality; a missing or poor article hides real interest.
- Bot filtering is imperfect; spikes can be automated traffic or news events.
- A language edition is not a country: readers of one language live in many markets.
## Suggested follow-ups
- `uv run scripts/wiki_interest.py analyze --topic "English language" --langs pl,cs,uk,de --months 48 --out runs/english-comparison-48m   # longer history`
- `uv run scripts/wiki_interest.py report --run runs/english-comparison --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF`
Files: runs/english-comparison/result.json, data.csv, chart.png
```

## assistant → bash
```
uv run scripts/wiki_interest.py report --run runs/english-comparison --title "Interest in learning English across Wikipedia language editions" --notes "Analysis of per‑million pageviews for the article 'English language' in Polish, Czech, Ukrainian and German Wikipedia over the last 24 months (2024‑09 → 2026‑08). All four language editions show a decline in interest, with Ukrainian Wikipedia having the highest current volume (107 views per million) but the steepest year‑over‑year drop (‑13.9%). Czech and Polish have moderate volume and high confidence in the trend, while German has the lowest volume and low confidence due to a non‑monotonic trend. For a B2C language‑learning app, the Czech and Polish audiences represent the most reliable current demand, while Ukrainian interest, though declining, remains substantial and could be worth targeted content or A/B testing. German Wikipedia readers show relatively low and unstable interest, suggesting it may be a lower priority for initial launch." --lang uk
```

## tool result
```
wrote runs/english-comparison/report.pdf
```

## assistant
**Порівняння інтересу до вивчення англійської (стаття «English language») у розділах Wikipedia**

| Мова Wikipedia | Середня кількість переглядів на мільйон переглядів (ostatні 3 місяці) | Середня кількість переглядів на мільйон (рік тому) | YoY % (12 міс. проти попередніх 12 міс.) | Річний приріст (скліплений) | self-assurance |
|----------------|----------------------------------------|----------------------------------------|---------------------------------|--------------------------|----------------|
| **Українська** (uk) | **107,21** | 116,70 | **‑13,88 %** | **‑15,54 %** | **Висока** |
| **Чеська** (cs) | 46,30 | 45,92 | ‑10,89 % | ‑11,78 % | Висока |
| **Польська** (pl) | 43,55 | 43,50 | ‑9,81 % | ‑10,02 % | Висока |
| **Німецька** (de) | 32,09 | 33,27 | ‑0,81 % | ‑0,67 % | Низька (тривога: тренд не monotonic, p = 1,0) |

**Ключові висновки**

1. **Всі чотири редакції показують спадання інтересу** за останні 24 місяці (2024‑09 → 2026‑08).  
2. **Ранг за поточною увагою (обсягом):** українська > чеська > польська > німецька.  
3. **Впевненість даних:** для української, чеської та польської confianza височа, а для німецької — низька, оскільки показник тривожний (не monotonicний тренд).  
4. **Показник покрыття (coverage %) = 100 % для всіх мов**, що означає, що стаття існувала у вікно спостереження для всіх місяців.

**Які аудиторії варто дослідити наступними й чому?**

- **Чеська та польська аудиторії** — найпередовильні з точки зору довіри до даних. Інтерес до англійської там значно вищий, ніж у німецькій редакції, і тренд, хоча спадаючий, є стабільним. Це найбільш надійні ринки для першого тестування функцій мовного навчання або контенту.
- **Українська аудиторія** має найбільший поточний обсяг переглядів, але показує найбільший рік‑від‑рік падіння (‑13,9 %). Варто розглянути цю аудиторію для **цільованого контенту або A/B тестів**, оскільки базовий інтерес все ще високий, але потребує моніторингу змін.
- **Німецька аудиторія** має найнижчий обсяг переглядів і низьку довіру до тренду. На цьому етапі можна вважати німецьку редакцію **нижчею пріоритетом**, доки не з'явиться додаткових доказах зростання або специфічного попиту.

**PDF‑звіт**

Короткий односторінковий звіт згенерирован і збережено за шляхом `runs/english-comparison/report.pdf`. У звіті міститься детальна таблиця, графіки динаміки та рекомендації у 3‑5 реченнях (див. вище).

**Дії далі**

- Можна розширити період спостереження (`--months 48`), щоб перевірити, чи є падіння тимчасовим флуктуацією.  
- Додаткові мови або конкретні статті (наприклад, «English grammar») можна проаналізувати тим самим способом.  
- Результати звіту можна використовувати як основу для планування локалізованих версій застосунку та маркетингових кампаній.
