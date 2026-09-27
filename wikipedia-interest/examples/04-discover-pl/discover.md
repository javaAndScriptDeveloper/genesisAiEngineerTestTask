# discover — pl.wikipedia — 2026-08 vs 2025-08 (per million of project views)
filters: include='angielsk|język|gramat|nauk|matemat|fizyk|astronom' exclude='film|serial'
| # | article | pm now | pm year ago | month-on-year % | views now | new in top? | growth/yr % (clipped, 24m) | confidence | spikes % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Język polski | 62.16 | 44.87 | 38.5 | 10933 | yes | 3.72 | low | 0 |
Note: Top lists count all readers of the month; a rise here is attention, not durable interest — run analyze --titles on the candidates you care about to get a 24-month trend with confidence.
Next: `uv run scripts/wiki_interest.py analyze --topic "<name it>" --langs pl --titles pl=Język_polski --months 24 --out runs/<slug>`
