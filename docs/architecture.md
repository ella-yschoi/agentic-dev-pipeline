# Architecture

## Pipeline Flow

```mermaid
flowchart TD
    A[PROMPT.md + requirements.md] --> B[Pipeline Start]
    B --> C{Iteration < MAX?}
    C -->|Yes| D[Phase 1: Implementation]
    C -->|No| Z[MAX ITERATIONS REACHED]

    D -->|First iteration| D1[Agent A: Full implementation]
    D -->|Subsequent| D2[Agent A: Targeted fixes from feedback]
    D1 --> E
    D2 --> E

    E[Phase 2: Quality Gates]
    E -->|Sequential| E1{Lint → Test → Security<br/>fast-fail}
    E -->|Parallel| E2{All gates concurrently<br/>collect all failures}
    E1 -->|All pass| G[Phase 3: Triangular Verification]
    E1 -->|Any fail| F[Save feedback]
    E2 -->|All pass| G
    E2 -->|Any fail| F

    F --> C

    G --> G1[Agent B: Blind Review]
    G1 --> G2[Agent C: Discrepancy Report]
    G2 --> H{TRIANGULAR_PASS?}
    H -->|Yes| I[Phase 4: LOOP_COMPLETE]
    H -->|No| F

    I --> J[Save metrics.json]
    Z --> J
```

## Module Dependency

```mermaid
graph LR
    CLI[cli.py] --> P[pipeline.py]
    CLI --> V[verify.py]
    CLI --> D[detect.py]

    API[api.py] --> P
    API --> V
    API --> D

    P --> V
    P --> D
    P --> L[log.py]
    P --> R[runner.py]
    P --> DOM[domain.py]

    V --> D
    V --> L
    V --> R
    V --> DOM

    CFG[config.py] --> DOM
```

## File Structure

```
src/agentic_dev_pipeline/
├── __init__.py          # Version + public API exports
├── __main__.py          # python -m entry point
├── api.py               # Pipeline class (library API)
├── cli.py               # Argument parsing, subcommands (run/verify/detect/init)
├── config.py            # Hierarchical config loading (PipelineConfig)
├── detect.py            # Pure detection functions (no side effects)
├── domain.py            # Domain types: enums, value objects, metrics
├── init_cmd.py          # init command scaffolding
├── log.py               # Logger with text/JSON modes
├── pipeline.py          # Main loop: implement → gates → verify → correct
├── runner.py            # ClaudeRunner protocol + CLI implementation
└── verify.py            # Triangular verification: Agent B + C
```

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Pipeline
    participant Runner as ClaudeRunner
    participant Gates as Quality Gates

    User->>CLI: run --prompt P --requirements R
    CLI->>Pipeline: run_pipeline(P, R)

    loop Each Iteration
        Pipeline->>Runner: Phase 1 (implement/fix)
        Runner-->>Pipeline: stdout (appended to log)

        Pipeline->>Gates: Phase 2 (lint, test, security, plugins)
        Gates-->>Pipeline: Pass/Fail + output

        alt Gate fails
            Pipeline->>Pipeline: Save feedback, continue loop
        end

        Pipeline->>Runner: Phase 3A (Agent B: blind review)
        Runner-->>Pipeline: blind-review.md

        Pipeline->>Runner: Phase 3B (Agent C: discrepancy report)
        Runner-->>Pipeline: discrepancy-report.md

        alt Verification fails
            Pipeline->>Pipeline: Save feedback, continue loop
        end
    end

    Pipeline-->>CLI: converged=true/false
    Pipeline->>Pipeline: Save metrics.json
    CLI-->>User: Exit code 0/1
```

## Key Design Decisions

### Why Three Agents?
- **Agent A** implements code — it has full context but is biased toward its own work
- **Agent B** reviews code blindly — sees code but not requirements, so its description is unbiased
- **Agent C** compares — sees requirements and blind review but not code, detecting real gaps

This triangular approach catches bugs that single-agent review misses.

### Why Sequential AND Parallel Gates?
- **Sequential** (default): Fast-fail order. If lint fails, there's no point running tests on broken code. Each failure provides focused feedback for the next iteration.
- **Parallel** (`--parallel-gates`): Collects ALL failures at once. Useful when gates are independent and you want comprehensive feedback in a single iteration.

### Why ClaudeRunner Protocol?
`pipeline.py` and `verify.py` both call claude CLI. Instead of duplicating subprocess logic, a single `ClaudeRunner` protocol provides the abstraction. `CliClaudeRunner` is the default implementation; tests can inject a mock.

### Why Domain Types?
`domain.py` centralizes enums (`GateStatus`, `IterationOutcome`), value objects (`GateResult`), and metrics dataclasses. This eliminates magic strings scattered across pipeline.py and verify.py, and keeps backward-compatible `metrics.json` output via `to_dict()` methods.

### Why Subprocess for Claude?
The pipeline calls `claude --print -p "..."` via subprocess. This keeps the pipeline independent of Claude's internal API and works with any Claude Code installation.

### Eval Safety
Quality gate commands run via `subprocess.run(cmd, shell=True)` but are first checked against injection patterns (`$(...)`, backticks, `; rm`, etc.). Commands from env vars with unsafe patterns are blocked.
