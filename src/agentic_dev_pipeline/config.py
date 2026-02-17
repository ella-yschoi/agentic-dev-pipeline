from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

# TOML kebab-case → dataclass snake_case
_KEY_MAP: dict[str, str] = {
    "prompt-file": "prompt_file",
    "requirements-file": "requirements_file",
    "max-iterations": "max_iterations",
    "max-retries": "max_retries",
    "base-branch": "base_branch",
}

# Environment variable → dataclass field
_ENV_MAP: dict[str, str] = {
    "PROMPT_FILE": "prompt_file",
    "REQUIREMENTS_FILE": "requirements_file",
    "MAX_ITERATIONS": "max_iterations",
    "CLAUDE_TIMEOUT": "timeout",
    "MAX_RETRIES": "max_retries",
    "BASE_BRANCH": "base_branch",
}

_INT_FIELDS = {"max_iterations", "timeout", "max_retries"}
_PATH_FIELDS = {"prompt_file", "requirements_file"}


def _coerce(key: str, value: object) -> object:
    """Coerce a raw config value to the correct Python type."""
    if key in _INT_FIELDS:
        return int(value)  # type: ignore[arg-type]
    if key in _PATH_FIELDS and value is not None:
        return Path(str(value))
    return value


def _normalize_toml(raw: dict[str, object]) -> dict[str, object]:
    """Convert TOML kebab-case keys to snake_case dataclass fields."""
    result: dict[str, object] = {}
    for k, v in raw.items():
        field_name = _KEY_MAP.get(k, k.replace("-", "_"))
        result[field_name] = _coerce(field_name, v)
    return result


def _read_toml(path: Path) -> dict[str, object]:
    """Read a TOML file, returning empty dict on failure."""
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text())  # type: ignore[return-value]
    except Exception:
        return {}


@dataclass
class PipelineConfig:
    """Pipeline configuration — only the settings users routinely configure.

    CLI-only concerns (webhook, parallel-gates, plugin-dir, json-logging)
    are handled by CLI flags and environment variables, not here.
    Project detection overrides (lint-cmd, test-cmd, etc.) are handled
    by detect.py and its environment variables.
    """

    prompt_file: Path | None = None
    requirements_file: Path | None = None
    max_iterations: int = 5
    timeout: int = 300
    max_retries: int = 2
    base_branch: str = "main"

    @staticmethod
    def from_pyproject(root: Path | None = None) -> dict[str, object]:
        """Read [tool.agentic-dev-pipeline] from pyproject.toml."""
        r = root or Path.cwd()
        data = _read_toml(r / "pyproject.toml")
        section = data.get("tool", {})
        if isinstance(section, dict):
            raw = section.get("agentic-dev-pipeline", {})
            if isinstance(raw, dict):
                return _normalize_toml(raw)
        return {}

    @staticmethod
    def from_file(root: Path | None = None) -> dict[str, object]:
        """Read .agentic-dev-pipeline.toml standalone config."""
        r = root or Path.cwd()
        raw = _read_toml(r / ".agentic-dev-pipeline.toml")
        return _normalize_toml(raw)

    @staticmethod
    def from_env() -> dict[str, object]:
        """Read config from environment variables."""
        result: dict[str, object] = {}
        for env_key, field_name in _ENV_MAP.items():
            val = os.environ.get(env_key)
            if val is not None:
                result[field_name] = _coerce(field_name, val)
        return result

    @classmethod
    def resolve(
        cls, explicit: dict[str, object] | None = None, project_root: Path | None = None
    ) -> PipelineConfig:
        """Merge all config sources into a single PipelineConfig.

        Priority: explicit > pyproject.toml > .toml file > env > defaults.
        """
        root = project_root or Path.cwd()

        # Collect layers (lowest priority first)
        env_layer = cls.from_env()
        file_layer = cls.from_file(root)
        pyproject_layer = cls.from_pyproject(root)
        explicit_layer = explicit or {}

        # Merge: later dict values override earlier
        merged: dict[str, object] = {}
        for layer in (env_layer, file_layer, pyproject_layer, explicit_layer):
            for k, v in layer.items():
                if v is not None:
                    merged[k] = v

        # Filter to only known fields
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in merged.items() if k in known}

        return cls(**filtered)
