# Contributing

Small project, simple rules.

- **Run everything from `wikipedia-interest/` with `uv`.** `make setup && make test` is the whole loop; `make help` lists the rest.
- **Tests first.** Every behaviour change starts with a failing test in `wikipedia-interest/tests/` (HTTP is mocked with respx; no test may hit the network unless marked `@pytest.mark.network`).
- **Thresholds live in one place.** `stats.THRESHOLDS` and `verify.THRESHOLDS`; `references/methodology.md` must mention the same numbers — a test enforces it.
- **The agent reads `SKILL.md`.** Keep it under 150 lines, define every column and flag you mention, and change it only after reading an eval transcript that shows why (`make eval`, then `eval/transcripts/`).
- **Lint:** `make lint` (ruff, 140 columns). CI runs lint, tests on 3.12/3.13, the Agent Skills validator and an offline smoke.
- **Releases:** bump `version` in `SKILL.md` and `pyproject.toml`, add a CHANGELOG entry, tag `vX.Y.Z`; the release workflow builds the skill archive and publishes it.
- **Commits** explain why, not what.
