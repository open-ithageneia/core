.DEFAULT_GOAL := help

.PHONY: help lint fix lint-python lint-js fix-python fix-js

help:
	@echo "Targets:"
	@echo "  make lint        Run Python (Ruff) + JS/TS (Biome) checks"
	@echo "  make fix         Auto-fix Python (Ruff) + JS/TS (Biome)"
	@echo "  make lint-python Run Ruff checks only"
	@echo "  make lint-js     Run Biome lint only"
	@echo "  make fix-python  Auto-fix Ruff + format"
	@echo "  make fix-js      Auto-fix Biome (check --write)"

lint: lint-python lint-js

fix: fix-python fix-js

lint-python:
	uv run ruff check .

fix-python:
	uv run ruff check --fix .
	uv run ruff format .

lint-js:
	npm run lint

fix-js:
	npm run biome:fixall
