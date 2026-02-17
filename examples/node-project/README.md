# Example: Node.js Project

This example shows how to use `agentic-dev-pipeline` as a **standalone CLI tool** in a non-Python project.

## Setup

```bash
# Install as a CLI tool (one-time)
uv tool install agentic-dev-pipeline
# or: pipx install agentic-dev-pipeline

# Initialize config files in your project
cd my-node-app
agentic-dev-pipeline init
# → Creates .agentic-dev-pipeline.toml (no pyproject.toml found)
# → Creates PROMPT.md and requirements.md templates
```

## Project structure

```
my-node-app/
├── src/
├── tests/
├── package.json
├── PROMPT.md                      ← fill in per feature
├── requirements.md                ← fill in per feature
└── .agentic-dev-pipeline.toml     ← pipeline config
```

## Usage

After filling in `PROMPT.md` and `requirements.md`:

```bash
# Zero-flag — reads config from .agentic-dev-pipeline.toml
agentic-dev-pipeline run

# Or override any setting via flags
agentic-dev-pipeline run --max-iterations 3 --timeout 600
```

## How it works

1. `agentic-dev-pipeline detect` auto-detects your Node project:
   - Lint: `eslint` or `npm run lint`
   - Test: `jest`, `vitest`, or `npm test`
   - Security: `semgrep` or `npm audit`

2. You can override any detected command:
   ```bash
   LINT_CMD="npx eslint src/" agentic-dev-pipeline run
   TEST_CMD="npx vitest run" agentic-dev-pipeline run
   ```

3. Check detected config anytime:
   ```bash
   agentic-dev-pipeline detect
   ```
