# English language, English grammar — pl,cs,uk,de,es — 2024-09..2026-08 (24 monthly)
Resolved English language: pl → «Język angielski» · cs → «Angličtina» · uk → «Англійська мова» · de → «Englische Sprache» · es → «Idioma inglés»
Resolved English grammar: pl → «Gramatyka języka angielskiego» · cs → «Anglická gramatika» · uk → «Граматика англійської мови» · de → «Englische Grammatik» · es → «Gramática del inglés»

| topic | lang | pm latest | pm year ago | YoY % | growth/yr % (clipped) | spikes % | coverage % | confidence |
|---|---|---|---|---|---|---|---|---|
| English language | pl | 43.55 | 43.5 | -9.81 | -9.9 | 0 | 100 | high |
| English language | cs | 46.3 | 45.92 | -10.89 | -11.67 | 0 | 100 | high |
| English language | uk | 107.21 | 116.7 | -13.88 | -15.57 | 0 | 100 | high |
| English language | de | 32.09 | 33.27 | -0.81 | -0.66 | 0 | 100 | low |
| English language | es | 45.92 | 46.56 | -9.85 | -10.53 | 0 | 100 | high |
| English grammar | pl | 1.03 | 1.52 | -13.24 | -10.27 | 14.53 | 100 | medium |
| English grammar | cs | 1.29 | 2.25 | -66.18 | -55.57 | 0 | 100 | high |
| English grammar | uk | 1.22 | 0.83 | -53.71 | -33.24 | 0 | 100 | high |
| English grammar | de | 0.69 | 0.81 | -26.56 | -14.41 | 0 | 100 | high |
| English grammar | es | 0.88 | 1.76 | -52.55 | -39.68 | 0 | 100 | high |

## Ranking (by score; score = clipped growth × confidence weight high 1.0 / medium 0.6 / low 0.25)
1. English language|de (-0.17); 2. English grammar|pl (-6.16); 3. English language|pl (-9.9); 4. English language|es (-10.53); 5. English language|cs (-11.67); 6. English grammar|de (-14.41); 7. English language|uk (-15.57); 8. English grammar|uk (-33.24); 9. English grammar|es (-39.68); 10. English grammar|cs (-55.57)
## Checks
- English language: resolved to Q1860 «English»; other candidates: Q328 «English Wikipedia» (English-language edition of Wikipedia); Q27968 «English studies» (discipline that studies the English language and literature); Q186579 «English-language literature» (literary works written in the English language). Use --qid to switch.
- English grammar: resolved to Q560583 «English grammar»; other candidates: Q139929339 «English Grammar» (); Q87475758 «English Grammar» (book on English grammar by Muhibbek Rustamov and Margarita Asiryans); Q136883633 «English Grammar» (book by Chestine Gowdy). Use --qid to switch.
- window 2024-09..2026-08 (24 monthly periods); current month excluded
- cache: 19 hits, 0 misses
- English grammar|cs: strongly seasonal (amplitude 1.59× the mean) — compare the same months across years, not adjacent months; 'pm latest' vs 'pm year ago' already does that
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article existence and quality; a missing or poor article hides real interest.
- Bot filtering is imperfect; spikes can be automated traffic or news events.
- A language edition is not a country: readers of one language live in many markets.
- English grammar|pl: spikes in 2025-07, 2025-09 carry 14.53% of views.
## Suggested follow-ups
- `uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl --granularity daily --start 2025-07 --end 2025-07 --out ../examples/03-english-multi-daily-2025-07   # inspect the 2025-07 spike day by day`
- `uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl,cs,uk,de,es --months 48 --out ../examples/03-english-multi-48m   # longer history`
- `uv run scripts/wiki_interest.py report --run ../examples/03-english-multi --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF`
Files: ../examples/03-english-multi/result.json, data.csv, chart.png
