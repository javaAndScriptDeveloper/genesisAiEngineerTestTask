# 05 · Пакетний режим — `--topics-file`, матриці тем × мов

## Що робить
`analyze` завжди вмів `--topics "a;b;c"`. `--topics-file topics.txt` (одна тема на рядок, `#` — коментар,
дублікати й порожні рядки відкидаються) дозволяє задавати десятки тем без командного рядка з крапками з
комою. Разом з `--langs` це матриця тем × мов за один виклик: один `result.json`, один `data.csv` у
довгому форматі (готовий для pandas/DuckDB), графік у форматі small multiples, рейтинг по всій матриці.

## Навіщо
Завдання просить пояснити, як розвивати навичку для **складніших досліджень і більших обсягів даних**.
Перший практичний крок — не переписувати сховище, а дати агентові й людині зручний спосіб задати велику
матрицю й отримати один артефакт. Кеш робить повторний прогін матриці 20 × 5 справою секунд; резюме
обрізається до 40 рядків з підказкою дивитись `result.json`, тому контекст агента не роздувається.

## Як користуватись
```bash
cat > topics.txt <<'T'
# освітні теми для перевірки
astronomy
chemistry
mathematics
programming
T
uv run scripts/wiki_interest.py analyze --topics-file topics.txt --langs uk,pl,cs,de,es --months 24 --out runs/edu-matrix
```
Далі — звичайні кроки: `verify --run runs/edu-matrix` для стійкості, `report --run …` для PDF, або
`data.csv` у будь-який інструмент аналітики. Наступні кроки масштабування (Parquet + DuckDB, дампи) описані
в roadmap README.

## Дрібні виправлення, що увійшли в цей самий крок
- `--titles` для мови, якої нема в `--langs`, і `--qid` при кількох темах більше не ігноруються мовчки —
  попередження в stderr.
- `--no-cache` показує чесний рядок `cache: 0 hits, N fetched fresh (reads bypassed)` замість `0 hits, 0 misses`.
- Кеш SQLite у режимі WAL з таймаутом 30 с — кілька агентів або прогонів eval можуть ділити один кеш.
- Не-JSON відповідь API (сторінка обслуговування) → зрозуміла `ApiError`, а не traceback.
- Теми письмом поза латиницею/кирилицею отримують читабельний slug `topic-<hash>`, а не порожній.

## Як перевірено
`test_topics_file_batch_mode`, `test_topics_file_empty_exit_3`, `test_ignored_inputs_are_warned_on_stderr`,
`test_no_cache_still_counts_misses`, `test_slug_falls_back_for_non_alphabetic_topics`,
`test_non_json_200_becomes_api_error`, `test_cache_uses_wal_and_busy_timeout`, `test_cache_bypass_reads_counts_misses`.
