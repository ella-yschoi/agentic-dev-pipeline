from __future__ import annotations

from pathlib import Path

_PROMPT_TEMPLATE = """\
# Feature: [Feature Name]

## Context

[Brief project description. What should the agent read before coding?]

Read the following for project context:
- [instruction file, e.g., CLAUDE.md, convention.md, CONTRIBUTING.md]
- [design doc, e.g., docs/design-doc.md, docs/architecture.md]

## Requirements

Read `[path/to/requirements.md]` for full requirements.

Summary:
1. [Key requirement 1]
2. [Key requirement 2]
3. [Key requirement 3]

## Existing Patterns to Follow

- Model example: `[path/to/existing/model.py]`
- Test example: `[path/to/existing/test_file.py]`

## Completion Criteria

- [ ] All functional requirements implemented
- [ ] Lint passes (0 errors)
- [ ] All tests pass (existing + new)
- [ ] Security scan passes (if configured)
- [ ] Project conventions followed

## On Failure

- Lint failure: read error output, fix specific issues
- Test failure: read failing test output, fix the implementation
- Security failure: read scan report, fix flagged issues
- Triangular verification failure: read discrepancy-report.md, fix each listed issue

## Completion Signal

When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
"""

_REQUIREMENTS_TEMPLATE = """\
# Requirements: [Feature Name]

## Functional Requirements

### FR-1: [Requirement Title]
- **Endpoint / Interface**: [describe]
- **Input**: [describe]
- **Output**: [describe]
- **Validation**: [describe constraints]

### FR-2: [Requirement Title]
- ...

## Non-Functional Requirements

### NFR-1: Testing
- Unit tests for each feature (happy path + error cases)

### NFR-2: Code Quality
- Follow existing project patterns
- Type annotations on all functions
"""

_TOML_CONFIG = """\
# agentic-dev-pipeline configuration
# See: https://github.com/ella-yschoi/agentic-dev-pipeline

prompt-file = "PROMPT.md"
requirements-file = "requirements.md"
# max-iterations = 5
"""

_PYPROJECT_SECTION = """\

[tool.agentic-dev-pipeline]
prompt-file = "PROMPT.md"
requirements-file = "requirements.md"
# max-iterations = 5
"""

_GITIGNORE_ENTRY = ".agentic-dev-pipeline/"


def run_init(project_root: Path | None = None, *, force: bool = False) -> list[str]:
    """Scaffold config files. Returns list of actions taken."""
    root = project_root or Path.cwd()
    actions: list[str] = []

    # 1. PROMPT template
    prompt_file = root / "PROMPT.md"
    if not prompt_file.exists() or force:
        prompt_file.write_text(_PROMPT_TEMPLATE)
        actions.append(f"Created {prompt_file.relative_to(root)}")
    else:
        actions.append(f"Skipped {prompt_file.relative_to(root)} (already exists)")

    # 2. Requirements template
    req_file = root / "requirements.md"
    if not req_file.exists() or force:
        req_file.write_text(_REQUIREMENTS_TEMPLATE)
        actions.append(f"Created {req_file.relative_to(root)}")
    else:
        actions.append(f"Skipped {req_file.relative_to(root)} (already exists)")

    # 3. Config: pyproject.toml section or standalone .toml
    pyproject = root / "pyproject.toml"
    standalone = root / ".agentic-dev-pipeline.toml"

    if pyproject.is_file():
        content = pyproject.read_text()
        if "[tool.agentic-dev-pipeline]" not in content:
            with pyproject.open("a") as f:
                f.write(_PYPROJECT_SECTION)
            actions.append("Added [tool.agentic-dev-pipeline] to pyproject.toml")
        else:
            actions.append("Skipped pyproject.toml (section already exists)")
    else:
        if not standalone.exists() or force:
            standalone.write_text(_TOML_CONFIG)
            actions.append(f"Created {standalone.name}")
        else:
            actions.append(f"Skipped {standalone.name} (already exists)")

    # 4. .gitignore
    gitignore = root / ".gitignore"
    if gitignore.is_file():
        content = gitignore.read_text()
        if _GITIGNORE_ENTRY not in content:
            with gitignore.open("a") as f:
                if not content.endswith("\n"):
                    f.write("\n")
                f.write(f"{_GITIGNORE_ENTRY}\n")
            actions.append(f"Added {_GITIGNORE_ENTRY} to .gitignore")
        else:
            actions.append("Skipped .gitignore (entry already exists)")
    else:
        gitignore.write_text(f"{_GITIGNORE_ENTRY}\n")
        actions.append("Created .gitignore")

    return actions
