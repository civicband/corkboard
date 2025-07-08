# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CivicBand is a Django + Datasette hybrid application that provides government and municipality meeting data through a web interface. The application uses a unique subdomain-based architecture where different municipalities access their data through dedicated subdomains.

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv
./uv_install.sh

# Install development dependencies
./install_dev.sh
```

### Testing
```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=django_plugins

# Run specific test file
python -m pytest tests/test_datasette_by_subdomain.py
```

### Code Quality
```bash
# Run linting
ruff check .

# Format code
ruff format .

# Type checking - not configured (no mypy/pyright in dependencies)
```

### Development Server
```bash
# Django development server
python manage.py runserver

# Docker development environment
docker-compose up
```

### Production Deployment
```bash
# Build and run production containers
docker-compose up django_blue django_green

# Run datasette services
docker-compose up sites_datasette_blue sites_datasette_green

# Changeover script for blue/green deployment
./changeover.sh
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

1. Use `uv` for dependency management
2. Test changes with `python -m pytest`
3. Format code with `ruff format .`
4. Run linting with `ruff check .`
5. For subdomain testing, use localhost (bypasses subdomain routing)
6. Use Docker compose for full environment testing

## Notes

- The subdomain routing logic in `datasette_by_subdomain.py` is central to the application's multi-tenant architecture
- Templates use Jinja2 with site-specific context variables
- Bot policies are configured in `botPolicy.yaml`
- Static files are served through WhiteNoise in production