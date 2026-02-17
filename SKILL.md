---
name: agentic-dev-pipeline
description: "Use when implementing a feature with automated quality + intent verification loop. Combines iteration with triangular verification. Invoke when the user asks to implement a feature end-to-end with verification, or says 'agentic dev pipeline'."
---

# Agentic Dev Pipeline

Implement a feature from a single task file through an automated loop: code → quality gates → triangular verification → self-correction, with zero human intervention.

**Project-agnostic.** Auto-detects lint, test, and security tools for Python, Node, Rust, Go, and custom setups.

## When to Use

- User asks to implement a feature with full automated verification
- User wants a "PROMPT.md → verified code" pipeline
- User mentions "agentic dev pipeline", "automated loop", or "agentic pipeline"

## Supported Project Types

| Type | Detected by | Lint | Test | Security |
|------|------------|------|------|----------|
| Python | `pyproject.toml` / `setup.py` / `setup.cfg` | ruff / flake8 / pylint | pytest / unittest | semgrep / bandit |
| Node | `package.json` | eslint / npm lint | jest / vitest / npm test | semgrep / npm audit |
| Rust | `Cargo.toml` | cargo clippy | cargo test | semgrep / cargo-audit |
| Go | `go.mod` | golangci-lint / go vet | go test | semgrep / gosec |
| Custom | env vars | any via `LINT_CMD` | any via `TEST_CMD` | any via `SECURITY_CMD` |

Detection priority: **ENV var → Makefile target → package.json script → tool existence**.

Python runner detection: `uv.lock` → `uv run`, `poetry.lock` → `poetry run`, otherwise bare. Tools are resolved from PATH first, then from the active venv (`sys.prefix`).

## Prerequisites

Before starting, ensure:
1. Python 3.11+ installed
2. A PROMPT file exists with: requirements summary, completion criteria, on-failure instructions, and a `<promise>LOOP_COMPLETE</promise>` completion signal
3. A requirements file exists for triangular verification (Agent B/C need it)
4. At least one quality tool is installed (lint, test, or security) — in PATH or active venv

## Pipeline Structure

```
PROMPT.md + requirements.md
    │
    ▼
┌─────────────────────────────────────────┐
│  Loop (max N iterations)                │
│                                         │
│  Phase 1: Implementation                │
│    Agent A: Write or fix code           │
│    - First iteration: full implement    │
│    - Later: targeted fixes from feedback│
│                                         │
│  Phase 2: Quality Gates (auto-detected) │
│    Sequential (default): fast-fail      │
│    Parallel (--parallel-gates): all     │
│    Includes: lint, test, security,      │
│      plugins, custom callable gates     │
│    ❌ Fail → save output as feedback    │
│       → back to Phase 1                 │
│                                         │
│  Phase 3: Triangular Verification       │
│    Agent B: blind review (no reqs)      │
│    Agent C: discrepancy report          │
│    ❌ Issues found → save report as     │
│       feedback → back to Phase 1        │
│                                         │
│  Phase 4: Complete                      │
│    All gates passed → LOOP_COMPLETE     │
└─────────────────────────────────────────┘
```

## Configuration

Settings are resolved in this priority order (highest wins):

**CLI flags / Python API args > `pyproject.toml` > `.agentic-dev-pipeline.toml` > Environment variables > Defaults**

### Config file: `pyproject.toml` (Python projects)

```toml
[tool.agentic-dev-pipeline]
prompt-file = "PROMPT.md"
requirements-file = "requirements.md"
max-iterations = 5
# timeout = 300
# max-retries = 2
# base-branch = "main"
```

### Config file: `.agentic-dev-pipeline.toml` (Non-Python projects)

```toml
prompt-file = "PROMPT.md"
requirements-file = "requirements.md"
max-iterations = 3
```

### Config environment variables

| Variable | Config field | Default |
|----------|-------------|---------|
| `PROMPT_FILE` | `prompt-file` | — |
| `REQUIREMENTS_FILE` | `requirements-file` | — |
| `MAX_ITERATIONS` | `max-iterations` | `5` |
| `CLAUDE_TIMEOUT` | `timeout` | `300` |
| `MAX_RETRIES` | `max-retries` | `2` |
| `BASE_BRANCH` | `base-branch` | `main` |

## Environment Variable Reference

