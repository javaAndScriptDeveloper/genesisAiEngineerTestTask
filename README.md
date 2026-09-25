# wikipedia-interest — Agent Skill для оцінки інтересу аудиторії за переглядами Wikipedia

Тестове завдання Genesis AI Engineer course, задача 1:
<https://gist.github.com/edugenesis/84f332ba58642cf12110b196775a8b72>

*English version below.*

## Що це

Самостійна навичка у форматі [Agent Skills](https://agentskills.io/specification), яка дає AI-агенту
відповідати засновникам B2C-продуктів на два питання:

- **які теми розвивати далі** — чи росте інтерес до теми, і наскільки цьому росту можна довіряти;
- **якими мовами запускатись** — як інтерес до теми відрізняється між мовними розділами Wikipedia.

Джерело даних — публічний [Wikimedia Pageviews API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)
плюс Wikidata для зіставлення теми зі статтями в кожній мові. Навичка виконує всю змістовну роботу
власним кодом (Python): резолвить назви статей, тягне ряди переглядів, нормалізує їх, рахує тренд,
піки, сезонність і рівень довіри, малює графік і збирає односторінковий PDF-звіт. Агент лише
викликає команди (шість: resolve, analyze, verify, compare, discover, report) та інтерпретує коротке резюме.

```
wikipedia-interest/                  ← сама навичка (все необхідне всередині)
├── SKILL.md                         ← інструкції для агента (≈130 рядків)
├── scripts/wiki_interest.py         ← CLI: resolve | analyze | verify | compare | discover | report
├── wiki_interest/                   ← код: api, cache, resolve, series, stats, run, summary, charts, pdf, verify, compare, discover
├── references/                      ← методологія, нотатки про API, приклади (читаються за потреби)
├── assets/report_notes_template.md  ← шаблон рекомендації для PDF
├── tests/                           ← 113 офлайн-тестів + 3 живих
├── pyproject.toml, uv.lock          ← відтворюване середовище (uv)
eval/                                ← харнес для перевірки на дешевій моделі через OpenRouter
examples/                            ← реальні результати трьох запитів із завдання (summary, chart, PDF)
docs/features/                       ← опис кожної можливості: що, навіщо, як користуватись, як перевірено
docs/demo/DEMO.md                    ← текст для демо і захисту
docs/superpowers/                    ← спека та план, за якими писався код
```

## Швидкий старт

Потрібні Python ≥ 3.12 та [uv](https://docs.astral.sh/uv/). Усі команди — з каталогу навички;
перший запуск сам створить `.venv` із зафіксованих у `uv.lock` версій.

```bash
cd wikipedia-interest

# 1. Що за стаття стоїть за темою в кожній мові (дешево, тільки Wikidata)
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs

# 2. Повний аналіз: ряди, нормалізація, тренд, довіра, графік
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --months 36 --out runs/astro-uk

# 3. Односторінковий PDF із вашою рекомендацією
uv run scripts/wiki_interest.py report --run runs/astro-uk --title "Астрономія в укр. Wikipedia" \
    --notes "3–6 речень висновку" --lang uk
```

`analyze` друкує резюме (≤ 40 рядків) і пише в `--out`: `summary.md`, `result.json`, `data.csv`,
`chart.png`. `report` додає `report.pdf`. Готові приклади — в [`examples/`](examples/).

Далі — три команди, які роблять відповідь перевіреною, а не лише порахованою (детально в
[`docs/features/`](docs/features/)):

```bash
# наскільки стійкий висновок: десктоп vs мобільні, боти, чутливість до вікна, контрольна перевірка з API
uv run scripts/wiki_interest.py verify --run runs/astro-uk
# що змінилось між двома запусками (уточнення: інша мова, коротше вікно, інші припущення)
uv run scripts/wiki_interest.py compare --runs runs/eng-24 runs/eng-12
# які статті ростуть у розділі, і чи це стійкий інтерес, а не разова увага
uv run scripts/wiki_interest.py discover --lang uk --include "астроном|косм" --sustained
```
Припущення можна змінювати флагами `--access`, `--agent`, `--spike-z`; великі матриці — `--topics-file`.

## Як користуватись з агентом

Скопіюйте каталог навички туди, де ваш агент шукає навички (для Claude Code —
`~/.claude/skills/wikipedia-interest`), і поставте запит природною мовою:

> Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній
> Wikipedia за останні два роки.

Агент за `SKILL.md`: за потреби викликає `resolve` і уточнює назви → викликає `analyze` → читає
резюме, починаючи з рядка `Resolved`, колонки `confidence` і секцій `Checks`/`Limitations` →
відповідає числами «на мільйон переглядів розділу», очищеним від піків ростом, рівнем довіри та
обмеженнями → за бажанням користувача робить `report`. Повторні й уточнюючі запити коштують секунди:
відповіді API кешуються в SQLite (`.cache/`), закриті місяці — назавжди.

## Архітектура і головні рішення

**Одна команда-конвейєр замість набору дрібних інструментів.** Дешевій моделі (Claude Haiku 4.5)
важко правильно зчепити 5–6 викликів. Тому `analyze` робить усе за один виклик і повертає
детерміноване текстове резюме, а не JSON; деталі лежать у `result.json` на випадок, якщо агент їх
потребує. Типовий запит — 1–3 виклики інструментів.

**Порівнюємо частку уваги, не сирі перегляди.** `per_million = views / project_views × 1e6` —
перегляди статті на мільйон переглядів усього мовного розділу за той самий період. Без цього
англійський розділ «виграє» будь-яке порівняння просто за розміром.

**Ріст без піків + явний рівень довіри.** Тренд — OLS на `log(per_million + ε)` (ε ∝ медіані ряду, нульові періоди не беруть участі у підгонці), анулізований. Піки
шукаємо робастним z-score (MAD, порог 3.5), заміняємо медіаною сусідів і перераховуємо тренд — саме
це число іде в заголовок. Монотонність перевіряємо Spearman ρ з permutation-тестом (без SciPy).
`confidence` = high / medium / low за фіксованими порогами (покриття, частка піків, p-value, розрив
між сирим і очищеним ростом, мінімум переглядів) і завжди з переліком причин. Пороги — в одному
місці (`stats.py: THRESHOLDS`) і продубльовані в
[`references/methodology.md`](wikipedia-interest/references/methodology.md).

**Чесність щодо відсутніх даних.** Немає статті у мові → статус `MISSING` з підказками пошуку, які
навичка **не** використовує автоматично; `SKILL.md` прямо вимагає казати «немає статті ≠ немає
інтересу». 404 від API → `NO DATA`, а не падіння. Поточний неповний місяць виключено. Сезонність
(наприклад, шкільні піки у вересні) виноситься в `Checks`, щоб агент не порівнював вересень з липнем.

**Ранжування пояснюване.** `score = очищений ріст × вага довіри` (1.0 / 0.6 / 0.25); правило
друкується в резюме, є `--rank-by growth|volume`.

**PDF без системних залежностей.** reportlab + matplotlib + шрифт DejaVu, який іде з matplotlib
(кирилиця, чеська, польська). Завжди одна сторінка A4: текст рекомендації зменшується й обрізається,
але блок припущень/обмежень не випадає ніколи.

## Як перевірено

| Рівень | Команда | Результат |
|---|---|---|
| Офлайн-юніт-тести (HTTP замокано respx) | `cd wikipedia-interest && uv run pytest -q` | 113 passed |
| Живі інтеграційні (три запити із завдання) | `uv run pytest -m network -q` | 3 passed |
| Відповідність спеці Agent Skills | `uvx --from skills-ref agentskills validate wikipedia-interest` | Valid skill |
| Харнес оцінки (локальний, рубрика) | `cd eval && uv run pytest -q` | 12 passed |
| Повний сценарій на дешевій моделі | `cd eval && uv run run_eval.py --runner claude-code --model haiku` (Haiku 4.5) або `--model nvidia/nemotron-3.5-lightning:free` (OpenRouter) | див. [`eval/RESULTS.md`](eval/RESULTS.md) |

Що покривають тести: спайк, вставлений у рівний ряд, знаходиться й вирізається; ріст на синтетичній
експоненті відтворюється з точністю до 2 п.п.; вікно < 12 місяців не ламає YoY; нульовий ряд не
дає NaN; назва з `/` і не-ASCII коректно кодується в URL; усі мови відсутні → exit 2 із підказкою;
дуже довгі нотатки → все одно одна сторінка PDF; `<title>` у тексті обмежень не ламає парсер PDF
(цю помилку знайшов живий прогін — тест доданий до фіксу).

### Перевірка на моделі класу Haiku 4.5

Модель для прогону — безкоштовна `nvidia/nemotron-3.5-lightning:free` через OpenRouter (ключ безкоштовного
рівня без кредитів не може викликати платний Claude Haiku 4.5 — API повертає 402; завдання явно дозволяє
безкоштовні моделі OpenRouter). Той самий харнес запускається на Haiku однією зміною `--model`, якщо на
ключі є кредити.

`eval/run_eval.py` дає моделі через OpenRouter `SKILL.md` як системний промпт і два інструменти —
`bash` (виконується в каталозі навички, вивід обрізано до 8 000 символів; це **не** пісочниця — команди
моделі виконуються локально без обмежень, запускайте лише з моделями, яким довіряєте) та `read_file`
(тільки всередині навички). Проганяються три запити із завдання й уточнення до третього («додай іспанський
розділ, візьми 12 місяців»). Для кожного зберігається транскрипт (`eval/transcripts/<model>/*.md`)
і рядок рубрики: скільки очікувань закрито в фінальній відповіді (згадано «на мільйон», рівень
довіри, відсутність польської статті, PDF…), скільки викликів інструментів, чи використано
`resolve`/`analyze`/`report`, токени, час. Результати та спостереження — в
[`eval/RESULTS.md`](eval/RESULTS.md).

Було три прогони. Перший показав, що модель вигадує польські назви статей і передає їх URL-кодованими,
плутає значення колонок і не робить PDF, коли просять; другий — що після мого виправлення вона зупинялась
запитати дозвіл перед `analyze`. Після другої правки `SKILL.md` фінальний прогін: усі чотири сценарії
виконано за 2–4 виклики інструментів, з числами «на мільйон», очищеним ростом, рівнем довіри з причинами,
чесним «статті немає» для польської та PDF-звітом на запит. Кожна правка інструкцій випливала з читання
транскриптів, а не лише з рубрики.

## Як я перевіряв результат AI-інструментів

Код написано з Claude Code за попередньо затвердженими спекою та планом
([`docs/superpowers/`](docs/superpowers/)). Що робив, щоб не довіряти згенерованому коду на слово:

1. **TDD для кожного модуля**: спочатку тест, який падає з очікуваною причиною, потім реалізація.
   Тест, який пройшов одразу, вважав підозрілим.
2. **Ручна звірка з сирим API**: значення `data.csv` для «Астрономія» (uk, 2025-03 = 1068
   переглядів) збіглося з прямим `curl` до `per-article`; аналогічно перевірено, що падіння −45 %/рік
   — не артефакт, а щорічно нижчі вересневі шкільні піки (9857 → 4687 → 1642).
3. **Візуальна перевірка артефактів**: рендерив PDF у PNG і дивився очима — так знайшов
   накладання заголовків таблиці й занадто малий графік, виправив.
4. **Живий прогін до написання документації**: саме він виявив краш reportlab на `<title>` у
   тексті обмежень і те, що сезонність рахується, але не показується агенту.
5. **Прогін на дешевій моделі** з читанням транскриптів рядок за рядком, а не лише рубрики.

## Обмеження

- Інтерес до статті ≠ готовність платити; це фільтр напрямів для подальшої перевірки.
- Перегляди залежать від існування та якості статті; відсутня чи погана стаття ховає реальний інтерес.
- Фільтр ботів Wikimedia неідеальний; піки можуть бути автоматичним трафіком або новинами.
- Мовний розділ ≠ країна.
- Дані з 2015-07; поточний місяць неповний і виключений.

## Roadmap: як розвивати навичку далі

1. **Тема як кластер, а не одна стаття.** Через Wikidata `P31`/`P279` та категорії збирати набір
   статей (астрономія → планети, телескопи, космонавтика) і сумувати `per_million` по кластеру;
   це знімає залежність від однієї назви й покриває мови, де головної статті немає.
2. **Режим відкриття тем.** Ендпоінти `top`/`top-per-country` по розділах, фільтр за категорією →
   список статей, що ростуть, які користувач не називав.
3. **Великі обсяги.** Місячні дампи pageviews або Wikimedia Enterprise → Parquet + DuckDB локально;
   матриця 50 тем × 20 мов стає одним запитом, кеш перетворюється на колонкове сховище.
4. **Країни, а не мови.** `top-per-country` і геодані, щоб розділити «іспаномовний розділ» на
   Іспанію, Мексику, Аргентину.
5. **Зміни режиму та прогноз.** Change-point detection, STL-декомпозиція сезонності, лінійна
   екстраполяція з інтервалами; попередження «тренд зламався».
6. **Багатосторінкові звіти й моніторинг.** HTML-дашборд, розклад повторних прогонів, алерти про
   різкі зміни.
7. **Калібрування довіри.** Набір розмічених минулих кейсів (теми, що стали / не стали продуктами)
   для підбору порогів; рубрика в eval — оцінювання сильнішою моделлю, а не regex.
8. **Швидкість і ціна.** Асинхронні запити, батчинг Wikidata, стримінг резюме для великих матриць.

## Ліцензія

MIT — див. [LICENSE](LICENSE).

---

# wikipedia-interest — an Agent Skill for measuring audience interest from Wikipedia pageviews

Genesis AI Engineer course, test task 1:
<https://gist.github.com/edugenesis/84f332ba58642cf12110b196775a8b72>

## What it is

A self-contained [Agent Skill](https://agentskills.io/specification) that lets an AI agent answer two
questions for B2C founders: **which topics to develop next** (is interest growing, and how much can
the growth be trusted) and **which languages to launch in** (how interest differs across Wikipedia
language editions).

Data comes from the public [Wikimedia Pageviews API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/reference/page-views.html)
plus Wikidata for mapping a topic to the article in each language. The skill does the substantive
work in its own Python code: resolves titles, fetches series, normalizes, computes trend, spikes,
seasonality and a confidence level, draws a chart and builds a one-page PDF. The agent only calls
the commands (six: resolve, analyze, verify, compare, discover, report) and interprets a short summary. See the directory tree above.

## Quick start

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/). Run everything from the skill
directory; the first run creates `.venv` from the pinned `uv.lock`.

```bash
cd wikipedia-interest
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs
uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 36 --out runs/astro-uk
uv run scripts/wiki_interest.py report --run runs/astro-uk --title "Astronomy in Ukrainian Wikipedia" --notes "3–6 sentences" --lang en
```

`analyze` prints a ≤ 40-line summary and writes `summary.md`, `result.json`, `data.csv`, `chart.png`
to `--out`; `report` adds `report.pdf`. Real outputs for the task's three prompts are in
[`examples/`](examples/).

Three more commands turn a computed answer into a verified one (details in [`docs/features/`](docs/features/), Ukrainian):

```bash
uv run scripts/wiki_interest.py verify  --run runs/astro-uk            # devices, bots, window sensitivity, fresh spot-check, baseline
uv run scripts/wiki_interest.py compare --runs runs/eng-24 runs/eng-12  # what changed between two runs
uv run scripts/wiki_interest.py discover --lang uk --include "astro|cosm" --sustained   # rising articles + 24-month trend
```
Assumptions are flags (`--access`, `--agent`, `--spike-z`); large matrices come from `--topics-file`.

## Using it with an agent

Copy the skill directory where your agent looks for skills (Claude Code: `~/.claude/skills/wikipedia-interest`)
and ask in plain language. Following `SKILL.md`, the agent runs `resolve` when titles are ambiguous,
then `analyze`, reads the summary starting with `Resolved`, `confidence`, `Checks` and
`Limitations`, answers with per-million numbers, clipped growth, confidence and caveats, and runs
`report` only when a shareable file is wanted. Follow-ups are cheap: API responses are cached in
SQLite, closed months permanently.

## Architecture and key decisions

- **One pipeline command, not a toolbox.** A Haiku-class model chains 5–6 calls poorly, so `analyze`
  does everything in one call and returns deterministic text; details live in `result.json`.
  Typical request: 1–3 tool calls.
- **Share of attention, not raw views.** `per_million = views / project_views × 1e6` makes editions
  comparable.
- **Spike-clipped growth with an explicit confidence level.** OLS on `log(per_million + ε)` with ε proportional to the series median and zero periods excluded, robust
  MAD spike detection (z > 3.5), median replacement, Spearman ρ with a permutation p-value; `confidence`
  high / medium / low from fixed thresholds with reasons always listed. Thresholds live in one place
  (`stats.py: THRESHOLDS`) and in [`references/methodology.md`](wikipedia-interest/references/methodology.md).
- **Honest about missing data.** No article → `MISSING` with search suggestions that are never used
  automatically; API 404 → `NO DATA`; current month excluded; strong seasonality surfaced in `Checks`.
- **Explainable ranking.** `score = clipped growth × confidence weight` (1.0 / 0.6 / 0.25), rule
  printed in the summary, `--rank-by growth|volume` available.
- **PDF without system dependencies.** reportlab + matplotlib's bundled DejaVu font; always exactly
  one A4 page.

## How it was tested

| Layer | Command | Result |
|---|---|---|
| Offline unit tests (HTTP mocked with respx) | `cd wikipedia-interest && uv run pytest -q` | 113 passed |
| Live integration (the task's three prompts) | `uv run pytest -m network -q` | 3 passed |
| Agent Skills spec compliance | `uvx --from skills-ref agentskills validate wikipedia-interest` | Valid skill |
| Eval harness (local, rubric) | `cd eval && uv run pytest -q` | 12 passed |
| Full scenario on a cheap model | `cd eval && uv run run_eval.py --runner claude-code --model haiku` (Haiku 4.5) or `--model nvidia/nemotron-3.5-lightning:free` (OpenRouter) | see [`eval/RESULTS.md`](eval/RESULTS.md) |

### Cheap-model evaluation

The model used is the free `nvidia/nemotron-3.5-lightning:free` on OpenRouter: a free-tier key with no
credits cannot call the paid Claude Haiku 4.5 (HTTP 402), and the task explicitly allows free OpenRouter
models. The same harness runs on Haiku by changing `--model` once credits exist.

`eval/run_eval.py` sends `SKILL.md` as the system prompt via OpenRouter with two tools, `bash`
(cwd = skill dir, output truncated; **not a sandbox** — the model's commands run unconfined on your
machine, so use trusted models only) and `read_file` (skill dir only), runs the three task prompts plus
a follow-up, saves transcripts under `eval/transcripts/<model>/` and appends a rubric row: expectations
matched in the final answer, tool-call count, whether `resolve`/`analyze`/`report` were used, tokens,
wall time. Results and observations: [`eval/RESULTS.md`](eval/RESULTS.md).

Three runs. The first showed the model inventing Polish titles, URL-encoding `--titles`, misreading
column meanings and skipping the requested PDF; the second showed my fix over-corrected (it stopped to ask
permission before `analyze`). After the second `SKILL.md` revision the final run completes all four
scenarios in 2–4 tool calls each, with per-million numbers, clipped growth, confidence with reasons, an
honest "no article" for Polish, and the PDF on request. Every instruction change came from reading the
transcripts, not just the rubric.

## How AI-generated code was verified

Written with Claude Code from an approved spec and plan ([`docs/superpowers/`](docs/superpowers/)).
Every module was test-first (a test that passed immediately was treated as suspect). Numbers were
cross-checked by hand against raw API calls (uk «Астрономія» 2025‑03 = 1068 views in both). PDFs were
rendered to PNG and inspected, which caught header overlap and an undersized chart. A live run before
writing docs caught a reportlab crash on `<title>` in limitation text and the unsurfaced seasonality.
Model transcripts were read line by line, not just scored.

## Roadmap

1. Topic clusters via Wikidata `P31`/`P279` and categories instead of single articles.
2. Discovery mode from `top` endpoints: rising articles the user did not name.
3. Bulk data: pageview dumps / Wikimedia Enterprise → Parquet + DuckDB; 50 topics × 20 languages in one query.
4. Countries, not languages: `top-per-country`.
5. Change-point detection, STL seasonality, simple forecasts with intervals.
6. Multi-page reports, HTML dashboard, scheduled monitoring with breakout alerts.
7. Calibrate confidence thresholds on labelled past cases; LLM-graded eval rubric.
8. Async fetching, batched Wikidata calls, streaming summaries for large matrices.

## License

MIT — see [LICENSE](LICENSE).
