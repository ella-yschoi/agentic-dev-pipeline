#!/bin/bash
# agentic-dev-pipeline.sh — Project-agnostic agentic dev pipeline
# Iteration: implement → quality gates → triangular verify → self-correct
#
# Required env vars:
#   PROMPT_FILE       — path to the PROMPT.md for the feature
#   REQUIREMENTS_FILE — path to the requirements doc (for triangular verification)
#
# Optional env vars (auto-detected if not set):
#   OUTPUT_DIR, LINT_CMD, TEST_CMD, SECURITY_CMD, SRC_DIRS, BASE_BRANCH, MAX_ITERATIONS
#
# Usage:
#   PROMPT_FILE=PROMPT.md REQUIREMENTS_FILE=requirements.md bash agentic-dev-pipeline.sh [max_iterations]

set -euo pipefail

# Claude Code nested call unblock (must be before any claude invocation)
unset CLAUDECODE 2>/dev/null || true

# Resolve SCRIPT_DIR (follows symlinks, macOS compatible)
_self="$0"
[ -L "$_self" ] && _self="$(readlink "$_self")"
SCRIPT_DIR="$(cd "$(dirname "$_self")" && pwd)"
unset _self

# Source shared detection library
# shellcheck source=detect-project.sh
. "$SCRIPT_DIR/detect-project.sh"

# Pre-flight: verify claude CLI exists
if ! command -v claude &>/dev/null; then
  echo "ERROR: 'claude' CLI not found in PATH. Install Claude Code first."
  exit 1
fi

# --- Required inputs ---
PROMPT_FILE="${PROMPT_FILE:?ERROR: PROMPT_FILE is required. Set it to the path of your prompt file.}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:?ERROR: REQUIREMENTS_FILE is required. Set it to the path of your requirements file.}"

# --- Auto-detect project configuration ---
detect_project_type
detect_lint_cmd
detect_test_cmd
detect_security_cmd
detect_src_dirs

# --- Configurable defaults ---
MAX_ITERATIONS=${1:-${MAX_ITERATIONS:-5}}
OUTPUT_DIR="${OUTPUT_DIR:-.agentic-dev-pipeline}"
LOOP_LOG="$OUTPUT_DIR/loop-execution.log"
FEEDBACK_FILE="$OUTPUT_DIR/feedback.txt"

mkdir -p "$OUTPUT_DIR"

# --- Validate inputs ---
if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: Prompt file not found: $PROMPT_FILE"
  exit 1
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "ERROR: Requirements file not found: $REQUIREMENTS_FILE"
  exit 1
fi

ITERATION=0
START_TIME=$(date +%s)

log() {
  local msg="[$(date '+%H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOOP_LOG"
}

log "=== Agentic Dev Pipeline ==="
print_detected_config | tee -a "$LOOP_LOG"
log "Max iterations: $MAX_ITERATIONS"
log "Prompt: $PROMPT_FILE"
log "Requirements: $REQUIREMENTS_FILE"
log "Output dir: $OUTPUT_DIR"
log "Started: $(date)"
log ""

while [ "$ITERATION" -lt "$MAX_ITERATIONS" ]; do
  ITERATION=$((ITERATION + 1))
  ITER_START=$(date +%s)

  log "--- Iteration $ITERATION / $MAX_ITERATIONS ---"

  # ============================================
  # Phase 1: Implementation (or fix)
  # ============================================
  log "[Phase 1] Agent A: Implement/Fix"

  if [ "$ITERATION" -eq 1 ]; then
    claude --print -p "$(cat "$PROMPT_FILE")" >> "$LOOP_LOG" 2>&1
  else
    FEEDBACK=$(cat "$FEEDBACK_FILE" 2>/dev/null || echo "No specific feedback available")
    claude --print -p "
Read $PROMPT_FILE for the full requirements.

Previous iteration ($((ITERATION - 1))) failed with this feedback:
---
$FEEDBACK
---

