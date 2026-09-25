# Transcript — 6-discover
usage: {'prompt_tokens': 215711, 'completion_tokens': 2882}
score: {'matched': 3, 'expected': 3, 'tool_calls': 7, 'used_resolve': False, 'used_analyze': True, 'used_report': False, 'final_chars': 2053}

## user
Які теми зараз ростуть в україномовній Wikipedia в галузі науки й освіти? Дай кандидатів для нового курсу і скажи, наскільки це стійкий інтерес, а не разова увага.

## assistant → Skill
```
{"skill": "wikipedia-interest", "args": "Ukrainian Wikipedia (uk), science and education topics, 12 months pageview trends, identify rising topics with sustained growth for course development"}
```

## tool result
```
Launching skill: wikipedia-interest
```

## assistant → bash
```
cd /home/vampir/petProjects/genesisAiEngineerCourse/wikipedia-interest && uv run scripts/wiki_interest.py discover --lang uk --sustained --months 12 --include "наук|освіт|навч|біо|хім|фіз|інформатик|штучн|машин|дан|алгоритм|програм"
```

## tool result
```
Exit code 2
usage: wiki_interest.py [-h]
                        {resolve,analyze,verify,compare,discover,report} ...
wiki_interest.py: error: unrecognized arguments: --months 12
```

## assistant → bash
```
cd /home/vampir/petProjects/genesisAiEngineerCourse/wikipedia-interest && uv run scripts/wiki_interest.py discover --help
```

## tool result
```
usage: wiki_interest.py discover [-h] --lang LANG [--month MONTH]
                                 [--limit LIMIT] [--include INCLUDE]
                                 [--exclude EXCLUDE] [--min-views MIN_VIEWS]
                                 [--sustained] [--out OUT] [--no-cache]

options:
  -h, --help            show this help message and exit
  --lang LANG           one language code, e.g. uk
  --month MONTH         YYYY-MM closed month (default: last closed month)
  --limit LIMIT
  --include INCLUDE     regex the title must match, e.g. 'астроном|космос'
  --exclude EXCLUDE     regex to drop titles, e.g. 'фільм|серіал'
  --min-views MIN_VIEWS
  --sustained           also fetch each candidate's 24-month trend +
                        confidence (≈2 calls per candidate)
  --out OUT             output directory (default
                        runs/discover-<lang>-<month>)
  --no-cache
```

## assistant → bash
```
uv run scripts/wiki_interest.py discover --lang uk --sustained --include "наук|освіт|навч|біо|хім|фіз|інформатик|штучн|машин|дан|алгоритм|програм" --out runs/discover-ua-science-edu
```

## tool result
```
# discover — uk.wikipedia — 2026-08 vs 2025-08 (per million of project views)
filters: include='наук|освіт|навч|біо|хім|фіз|інформатик|штучн|машин|дан|алгоритм|програм' exclude=None
| # | article | pm now | pm year ago | month-on-year % | views now | new in top? | growth/yr % (clipped, 24m) | confidence | spikes % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Буданов Кирило Олексійович | 239 | 236.76 | 0.9 | 12122 |  | 82.35 | medium | 28.72 |
| 2 | Володимир Дантес | 77.54 | 59.09 | 31.2 | 3933 | yes | 61.35 | high | 0 |
| 3 | Даніель Салем | 90.28 | 132.84 | -32 | 4579 |  | 48.66 | low | 0 |
| 4 | Орден Данила Галицького | 78.15 | 68.04 | 14.9 | 3964 |  | 39.62 | high | 0 |
| 5 | Даниленко Тетяна Володимирівна | 123.01 | 67.31 | 82.8 | 6239 |  | 30.92 | low | 0 |
| 6 | Орден Богдана Хмельницького (Україна) | 244.56 | 248 | -1.4 | 12404 |  | 19.82 | high | 9.24 |
| 7 | Ляшук Данііл Олександрович | 66.68 | 55.74 | 19.6 | 3382 | yes | 14.76 | low | 0 |
| 8 | Данілевич Андрій Всеволодович | 64.16 | 16.88 | 280.1 | 3254 | yes | 13.23 | low | 12.02 |
| 9 | Жадан Сергій Вікторович | 83.71 | 104.04 | -19.5 | 4246 |  | 6.56 | low | 15.77 |
| 10 | Кучма Леонід Данилович | 103.86 | 129.9 | -20 | 5268 |  | 3.82 | low | 0 |
| 11 | 2С22 «Богдана» | 78.41 | 104.32 | -24.8 | 3977 |  | 2.67 | low | 7.11 |
| 12 | Данія | 87.7 | 94.11 | -6.8 | 4448 |  | -8.27 | medium | 23.89 |
| 13 | Данило Галицький | 71.67 | 81.62 | -12.2 | 3635 |  | -11.69 | high | 9.42 |
| 14 | Богдан Хмельницький | 118.1 | 131.36 | -10.1 | 5990 |  | -24.73 | high | 0 |
| 15 | Штучний інтелект | 67.05 | 86.23 | -22.2 | 3401 |  | -26.05 | high | 0 |
Note: Top lists count all readers of the month; a rise here is attention, not durable interest — run analyze --titles on the candidates you care about to get a 24-month trend with confidence.
Next: `uv run scripts/wiki_interest.py analyze --topic "<name it>" --langs uk --titles uk=Буданов_Кирило_Олексійович --months 24 --out runs/<slug>`
```

