# 01 · Керовані припущення — `--access`, `--agent`, `--spike-z`

## Що робить
`analyze` за замовчуванням рахує **людський трафік** (`agent=user`) з **усіх пристроїв** (`all-access`)
і вважає піком період із робастним z > 3.5. Три флаги дозволяють змінити ці припущення, не змінюючи
код:

| Флаг | Значення | Навіщо |
|---|---|---|
| `--access` | `all-access` (типово), `desktop`, `mobile-web`, `mobile-app` | інтерес мобільної аудиторії ≠ десктопної; для мобільного застосунку важливіше перше |
| `--agent` | `user` (типово), `all-agents`, `spider`, `automated` | порівняти з «усім трафіком» і побачити частку ботів; або навпаки — вивчити саме ботів |
| `--spike-z` | число > 0 (типово 3.5) | суворіше/м'якше вирізання піків, якщо тема новинна або, навпаки, дуже рівна |

Змінені припущення **потрапляють у розділ Assumptions** резюме, `result.json` (`options`) і PDF —
висновок ніколи не виглядає як «типовий», якщо він отриманий на інших параметрах. Кеш відповідей
розрізняє їх автоматично (інша URL), а `--out` за замовчуванням отримує суфікс, напр. `…-mobile-web-user`.

## Навіщо
Завдання прямо каже: користувачі «можуть уточнювати запити й змінювати припущення після першої
відповіді». Найчастіші уточнення засновника: «а на мобільних?», «а це не боти?», «а якщо не вирізати
піки?». Кожне — один повторний виклик `analyze` з флагом, секунди завдяки кешу.

## Як користуватись
```bash
# мобільна аудиторія
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --access mobile-web --out runs/astro-uk-mobile
# весь трафік, щоб оцінити частку ботів (порівняйте з базовим запуском або запустіть verify)
uv run scripts/wiki_interest.py analyze --topic "астрономія" --langs uk --agent all-agents --out runs/astro-uk-allagents
# м'якше вирізання піків
uv run scripts/wiki_interest.py analyze --topic "Bitcoin" --langs uk,pl --spike-z 2.5 --out runs/btc
```
Агент: якщо користувач згадує пристрої, ботів або просить «не викидати піки» — додати відповідний флаг
і в відповіді назвати змінене припущення.

## Як перевірено
- `test_per_article_and_aggregate_accept_access_and_agent` — параметри потрапляють у правильні URL API.
- `test_fetch_series_and_totals_pass_access_and_agent_into_urls` — і ряд статті, і нормалізатор
  розділу беруться з того самого зрізу трафіку (інакше «на мільйон» було б некоректним).
- `test_spike_threshold_can_be_overridden` — поріг змінює набір піків.
- `test_assumptions_reflect_access_agent_and_spike_overrides` — Assumptions і `options` у JSON відображають зміни.
- `test_analyze_rejects_bad_access_value`, `test_access_and_agent_values_are_validated` — помилкові
  значення → exit 3 з переліком дозволених.
