# verify — ../examples/03-english-multi — 2024-09..2026-08
## English language|pl «Język angielski» → **ROBUST**
- devices [ok]: desktop -14.3%/yr vs mobile-web -7.4%/yr (gap 6.9 pts)
- bots [ok]: 21.9% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -10.0%/yr · without last 3 -12.6%/yr · without first 3 -9.0%/yr
- spot check [ok]: 2025-10: stored 10137 vs API now 10137
- baseline: raw article views -19.5%/yr, whole pl.wikipedia -10.4%/yr → relative -9.1%/yr
## English language|cs «Angličtina» → **ROBUST**
- devices [ok]: desktop -16.3%/yr vs mobile-web -8.0%/yr (gap 8.3 pts)
- bots [ok]: 28.6% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -11.8%/yr · without last 3 -12.9%/yr · without first 3 -8.9%/yr
- spot check [ok]: 2024-10: stored 4139 vs API now 4139
- baseline: raw article views -24.4%/yr, whole cs.wikipedia -14.2%/yr → relative -10.2%/yr
## English language|uk «Англійська мова» → **ROBUST**
- devices [ok]: desktop -19.4%/yr vs mobile-web -13.5%/yr (gap 5.9 pts)
- bots [ok]: 25.6% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -15.5%/yr · without last 3 -14.9%/yr · without first 3 -13.5%/yr
- spot check [ok]: 2026-01: stored 6888 vs API now 6888
- baseline: raw article views -37.0%/yr, whole uk.wikipedia -25.3%/yr → relative -11.7%/yr
## English language|de «Englische Sprache» → **FRAGILE**
- devices [ok]: desktop -1.4%/yr vs mobile-web -0.5%/yr (gap 0.9 pts)
- bots [alert]: 74.8% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -0.7%/yr · without last 3 +1.7%/yr · without first 3 -2.4%/yr (flat: within ±5 pts, sign changes ignored)
- spot check [ok]: 2026-08: stored 20354 vs API now 20354
- baseline: raw article views -8.8%/yr, whole de.wikipedia -8.2%/yr → relative -0.6%/yr
## English language|es «Idioma inglés» → **ROBUST**
- devices [ok]: desktop -14.3%/yr vs mobile-web -7.6%/yr (gap 6.7 pts)
- bots [ok]: 22.7% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -10.6%/yr · without last 3 -11.2%/yr · without first 3 -8.5%/yr
- spot check [ok]: 2025-11: stored 27226 vs API now 27226
- baseline: raw article views -29.1%/yr, whole es.wikipedia -20.5%/yr → relative -8.6%/yr
## English grammar|pl «Gramatyka języka angielskiego» → **FRAGILE**
- devices [alert]: desktop -0.6%/yr vs mobile-web -32.1%/yr (gap 31.5 pts)
- bots [warn]: 48.1% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -17.5%/yr · without last 3 -17.8%/yr · without first 3 -19.8%/yr
- spot check [ok]: 2025-08: stored 197 vs API now 197
- baseline: raw article views -26.8%/yr, whole pl.wikipedia -10.4%/yr → relative -16.4%/yr
## English grammar|cs «Anglická gramatika» → **FRAGILE**
- devices [alert]: desktop -54.9%/yr vs mobile-web -73.0%/yr (gap 18.1 pts)
- bots [warn]: 39.1% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -65.5%/yr · without last 3 -66.8%/yr · without first 3 -60.2%/yr
- spot check [ok]: 2025-02: stored 372 vs API now 372
- baseline: raw article views -70.6%/yr, whole cs.wikipedia -14.2%/yr → relative -56.4%/yr
## English grammar|uk «Граматика англійської мови» → **FRAGILE**
- devices [alert]: desktop -54.9%/yr vs mobile-web -35.1%/yr (gap 19.7 pts)
- bots [alert]: 58.4% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -47.7%/yr · without last 3 -58.8%/yr · without first 3 -52.3%/yr
- spot check [ok]: 2026-07: stored 58 vs API now 58
- baseline: raw article views -61.1%/yr, whole uk.wikipedia -25.3%/yr → relative -35.8%/yr
## English grammar|de «Englische Grammatik» → **FRAGILE**
- devices [alert]: desktop -7.0%/yr vs mobile-web -46.4%/yr (gap 39.3 pts)
- bots [warn]: 45.0% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -27.3%/yr · without last 3 -26.4%/yr · without first 3 -12.1%/yr
- spot check [ok]: 2025-12: stored 582 vs API now 582
- baseline: raw article views -33.4%/yr, whole de.wikipedia -8.2%/yr → relative -25.2%/yr
## English grammar|es «Gramática del inglés» → **MIXED**
- devices [warn]: desktop -45.9%/yr vs mobile-web -60.5%/yr (gap 14.6 pts)
- bots [ok]: 31.9% of all traffic to this article is non-human (spiders/automated)
- window [ok]: full -54.6%/yr · without last 3 -54.9%/yr · without first 3 -53.8%/yr
- spot check [ok]: 2025-06: stored 1058 vs API now 1058
- baseline: raw article views -64.2%/yr, whole es.wikipedia -20.5%/yr → relative -43.7%/yr
Note: verify measures stability of the trend, not its direction: a robust decline is still a decline.
Verdict rule: alert on devices/bots/window/spot check → fragile; only warnings → mixed; else robust.