### Config variables (also settable via config files)

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMPT_FILE` | — | Path to the prompt file (or `--prompt`) |
| `REQUIREMENTS_FILE` | — | Path to the requirements doc (or `--requirements`) |
| `MAX_ITERATIONS` | `5` | Maximum loop iterations |
| `CLAUDE_TIMEOUT` | `300` | Timeout per claude call (seconds) |
| `MAX_RETRIES` | `2` | Max retries per claude call |
| `BASE_BRANCH` | `main` | Git diff base branch |

### CLI-only variables (not in config files)

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `.agentic-dev-pipeline/` | Artifact output directory |
| `WEBHOOK_URL` | — | Webhook URL for notifications |
| `PARALLEL_GATES` | `false` | Run gates in parallel (`true`/`1`/`yes`) |
| `PLUGIN_DIR` | — | Custom gate plugin directory (.sh/.py files) |
| `LOG_FORMAT` | `text` | Log format: `text` or `json` |
| `DEBUG` | — | Enable debug output to stderr |

### Detection override variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PROJECT_TYPE` | (auto) | Force project type: `python`, `node`, `rust`, `go` |
| `LINT_CMD` | (auto) | Lint command |
| `TEST_CMD` | (auto) | Test command |
| `SECURITY_CMD` | (auto) | Security scan command (empty string = skip) |
| `SRC_DIRS` | (auto) | Source directories (space-separated) |
| `INSTRUCTION_FILES` | (auto) | Instruction files for Agent B (space-separated) |
| `DESIGN_DOCS` | (auto) | Design doc paths for Agent B (space-separated) |
| `CHANGED_FILES` | (auto) | Changed file list for verification (space-separated) |

## Execution Steps

### Method A: CLI (terminal)

```bash
cd <project-root>

# Initialize config files (first time)
agentic-dev-pipeline init
agentic-dev-pipeline init --force   # overwrite existing files

# Zero-flag run — reads config from pyproject.toml or .agentic-dev-pipeline.toml
agentic-dev-pipeline run

# Full pipeline with explicit flags
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md

# With options
agentic-dev-pipeline run \
  --prompt PROMPT.md \
  --requirements requirements.md \
  --max-iterations 3 \
  --timeout 600 \
  --max-retries 3 \
  --parallel-gates \
  --plugin-dir ./gates/ \
  --webhook-url "https://hooks.slack.com/..."

# Via python -m
python -m agentic_dev_pipeline run --prompt PROMPT.md --requirements requirements.md
```

With env var overrides:
```bash
LINT_CMD="npm run lint" TEST_CMD="npm test" SECURITY_CMD="" \
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Method B: Python API

```python
from agentic_dev_pipeline import Pipeline

# Minimal
Pipeline("PROMPT.md", "requirements.md").run()

# Zero-flag (reads from config files)
Pipeline().run()

# With custom Python gate
def no_todos() -> tuple[bool, str]:
    import subprocess
    result = subprocess.run(["grep", "-r", "TODO", "src/"], capture_output=True, text=True)
    if result.returncode == 0:
        return False, f"Found TODOs:\n{result.stdout}"
    return True, "No TODOs found"

Pipeline("PROMPT.md", "req.md").add_gate("no-todos", no_todos).run()

# Verification only
Pipeline(requirements_file="requirements.md").verify()

# Project detection only
config = Pipeline().detect()
print(config.lint_cmd)
```

**Pipeline reference**:

| Method | Returns | Description |
|--------|---------|-------------|
| `Pipeline(...)` | `Pipeline` | Create with optional config overrides |
| `.add_gate(name, func)` | `Pipeline` | Add custom gate (chainable) |
| `.run()` | `bool` | Run full pipeline. `True` if converged |
| `.verify()` | `bool` | Run triangular verification only |
| `.detect()` | `ProjectConfig` | Run project auto-detection |
| `.config` | `PipelineConfig` | Access resolved config |

Gate function signature: `() -> tuple[bool, str]` — returns `(passed, message)`.

### Method C: Skill Invocation (inside Claude Code session)

When orchestrating within a Claude Code session:

1. **Phase 1** — Implement the feature per PROMPT.md. On subsequent iterations, read the feedback file and make targeted fixes only.

2. **Phase 2** — Run auto-detected quality gates:
   - Use `agentic-dev-pipeline detect` to check detected commands
   - Run `$LINT_CMD`, then `$TEST_CMD`, then `$SECURITY_CMD`
   - If any fails, capture the error output and loop back to Phase 1

3. **Phase 3** — Triangular verification using two subagents:
   - **Agent B** (Task tool, general-purpose): Read code files + auto-detected instruction files + design docs. Do NOT read requirements. Describe what each file does, list violations and potential issues. Write to `$OUTPUT_DIR/blind-review.md`.
   - **Agent C** (Task tool, general-purpose): Read requirements + blind-review.md. Do NOT read code. Compare and produce discrepancy report. Write to `$OUTPUT_DIR/discrepancy-report.md`.
   - If `TRIANGULAR_PASS` is NOT in the discrepancy report, use the report as feedback and loop back to Phase 1.

4. **Phase 4** — All gates passed. Report LOOP_COMPLETE with iteration count and timing.

### Standalone Commands

```bash
# Triangular verification only
agentic-dev-pipeline verify --requirements requirements.md
agentic-dev-pipeline verify --requirements r.md --output-dir out/ --base-branch develop

