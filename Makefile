PY := .venv/bin/python
PKG := snowmcp

# The mutation-score floor. Raise it as survivors are closed; never lower it.
MIN_MUTATION_SCORE ?= 80

.PHONY: setup test unit integration qa coverage mutation gate clean install

setup:
	uv venv --python 3.12 .venv
	uv pip install --python .venv/bin/python -e ".[dev]" || uv pip install --python .venv/bin/python "mcp>=2.0" pytest pytest-cov pytest-asyncio mutmut hypothesis

install:
	uv pip install --python .venv/bin/python -e .

test:
	$(PY) -m pytest tests/ -q

unit:
	$(PY) -m pytest tests/unit -q

integration:
	$(PY) -m pytest tests/integration -q

qa:
	$(PY) -m pytest tests/qa -q

coverage:
	$(PY) -m pytest tests/ -q --cov=$(PKG) --cov-branch --cov-report=term-missing --cov-fail-under=100

mutation:
	rm -rf mutants
	PYTHONPATH=src .venv/bin/mutmut run
	.venv/bin/mutmut results
	$(PY) scripts/mutation_gate.py --min-score $(MIN_MUTATION_SCORE)

gate: coverage mutation

clean:
	rm -rf mutants .coverage .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
