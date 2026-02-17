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
| Python | `pyproject.toml` | ruff / flake8 / pylint | pytest / unittest | semgrep / bandit |
| Node | `package.json` | eslint / npm lint | jest / vitest / npm test | semgrep / npm audit |
| Rust | `Cargo.toml` | cargo clippy | cargo test | semgrep / cargo-audit |
| Go | `go.mod` | golangci-lint / go vet | go test | semgrep / gosec |
| Custom | env vars | any via `LINT_CMD` | any via `TEST_CMD` | any via `SECURITY_CMD` |

Detection priority: **ENV var → Makefile target → package.json script → tool existence**.

Python runner detection: `uv.lock` → `uv run`, `poetry.lock` → `poetry run`, otherwise bare.

## Prerequisites

Before starting, ensure:
1. A PROMPT file exists with: requirements summary, completion criteria, on-failure instructions, and a `<promise>LOOP_COMPLETE</promise>` completion signal
2. A requirements file exists for triangular verification (Agent B/C need it)
3. At least one quality tool is installed (lint, test, or security)

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
│    lint → test → security (sequential)  │
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

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMPT_FILE` | **(required)** | Path to the prompt file |
| `REQUIREMENTS_FILE` | **(required)** | Path to the requirements doc |
| `OUTPUT_DIR` | `.agentic-dev-pipeline/` | Artifact output directory |
| `LINT_CMD` | (auto-detect) | Lint command |
| `TEST_CMD` | (auto-detect) | Test command |
| `SECURITY_CMD` | (auto-detect) | Security scan command (empty = skip) |
| `SRC_DIRS` | (auto-detect) | Source directories |
| `BASE_BRANCH` | `main` | Git diff base branch |
| `MAX_ITERATIONS` | `5` | Maximum loop iterations |

## Execution Steps

### Method A: Shell Script (terminal, outside Claude Code)

```bash
cd <project-root>

PROMPT_FILE="path/to/PROMPT.md" \
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 5
```

With overrides:

```bash
PROMPT_FILE="PROMPT.md" \
REQUIREMENTS_FILE="requirements.md" \
LINT_CMD="npm run lint" \
TEST_CMD="npm test" \
SECURITY_CMD="" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 3
```

### Method B: Skill Invocation (inside Claude Code session)

When orchestrating within a Claude Code session:

1. **Phase 1** — Implement the feature per PROMPT.md. On subsequent iterations, read the feedback file and make targeted fixes only.

2. **Phase 2** — Run auto-detected quality gates sequentially (fast-fail order):
   - Source `detect-project.sh` to determine commands
   - Run `$LINT_CMD`, then `$TEST_CMD`, then `$SECURITY_CMD`
   - If any fails, capture the error output and loop back to Phase 1

3. **Phase 3** — Triangular verification using two subagents:
   - **Agent B** (Task tool, general-purpose): Read code files + auto-detected instruction files + design docs. Do NOT read requirements. Describe what each file does, list violations and potential issues. Write to `$OUTPUT_DIR/blind-review.md`.
   - **Agent C** (Task tool, general-purpose): Read requirements + blind-review.md. Do NOT read code. Compare and produce discrepancy report. Write to `$OUTPUT_DIR/discrepancy-report.md`.
   - If `TRIANGULAR_PASS` is NOT in the discrepancy report, use the report as feedback and loop back to Phase 1.

4. **Phase 4** — All gates passed. Report LOOP_COMPLETE with iteration count and timing.

### Triangular Verify Only (standalone)

```bash
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/triangular-verify.sh
```

## Output Files

After completion, check `$OUTPUT_DIR/` (default: `.agentic-dev-pipeline/`):

| File | Content |
|------|---------|
| `loop-execution.log` | Full execution log (iterations, timing, phase results) |
| `blind-review.md` | Agent B's blind code review |
| `discrepancy-report.md` | Agent C's requirements vs code comparison |
| `feedback.txt` | Last iteration's feedback (deleted on success) |

## Key Design Principles

1. **Failure = Data**: Each iteration's failure output becomes the next iteration's input
2. **Safety first**: `MAX_ITERATIONS` prevents infinite loops (default: 5)
3. **Convergence**: Most work done in iteration 1, subsequent iterations fix edge cases
4. **Completion signal**: Exact `LOOP_COMPLETE` string exits the loop

## Examples

### Python project (auto-detected)

```bash
PROMPT_FILE="docs/PROMPT-auth-module.md" \
REQUIREMENTS_FILE="docs/requirements-auth.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh
```

### Node project with custom commands

```bash
PROMPT_FILE="PROMPT.md" \
REQUIREMENTS_FILE="requirements.md" \
LINT_CMD="npm run lint" \
TEST_CMD="npm test" \
SECURITY_CMD="" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh
```

### Rust project, custom output dir

```bash
PROMPT_FILE="PROMPT.md" \
REQUIREMENTS_FILE="requirements.md" \
OUTPUT_DIR="target/loop-output" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh 3
```

## Prompt Template

See `PROMPT-TEMPLATE.md` in this skill directory for a copy-and-fill template.

## Troubleshooting

### `claude` command not found
Shell scripts require `claude` CLI in PATH. Run `which claude` to check.

### Nested claude call blocked
Scripts include `unset CLAUDECODE` but running from a terminal (outside Claude Code) is recommended.

### Quality gate keeps failing
- Ensure existing tests pass before starting
- Ensure dependencies are installed
- Check that the detected commands match what you expect (`print_detected_config`)

### TRIANGULAR_PASS not achieved
- Read `$OUTPUT_DIR/discrepancy-report.md` for specific mismatches
- Make requirements more specific if Agent C can't judge
- The loop auto-corrects; increase `MAX_ITERATIONS` if needed

### Wrong tools detected
Override with environment variables: `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD`.
