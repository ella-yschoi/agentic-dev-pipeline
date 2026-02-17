# agentic-dev-pipeline

A Claude Code skill that autonomously implements features through an automated loop: code → quality gates → triangular verification → self-correction, with zero human intervention.

## Installation

```bash
git clone https://github.com/ella-yschoi/agentic-dev-pipeline.git ~/.agents/skills/agentic-dev-pipeline
```

Claude Code automatically recognizes `~/.agents/skills/agentic-dev-pipeline/SKILL.md`.

## Quick Start

```bash
cd <project-root>

PROMPT_FILE="path/to/PROMPT.md" \
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh
```

Inside a Claude Code session:

```
Use the agentic-dev-pipeline skill to implement <feature>.
PROMPT: path/to/PROMPT.md
Requirements: path/to/requirements.md
```

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
│                                         │
│  Phase 2: Quality Gates (auto-detected) │
│    lint → test → security (sequential)  │
│    ❌ Fail → feedback → Phase 1        │
│                                         │
│  Phase 3: Triangular Verification       │
│    Agent B: blind review (no reqs)      │
│    Agent C: discrepancy report          │
│    ❌ Issues → feedback → Phase 1      │
│                                         │
│  Phase 4: Complete                      │
│    All gates passed → LOOP_COMPLETE     │
└─────────────────────────────────────────┘
```

## Supported Project Types

`detect-project.sh` analyzes the project root to auto-detect tools.

| Type | Detected by | Lint | Test | Security |
|------|------------|------|------|----------|
| Python | `pyproject.toml` | ruff / flake8 / pylint | pytest / unittest | semgrep / bandit |
| Node | `package.json` | eslint / npm lint | jest / vitest / npm test | semgrep / npm audit |
| Rust | `Cargo.toml` | cargo clippy | cargo test | semgrep / cargo-audit |
| Go | `go.mod` | golangci-lint / go vet | go test | semgrep / gosec |
| Custom | env vars | `LINT_CMD` | `TEST_CMD` | `SECURITY_CMD` |

Detection priority: **ENV var → Makefile target → package.json script → tool existence**

Python runner detection: `uv.lock` → `uv run`, `poetry.lock` → `poetry run`, otherwise bare.

## Environment Variables

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

## File Structure

```
agentic-dev-pipeline/
├── SKILL.md                  ← Claude Code skill definition
├── agentic-dev-pipeline.sh   ← Main loop script
├── detect-project.sh         ← Project auto-detection library
├── triangular-verify.sh      ← Standalone triangular verification
├── PROMPT-TEMPLATE.md        ← Copy-and-fill prompt template
└── README.md
```

## Triangular Verification (Standalone)

```bash
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/triangular-verify.sh
```

## Output Files

Located in `$OUTPUT_DIR/` (default: `.agentic-dev-pipeline/`):

| File | Content |
|------|---------|
| `loop-execution.log` | Full execution log |
| `blind-review.md` | Agent B's blind code review |
| `discrepancy-report.md` | Agent C's requirements vs code comparison |
| `feedback.txt` | Last iteration's feedback (deleted on success) |

## Experiment Results

Experiment logs using this skill are available in the [renewal-review](https://github.com/ella-yschoi/renewal-review) project at `docs/logs/experiments-log.md`.

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) CLI (`claude` must be in PATH)
- At least one quality tool for your project (lint, test, or security)

## Troubleshooting

- **`claude` command not found**: Check PATH with `which claude`
- **Nested claude call blocked**: Run from a terminal outside Claude Code (scripts include `unset CLAUDECODE`)
- **Wrong tools detected**: Override with `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD` env vars
- **TRIANGULAR_PASS not achieved**: Read `$OUTPUT_DIR/discrepancy-report.md` for specifics; make requirements more precise

## License

MIT
