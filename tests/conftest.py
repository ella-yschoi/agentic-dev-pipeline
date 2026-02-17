"""Shared pytest fixtures."""

import sys
from pathlib import Path

import pytest


@pytest.fixture
def python_project(tmp_path: Path) -> Path:
    """Create a minimal Python project in tmp_path."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    return tmp_path


@pytest.fixture
def node_project(tmp_path: Path) -> Path:
    """Create a minimal Node project in tmp_path."""
    (tmp_path / "package.json").write_text(
        '{"name": "test", "scripts": {"lint": "eslint .", "test": "jest"}}\n'
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "index.js").write_text("module.exports = {};\n")
    return tmp_path


@pytest.fixture
def rust_project(tmp_path: Path) -> Path:
    """Create a minimal Rust project in tmp_path."""
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"\nversion = "0.1.0"\n')
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.rs").write_text("fn main() {}\n")
    return tmp_path


@pytest.fixture
def go_project(tmp_path: Path) -> Path:
    """Create a minimal Go project in tmp_path."""
    (tmp_path / "go.mod").write_text("module test\n\ngo 1.21\n")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "main.go").write_text("package main\n")
    return tmp_path


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Create a project with no language markers."""
    (tmp_path / "README.md").write_text("# Test\n")
    return tmp_path


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch):
    """Remove all detection-related env vars to ensure clean state."""
    for var in (
        "PROJECT_TYPE", "SRC_DIRS", "LINT_CMD", "TEST_CMD", "SECURITY_CMD",
        "INSTRUCTION_FILES", "DESIGN_DOCS", "CHANGED_FILES", "BASE_BRANCH",
        "DEBUG", "LOG_FORMAT", "WEBHOOK_URL", "CLAUDE_TIMEOUT", "MAX_RETRIES",
    ):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def no_venv(monkeypatch):
    """Disable venv fallback (for tests that clear PATH to simulate missing tools)."""
    monkeypatch.setattr(sys, "prefix", sys.base_prefix)
