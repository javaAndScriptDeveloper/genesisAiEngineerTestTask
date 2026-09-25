# Transcript — 2-astro-uk
usage: {'prompt_tokens': 96374, 'completion_tokens': 1671}
score: {'matched': 2, 'expected': 3, 'tool_calls': 3, 'used_resolve': True, 'used_analyze': True, 'used_report': False, 'final_chars': 1311}

## user
Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню можна довіряти?

## assistant
Це чудова тема для аналізу! Я скористаюсь навичкою `wikipedia-interest`, щоб перевірити тренди перегляду астрономії в українській Wikipedia, оцінити зростання й надійність цих даних.

## assistant → Skill
```
{"skill": "wikipedia-interest", "args": "astronomy Ukrainian Wikipedia trustworthy growth"}
```

## tool result
```
Launching skill: wikipedia-interest
```

## assistant
Розпочну аналіз. Спочатку з'ясую, як називається стаття про астрономію в українській Wikipedia, потім проаналізую тренди.

## assistant → bash
```
cd /home/vampir/petProjects/genesisAiEngineerCourse/eval/.claude-workspace/.claude/skills/wikipedia-interest && uv run scripts/wiki_interest.py resolve --topic "astronomy" --langs uk
```

## tool result
```
topic: astronomy  →  Q333 «astronomy»
| lang | status | title | note |
|---|---|---|---|
| uk | found | Астрономія | Wikidata sitelink of Q333 |
other Wikidata candidates: Q752075 «Astronomy and Astrophysics» (scientific journal covering theoretical, observational, and instrumental astronomy and astrophysics); Q123958410 «Astronomy» (vocal track by Conan Gray; 2021 studio recording); Q3027134 «Astronomy Reports» (journal)
(use --qid to pick one)
```

## assistant → bash
```
cd /home/vampir/petProjects/genesisAiEngineerCourse/eval/.claude-workspace/.claude/skills/wikipedia-interest && uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 24 --out runs/astro-uk
```

## tool result
```
# astronomy — uk — 2024-09..2026-08 (24 monthly)
Resolved (Q333) astronomy: uk → «Астрономія»

| topic | lang | pm latest (3-mo avg) | pm year ago (3-mo avg) | YoY % (12m vs prior 12m) | growth/yr % (clipped) | spikes % | coverage % of window | confidence |
|---|---|---|---|---|---|---|---|---|
| astronomy | uk | 6.33 | 5.9 | -45.52 | -51.33 | 0 | 100 | high |

## Ranking (by volume: pm latest, i.e. current attention share)
1. astronomy|uk (6.33)
## Checks
- astronomy: resolved to Q333 «astronomy»; other candidates: Q752075 «Astronomy and Astrophysics» (scientific journal covering theoretical, observational, and instrumental astronomy and astrophysics); Q123958410 «Astronomy» (vocal track by Conan Gray; 2021 studio recording); Q3027134 «Astronomy Reports» (journal). Use --qid to switch.
- every row is declining → ranked by volume (current attention share) instead of score; a score ranking would only order declines and favour low-confidence ones. Use --rank-by growth to see which declines slowest.
- window 2024-09..2026-08 (24 monthly periods); current month excluded
- cache: 4 hits, 0 misses
- astronomy|uk: strongly seasonal (amplitude 2.86× the mean) — compare the same months across years, not adjacent months; 'pm latest' vs 'pm year ago' already does that
## Limitations
- Wikipedia interest is not willingness to pay; validate promising directions with real user research.
- Views depend on article existence and quality; a missing or poor article hides real interest.
- Bot filtering is imperfect; spikes can be automated traffic or news events.
- A language edition is not a country: readers of one language live in many markets.
## Suggested follow-ups
- `uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 48 --out runs/astro-uk-48m   # longer history`
- `uv run scripts/wiki_interest.py report --run runs/astro-uk --title "..." --notes "your 3-5 sentence recommendation"   # one-page PDF`
Files: runs/astro-uk/result.json, data.csv, chart.png
```

## assistant
Результати показують **не дуже оптимістичну картину** для астрономії в українській Wikipedia:

## Основні знахідки

**Інтерес знижується, а не зростає:**
- **YoY зміна:** -45,52% (останні 12 місяців проти попередніх 12 місяців)
- **Середня кількість переглядів:** 6,33 на мільйон переглядів проекту (останні 3 місяці)
- Порівняно з роком тому: 5,9 на мільйон

**Надійність цього висновку: ВИСОКА** ✓
- Дані покривають всі 24 місяці вікна (100% покриття)
- Немає викидів або новинних сплесків (0% спайків)
- Стійкий сезонний паттерн (передбачуваний)
- Чітка тенденція до зниження

## Контекст

Стаття добре знаходиться в українській Wikipedia (існує як "Астрономія"), але читачів до неї дивиться все менше. Це може означати:
- Загальна втрата інтересу до основної тематики
- Конкуренцію з інших джерел контенту
- Миграцію аудиторії на інші платформи

## Рекомендація

**З позиції Wikipedia: астрономія не показує зростаючого попиту.** Прискорювати розробку курсу на основі цих трендів не рекомендується. Замість цього варто:

1. Провести прямий опит цільової аудиторії (чи насправді люди цікавляться астрономією?)
2. Перевірити попит через пошукові системи або соціальні медіа
3. Порівняти з іншими темами в українській Wikipedia, щоб знайти зростаючі інтереси

Чи хочете проаналізувати інші теми для порівняння?
