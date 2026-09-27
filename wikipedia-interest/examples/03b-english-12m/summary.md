# English language — pl,cs,uk,de,es — 2025-09..2026-08 (12 monthly)
Resolved (Q1860) English language: pl → «Język angielski» · cs → «Angličtina» · uk → «Англійська мова» · de → «Englische Sprache» · es → «Idioma inglés»

| topic | lang | pm latest (3-mo avg) | pm year ago (3-mo avg) | YoY % (12m vs prior 12m) | growth/yr % (clipped) | spikes % | coverage % of window | confidence |
|---|---|---|---|---|---|---|---|---|
| English language | pl | 43.55 | – | – | -2.65 | 0 | 100 | low |
| English language | cs | 46.3 | – | – | -2.14 | 0 | 100 | low |
| English language | uk | 107.21 | – | – | -15.67 | 0 | 100 | medium |
| English language | de | 32.09 | – | – | -6.39 | 0 | 100 | low |
| English language | es | 45.92 | – | – | -7.04 | 0 | 100 | low |
Reasons English language|pl (low): trend not monotonic (p=0.65); only 12 months (< 24): no year-over-year check
Reasons English language|cs (low): trend not monotonic (p=0.95); only 12 months (< 24): no year-over-year check
Reasons English language|uk (medium): weak monotonic trend (p=0.06); only 12 months (< 24): no year-over-year check
Reasons English language|de (low): trend not monotonic (p=0.48); only 12 months (< 24): no year-over-year check
Reasons English language|es (low): trend not monotonic (p=0.55); only 12 months (< 24): no year-over-year check

## Ranking (by volume: pm latest, i.e. current attention share)
1. English language|uk (107.21); 2. English language|cs (46.3); 3. English language|es (45.92); 4. English language|pl (43.55); 5. English language|de (32.09)
## Checks
- English language: resolved to Q1860 «English»; other candidates: Q328 «English Wikipedia» (English-language edition of Wikipedia); Q27968 «English studies» (discipline that studies the English language and literature); Q186579 «English-language literature» (literary works written in the English language). Use --qid to switch.
- every row is declining → ranked by volume (current attention share) instead of score; a score ranking would only order declines and favour low-confidence ones. Use --rank-by growth to see which declines slowest.
- window 2025-09..2026-08 (12 monthly periods); current month excluded
- cache: 12 hits, 0 misses
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article existence and quality; a missing or poor article hides real interest.
- Bot filtering is imperfect; spikes can be automated traffic or news events.
- A language edition is not a country: readers of one language live in many markets.
## Suggested follow-ups
- `uv run scripts/wiki_interest.py analyze --topic "English language" --langs pl,cs,uk,de,es --months 48 --out ../examples/03b-english-12m-48m   # longer history`
- `uv run scripts/wiki_interest.py report --run ../examples/03b-english-12m --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF`
Files: ../examples/03b-english-12m/result.json, data.csv, chart.png
