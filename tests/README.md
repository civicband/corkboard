# CivicBand Tests

Tests for the CivicBand corkboard application.

**Requires Python 3.11+**

## Running Tests

With uv installed:

```bash
# Install test dependencies separately (without installing the package itself)
uv pip install pytest pytest-asyncio pytest-cov

# Alternatively, use the group definitions
uv pip install -r requirements-dev.txt

# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=django_plugins

# Run specific test file
python -m pytest tests/test_datasette_by_subdomain.py
```