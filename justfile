install-uv:
    #!/usr/bin/env bash
    if ! command -v uv &> /dev/null; then
        echo "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

install: install-uv
    @echo "-----------------------------------"
    @echo "- Installing dependencies -"
    @echo "-----------------------------------"
    uv sync

sync: install-uv
    @echo "-----------------------------------"
    @echo "- Syncing and upgrading dependencies -"
    @echo "-----------------------------------"
    uv sync --upgrade

format: install-uv
    @echo "-----------------------------------"
    @echo "- Formatting code -"
    @echo "-----------------------------------"
    uv run ruff format src tests

lint: install-uv
    @echo "-----------------------------------"
    @echo "- Linting code -"
    @echo "-----------------------------------"
    uv run ruff check --fix src tests

typecheck: install-uv
    @echo "-----------------------------------"
    @echo "- Running type checker -"
    @echo "-----------------------------------"
    uv run ty check

test: install-uv
    @echo "-----------------------------------"
    @echo "- Running tests -"
    @echo "-----------------------------------"
    PYTHONPATH=src uv run python -m pytest tests -v

test-cov: install-uv
    @echo "-----------------------------------"
    @echo "- Running tests with coverage -"
    @echo "-----------------------------------"
    PYTHONPATH=src uv run python -m pytest tests --cov=fellowship_recorder --cov-report=term-missing --cov-report=html

check: lint typecheck test

clean:
    @echo "-----------------------------------"
    @echo "- Cleaning build artifacts -"
    @echo "-----------------------------------"
    rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache htmlcov .coverage
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
