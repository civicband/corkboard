# CivicBand Development Commands
# Uses uv for package management and project tooling

# Default recipe - show available commands
default:
    @just --list

# Install all dependencies (including dev)
install:
    uv sync --all-extras

# Sync dependencies from lock file
sync:
    uv sync --all-extras

# Run all tests
test:
    python -m pytest

# Run tests with coverage report
test-cov:
    python -m pytest --cov=django_plugins --cov=plugins --cov=pages --cov=config --cov=scripts --cov-report=term-missing --cov-report=html

# Run specific test file
test-file file:
    python -m pytest {{file}}

# Run tests matching a pattern
test-match pattern:
    python -m pytest -k {{pattern}}

# Lint code with ruff
lint:
    ruff check .

# Auto-fix linting issues
lint-fix:
    ruff check --fix .

# Format code with ruff
format:
    ruff format .

# Check formatting without making changes
format-check:
    ruff format --check .

# Run all quality checks (lint, format-check, test)
check: lint format-check test

# Install pre-commit hooks
hooks:
    pre-commit install
    pre-commit install --hook-type pre-push

# Run pre-commit hooks on all files
hooks-run:
    pre-commit run --all-files

# Run Django development server
serve:
    python manage.py runserver

# Run Django development server on specific port
serve-port port:
    python manage.py runserver {{port}}

# Run Django migrations
migrate:
    python manage.py migrate

# Create Django migrations
makemigrations:
    python manage.py makemigrations

# Open Django shell
shell:
    python manage.py shell

# Run Docker development environment
docker-up:
    docker-compose up

# Run Docker in detached mode
docker-up-d:
    docker-compose up -d

# Stop Docker containers
docker-down:
    docker-compose down

# View Docker logs
docker-logs:
    docker-compose logs -f

# Blue/green deployment changeover
deploy:
    ./changeover.sh

# Clean Python cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    find . -type f -name "*.pyo" -delete
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    rm -rf htmlcov/

# Deep clean (includes .venv)
clean-all: clean
    rm -rf .venv/

# Setup development environment from scratch
setup:
    uv sync --all-extras
    python manage.py migrate
    just hooks
    @echo ""
    @echo "✅ Development environment ready!"
    @echo "Run 'just serve' to start the Django development server"

# Run analytics retrieval script
analytics-retrieve days="7":
    python scripts/retrieve_umami_analytics.py --days {{days}} --events

# Run analytics retrieval with summary
analytics-summary days="7":
    python scripts/retrieve_umami_analytics.py --days {{days}} --events --summary

# View analytics database with datasette
analytics-view:
    datasette analytics/umami_events.db --metadata analytics-metadata.json

# Update dependencies in lock file
update:
    uv lock --upgrade

# Show outdated dependencies
outdated:
    uv pip list --outdated

# Run security audit (if safety is installed)
audit:
    uv pip list --format=json | python -c "import sys, json; print('\n'.join([p['name'] + '==' + p['version'] for p in json.load(sys.stdin)]))" | safety check --stdin