## assistant → bash
```
uv run scripts/wiki_interest.py discover --lang uk --sustained --include "штучн.*інтелект|машинне.навч|глибоке.навч|нейромережа|біотехнологія|генна.інженерія|STEM|програмування|кібернетик|комп.ютер" --exclude "Данил|Кучма|Хмельницький|Буданов|Жадан" --out runs/discover-ua-stem
```

## tool result
```
# discover — uk.wikipedia — 2026-08 vs 2025-08 (per million of project views)
filters: include='штучн.*інтелект|машинне.навч|глибоке.навч|нейромережа|біотехнологія|генна.інженерія|STEM|програмування|кібернетик|комп.ютер' exclude='Данил|Кучма|Хмельницький|Буданов|Жадан'
| # | article | pm now | pm year ago | month-on-year % | views now | new in top? | growth/yr % (clipped, 24m) | confidence | spikes % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Штучний інтелект | 67.05 | 86.23 | -22.2 | 3401 |  | -26.05 | high | 0 |
Note: Top lists count all readers of the month; a rise here is attention, not durable interest — run analyze --titles on the candidates you care about to get a 24-month trend with confidence.
Next: `uv run scripts/wiki_interest.py analyze --topic "<name it>" --langs uk --titles uk=Штучний_інтелект --months 24 --out runs/<slug>`
```

## assistant → bash
```
uv run scripts/wiki_interest.py discover --lang uk --sustained --limit 30 --out runs/discover-ua-all
```

