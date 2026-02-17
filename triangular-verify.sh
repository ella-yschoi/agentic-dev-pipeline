#!/bin/bash
# triangular-verify.sh — Project-agnostic triangular verification
# Agent B (blind review) + Agent C (discrepancy report)
#
# Required env vars:
#   REQUIREMENTS_FILE — path to the requirements doc (source of truth)
#
# Optional env vars (auto-detected if not set):
#   OUTPUT_DIR, BASE_BRANCH, SRC_DIRS, INSTRUCTION_FILES, DESIGN_DOCS
#
# Usage:
#   REQUIREMENTS_FILE=requirements.md bash triangular-verify.sh

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
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:?ERROR: REQUIREMENTS_FILE is required.}"

# --- Auto-detect project configuration ---
detect_project_type
detect_src_dirs
detect_instruction_files
detect_design_docs
detect_changed_files

# --- Configurable defaults ---
OUTPUT_DIR="${OUTPUT_DIR:-.agentic-dev-pipeline}"
BLIND_REVIEW_FILE="$OUTPUT_DIR/blind-review.md"
DISCREPANCY_FILE="$OUTPUT_DIR/discrepancy-report.md"

mkdir -p "$OUTPUT_DIR"

# --- Build context file list for Agent B ---
CONTEXT_FILES=""
if [ -n "${INSTRUCTION_FILES:-}" ]; then
  CONTEXT_FILES="Project rules/conventions: $INSTRUCTION_FILES"
fi
if [ -n "${DESIGN_DOCS:-}" ]; then
  CONTEXT_FILES="${CONTEXT_FILES:+$CONTEXT_FILES\n}Design documents: $DESIGN_DOCS"
fi

echo "[triangular-verify] Started: $(date)"
echo "[triangular-verify] Requirements: $REQUIREMENTS_FILE"
echo "[triangular-verify] Changed files:"
echo "$CHANGED_FILES"
echo ""

# --- Agent B: Blind Review ---
echo "[triangular-verify] Phase B: Blind review (read code only, describe behavior)"

claude --print -p "
You are Agent B in a triangular verification process.

$(if [ -n "$CONTEXT_FILES" ]; then
  printf "Read the following files for project context:\n%b\n" "$CONTEXT_FILES"
fi)

Do NOT read any requirements document ($REQUIREMENTS_FILE).

The following files were recently changed or created:
$CHANGED_FILES

For each file:
1. Describe what this code does (behavior and intent, not just structure)
2. List any convention/rule violations found in the project rules
3. List potential issues, edge cases, or bugs

Output your analysis as structured markdown.
" > "$BLIND_REVIEW_FILE" 2>&1

echo "[triangular-verify] Blind review saved to $BLIND_REVIEW_FILE"

# --- Agent C: Discrepancy Report ---
echo "[triangular-verify] Phase C: Discrepancy report (requirements vs blind review)"

claude --print -p "
You are Agent C in a triangular verification process.

Read these two documents carefully:
1. $REQUIREMENTS_FILE (original requirements — the source of truth)
2. $BLIND_REVIEW_FILE (blind code analysis by another agent)

Do NOT read any code files directly.

Compare them and produce a discrepancy report with these sections:

## Requirements Met
List each requirement from the requirements doc that is confirmed by the blind review, with evidence.

## Requirements Missed
Requirements present in the requirements doc but NOT reflected in the blind review.

## Extra Behavior
Behavior described in the blind review but NOT in the requirements.

## Potential Bugs
Where the blind review contradicts or conflicts with requirements.

## Verdict
If ALL requirements are met and no critical issues found, output exactly on its own line:
TRIANGULAR_PASS

Otherwise, list each issue that must be fixed.
" > "$DISCREPANCY_FILE" 2>&1

echo "[triangular-verify] Discrepancy report saved to $DISCREPANCY_FILE"

# --- Result ---
echo ""
if grep -q "TRIANGULAR_PASS" "$DISCREPANCY_FILE"; then
  echo "[triangular-verify] RESULT: PASS"
  echo "[triangular-verify] Ended: $(date)"
  exit 0
else
  echo "[triangular-verify] RESULT: FAIL — issues found in $DISCREPANCY_FILE"
  echo "[triangular-verify] Ended: $(date)"
  exit 1
fi
