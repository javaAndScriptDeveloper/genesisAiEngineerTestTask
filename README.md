# wikipedia-interest — Agent Skill: інтерес аудиторії за переглядами Wikipedia

Тестове завдання Genesis AI Engineer course, задача 1:
<https://gist.github.com/edugenesis/84f332ba58642cf12110b196775a8b72>

Навичка у форматі [Agent Skills](https://agentskills.io/specification), яка дає AI-агенту допомагати
засновникам B2C-продуктів вирішувати, **які теми розвивати** і **якими мовами запускатись**, на основі
статистики переглядів Wikipedia. Уся навичка — в директорії [`wikipedia-interest/`](wikipedia-interest/).

*English summary at the end.*

## Відповідність вимогам завдання

| Вимога з завдання | Де реалізовано |
|---|---|
| Самостійна навичка у форматі Agent Skills, `SKILL.md` + власний код, який виконує змістовну роботу | [`wikipedia-interest/SKILL.md`](wikipedia-interest/SKILL.md), код у [`wiki_interest/`](wikipedia-interest/wiki_interest/), CLI [`scripts/wiki_interest.py`](wikipedia-interest/scripts/wiki_interest.py); `agentskills validate` — Valid |
| Аналіз даних про перегляди Wikipedia | Pageviews API (per-article, aggregate, top) + Wikidata для зіставлення тем зі статтями; нормалізація «на мільйон переглядів розділу» |
| Графіки | `chart.png` у кожному запуску (`charts.py`) |
| Короткі звіти, якими можна поділитись (PDF на одну сторінку) | `report` → `report.pdf`, завжди одна сторінка A4 (`pdf.py`) |
| Приклади запитів із завдання працюють | [`examples/01…03`](wikipedia-interest/examples/) — реальні виводи, графіки, PDF |
| Уточнення запитів і зміна припущень після першої відповіді | `--access`, `--agent`, `--spike-z`, `--months/--start/--end`, `--titles`, `--qid`; `compare --runs A B` показує, що змінилось |
| Допомога агенту оцінювати результати | рівень довіри `high/medium/low` з причинами у резюме; `Checks` і `Limitations` у кожному запуску |
| Допомога агенту перевіряти висновки | `verify --run`: десктоп vs мобільні, частка ботів, чутливість до вікна, контрольний перезапит з API, базова лінія розділу |
| Ефективні повторні й пов'язані запити | SQLite-кеш (закриті місяці — назавжди), `compare`, `discover` для пошуку суміжних тем, `--topics-file` для матриць |
| Рекомендації спираються на дані; припущення й обмеження зрозумілі | резюме, `result.json` і PDF містять `assumptions` та `limitations`; агент зобов'язаний їх цитувати |
| Зручно дешевій моделі (Claude Haiku 4.5); повний сценарій перевірено на такій моделі | 1–3 виклики інструментів на запит; [`eval/RESULTS.md`](wikipedia-interest/eval/RESULTS.md): Haiku 4.5 — 6 сценаріїв, усі очікування закриті; безкоштовна модель через OpenRouter — 4 сценарії |
| Без скомпільованих файлів; залежності відтворювані | `pyproject.toml` + `uv.lock`, pure-Python (PDF через reportlab + шрифт із matplotlib) |
| Пояснити, як розвивати далі для складніших досліджень і більших даних | розділ «Roadmap» нижче; пакетний режим уже є |
| Використання AI при розробці і перевірка його результату | розділ «Як я використовував AI» нижче; спека, план і рев'ю в [`docs/process/`](wikipedia-interest/docs/process/) |

## Що всередині

```
wikipedia-interest/                    ← навичка (усе необхідне всередині)
├── SKILL.md                           ← інструкції для агента (≈130 рядків)
├── scripts/wiki_interest.py           ← CLI: resolve | analyze | verify | compare | discover | report
├── wiki_interest/                     ← код: api, cache, resolve, series, stats, run, summary, charts, pdf, verify, compare, discover
├── references/                        ← методологія, нотатки про API, приклади (агент читає за потреби)
├── assets/report_notes_template.md    ← шаблон рекомендації для PDF
├── tests/                             ← 114 офлайн-тестів (HTTP замокано) + 3 живих
├── pyproject.toml, uv.lock            ← відтворюване середовище (uv)
├── examples/                          ← реальні результати запитів із завдання: summary, chart, PDF, verify, compare
├── eval/                              ← харнес перевірки на дешевій моделі (OpenRouter або Claude Code) + транскрипти + RESULTS.md
└── docs/
    ├── features/                      ← опис кожної можливості: що, навіщо, як користуватись, як перевірено
    └── process/                       ← спека та план, за якими писався код
```

## Швидкий старт

Потрібні Python ≥ 3.12 та [uv](https://docs.astral.sh/uv/). Усі команди — з директорії навички;
перший запуск створює `.venv` із версій, зафіксованих у `uv.lock`.

```bash
cd wikipedia-interest

# 1. Яка стаття стоїть за темою в кожній мові (дешево, лише Wikidata)
uv run scripts/wiki_interest.py resolve --topic "intermittent fasting" --langs pl,cs

# 2. Аналіз: ряди, нормалізація, тренд, довіра, графік, резюме
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --months 36 --out runs/astro-uk

# 3. Наскільки стійкий висновок: пристрої, боти, вікно, контрольна перевірка з API
uv run scripts/wiki_interest.py verify --run runs/astro-uk

# 4. PDF на одну сторінку з рекомендацією
uv run scripts/wiki_interest.py report --run runs/astro-uk --title "Астрономія в укр. Wikipedia" --notes "3–6 речень висновку" --lang uk

# Уточнення і суміжні запити
uv run scripts/wiki_interest.py analyze --topic "English language" --langs pl,cs,uk,de --months 24 --out runs/eng-24
uv run scripts/wiki_interest.py analyze --topic "English language" --langs pl,cs,uk,de,es --months 12 --out runs/eng-12
uv run scripts/wiki_interest.py compare --runs runs/eng-24 runs/eng-12                       # що змінилось між запусками
uv run scripts/wiki_interest.py discover --lang uk --include "астроном|косм" --sustained   # які статті ростуть у розділі
```

`analyze` друкує резюме (≤ 40 рядків) і пише в `--out`: `summary.md`, `result.json`, `data.csv`, `chart.png`.
Готові приклади — в [`wikipedia-interest/examples/`](wikipedia-interest/examples/).

## Як користуватись з агентом

Скопіюйте (або зробіть символічне посилання) директорію навички туди, де агент шукає навички — для Claude
Code це `~/.claude/skills/wikipedia-interest` — і поставте запит природною мовою:

> Порівняй зростання інтересу до інтервального голодування в польськомовній та чеськомовній Wikipedia
> за останні два роки.

За `SKILL.md` агент: за потреби викликає `resolve` → викликає `analyze` → читає резюме, починаючи з рядка
`Resolved`, колонки `confidence`, `Reasons`, `Checks`, `Limitations` → відповідає числами «на мільйон
переглядів розділу», очищеним від піків ростом, рівнем довіри з причинами й обмеженнями → на запит про
довіру чи ботів викликає `verify`, на запит про PDF — `report`. Повторні й уточнюючі запити коштують
секунди: відповіді API кешуються в SQLite, закриті місяці — назавжди.

## Головні рішення

- **Одна команда-конвейєр замість набору дрібних інструментів.** Дешевій моделі важко правильно зчепити
  5–6 викликів; `analyze` робить усе за один виклик і повертає детермінований текст. Деталі — у `result.json`.
- **Частка уваги, не сирі перегляди.** `per_million = views / project_views × 1e6`. Розділи різного розміру
  стають порівнюваними; знімається й загальне падіння трафіку Wikipedia.
- **Ріст без піків + явний рівень довіри.** OLS на `log(per_million + ε)` (ε ∝ медіані ряду, нульові періоди
  не беруть участі у підгонці), піки — робастний z-score (MAD), тренд перераховується без них.
  `confidence` — фіксовані пороги (покриття, частка піків, p-value монотонності, розрив між сирим і очищеним
  ростом, мінімум переглядів) із переліком причин. Пороги — в одному місці й у
  [`references/methodology.md`](wikipedia-interest/references/methodology.md).
- **Чесність щодо даних.** Відсутня стаття → `MISSING` з кандидатами, які **не** підставляються; 404 →
  `NO DATA`; поточний місяць виключено; місяць, який Wikimedia ще не опублікувала, не кешується назавжди;
  сезонність виноситься в `Checks`; коли всі теми падають, рейтинг перемикається на обсяг і резюме це пояснює.
- **Перевірка окремо від обчислення.** `verify` перемірює висновок іншими способами; на прикладах виявляє, що
  стаття «Englische Sprache» (de) має 74.8 % не-людського трафіку.

Опис кожної можливості — [`docs/features/`](wikipedia-interest/docs/features/).

## Як перевірено

| Рівень | Команда | Результат |
|---|---|---|
| Офлайн-юніт-тести (HTTP замокано respx) | `cd wikipedia-interest && uv run pytest -q` | 114 passed |
| Живі інтеграційні (запити із завдання) | `uv run pytest -m network -q` | 3 passed |
| Відповідність спеці Agent Skills | `uvx --from skills-ref agentskills validate wikipedia-interest` | Valid skill |
| Тести харнесу оцінки | `cd wikipedia-interest/eval && uv run pytest -q` | 12 passed |
| Повний сценарій на дешевій моделі | `uv run run_eval.py --runner claude-code --model haiku` або `--model nvidia/nemotron-3.5-lightning:free` | [`eval/RESULTS.md`](wikipedia-interest/eval/RESULTS.md) |

Що покривають тести: спайк у рівному ряду знаходиться й вирізається; ріст на синтетичній експоненті
відтворюється з точністю до 2 п.п. на будь-якому рівні трафіку; вікно < 12 місяців не ламає YoY; нульовий
ряд без NaN; назва з `/` і не-ASCII коректно кодується; усі мови відсутні → exit 2 із підказкою; невідомий код
мови → exit 3 із підказкою; довгі нотатки → все одно одна сторінка PDF; неповний місяць не потрапляє в кеш
назавжди; `verify` шанує `--access/--agent` запуску; `discover` не крашиться на неопублікованому місяці.

### Перевірка на дешевій моделі

`eval/run_eval.py` дає моделі `SKILL.md` як системний промпт і два інструменти — `bash` (у директорії
навички; не пісочниця — запускати лише з довіреними моделями) та `read_file` — і проганяє шість сценаріїв:
три запити із завдання, уточнення («додай іспанську, візьми 12 місяців»), «а це не боти?» (→ `verify`) і
«що росте в науці?» (→ `discover`). Для кожного зберігається транскрипт і рядок рубрики: закриті очікування,
кількість викликів інструментів, використані команди, токени, час.

Два раннери: OpenRouter (tool calling; безкоштовна `nvidia/nemotron-3.5-lightning:free`, бо ключ
безкоштовного рівня не викликає платні моделі) і `claude -p` через підписку Claude Code (**Claude Haiku
4.5**). Результат: Haiku 4.5 проходить усі шість сценаріїв за 2–4 виклики інструментів і 21–73 с, цитує
числа й причини довіри з резюме, чесно повідомляє про відсутню польську статтю, робить PDF на запит і
сама викликає `verify` на питання про ботів. Інструкції в `SKILL.md` доводились за транскриптами: перший
прогін безкоштовної моделі вигадував польські назви статей і плутав колонки — після двох правок став чистим.
Деталі й спостереження — [`eval/RESULTS.md`](wikipedia-interest/eval/RESULTS.md).

## Як я використовував AI і перевіряв його результат

Код написано з Claude Code за процесом: уточнення вимог → письмова спека → план із тестами → розробка
через тести (жоден модуль не писався без тесту, що падає) → два незалежних рев'ю свіжим агентом (знайдено
4 критичних і 9 важливих проблем, усі виправлені з тестом спочатку). Результат AI перевіряв: прогоном
тестів; ручною звіркою чисел з прямими запитами до API (uk «Астрономія», 2025‑03 = 1068 переглядів у
`data.csv` і в API); візуальним переглядом PDF; читанням транскриптів дешевих моделей рядок за рядком.
Спека, план і рішення — [`docs/process/`](wikipedia-interest/docs/process/).

## Обмеження

- Інтерес до статті ≠ готовність платити; це фільтр напрямів для подальшої перевірки.
- Перегляди залежать від існування та якості статті; відсутня чи слабка стаття ховає реальний інтерес.
- Фільтр ботів Wikimedia неідеальний — тому є `verify` з часткою ботів.
- Мовний розділ ≠ країна.
- Дані з 2015‑07; поточний місяць неповний і виключений; дані за минулий місяць з'являються за кілька днів.

## Roadmap: як розвивати далі

1. **Тема як кластер, а не одна стаття.** Wikidata `P31`/`P279` та категорії → набір статей (астрономія →
   планети, телескопи, космонавтика); сума `per_million` по кластеру знімає залежність від однієї назви.
2. **`discover` за класами Wikidata й категоріями**, а не лише за регулярними виразами.
3. **Великі обсяги.** Місячні дампи pageviews або Wikimedia Enterprise → Parquet + DuckDB; матриця 50 тем ×
   20 мов — один локальний запит; спільний кеш результатів для команди (Redis/S3) за канонічним ключем
   запиту і версією методики.
4. **Країни, а не мови.** `top-per-country`, щоб розділити іспаномовний розділ на Іспанію, Мексику, Аргентину.
5. **Зміни режиму та прогноз.** Change-point detection, STL-сезонність, екстраполяція з інтервалами.
6. **Багатосторінкові звіти, дашборд, моніторинг** з алертами про різкі зміни.
7. **Калібрування довіри** на розмічених минулих кейсах; оцінка в eval сильнішою моделлю замість regex.

## Ліцензія

MIT — [LICENSE](LICENSE).

---

## English summary

An [Agent Skill](https://agentskills.io/specification) that lets an AI agent help B2C founders decide which
topics to develop and which languages to launch in, from Wikipedia pageview statistics. Everything lives in
[`wikipedia-interest/`](wikipedia-interest/): `SKILL.md`, a Python CLI (`resolve`, `analyze`, `verify`,
`compare`, `discover`, `report`), references, tests, examples, the cheap-model eval harness and docs.

Key ideas: one pipeline command so a Haiku-class model needs 1–3 tool calls; interest measured as views per
million project views; spike-clipped growth with an explicit confidence level and reasons; `verify` re-measures
a conclusion on devices, bots, trimmed windows and a fresh API spot-check; SQLite cache makes follow-ups
instant; one-page PDF via reportlab. Tested with 114 offline + 3 live tests, the Agent Skills validator, and
end-to-end runs on Claude Haiku 4.5 (all six scenarios pass) and a free OpenRouter model — see
[`eval/RESULTS.md`](wikipedia-interest/eval/RESULTS.md).

```bash
cd wikipedia-interest
uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 36 --out runs/astro-uk
uv run scripts/wiki_interest.py verify  --run runs/astro-uk
uv run scripts/wiki_interest.py report  --run runs/astro-uk --title "Astronomy in Ukrainian Wikipedia" --notes "…" --lang en
```