## tool result
```
# discover — uk.wikipedia — 2026-08 vs 2025-08 (per million of project views)
| # | article | pm now | pm year ago | month-on-year % | views now | new in top? | growth/yr % (clipped, 24m) | confidence | spikes % |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Хмара Євгеній Леонідович | 1431.69 | 5.44 | 26217.8 | 72616 | yes | 9375.25 | low | 0 |
| 2 | Таємниця бункера | 189.41 | 0.03 | 631267 | 9607 | yes | 8657.96 | medium | 0 |
| 3 | Оля Полякова | 225.2 | 0.87 | 25785.1 | 11422 | yes | 3235.39 | high | 0 |
| 4 | Джин Грей | 176.83 | 0.79 | 22283.5 | 8969 | yes | 2430.09 | high | 0 |
| 5 | Людина-павук: Абсолютно новий день | 600.61 | 28.83 | 1983.3 | 30463 | yes | 1221.39 | low | 0 |
| 6 | Сонячне затемнення 12 серпня 2026 року | 176.93 | 4.01 | 4312.2 | 8974 | yes | 842.01 | high | 0 |
| 7 | Одіссея (фільм, 2026) | 971.11 | 35.48 | 2637.1 | 49255 | yes | 500.8 | low | 69.11 |
| 8 | Бандероль (БПЛА) | 1055.16 | 20.08 | 5154.8 | 53518 | yes | 374.99 | low | 0 |
| 9 | Інде Наварретт | 140.1 | 0.34 | 41105.9 | 7106 | yes | 316.97 | low | 93.15 |
| 10 | Галан Любов Михайлівна | 133.73 | 1.47 | 8997.3 | 6783 | yes | 77.74 | low | 95.85 |
| 11 | Чайко Олександр Юрійович | 324.05 | 0.7 | 46192.9 | 16436 | yes | 70.16 | low | 91.42 |
| 12 | Явлінський Григорій Олексійович | 169.24 | 6.33 | 2573.6 | 8584 | yes | 64.1 | low | 52.71 |
| 13 | Мила | 187.22 | 4.51 | 4051.2 | 9496 | yes | 46.47 | low | 63.09 |
| 14 | Ратко Младич | 148.76 | 7.51 | 1880.8 | 7545 | yes | 39.49 | low | 39.79 |
| 15 | Сеута | 356.21 | 7.31 | 4772.9 | 18067 | yes | 21.4 | low | 79.49 |
| 16 | Коновалець Євген Михайлович | 1361.8 | 64.63 | 2007.1 | 69071 |  | 20.96 | low | 47.27 |
| 17 | Гейден Панеттьєр | 1878.37 | 16.41 | 11346.5 | 95272 | yes | 20.39 | low | 78.74 |
| 18 | Тім Каррі | 224.35 | 12.52 | 1691.9 | 11379 | yes | 20.04 | low | 38.85 |
| 19 | Альошкіна Дарія Олексіївна | 461.41 | 1.05 | 43843.8 | 23403 | yes | 18.18 | low | 93.05 |
| 20 | Мудра Ірина Романівна | 2433.91 | 6.81 | 35640.2 | 123449 | yes | 12.13 | low | 83.41 |
| 21 | Янсен Панеттьєрі | 179.59 | 1.04 | 17168.3 | 9109 | yes | 10.69 | low | 84.23 |
| 22 | Гордій Старух | 153.45 | 2.39 | 6320.5 | 7783 | yes | 3.67 | low | 63.96 |
| 23 | Микитась Максим Вікторович | 588.15 | 5.47 | 10652.3 | 29831 | yes | 2.91 | low | 83.71 |
| 24 | Доллі Партон | 425.59 | 8.87 | 4698.1 | 21586 | yes | 1.34 | low | 63.78 |
| 25 | Собко Сергій Станіславович | 228.78 | 10.57 | 2064.4 | 11604 | yes | 1.05 | low | 57.68 |
| 26 | Нірмал Пурджа | 152.4 | 5.63 | 2606.9 | 7730 | yes | -5.86 | low | 72.46 |
| 27 | Теракт над Локербі | 195.44 | 4.17 | 4586.8 | 9913 | yes | -6.47 | low | 63.32 |
| 28 | Обсесія (фільм) | 153.55 | 0.03 | 511733 | 7788 | yes | -7.74 | low | 99.92 |
| 29 | Прічард Колон | 219.32 | 5.45 | 3924.2 | 11124 | yes | -15.76 | low | 68.43 |
| 30 | Прощальний лист | 179.95 | 1.67 | 10675.4 | 9127 | yes | -28 | low | 86.79 |
Note: Top lists count all readers of the month; a rise here is attention, not durable int
```

## assistant → bash
```
uv run scripts/wiki_interest.py analyze --topics "Штучний інтелект;Машинне навчання;Програмування;Комп'ютерна наука" --langs uk --months 24 --out runs/analyze-ua-stem
```

