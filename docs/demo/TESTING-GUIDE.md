# Як перевірити навичку руками: промпти, очікування, артефакти

## 1. Промпти для агента (Claude Code з навичкою, `claude --model haiku`)

Кожний промпт — що агент має зробити і що має бути у відповіді. Якщо чогось нема — це знахідка.

| # | Промпт | Очікувані команди | У відповіді має бути |
|---|---|---|---|
| A1 | Чи зростає інтерес до астрономії в україномовній Wikipedia, і наскільки цьому можна довіряти? | `analyze` (можливо `resolve` перед) | «на мільйон», ріст −4x %/рік, довіра high + причини, згадка сезонності |
| A2 | Порівняй інтерес до інтервального голодування в польській і чеській Wikipedia за 2 роки. | `resolve` → `analyze --langs pl,cs` | pl: статті немає, кандидати не використані; cs: 2.1 vs 4.5 на млн, довіра |
| A3 | Ми робимо застосунок для вивчення мов. Порівняй інтерес до англійської в pl, cs, uk, de і скажи, які аудиторії досліджувати першими. Зроби PDF. | `analyze` → `report` | таблиця по мовах, uk ≈107 на млн, «усі падають → рейтинг за обсягом», шлях до `report.pdf` |
| A4 (після A3) | Тепер додай іспанську і візьми лише 12 місяців. Що змінилось? | `analyze` (нові флаги) → бажано `compare` | Δ по рядках; для pl/cs довіра high→low через коротке вікно |
| A5 (після A1) | А це не боти? Може, тільки мобільні читачі? Перевір. | `verify` | вердикт robust/mixed/fragile, десктоп vs мобільні, % ботів, контрольна перевірка |
| A6 | Що зараз росте в українській Wikipedia в темах науки й освіти? Це стійкий інтерес чи разова увага? | `discover --include … --sustained` | список кандидатів, для кожного 24-місячний ріст і довіра; чесне «топ — це увага» |
| A7 | Порівняй інтерес до біткоїна в uk і pl лише на мобільних. | `analyze --access mobile-web` | у відповіді названо змінене припущення (мобільні) |
| A8 | Чи є інтерес до «Diablo IV» у чеській Wikipedia? | `resolve` → `analyze` | коректна назва статті через Wikidata; якщо статті нема — MISSING без вигадок |
| A9 | Порівняй астрономію в укр і чеській Wikipedia (свідомо: «cz»). | агент має використати `cs` | якщо передасть `cz` — CLI поверне підказку «Czech is cs», агент виправиться |
| A10 | Наскільки популярна головна сторінка англійської Wikipedia? | `analyze` | працює, але агент має сказати, що це не тема, а службова сторінка (обмеження) |

Червоні прапорці у відповідях агента: число, якого нема в `summary.md`; «довіра висока» без причин; вигадана назва статті для відсутньої мови; порівняння сирих переглядів між мовами; PDF «збережено» без шляху.

## 2. Що дивитись у артефактах після `analyze --out runs/<slug>`

```
runs/<slug>/
├── summary.md    ← те, що читає агент. Перевір: рядок Resolved, таблиця, Reasons, Checks, Limitations
├── result.json   ← повні дані. Ключі: resolutions, series[], metrics{}, ranking, checks, assumptions, options
├── data.csv      ← довгий формат: topic,lang,title,period,views,project_views,per_million
├── chart.png     ← лінії per-million, трикутники = піки, пунктир = очищений тренд
├── verify.md/json    (після verify)
├── compare.md/json   (після compare, у папці другого запуску)
└── report.pdf        (після report)
```

### Швидкі перевірки правильності
1. **Нормалізація.** Візьми рядок з `data.csv`: `per_million == views / project_views * 1e6` (точність 4 знаки).
   ```bash
   awk -F, 'NR>1 && $6>0 {d=$5/$6*1e6-$7; if (d>0.001||d<-0.001) print "MISMATCH", $0}' runs/astro-uk/data.csv
   ```
