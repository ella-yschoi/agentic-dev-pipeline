"""Example: Run agentic-dev-pipeline from Python code.

This script shows three ways to use the Pipeline API:
1. Zero-flag — reads config from pyproject.toml
2. Explicit args — pass everything in code
3. Custom gate — add a Python callable quality gate
"""

import subprocess
import sys

from agentic_dev_pipeline import Pipeline


# ── 1. Zero-flag (reads from pyproject.toml) ─────────────
def run_from_config():
    converged = Pipeline().run()
    sys.exit(0 if converged else 1)


# ── 2. Explicit args ─────────────────────────────────────
def run_explicit():
    converged = Pipeline(
        prompt_file="PROMPT.md",
        requirements_file="requirements.md",
        max_iterations=3,
        timeout=600,
        base_branch="develop",
    ).run()
    sys.exit(0 if converged else 1)


# ── 3. Custom gate ───────────────────────────────────────
def no_todos() -> tuple[bool, str]:
    """Fail if any TODO comments remain in source code."""
    result = subprocess.run(
        ["grep", "-rn", "TODO", "src/"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return False, f"Found TODOs:\n{result.stdout}"
    return True, "No TODOs found"


def no_print_statements() -> tuple[bool, str]:
    """Fail if any print() calls remain in source code."""
    result = subprocess.run(
        ["grep", "-rn", "print(", "src/"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return False, f"Found print() calls:\n{result.stdout}"
    return True, "No print() calls found"


def run_with_gates():
    converged = (
        Pipeline(
            prompt_file="PROMPT.md",
            requirements_file="requirements.md",
        )
        .add_gate("no-todos", no_todos)
        .add_gate("no-print", no_print_statements)
        .run()
    )
    sys.exit(0 if converged else 1)


if __name__ == "__main__":
    # Pick one:
    run_from_config()
    # run_explicit()
    # run_with_gates()