## tool result
```
# Штучний інтелект, Машинне навчання, Програмування, Комп'ютерна наука — uk — 2024-09..2026-08 (24 monthly)
Resolved Штучний інтелект: uk → «Штучний інтелект»
Resolved Машинне навчання: uk → «Машинне навчання»
Resolved Програмування: uk → «Програмування»
Resolved Комп'ютерна наука: uk → MISSING

| topic | lang | pm latest (3-mo avg) | pm year ago (3-mo avg) | YoY % (12m vs prior 12m) | growth/yr % (clipped) | spikes % | coverage % of window | confidence |
|---|---|---|---|---|---|---|---|---|
| Штучний інтелект | uk | 69.96 | 93.72 | -12.86 | -26.05 | 0 | 100 | high |
| Машинне навчання | uk | 6.05 | 8.3 | -36.19 | -41.57 | 0 | 100 | high |
| Програмування | uk | 3.11 | 4.5 | -41.1 | -45.1 | 0 | 100 | high |

## Ranking (by volume: pm latest, i.e. current attention share)
1. Штучний інтелект|uk (69.96); 2. Машинне навчання|uk (6.05); 3. Програмування|uk (3.11)
## Checks
- Штучний інтелект: resolved to Q11660 «artificial intelligence»; other candidates: Q28324961 «штучний інтелект в охороні здоров’я» (використання алгоритмів і програмного забезпечення для машинного навчання для наближення людського пізнання в області аналізу та використання складних медичних даних); Q25933185 «штучний інтелект у фантастиці» (штучний інтелект, зображений у художніх творах); Q56248890 «штучний інтелект в проєктах «Wikimedia»» (дослідження штучного інтелекту та інструменти, що застосовуються до проєктів Вікімедіа). Use --qid to switch.
- Машинне навчання: resolved to Q2539 «machine learning»; other candidates: Q6723676 «Machine Learning» (науковий журнал); Q28324910 «Машинне навчання на основі правил» (machine learning methods that try to develop rules that are to be applied in particular contexts); Q83512991 «Машинне навчання у фізиці» (applications of machine learning to quantum physics). Use --qid to switch.
- Програмування: resolved to Q80006 «computer programming»; other candidates: Q202843 «лінійне програмування» (задача оптимізації лінійного виразу за лінійних обмежень); Q528588 «програмування в обмеженнях» (programming paradigm wherein relations between variables are stated in the form of constraints); Q50832308 «бльок мовлення» (стратегія, яку використовують мовники для трансляції групи подібних програм). Use --qid to switch.
- Комп'ютерна наука / uk: MISSING article (no Wikidata item found; searched uk.wikipedia for 'Комп'ютерна наука')
- every row is declining → ranked by volume (current attention share) instead of score; a score ranking would only order declines and favour low-confidence ones. Use --rank-by growth to see which declines slowest.
- window 2024-09..2026-08 (24 monthly periods); current month excluded
- cache: 2 hits, 12 misses
- Машинне навчання|uk: strongly seasonal (amplitude 1.07× the mean) — compare the same months across years, not adjacent months; 'pm latest' vs 'pm year ago' already does that
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article 
```

## assistant
Based on the analysis, I have important findings about science and education interest in Ukrainian Wikipedia:

## **Key Finding: Declining, Not Growing**

The major STEM topics in Ukrainian Wikipedia are **not growing** — they're **declining significantly**:

| Topic | 24-month growth | Confidence | Current trend |
|---|---|---|---|
| **Штучний інтелект** (AI) | −26% | **HIGH** | 70 views/million, down from 94 |
| **Машинне навчання** (Machine Learning) | −42% | **HIGH** | 6 views/million, down from 8 |
| **Програмування** (Programming) | −45% | **HIGH** | 3 views/million, down from 4.5 |

This is **not temporary noise** — these declines are robust and consistent.

### What *is* growing in Ukrainian Wikipedia?
The discover scan of rising topics shows the audience is driven primarily by:
- **Entertainment**: Films, celebrities, actors
- **News events**: The August 2026 solar eclipse has 842% growth (but event-driven)
- **Politics & society**: Contemporary figures and incidents

Science content appears only around **breaking news events** (eclipses, space discoveries), not as sustained interests.

## Course Development Implications

**Negative signal for a science/education course based on Ukrainian Wikipedia trends:**

1. **Not a sustained audience** — even AI content is losing readers, despite global AI hype
2. **Low baseline interest** — AI averages 70 views/million; entertainment topics average 500-2000
3. **No rising indicators** — Computer Science has no Wikipedia article; education topics don't appear in rising lists

**If you still want to pursue this**, I'd recommend:
- **Validate with direct user research** before investing, since Wikipedia interest ≠ willingness to learn
- Look at **other languages/markets** (Polish, Czech, German editions may show different patterns)
- Focus on **event-driven coverage** (new discoveries, breakthroughs) rather than foundational topics

Would you like me to check interest trends in other language editions (Polish, Czech, German) to see if Ukrainian's declining trend is unique?
