# Transcript — 2-astro-uk
usage: {'prompt_tokens': 7128, 'completion_tokens': 1622}
score: {'matched': 3, 'expected': 3, 'tool_calls': 2, 'used_resolve': True, 'used_analyze': True, 'used_report': False, 'final_chars': 2625}

## system
(SKILL.md as system prompt — omitted)

## user
Ми думаємо додати курс з астрономії до освітнього застосунку. Чи зростає інтерес до цієї теми в україномовній Wikipedia, і наскільки цьому зростанню можна довіряти?

## assistant → bash
```
uv run scripts/wiki_interest.py resolve --topic "astronomy" --langs uk
```

## tool result
```
topic: astronomy  →  Q333 «astronomy»
| lang | status | title | note |
|---|---|---|---|
| uk | found | Астрономія | Wikidata sitelink of Q333 |
other Wikidata candidates: Q752075 «Astronomy and Astrophysics» (scientific journal covering theoretical, observational, and instrumental astronomy and astrophysics); Q123958410 «Astronomy» (vocal track by Conan Gray; 2021 studio recording); Q3027134 «Astronomy Reports» (journal)
(use --qid to pick one)

[stderr]
warning: `VIRTUAL_ENV=/home/vampir/petProjects/genesisAiEngineerCourse/eval/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## assistant → bash
```
uv run scripts/wiki_interest.py analyze --topic "astronomy" --langs uk --months 24 --out runs/astro-uk
```

## tool result
```
# astronomy — uk — 2024-09..2026-08 (24 monthly)
Resolved (Q333) astronomy: uk → «Астрономія»

| topic | lang | pm latest | pm year ago | YoY % | growth/yr % (clipped) | spikes % | coverage % | confidence |
|---|---|---|---|---|---|---|---|---|
| astronomy | uk | 6.33 | 5.9 | -45.52 | -49.02 | 0 | 100 | high |

## Ranking (by score; score = clipped growth × confidence weight high 1.0 / medium 0.6 / low 0.25)
1. astronomy|uk (-49.02)
## Checks
- astronomy: resolved to Q333 «astronomy»; other candidates: Q752075 «Astronomy and Astrophysics» (scientific journal covering theoretical, observational, and instrumental astronomy and astrophysics); Q123958410 «Astronomy» (vocal track by Conan Gray; 2021 studio recording); Q3027134 «Astronomy Reports» (journal). Use --qid to switch.
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


[stderr]
warning: `VIRTUAL_ENV=/home/vampir/petProjects/genesisAiEngineerCourse/eval/.venv` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
```

## assistant
**Коротка відповідь**

Інтерес до теми «астрономія» в українській Вікіпедії **зменшується**. За останні 24 місяці (2024‑09 → 2026‑08) показник «переглядів на мільйон переглядів проекту» (pm) змінився з 5,9 на 6,33, але **скорочення clipped на рік становить –49,02 %**. Точність оцінки — **вища** (high confidence).

**Числові дані (за 24 місяці)**

| Мережа | pm (останній місяць) | pm (рік тому) | YoY % | Clipped growth/yr % | Spikes % | Coverage % | Confidence |
|--------|----------------------|----------------|-------|----------------------|----------|------------|------------|
| Українська Вікіпедія (астрономія) | **6,33** | **5,9** | –45,52 % | **–49,02 %** | 0 % | 100 % | **high** |

**Чому можна довіряти цьому висновку?**

1. **Coverage 100 %** — стаття «Астрономія» існувала у вікно аналізу, немає інфляції зростання через відсутність статті.
2. **Spikes 0 %** — не виявлено різких піків, що свідчить про те, що падіння не спричинене однією новиною або подією.
3. **Confidence high** — оцінка базується на стабільності часу та наявності всіх даних.

**Ограничення, які варто пам’ятати**

- Вікіпедійний трафік не є прямого показника готовності платити, тому результат краще перевіряти реальним дослідженням користувачів.
- Дані мають **seasonal (seasonal) характер** — амплітудаseasonality становить 2,86× середнього. Спочатку порівнюйте *одні й ті самі місяці* у різних роках, а не сусідні місяці.
- «Мова» не є «країною»: читачі української Вікіпедії розподілені по різних країнах, тому це не country‑level дані.
- Аналіз охоплює період з 2015‑07, але у нашому випадку використовуються останні 24 місяці.

**Що можна зроби далі?**

- Продовжити історію (`--months 48`), щоб побачити, чи є тренд довгостроковим або лише короткостроковим флуктуацією.
- Порівняти інтерес з іншими мовами (наприклад, `pl, cs, de`), щоб розібрати, чи є падіння унікальним для української або загальнобудівним.
- Згенерувати односторінковий PDF‑звіт (`report`), якщо потрібно поділитися результатами з командою.

**Рекомендація (3‑5 речень)**

Інтерес до астрономії в українській Вікіпедії зменшується з clipped‑ростом –49 % на рік, що має високу довіру (high confidence), оскільки стаття існувала повністю, а піків немає. Це може свідчити про спад спокуси аудиторії або про сезонність, тому перед додаванням курсу до застосунку варто перевірити, чи не є падіння тимчасовим, та зібрати додаткові дані про поведінку користувачів у власному продукті. Якщо планується запуск на українській аудиторії, рекомендується протестувати контент з групою реальних користувачів, щоб підтвердити, чи відповідає цей тренд їхній реальній потребі.
