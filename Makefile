# Convenience targets for reviewers. Everything runs from the skill directory via uv.
SKILL := wikipedia-interest
RUN   := cd $(SKILL) && uv run scripts/wiki_interest.py

.PHONY: help setup test test-live lint validate eval eval-tests smoke demo clean

help:            ## show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*##' '{printf "  %-12s %s\n", $$1, $$2}'

setup:           ## create the venv from uv.lock
	cd $(SKILL) && uv sync --frozen

test:            ## offline unit tests (HTTP mocked)
	cd $(SKILL) && uv run pytest -q

test-live:       ## the three task queries against the real Wikimedia API
	cd $(SKILL) && uv run pytest -m network -q

lint:            ## ruff lint + format check
	cd $(SKILL) && uvx ruff check . && uvx ruff format --check wiki_interest scripts tests eval

validate:        ## Agent Skills spec validator
	uvx --from skills-ref agentskills validate $(SKILL)

eval-tests:      ## tests of the eval harness itself
	cd $(SKILL)/eval && uv run pytest -q

eval:            ## run all six scenarios on Claude Haiku 4.5 via the local claude CLI
	cd $(SKILL)/eval && uv run run_eval.py --runner claude-code --model haiku

smoke:           ## report + compare on the shipped examples (no network)
	$(RUN) report --run examples/02-astronomy-uk --title "Smoke" --notes "smoke" --lang uk --out /tmp/wi-smoke
	$(RUN) compare --runs examples/03-english-multi examples/03b-english-12m --out /tmp/wi-smoke
	@echo "artifacts in /tmp/wi-smoke"

demo:            ## the task's first example end to end (network)
	$(RUN) resolve --topic "intermittent fasting" --langs pl,cs
	$(RUN) analyze --topic "intermittent fasting" --langs pl,cs --months 24 --out runs/demo
	$(RUN) verify  --run runs/demo

clean:           ## remove caches, runs and venvs
	rm -rf $(SKILL)/.cache $(SKILL)/runs $(SKILL)/.venv $(SKILL)/eval/.venv $(SKILL)/eval/.claude-workspace
