# CivicBand Corkboard Development Commands
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
test *args:
    uv run pytest {{args}}

# Run tests with coverage report
test-cov:
    uv run pytest --cov=django_plugins --cov=plugins --cov=pages --cov=config --cov=scripts --cov-report=term-missing --cov-report=html

# Run specific test file
test-file file:
    uv run pytest {{file}}

# Run tests matching a pattern
test-match pattern:
    uv run pytest -k {{pattern}}

# Lint code with ruff
lint:
    uv run ruff check .

# Auto-fix linting issues
lint-fix:
    uv run ruff check --fix .

# Alias for lint-fix (matches civic-observer)
ruff:
    uv run ruff check . --fix

# Format code with ruff
format:
    uv run ruff format .

# Check formatting without making changes
format-check:
    uv run ruff format --check .

# Run type checking with mypy
mypy:
    uv run mypy .

# Run all quality checks (lint, format-check, test)
check: lint format-check test

# Install pre-commit hooks
hooks:
    uv run pre-commit install
    uv run pre-commit install --hook-type pre-push

# Run pre-commit hooks on all files
hooks-run:
    uv run pre-commit run --all-files

# Run Django development server
serve:
    uv run python manage.py runserver

# Run Django development server on specific port
serve-port port:
    uv run python manage.py runserver {{port}}

# Run Django migrations
migrate:
    uv run python manage.py migrate

# Create Django migrations
makemigrations:
    uv run python manage.py makemigrations

# Open Django shell
shell:
    uv run python manage.py shell

# Run Django management command
manage *args:
    uv run python manage.py {{args}}

# Start development environment (Redis + Django dev server)
dev:
    @echo "Starting development environment..."
    docker compose up -d redis
    @echo "Waiting for Redis to be ready..."
    @sleep 2
    @echo "Redis ready. Starting Django dev server..."
    DEBUG=true REDIS_URL=redis://localhost:6379 uv run python manage.py runserver

# Start full Docker stack (all services)
dev-docker:
    docker compose up django_blue redis

# Run Docker development environment
docker-up:
    docker compose up

# Run Docker in detached mode
docker-up-d:
    docker compose up -d

# Stop Docker containers
docker-down:
    docker compose down

# View Docker logs
docker-logs:
    docker compose logs -f

# Start just Redis for local development
redis:
    docker compose up -d redis

# Stop Redis
redis-down:
    docker compose stop redis

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
    uv run python manage.py migrate
    just hooks
    @echo ""
    @echo "✅ Development environment ready!"
    @echo "Run 'just serve' to start the Django development server"

# Run analytics retrieval script
analytics-retrieve days="7":
    uv run python scripts/retrieve_umami_analytics.py --days {{days}} --events

# Run analytics retrieval with summary
analytics-summary days="7":
    uv run python scripts/retrieve_umami_analytics.py --days {{days}} --events --summary

# View analytics database with datasette
analytics-view:
    uv run datasette analytics/umami_events.db --metadata analytics-metadata.json

# Update dependencies in lock file
update:
    uv lock --upgrade

# Show outdated dependencies
outdated:
    uv pip list --outdated

# Run security audit
audit:
    uv pip list --format=json | uv run python -c "import sys, json; print('\n'.join([p['name'] + '==' + p['version'] for p in json.load(sys.stdin)]))" | uv run safety check --stdin
