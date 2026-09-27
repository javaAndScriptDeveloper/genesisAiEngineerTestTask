# 06 · Оцінка на дешевій моделі — `eval/run_eval.py`

## Що робить
Харнес дає моделі `SKILL.md` як системний промпт і два інструменти (`bash` у каталозі навички,
`read_file` лише всередині навички), проганяє сценарії з `eval/prompts.json` (три запити із завдання,
уточнення до третього, «перевір, чи це не боти» для `verify`, «що росте в науці» для `discover`) і для
кожного зберігає транскрипт (`eval/transcripts/<runner>/…md`) та рядок рубрики в `eval/RESULTS.md`:
скільки очікувань закрито (regex по фінальній відповіді), кількість викликів інструментів, чи використано
`resolve`/`analyze`/`report`, токени, час.

Два раннери:
- **`--runner openrouter --model <id>`** — OpenRouter chat completions з tool calling. Безкоштовні моделі
  (`nvidia/nemotron-3.5-lightning:free`) працюють, але повільно (30–120 с на виклик) і нестабільно; харнес
  чекає 429/5xx з довгими паузами й один раз «підштовхує» модель, якщо вона повернула порожню відповідь.
- **`--runner claude-code --model haiku`** — локальний `claude -p` (підписка Claude Code): навичка
  підключається символічним посиланням у `.claude/skills/` тимчасового проєкту, події `stream-json`
  перетворюються у ті самі структури, що й у OpenRouter, тож рубрика й транскрипти ідентичні за формою.
  Haiku 4.5 проходить сценарій за 26–60 с на запит. Це відповідь на вимогу завдання «перевір повний
  сценарій на швидкій недорогій моделі».

## Навіщо
Рубрика — не самоціль: кожна зміна `SKILL.md` у цьому проєкті прийшла з **читання транскриптів**.
Перший прогін показав вигадані польські назви, URL-кодовані `--titles`, плутанину «pm latest = 30 днів» і
пропущений PDF; другий — що виправлення змусило модель зупинятись і питати дозвіл; третій — що після
правок дешева модель робить 2–4 виклики й цитує причини довіри. Це і є «як я перевіряв результат AI».

## Як користуватись
```bash
cp .env.example .env                                   # OPENROUTER_API_KEY, якщо потрібен OpenRouter
cd eval && uv run pytest -q                            # 10 офлайн-тестів харнесу
uv run run_eval.py --runner claude-code --model haiku  # усі сценарії на Haiku 4.5 (хвилини)
uv run run_eval.py --runner claude-code --model haiku --prompt-id 5-verify
uv run run_eval.py --model nvidia/nemotron-3.5-lightning:free  # безкоштовна модель через OpenRouter
```
Читайте транскрипти, не лише таблицю: регулярні вирази ловлять слова, а не істину.

## Як перевірено
- `test_bash_runs_in_skill_dir`, `test_read_file_blocks_escape`, `test_score_counts_expectations_and_tool_calls`,
  `test_chat_explains_402_and_retries_429`, `test_chat_retries_error_codes_inside_200_body`,
  `test_empty_final_answer_gets_one_nudge`, `test_claude_events_become_openai_shaped_messages`,
  `test_claude_events_map_read_and_other_tools`, `test_claude_cmd_builds_resumable_command`.
- Реальні прогони: Nemotron (free) — 4 ітерації; Haiku 4.5 — повний сценарій; усе в `eval/RESULTS.md`.

## Що це не є
`bash` у харнесі виконується без пісочниці — команди моделі працюють локально. Запускайте лише з моделями,
яким довіряєте, і не з правами, яких шкода.
