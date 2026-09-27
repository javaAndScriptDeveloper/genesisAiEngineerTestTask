# Transcript — 3-english-multi
usage: {'prompt_tokens': 16724, 'completion_tokens': 2445}
score: {'matched': 2, 'expected': 3, 'tool_calls': 4, 'used_resolve': True, 'used_analyze': True, 'used_report': True, 'final_chars': 3473}

## system
(SKILL.md as system prompt — omitted)

## user
Ми створюємо застосунок для вивчення мов. Порівняй інтерес до вивчення англійської у польському, чеському, українському та німецькому розділах Wikipedia та підготуй короткий PDF-звіт: які аудиторії варто дослідити наступними й чому?

## assistant → bash
```
ls -la
```

## tool result
```
total 244
drwxrwxr-x 11 vampir vampir   4096 Sep 26 00:43 .
drwxrwxr-x  8 vampir vampir   4096 Sep 26 00:15 ..
drwxrwxr-x  2 vampir vampir   4096 Sep 23 19:44 assets
drwxrwxr-x  2 vampir vampir   4096 Sep 26 00:39 .cache
-rw-rw-r--  1 vampir vampir    524 Sep 23 19:32 pyproject.toml
drwxrwxr-x  3 vampir vampir   4096 Sep 23 19:32 .pytest_cache
-rw-rw-r--  1 vampir vampir      5 Sep 23 19:32 .python-version
drwxrwxr-x  2 vampir vampir   4096 Sep 23 19:44 references
drwxrwxr-x  3 vampir vampir   4096 Sep 26 00:43 runs
drwxrwxr-x  3 vampir vampir   4096 Sep 23 19:41 scripts
-rw-rw-r--  1 vampir vampir   6645 Sep 26 00:41 SKILL.md
drwxrwxr-x  4 vampir vampir   4096 Sep 23 19:47 tests
-rw-rw-r--  1 vampir vampir 184922 Sep 23 19:32 uv.lock
drwxrwxr-x  5 vampir vampir   4096 Sep 23 19:32 .venv
drwxrwxr-x  3 vampir vampir   4096 Sep 26 00:14 wiki_interest
```

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
| English language | pl | 43.55 | 43.5 | -9.81 | -9.9 | 0 | 100 | high |
| English language | cs | 46.3 | 45.92 | -10.89 | -11.67 | 0 | 100 | high |
| English language | uk | 107.21 | 116.7 | -13.88 | -15.57 | 0 | 100 | high |
| English language | de | 32.09 | 33.27 | -0.81 | -0.66 | 0 | 100 | low |

## Ranking (by score; score = clipped growth × confidence weight high 1.0 / medium 0.6 / low 0.25)
1. English language|de (-0.17); 2. English language|pl (-9.9); 3. English language|cs (-11.67); 4. English language|uk (-15.57)
## Checks
- English language: resolved to Q1860 «English»; other candidates: Q328 «English Wikipedia» (English-language edition of Wikipedia); Q27968 «English studies» (discipline that studies the English language and literature); Q186579 «English-language literature» (literary works written in the English language). Use --qid to switch.
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
uv run scripts/wiki_interest.py report --run runs/english-comparison --title "Interest in learning English across Wikipedia language editions" --notes "German Wikipedia shows the smallest decline in interest for learning English, suggesting a relatively stable but low‑engagement audience; Polish and Czech audiences also show moderate declines but higher engagement; Ukrainian audience has the highest raw interest but a steep drop, warranting further study to understand causes. Overall, German and Polish readers may be the most promising for future language‑learning product features, while Ukrainian audience merits deeper research into the decline." --lang en
```

## tool result
```
wrote runs/english-comparison/report.pdf
```

## assistant
**Резюме з аналізу Wikipedia (24‑місячний період 2024‑09 → 2026‑08)**

| Мова | Стаття | Середня кількість переглядів на 1 млн переглядів (ostatні 3 місяці) | Середня кількість переглядів на 1 млн (рік тому) | YoY % (12 міс. проти попередніх 12 міс.) | clipped growth/рік % | confidence |
|------|--------|-----------------------------------|-----------------------------------|-----------------------------------|-------------------|------------|
| Польська (pl) | **Język angielski** | **43.55** | 43.5 | **‑9.81 %** | **‑9.9 %** | **high** |
| Чеська (cs) | **Angličtina** | **46.30** | 45.92 | **‑10.89 %** | **‑11.67 %** | **high** |
| Українська (uk) | **Англійська мова** | **107.21** | 116.7 | **‑13.88 %** | **‑15.57 %** | **high** |
| Німецька (de) | **Englische Sprache** | **32.09** | 33.27 | **‑0.81 %** | **‑0.66 %** | **low** |

*Всі мови мають статті,Coverage = 100 % (стаття існувала у вікно спостереження).*

### Як читати таблицю
* **pm latest** — середня кількість переглядів на 1 млн переглядів за останні 3 місяці.  
* **pm year ago** — той самий показник за тримісячний період один рік раніше.  
* **YoY %** — зміна за останні 12 місяців порівняно з попередніми 12 місяцями.  
* **clipped growth/рік** — тренд після виключення піків (spikes % = 0 у всіх випадках, тому зростання/спадання чисте).  
* **confidence** — оцінка довіри до числа: *high* — стабільні дані, *low* — менше обсягів/факторів, що підвищують невизначеність.

### Ранжування за оцінкою (score = clipped growth × вага confidence)
1. **Німецька** – score ≈ ‑0.17 (найменший відносний падінь, але довіра **low** через менший обсяг).  
2. **Польська** – score ≈ ‑9.9 (high confidence).  
3. **Чеська** – score ≈ ‑11.67 (high confidence).  
4. **Українська** – score ≈ ‑15.57 (high confidence, але найбільший відносний спадання).

### Що це означає для вашого продукту мовного навчання

* **Німецька аудиторія** – найменший відносний падінь інтересу, але поточний обсяг переглядів (32 на 1 млн) є найнижчим з чотирьох. Це може свідчити про стабільний, але малоактивний сегмент, який варто тестувати через специфічні мовні ресурси або додатки, спрямовані на підтримку інтересу.
* **Польська та чеська аудиторії** – мають подібні рівні інтересу (близько 44‑46 на 1 млн) і показують поміркований спадання (≈ ‑10 %). Довіра до цифр **high**, тому ці аудиторії можна вважаєти надійними для планування функцій або контенту.
* **Українська аудиторія** – найвищий обсяг переглядів (107 на 1 млн), але саме найбільше відносне падіння (‑15.57 %). Варто глибше розібратися, чому впадає інтерес (можливо, політичні,seasonal або зміни в доступі до контенту). Це може бути можливість для інтервенції (наприклад, спеціальні матеріали або кампанії), щоб зупинити падіння.

### Рекомендації (короткий PDF‑звіт)

> **Німецька аудиторія** має найменший відносний спадання інтересу до вивчення англійської, хоча поточний рівень переглядів нижчий за інші мови. **Польська та чеська аудиторії** показують стабільний, але поміркований падінь з високою довірою до даних — це найпередбачуваніші сегменти для додаткових функцій або контенту. **Українська аудиторія** має найбільший поточний інтерес, але інтенсивність падіння вимагає глибокого аналізу причин; це можливий цільний ринок для спеціальних інтервенцій або кампаній по підтримці інтересу.

PDF‑звіт створено у `runs/english-comparison/report.pdf` і містить вищеперелічені висновки, графіки трендів та рекомендації для подальшого дослідження аудиторій.
