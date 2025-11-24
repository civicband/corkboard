# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CivicBand is a Django + Datasette hybrid application that provides government and municipality meeting data through a web interface. The application uses a unique subdomain-based architecture where different municipalities access their data through dedicated subdomains.

## Development Commands

We use `just` as our command runner. Run `just` without arguments to see all available commands.

### Environment Setup
```bash
# Full development setup (install dependencies, run migrations, install hooks)
just setup

# Install dependencies only
just install

# Install pre-commit hooks
just hooks
```

### Testing
```bash
# Run all tests
just test

# Run tests with coverage report
just test-cov

# Run specific test file
just test-file tests/test_datasette_by_subdomain.py

# Run tests matching a pattern
just test-match "subdomain"
```

### Code Quality
```bash
# Run all quality checks (lint, format check, tests)
just check

# Run linting
just lint

# Auto-fix linting issues
just lint-fix

# Format code
just format

# Check formatting without changes
just format-check

# Run pre-commit hooks on all files
just hooks-run
```

### Development Server
```bash
# Django development server
just serve

# Django development server on custom port
just serve-port 8080

# Docker development environment
just docker-up

# Docker in detached mode
just docker-up-d

# View Docker logs
just docker-logs

# Stop Docker containers
just docker-down
```

### Database Management
```bash
# Run Django migrations
just migrate

# Create Django migrations
just makemigrations

# Open Django shell
just shell
```

### Analytics
```bash
# Retrieve analytics data (last 7 days)
just analytics-retrieve

# Retrieve analytics with summary
just analytics-summary

# View analytics database
just analytics-view
```

### Maintenance
```bash
# Clean Python cache files
just clean

# Deep clean (includes .venv)
just clean-all

# Update dependencies
just update

# Check for outdated dependencies
just outdated
```

### Production Deployment
```bash
# Blue/green deployment changeover
just deploy

# Build and run production containers
docker-compose up django_blue django_green

# Run datasette services
docker-compose up sites_datasette_blue sites_datasette_green
```

## Architecture

### Core Components

1. **Django Application (`config/`)**
   - Main Django project with settings in `config/settings.py`
   - ASGI configuration in `config/asgi.py` with djp plugin integration
   - URL routing in `config/urls.py`

2. **Subdomain Routing (`django_plugins/datasette_by_subdomain.py`)**
   - Custom ASGI middleware that intercepts requests by subdomain
   - Dynamically creates Datasette instances for each municipality
   - Routes `subdomain.civic.band` to corresponding SQLite database at `../sites/{subdomain}/meetings.db`

3. **Pages App (`pages/`)**
   - Simple Django app serving static content (home, how, why, RSS)
   - Template-based views for informational pages

4. **Datasette Plugins (`plugins/`)**
   - Custom Datasette plugins for enhanced functionality
   - `corkboard.py` - Template variables for site customization
   - `search_all.py`, `search_highlight.py` - Search functionality
   - `umami.py` - Analytics integration
   - `robots.py` - SEO/crawling control

5. **Templates (`templates/`)**
   - Django templates in `templates/pages/`
   - Datasette templates in `templates/datasette/`
   - Site-specific templates in `templates/sites-database/`
   - Configuration templates in `templates/config/`

### Key Architecture Patterns

- **Hybrid Django/Datasette**: Uses djp to integrate Datasette plugins with Django
- **Subdomain-based Multi-tenancy**: Each municipality gets its own subdomain and database
- **Blue/Green Deployment**: Docker compose setup with blue/green deployment strategy
- **Plugin-based Extension**: Both Django (djp) and Datasette plugins for customization

### Database Structure

- Main application uses SQLite (`civic.db`)
- Each municipality has its own database at `../sites/{subdomain}/meetings.db`
- Site registry stored in `sites.db`

### Dependencies

- **Django 5.1+**: Web framework
- **Datasette**: Data exploration and API
- **djp**: Django plugin system
- **uv**: Package management
- **sqlite-utils**: Database utilities

## Development Workflow

1. **Setup:** Run `just setup` to initialize development environment
2. **Make changes:** Edit code and write tests for new functionality
3. **Quality checks:** Run `just check` to lint, format-check, and test
4. **Manual testing:** Use `just serve` for local development server
5. **Commit:** Git hooks automatically run linting and formatting checks
6. **Push:** GitHub Actions runs full test suite with coverage verification

### Key Commands

- `just test` - Run test suite
- `just check` - Run all quality checks
- `just serve` - Start development server
- `just format` - Auto-format code
- For subdomain testing, use localhost (bypasses subdomain routing)
- Use Docker compose for full environment testing

## Notes

- The subdomain routing logic in `datasette_by_subdomain.py` is central to the application's multi-tenant architecture
- Templates use Jinja2 with site-specific context variables
- Bot policies are configured in `botPolicy.yaml`
- Static files are served through WhiteNoise in production