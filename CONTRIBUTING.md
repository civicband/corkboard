# Contributing to CivicBand

Thank you for your interest in contributing to CivicBand! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- [just](https://github.com/casey/just) command runner
- Git

### Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/yourusername/corkboard.git
cd corkboard
```

2. **Set up the development environment:**

```bash
just setup
```

This command will:
- Install all dependencies using `uv`
- Run Django migrations
- Install pre-commit hooks

3. **Run the development server:**

```bash
just serve
```

Visit `http://localhost:8000` to see the application.

## Development Workflow

### Available Commands

We use `just` as our command runner. Run `just` without arguments to see all available commands:

```bash
just
```

Key commands:

- `just install` - Install all dependencies
- `just test` - Run all tests
- `just test-cov` - Run tests with coverage report
- `just lint` - Check code style
- `just format` - Auto-format code
- `just check` - Run all quality checks (lint, format, test)
- `just serve` - Start Django development server
- `just hooks` - Install pre-commit hooks

### Making Changes

1. **Create a new branch:**

```bash
git checkout -b feature/your-feature-name
```

2. **Make your changes** and write tests for new functionality

3. **Run quality checks:**

```bash
just check
```

This will run linting, formatting checks, and all tests.

4. **Commit your changes:**

```bash
git add .
git commit -m "Description of your changes"
```

Pre-commit hooks will automatically:
- Check code formatting with ruff
- Lint code with ruff
- Check for common issues (trailing whitespace, large files, etc.)

5. **Push your changes and create a pull request:**

```bash
git push origin feature/your-feature-name
```

## Code Quality Standards

### Linting and Formatting

We use [ruff](https://docs.astral.sh/ruff/) for both linting and formatting:

- **Lint check:** `just lint`
- **Auto-fix linting issues:** `just lint-fix`
- **Format code:** `just format`
- **Check formatting:** `just format-check`

Configuration is in `pyproject.toml` under `[tool.ruff]`.

### Testing

We maintain a minimum of 70% test coverage. All new code should include tests.

**Run tests:**

```bash
just test
```

**Run tests with coverage:**

```bash
just test-cov
```

This generates an HTML coverage report in `htmlcov/`.

**Run specific tests:**

```bash
just test-file tests/test_datasette_by_subdomain.py
just test-match "test_subdomain"
```

### Writing Tests

- Tests are located in the `tests/` directory
- We use pytest for testing
- Use descriptive test names and docstrings
- Mock external dependencies (APIs, databases when appropriate)
- Aim for clear, maintainable test code

**Test file naming:**
- `test_*.py` for test files
- `Test*` for test classes
- `test_*` for test functions

**Example test:**

```python
def test_extract_subdomain():
    """Extract subdomain from multi-level hostname."""
    result = extract_subdomain("alameda.ca.civic.org")
    assert result == "alameda.ca"
```

## Project Structure

```
corkboard/
├── config/              # Django configuration
├── django_plugins/      # Django plugins (djp)
├── pages/              # Django pages app
├── plugins/            # Datasette plugins
├── scripts/            # Utility scripts
├── templates/          # Django and Datasette templates
├── tests/              # Test files
│   ├── conftest.py    # Shared pytest fixtures
│   └── test_plugins/  # Plugin tests
├── analytics/          # Analytics data (gitignored)
├── justfile           # Command runner configuration
├── pyproject.toml     # Project dependencies and configuration
└── .pre-commit-config.yaml  # Pre-commit hooks configuration
```

## Dependency Management

We use `uv` for dependency management:

**Add a new dependency:**

```bash
# Edit pyproject.toml to add the dependency
# Then sync:
uv sync
```

**Update dependencies:**

```bash
just update
```

**Check for outdated dependencies:**

```bash
just outdated
```

## Git Hooks

Pre-commit hooks are automatically installed with `just setup` or `just hooks`.

**Manually run hooks on all files:**

```bash
just hooks-run
```

**Skip hooks (not recommended):**

```bash
git commit --no-verify
```

## Continuous Integration

All pull requests run through GitHub Actions CI, which:

1. Runs linting checks
2. Runs formatting checks
3. Runs full test suite with coverage
4. Verifies 70%+ code coverage
5. Uploads coverage reports

You can view the workflow in `.github/workflows/test.yml`.

## Code Style Guidelines

### Python Code

- Follow PEP 8 (enforced by ruff)
- Use type hints where appropriate
- Write descriptive variable and function names
- Keep functions focused and small
- Add docstrings to modules, classes, and complex functions

### Docstring Format

```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of function.

    Longer description if needed. Explain parameters
    and return values.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value
    """
    pass
```

### Django Code

- Follow Django coding style
- Use class-based views when appropriate
- Keep views simple, move logic to models or utilities

### Datasette Plugins

- Use hookimpl decorator for hooks
- Follow Datasette plugin conventions
- Document plugin configuration options

## Database Migrations

**Create migrations:**

```bash
just makemigrations
```

**Run migrations:**

```bash
just migrate
```

## Docker Development

**Start Docker environment:**

```bash
just docker-up
```

**View logs:**

```bash
just docker-logs
```

**Stop Docker:**

```bash
just docker-down
```

## Analytics

**Retrieve analytics data:**

```bash
just analytics-retrieve
```

**View analytics in Datasette:**

```bash
just analytics-view
```

## Getting Help

- Check existing issues and pull requests
- Read the documentation in `CLAUDE.md`
- Ask questions in issues or discussions

## License

By contributing to CivicBand, you agree that your contributions will be licensed under the same license as the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors

Thank you for contributing to CivicBand!