2. **Сирі перегляди збігаються з API.** Один місяць напряму:
   ```bash
   curl -s -H "User-Agent: test" "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/uk.wikipedia/all-access/user/%D0%90%D1%81%D1%82%D1%80%D0%BE%D0%BD%D0%BE%D0%BC%D1%96%D1%8F/monthly/20250301/20250331" | python3 -m json.tool | grep views
   grep ",2025-03," runs/astro-uk/data.csv
   ```
   Або в браузері — офіційний інструмент Wikimedia: `https://pageviews.wmcloud.org/?project=uk.wikipedia.org&agent=user&pages=Астрономія` — ті самі місячні числа.
3. **YoY руками.** У `data.csv` середнє `per_million` за останні 12 місяців проти попередніх 12 → має збігатись з `yoy_pct` у `result.json` (`metrics.<topic|lang>.yoy_pct`).
4. **pm latest.** Середнє `per_million` за останні 3 місяці = `pm_latest`.
5. **Піки.** `metrics.<key>.spike_periods` → у `chart.png` на цих місяцях трикутники; у `data.csv` ці місяці візуально вище сусідів.
6. **Довіра.** `metrics.<key>.confidence` і `reasons` — кожна причина має відповідати числу в тій самій метриці (наприклад, `coverage 50% < 70%` ↔ `coverage_pct: 50`).
7. **Припущення.** Якщо запуск був з `--access mobile-web`, у `result.json → options` і в `assumptions[0]` це написано; у PDF — у футері.
8. **PDF.** Одна сторінка: `python3 -c "import pypdf;print(len(pypdf.PdfReader('runs/astro-uk/report.pdf').pages))"` → `1`.

### Кеш
```bash
sqlite3 wikipedia-interest/.cache/cache.sqlite "select count(*), sum(ttl_until is null) as permanent from responses;"
sqlite3 wikipedia-interest/.cache/cache.sqlite "select url from responses where url like '%per-article%' limit 3;"
```
Повторний `analyze` з тими ж параметрами має показати в Checks `cache: N hits, 0 misses`. Поточний або ще
не опублікований місяць не має бути `permanent` (перевірка `test_is_closed_waits_for_wikimedia_to_load_the_month`).

## 3. Що дивитись у транскриптах eval (`eval/transcripts/claude-code-haiku/*.md`)

- `## assistant → bash` — точна команда, яку викликала модель. Прапорці: вигадані `--titles`, неіснуючі флаги, повторні `analyze` з варіаціями.
- `## tool result` — те, що бачила модель. Числа у фінальній відповіді мають бути звідси.
- Рядок `score:` — `matched/expected`, `tool_calls`, `used_resolve/analyze/report`. Норма: 2–4 виклики.
- `usage:` — токени. Для Claude Code вхідні включають cache reads, тому великі; порівнювати між раннерами не варто.

## 4. Негативні перевірки (мають ламатись правильно)

| Команда | Очікування |
|---|---|
| `analyze --topic x --langs cz` | exit 3, «Czech is cs» |
| `analyze --topic x --langs uk --start 2026-08 --end 2026-01` | exit 3, «start … is after end» |
| `analyze --topic "zzzqqq" --langs uk` | exit 2, «no usable series», `summary.md` все одно записано |
| `report --run runs/nope` | exit 3, «run analyze … first» |
| `discover --lang xx` | exit 3, підказка про код мови |
| `discover --lang uk --include "("` | exit 3, «bad regular expression» |
| `analyze … --access mobile` | exit 3, перелік дозволених значень |

## 5. Автоматика (доказ для рев'юера)
```bash
cd wikipedia-interest && uv run pytest -q && uv run pytest -m network -q
cd .. && uvx --from skills-ref agentskills validate wikipedia-interest
cd eval && uv run pytest -q && uv run run_eval.py --runner claude-code --model haiku
```
