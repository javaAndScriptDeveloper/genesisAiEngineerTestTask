---
name: wikipedia-interest
description: Analyze Wikipedia pageview trends to compare audience interest in topics across language editions, rate how trustworthy the growth is, plot charts and build a one-page PDF report. Use when a user asks which topics or languages/markets to invest in, whether interest in a subject is growing, or wants Wikipedia/Wikimedia pageview statistics compared between languages.
license: MIT
compatibility: Requires Python 3.12+, uv, and internet access to wikimedia.org and wikidata.org
metadata:
  author: vampir
  version: "0.1.0"
---

# Wikipedia Interest

Compare how much readers of different Wikipedia language editions care about a topic, whether that
interest is growing, and how much to trust the growth. Built for B2C founders choosing which topics
to develop and which languages/markets to launch next.

## Use it when
- "Is interest in X growing in <language> Wikipedia?" / "Can we trust that growth?"
- "Compare X across pl/cs/uk…" / "Which of these languages/topics should we explore next?"
- The user wants a chart or a one-page PDF to share.

## Not for
Revenue or willingness to pay, search-engine demand, article edits, anything before 2015-07,
country-level data (a language edition is not a country).

## Setup (once per machine)
Run every command from this skill's directory. `uv` installs pinned dependencies on first run.

```bash
uv run scripts/wiki_interest.py --help
```

## Workflow
1. **Resolve titles first when the topic is ambiguous, non-English, or the user named specific articles.**
   `resolve` is cheap (Wikidata only). Show the user the table if any language is `missing` or if
   "other Wikidata candidates" appear, and confirm before analyzing.
   ```bash
   uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
   ```
2. **Analyze.** One call fetches, normalizes and scores everything, prints a ≤40-line summary and
   writes `result.json`, `data.csv`, `chart.png` under `--out`.
   ```bash
   uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 24 --out runs/astro-uk
   uv run scripts/wiki_interest.py analyze --topics "English language;English grammar" --langs pl,cs,uk,de --out runs/eng
   ```
   Useful flags: `--months N` (default 24 full months) or `--start YYYY-MM --end YYYY-MM`;
   `--titles pl=Post_przerywany` to force a title; `--qid Q…` to pick a Wikidata item;
   `--granularity daily` for short windows; `--rank-by score|growth|volume`.
3. **Read the summary before answering.** In this order: `Resolved` line (which languages actually
   have data), the `confidence` column, `## Checks`, `## Limitations`, then the numbers.
   Column meanings: `pm latest` = mean views per million over the last 3 months of the window;
   `pm year ago` = the same 3 months one year earlier; `YoY %` = last 12 months vs the 12 before;
   `coverage %` = share of months *in the window* with any views (not since 2015).
4. **Answer** with: per-million values (not raw views) for each language, clipped growth per year,
   YoY %, the confidence level with its reasons, and the limitations that apply. Quote the ranking
   rule when you rank. Mention missing languages explicitly.
5. **Report** whenever the user mentions a PDF, a report, a one-pager or something to share
   (звіт, PDF, поділитися) — and only then. Write 3–6 sentences of recommendation
   yourself (template: [assets/report_notes_template.md](assets/report_notes_template.md)) and pass
   them via `--notes`; `--lang uk` switches labels to Ukrainian.
   ```bash
   uv run scripts/wiki_interest.py report --run runs/astro-uk --title "Astronomy in Ukrainian Wikipedia" --notes "..." --lang uk
   ```

## Interpretation rules (do not skip)
- Compare languages by **views per million project views**; raw views favour big editions.
- **Missing article ≠ no interest.** Say the article does not exist and stop there. Never guess or
  invent a title; use `--titles` only when the user confirmed one, written as plain text
  (`--titles pl=Post_przerywany`), never URL-encoded.
- **One `resolve` (if needed) + one `analyze` is the whole job.** Do not re-run `analyze` with
  variations to "fix" a missing language; report what the summary says.
- Headline growth is the **clipped** figure (spikes removed). If `spikes %` is high, say growth is
  news-driven; offer the daily follow-up command printed in the summary.
- Never state a growth number without its **confidence** (high / medium / low) and at least one
  reason from `result.json` → `metrics.<key>.reasons`.
- `coverage %` < 100 means the article did not exist for part of the window; growth is inflated.
- Negative growth is a real finding: say interest is declining, do not soften it.
- The current month is excluded; data starts 2015-07.
- Always list the assumptions that matter (filters, normalization, window).

## Follow-ups and related questions
- Re-run `analyze` with changed flags; responses are cached in `.cache/`, so adding a language or
  changing the window costs seconds. Keep related runs in sibling `--out` directories.
- "Which audiences next?" → one `analyze` with all candidate `--langs`, then rank; explain the
  score rule and show the confidence of each row.
- "How trustworthy?" → read `reasons`, `spike_share_pct`, `coverage_pct`, `p_value` from
  `result.json`; the summary's Limitations already lists the important ones.
- Exit code 2 = nothing usable (check titles); 3 = bad arguments (message says what to fix).

## Commands
| command | purpose | key flags |
|---|---|---|
| `resolve` | map topic → article per language, cheap preview | `--topic --langs --lang-hint --qid --titles --json` |
| `analyze` | fetch + normalize + trend + confidence + chart | `--topic/--topics --langs --months/--start/--end --granularity --rank-by --titles --out` |
| `report` | one-page PDF from a run | `--run --title --notes/--notes-file --lang --out` |

## Read more
- [references/methodology.md](references/methodology.md) — metrics, thresholds, confidence rules, ranking.
- [references/api-notes.md](references/api-notes.md) — endpoints, quirks, cache, error codes.
- [references/examples.md](references/examples.md) — the three canonical requests worked end to end.
