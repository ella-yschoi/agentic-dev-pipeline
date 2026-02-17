# Example: Python Project

This example shows how to use `agentic-dev-pipeline` as a **dev dependency** in a Python project.

## Setup

```bash
# Add as dev dependency
uv add --dev agentic-dev-pipeline

# Initialize config files
agentic-dev-pipeline init
# → Adds [tool.agentic-dev-pipeline] to pyproject.toml
# → Creates PROMPT.md and requirements.md templates
```

## Project structure

```
my-python-app/
├── src/
│   └── my_app/
├── tests/
├── PROMPT.md              ← fill in per feature
├── requirements.md        ← fill in per feature
├── pyproject.toml         ← contains [tool.agentic-dev-pipeline]
└── run_pipeline.py        ← optional: Python API usage
```

## Usage

### CLI (zero-flag)

After filling in `PROMPT.md` and `requirements.md`:

```bash
agentic-dev-pipeline run
```

Config is read from `pyproject.toml` automatically.

### Python API

```bash
python run_pipeline.py
```

See `run_pipeline.py` for the code.
