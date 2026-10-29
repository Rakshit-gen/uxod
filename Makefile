.PHONY: install test lint examples

install:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check uxod tests

examples:
	for f in examples/*.json; do .venv/bin/uxod replay $$f -o out/$$(basename $$f .json); done
