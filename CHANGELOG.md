# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Tool detection now falls back to active venv (`sys.prefix`) when commands are not found on PATH
- `ruff` and `bandit` now use runner prefix (`uv run`/`poetry run`) consistently like other Python tools

### Added
- `domain.py`: Domain types — `GateStatus`, `IterationOutcome` enums, `GateResult`, `IterationMetrics`, `PipelineMetrics` dataclasses
- `runner.py`: `ClaudeRunner` protocol + `CliClaudeRunner` implementation (unified claude subprocess logic)
- `GateStatus` and `ClaudeRunner` added to public exports (`__init__.py`)
- Parallel gate execution (`--parallel-gates` / `PARALLEL_GATES`)
- Plugin gate support (`--plugin-dir` / `PLUGIN_DIR`)
- Python API: `Pipeline` class with `.add_gate()`, `.run()`, `.verify()`, `.detect()`
- Hierarchical config resolution (CLI > pyproject.toml > .toml > env > defaults)
- `agentic-dev-pipeline init` scaffolding command

### Changed
- Full Python rewrite of all shell scripts (pipeline, detect, verify)
- pytest-based test suite replacing bats
- Structured JSON logging and metrics collection
- CLI entry point via `python -m agentic_dev_pipeline`
- Decomposed `run_pipeline()` God Function into phase functions (`_run_implementation_phase`, `_run_quality_gates`, etc.)
- Removed duplicate `_run_claude()` from `verify.py` — now uses `ClaudeRunner`
- Removed `sys.argv` hack in `cli.py` verify command — directly calls `run_triangular_verification()`
- Webhook notification switched from `curl` subprocess to `urllib.request`
- Extracted `_prepare()` method in `api.py` to remove duplicate setup logic
- `GateFunction` type alias moved from `config.py` to `domain.py` (re-exported for backward compat)
- Magic strings replaced with `GateStatus`/`IterationOutcome` enums
- `TRIANGULAR_PASS` string centralized as `domain.TRIANGULAR_PASS_MARKER`

## [0.1.0] - 2026-02-16

### Added
- Initial release of agentic-dev-pipeline skill
- Main pipeline orchestrator (`agentic-dev-pipeline.sh`)
- Project auto-detection library (`detect-project.sh`) — Python, Node, Rust, Go
- Triangular verification (`triangular-verify.sh`) — Agent B blind review + Agent C discrepancy
- PROMPT template (`PROMPT-TEMPLATE.md`)
- Skill definition (`SKILL.md`)
- README with full documentation