# Print detected project configuration
agentic-dev-pipeline detect

# Version
agentic-dev-pipeline --version
```

## Quality Gates

### Gate types

1. **Shell gates** (auto-detected): lint, test, security commands
2. **Plugin gates** (`--plugin-dir`): `.sh` and `.py` files in a directory, run as `bash <file>` or `python3 <file>`
3. **Callable gates** (Python API): functions registered via `Pipeline.add_gate()`

### Execution modes

- **Sequential** (default): Fast-fail order. Stops at first failure.
- **Parallel** (`--parallel-gates`): Runs all gates concurrently. Collects ALL failures into feedback.

### Safety

Gate commands are checked against shell injection patterns (`$(...)`, backticks, `; rm`, etc.). Unsafe commands are blocked.

## Output Files

After completion, check `$OUTPUT_DIR/` (default: `.agentic-dev-pipeline/`):

| File | Content |
|------|---------|
| `loop-execution.log` | Full execution log (iterations, timing, phase results) |
| `blind-review.md` | Agent B's blind code review |
| `discrepancy-report.md` | Agent C's requirements vs code comparison |
| `metrics.json` | Execution metrics (timing, iterations, gate results) |
| `feedback.txt` | Last iteration's feedback (deleted on success) |

### metrics.json format

```json
{
  "started_at": "2026-01-01T00:00:00+0900",
  "ended_at": "2026-01-01T00:05:00+0900",
  "total_duration_s": 300.0,
  "total_iterations": 2,
  "converged": true,
  "iterations": [
    {
      "iteration": 1,
      "duration_s": 120.0,
      "phase1_done": true,
      "lint_result": "pass",
      "test_result": "fail",
      "security_result": "skipped",
      "plugin_results": [],
      "verification_result": "skipped",
      "outcome": "gate_fail"
    }
  ]
}
```

## Key Design Principles

1. **Failure = Data**: Each iteration's failure output becomes the next iteration's input
2. **Safety first**: `MAX_ITERATIONS` prevents infinite loops (default: 5)
3. **Convergence**: Most work done in iteration 1, subsequent iterations fix edge cases
4. **Completion signal**: Exact `LOOP_COMPLETE` string exits the loop

## Examples

### Python project (auto-detected)

```bash
agentic-dev-pipeline run \
  --prompt docs/PROMPT-auth-module.md \
  --requirements docs/requirements-auth.md
```

### Node project with custom commands

```bash
LINT_CMD="npm run lint" TEST_CMD="npm test" SECURITY_CMD="" \
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Parallel gates with plugins

```bash
agentic-dev-pipeline run \
  --prompt PROMPT.md \
  --requirements requirements.md \
  --parallel-gates \
  --plugin-dir ./custom-gates/
```

### JSON logging with webhook

```bash
LOG_FORMAT=json WEBHOOK_URL="https://hooks.slack.com/..." \
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

## Prompt Template

Run `agentic-dev-pipeline init` to generate `PROMPT.md` and `requirements.md` templates.
See `examples/` for filled-in examples.

## Troubleshooting

### `claude` command not found
The pipeline requires `claude` CLI in PATH. Run `which claude` to check.

### Nested claude call blocked
The pipeline unsets `CLAUDECODE` env var automatically. Running from a terminal (outside Claude Code) is recommended.

### Quality gate keeps failing
- Ensure existing tests pass before starting
- Ensure dependencies are installed
- Run `agentic-dev-pipeline detect` to check detected commands

### TRIANGULAR_PASS not achieved
- Read `.agentic-dev-pipeline/discrepancy-report.md` for specific mismatches
- Make requirements more specific if Agent C can't judge
- The loop auto-corrects; increase `--max-iterations` if needed

### Wrong tools detected
Override with environment variables: `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD`.

### Timeout issues
Increase with `--timeout 600` or `CLAUDE_TIMEOUT=600`.
