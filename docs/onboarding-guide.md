# Onboarding Guide

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Claude Code CLI (`claude` in PATH)
- Git
- At least one quality tool installed (linter, test runner, or security scanner) — in PATH or active venv

## Quick Start (5 minutes)

### 1. Install

```bash
# As a dev dependency (Python projects)
uv add --dev agentic-dev-pipeline

# Or as a standalone CLI tool (any project)
uv tool install agentic-dev-pipeline

# Or from source
git clone https://github.com/ella-yschoi/agentic-dev-pipeline.git
cd agentic-dev-pipeline
uv sync
```

### 2. Prepare Your Project

Initialize config files (creates templates + config):

```bash
cd your-project
agentic-dev-pipeline init
```

Or create the two files manually:

**PROMPT.md** (what to build):
```markdown
# Feature: Add Health Check Endpoint

## Context
Read CLAUDE.md for project conventions.

## Requirements
Read `requirements.md` for full requirements.
Summary: Add GET /health that returns {"status": "ok"}.

## Completion Criteria
- [ ] Endpoint implemented
- [ ] Tests pass
- [ ] Lint passes

## Completion Signal
When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
```

**requirements.md** (source of truth for verification):
```markdown
# Requirements: Health Check
1. GET /health returns 200 with {"status": "ok"}
2. Response time < 100ms
3. No authentication required
```

### 3. Run

```bash
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### 4. Check Results

```bash
# Execution log
cat .agentic-dev-pipeline/loop-execution.log

# Metrics
cat .agentic-dev-pipeline/metrics.json | python -m json.tool

# Verification artifacts
cat .agentic-dev-pipeline/blind-review.md
cat .agentic-dev-pipeline/discrepancy-report.md
```

## Project Type Guide

### Python Project
```bash
# Auto-detects: pyproject.toml/setup.py/setup.cfg → ruff/pytest/bandit (from PATH or active venv)
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Node Project
```bash
# Auto-detects: package.json → eslint/jest/npm audit
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Rust Project
```bash
# Auto-detects: Cargo.toml → cargo clippy/test/audit
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Go Project
```bash
# Auto-detects: go.mod → golangci-lint/go test/gosec
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

### Custom / Override
```bash
LINT_CMD="make lint" TEST_CMD="make test" SECURITY_CMD="" \
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

## Useful Commands

```bash
# Check what tools are detected for your project
agentic-dev-pipeline detect

# Run triangular verification standalone
agentic-dev-pipeline verify --requirements requirements.md

# Run gates in parallel (collect all failures at once)
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md --parallel-gates

# Custom gate plugins
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md --plugin-dir ./gates/

# Enable debug logging
DEBUG=true agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md

# JSON log output (for jq processing)
LOG_FORMAT=json agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md

# Webhook notification on completion
WEBHOOK_URL="https://hooks.slack.com/..." \
agentic-dev-pipeline run --prompt PROMPT.md --requirements requirements.md
```

## FAQ

### Q: How many iterations does it usually take?
Most features converge in 1-2 iterations. Complex features with many requirements may take 3-4.

### Q: Can I use it without quality tools?
Yes — the pipeline skips any gate without a detected command. But at least one gate is recommended.

### Q: What if the pipeline doesn't converge?
1. Check `metrics.json` to see which phase fails
2. Check `feedback.txt` for the last error
3. Try increasing `--max-iterations`
4. Make your requirements more specific

### Q: Can I run it in CI?
Yes, but it requires `claude` CLI access. Set up API credentials in your CI environment.

### Q: What does triangular verification actually check?
Agent B reads your code without seeing requirements and describes what it does.
Agent C compares that description against your requirements.
If they match → PASS. If not → the discrepancy report lists exactly what's wrong.
