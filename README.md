# agentic-dev-pipeline

AI가 코드 작성부터 품질 검증, 의도 검증까지 사람 개입 없이 반복 실행하는 Claude Code 스킬.

## 설치

```bash
# 스킬 디렉토리에 클론
git clone https://github.com/ella-yschoi/agentic-dev-pipeline.git ~/.agents/skills/agentic-dev-pipeline
```

Claude Code가 `~/.agents/skills/agentic-dev-pipeline/SKILL.md`를 자동으로 인식한다.

## Quick Start

```bash
cd <project-root>

PROMPT_FILE="path/to/PROMPT.md" \
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/agentic-dev-pipeline.sh
```

Claude Code 세션 안에서:

```
agentic-dev-pipeline Skill을 사용해서 <기능명>을 구현해줘.
PROMPT: path/to/PROMPT.md
Requirements: path/to/requirements.md
```

## 파이프라인 구조

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

## 지원 프로젝트 타입

`detect-project.sh`가 프로젝트 루트를 분석하여 자동 감지한다.

| Type | Detected by | Lint | Test | Security |
|------|------------|------|------|----------|
| Python | `pyproject.toml` | ruff / flake8 / pylint | pytest / unittest | semgrep / bandit |
| Node | `package.json` | eslint / npm lint | jest / vitest / npm test | semgrep / npm audit |
| Rust | `Cargo.toml` | cargo clippy | cargo test | semgrep / cargo-audit |
| Go | `go.mod` | golangci-lint / go vet | go test | semgrep / gosec |
| Custom | env vars | `LINT_CMD` | `TEST_CMD` | `SECURITY_CMD` |

감지 우선순위: **ENV var → Makefile target → package.json script → tool existence**

Python runner: `uv.lock` → `uv run`, `poetry.lock` → `poetry run`, otherwise bare.

## 환경변수

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

## 파일 구조

```
agentic-dev-pipeline/
├── SKILL.md                  ← Claude Code 스킬 정의
├── agentic-dev-pipeline.sh   ← 메인 루프 스크립트
├── detect-project.sh         ← 프로젝트 자동 감지
├── triangular-verify.sh      ← 삼각 검증 단독 실행
├── PROMPT-TEMPLATE.md        ← 범용 프롬프트 템플릿
└── README.md
```

## 삼각 검증만 단독 실행

```bash
REQUIREMENTS_FILE="path/to/requirements.md" \
bash ~/.agents/skills/agentic-dev-pipeline/triangular-verify.sh
```

## 출력 파일

`$OUTPUT_DIR/` (기본: `.agentic-dev-pipeline/`):

| File | Content |
|------|---------|
| `loop-execution.log` | Full execution log |
| `blind-review.md` | Agent B's blind code review |
| `discrepancy-report.md` | Agent C's requirements vs code comparison |
| `feedback.txt` | Last iteration's feedback (deleted on success) |

## 실험 결과

이 스킬을 사용한 실험 기록은 [renewal-review](https://github.com/ella-yschoi/renewal-review) 프로젝트의 `docs/logs/experiments-log.md`에서 확인할 수 있다.

## 필수 조건

- [Claude Code](https://claude.ai/claude-code) CLI (`claude` 명령이 PATH에 있어야 함)
- 프로젝트에 맞는 lint/test 도구 (하나 이상)

## 트러블슈팅

- **`claude` command not found**: `which claude`로 PATH 확인
- **Nested claude call blocked**: 터미널에서 직접 실행 권장 (스크립트에 `unset CLAUDECODE` 포함)
- **Wrong tools detected**: `LINT_CMD`, `TEST_CMD`, `SECURITY_CMD` 환경변수로 오버라이드
- **TRIANGULAR_PASS not achieved**: `$OUTPUT_DIR/discrepancy-report.md` 확인, requirements를 더 구체적으로 작성

## License

MIT
