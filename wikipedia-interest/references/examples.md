# Worked examples

## 1. "Compare growth of interest in intermittent fasting in Polish and Czech Wikipedia over two years"
```bash
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
# pl → missing (no plwiki article linked to Q1666254; search candidates listed), cs → «Přerušovaný půst»
uv run scripts/wiki_interest.py analyze --topic "intermittent fasting" --langs pl,cs --months 24 --out runs/if-pl-cs
```
Answer shape: "Czech: X per million now vs Y a year ago, clipped growth Z %/yr, confidence …
because …; Polish Wikipedia has no article on the topic, so there is no signal — that is not
evidence of no interest. If the user confirms one of the search candidates is the same topic,
re-run with `--titles pl=<that title>`." If growth is negative, say interest is declining.

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