Fix the issues described above. Do NOT start from scratch.
Read the existing code first, then make targeted fixes only.
After fixing, verify your changes match the requirements.
" >> "$LOOP_LOG" 2>&1
  fi

  log "[Phase 1] Agent A completed"

  # ============================================
  # Phase 2: Quality Gates (auto-detected)
  # ============================================
  log "[Phase 2] Quality gates"

  GATE_PASS=true
  GATE_OUTPUT=""

  # Lint
  if [ -n "${LINT_CMD:-}" ]; then
    log "[Phase 2] Running lint: $LINT_CMD"
    if LINT_OUT=$(eval "$LINT_CMD" 2>&1); then
      log "[Phase 2] Lint: PASS"
    else
      log "[Phase 2] Lint: FAIL"
      GATE_OUTPUT="Lint ($LINT_CMD) FAILED:\n$LINT_OUT"
      GATE_PASS=false
    fi
  else
    log "[Phase 2] Lint: SKIPPED (no lint command detected)"
  fi

  # Tests (only if lint passed)
  if [ "$GATE_PASS" = true ] && [ -n "${TEST_CMD:-}" ]; then
    log "[Phase 2] Running tests: $TEST_CMD"
    if TEST_OUT=$(eval "$TEST_CMD" 2>&1); then
      log "[Phase 2] Tests: PASS"
    else
      log "[Phase 2] Tests: FAIL"
      GATE_OUTPUT="Tests ($TEST_CMD) FAILED:\n$TEST_OUT"
      GATE_PASS=false
    fi
  elif [ "$GATE_PASS" = true ]; then
    log "[Phase 2] Tests: SKIPPED (no test command detected)"
  fi

  # Security (only if lint + tests passed)
  if [ "$GATE_PASS" = true ] && [ -n "${SECURITY_CMD:-}" ]; then
    log "[Phase 2] Running security scan: $SECURITY_CMD"
    if SECURITY_OUT=$(eval "$SECURITY_CMD" 2>&1); then
      log "[Phase 2] Security: PASS"
    else
      log "[Phase 2] Security: FAIL"
      GATE_OUTPUT="Security ($SECURITY_CMD) FAILED:\n$SECURITY_OUT"
      GATE_PASS=false
    fi
  elif [ "$GATE_PASS" = true ]; then
    log "[Phase 2] Security: SKIPPED (no security command detected)"
  fi

  if [ "$GATE_PASS" = false ]; then
    printf "%b" "$GATE_OUTPUT" > "$FEEDBACK_FILE"
    ITER_END=$(date +%s)
    log "[Phase 2] FAILED — looping back (iteration took $((ITER_END - ITER_START))s)"
    log ""
    continue
  fi
  log "[Phase 2] ALL PASSED"

  # ============================================
  # Phase 3: Triangular Verification
  # ============================================
  log "[Phase 3] Triangular verification"

  if REQUIREMENTS_FILE="$REQUIREMENTS_FILE" OUTPUT_DIR="$OUTPUT_DIR" BASE_BRANCH="${BASE_BRANCH:-main}" \
     bash "$SCRIPT_DIR/triangular-verify.sh" >> "$LOOP_LOG" 2>&1; then
    log "[Phase 3] PASSED"
  else
    if [ -f "$OUTPUT_DIR/discrepancy-report.md" ]; then
      cp "$OUTPUT_DIR/discrepancy-report.md" "$FEEDBACK_FILE"
    else
      echo "Triangular verification failed but no discrepancy report found." > "$FEEDBACK_FILE"
    fi
    ITER_END=$(date +%s)
    log "[Phase 3] FAILED — issues found, looping back (iteration took $((ITER_END - ITER_START))s)"
    log ""
    continue
  fi

  # ============================================
  # Phase 4: Complete
  # ============================================
  END_TIME=$(date +%s)
  TOTAL_TIME=$((END_TIME - START_TIME))

  log ""
  log "=== LOOP_COMPLETE ==="
  log "Finished in $ITERATION iteration(s), total ${TOTAL_TIME}s"
  log "Ended: $(date)"

  rm -f "$FEEDBACK_FILE"
  exit 0
done

# Max iterations reached
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

log ""
log "=== MAX ITERATIONS REACHED ==="
log "Completed $MAX_ITERATIONS iterations without full convergence."
log "Total time: ${TOTAL_TIME}s"
log "Review remaining issues in: $FEEDBACK_FILE"
log "Review full log in: $LOOP_LOG"
exit 1
