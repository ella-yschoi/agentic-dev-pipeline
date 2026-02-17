# Contributing to agentic-dev-pipeline

## Development Setup

### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install
```bash
# Clone the repo
git clone https://github.com/ella-yschoi/agentic-dev-pipeline.git
cd agentic-dev-pipeline

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
pip install pytest ruff
```

### Verify
```bash
# Run tests
make test

# Run linter
make lint

# Run both
make check
```

## Project Structure

```
src/agentic_dev_pipeline/
├── __init__.py       # Package version + public API exports
├── __main__.py       # python -m entry point
├── api.py            # Pipeline class (library API)
├── cli.py            # CLI argument parsing (run/verify/detect/init)
├── config.py         # Hierarchical config loading (PipelineConfig)
├── detect.py         # Project auto-detection (8 detection functions)
├── domain.py         # Domain types: enums, value objects, metrics
├── init_cmd.py       # init command scaffolding
├── log.py            # Structured logging (text + JSON Lines)
├── pipeline.py       # Main pipeline orchestrator (phase functions)
├── runner.py         # ClaudeRunner protocol + CLI implementation
└── verify.py         # Triangular verification (Agent B + C)

tests/
├── conftest.py       # Shared fixtures
├── unit/             # Unit tests for each module
└── integration/      # End-to-end tests with mock claude
```

## Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# With verbose output
uv run pytest tests/ -v
```

## Code Style

- **Linter**: ruff (configured in `pyproject.toml`)
- **Line length**: 100 characters
- **Target**: Python 3.11+
- **Formatting**: `make format` to auto-fix

### Rules
- All public functions need docstrings
- Type annotations on all function signatures
- Use `from __future__ import annotations` in all modules
- Prefer `Path` over string paths

## Making Changes

1. Create a feature branch from `main`
2. Make your changes
3. Ensure `make check` passes (lint + tests)
4. Open a PR with description of changes

## Adding a New Detection

To add support for a new language/project type:

1. Add detection logic in `detect.py`:
   - `detect_project_type()`: new marker file check
   - `detect_lint_cmd()`: tool detection
   - `detect_test_cmd()`: test framework detection
   - `detect_security_cmd()`: security scanner detection

2. Add test fixture in `tests/conftest.py` (e.g. `<lang>_project`)

3. Add unit tests in `tests/unit/test_detect_*.py`

## Pull Request Guidelines

- Keep PRs focused (one feature/fix per PR)
- All tests must pass
- Lint must pass
- Update CHANGELOG.md for user-facing changes
