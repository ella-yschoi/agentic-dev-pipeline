#!/bin/bash
# detect-project.sh — Project auto-detection library
# Source this file from self-correcting-loop.sh and triangular-verify.sh
# All functions are pure detectors; they set variables but never modify files.

# Usage:
#   . "$(dirname "$0")/detect-project.sh"
#   detect_project_type   # sets PROJECT_TYPE
#   detect_lint_cmd       # sets LINT_CMD
#   detect_test_cmd       # sets TEST_CMD
#   detect_security_cmd   # sets SECURITY_CMD
#   detect_src_dirs       # sets SRC_DIRS
#   ...

# ---------- helpers ----------

_cmd_exists() { command -v "$1" &>/dev/null; }

_has_makefile_target() {
  [ -f Makefile ] && grep -qE "^$1:" Makefile 2>/dev/null
}

_has_npm_script() {
  [ -f package.json ] || return 1
  if _cmd_exists node; then
    node -e "
      const pkg = JSON.parse(require('fs').readFileSync('package.json','utf8'));
      process.exit((pkg.scripts && pkg.scripts[process.argv[1]]) ? 0 : 1);
    " "$1" 2>/dev/null
  elif _cmd_exists python3; then
    python3 -c "
import json, sys
d = json.load(open('package.json'))
sys.exit(0 if sys.argv[1] in d.get('scripts', {}) else 1)
" "$1" 2>/dev/null
  else
    # Fallback: grep for the script name in package.json
    grep -q "\"$1\"" package.json 2>/dev/null
  fi
}

# Detect Python runner: uv > poetry > bare
_python_runner() {
  if [ -f uv.lock ] && _cmd_exists uv; then
    echo "uv run"
  elif [ -f poetry.lock ] && _cmd_exists poetry; then
    echo "poetry run"
  else
    echo ""
  fi
}

# ---------- detect_project_type ----------

detect_project_type() {
  if [ -n "${PROJECT_TYPE:-}" ]; then return; fi

  if [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then
    PROJECT_TYPE="python"
  elif [ -f package.json ]; then
    PROJECT_TYPE="node"
  elif [ -f Cargo.toml ]; then
    PROJECT_TYPE="rust"
  elif [ -f go.mod ]; then
    PROJECT_TYPE="go"
  else
    PROJECT_TYPE="unknown"
  fi
  export PROJECT_TYPE
}

# ---------- detect_lint_cmd ----------

detect_lint_cmd() {
  if [ -n "${LINT_CMD:-}" ]; then return; fi

  detect_project_type
  detect_src_dirs

  # 1. Makefile target
  if _has_makefile_target lint; then
    LINT_CMD="make lint"
    export LINT_CMD; return
  fi

  # 2. npm script
  if [ "$PROJECT_TYPE" = "node" ] && _has_npm_script lint; then
    LINT_CMD="npm run lint"
    export LINT_CMD; return
  fi

  # 3. Tool existence by project type
  local runner
  runner=$(_python_runner)

  case "$PROJECT_TYPE" in
    python)
      if _cmd_exists ruff; then
        LINT_CMD="ruff check $SRC_DIRS"
      elif _cmd_exists flake8; then
        LINT_CMD="${runner:+$runner }flake8 $SRC_DIRS"
      elif _cmd_exists pylint; then
        LINT_CMD="${runner:+$runner }pylint $SRC_DIRS"
      else
        LINT_CMD=""
      fi
      ;;
    node)
      if _cmd_exists eslint; then
        LINT_CMD="npx eslint $SRC_DIRS"
      else
        LINT_CMD=""
      fi
      ;;
    rust)
      LINT_CMD="cargo clippy -- -D warnings"
      ;;
    go)
      LINT_CMD="golangci-lint run ./..."
      if ! _cmd_exists golangci-lint; then
        LINT_CMD="go vet ./..."
      fi
      ;;
    *)
      LINT_CMD=""
      ;;
  esac
  export LINT_CMD
}

# ---------- detect_test_cmd ----------

detect_test_cmd() {
  if [ -n "${TEST_CMD:-}" ]; then return; fi

  detect_project_type

  # 1. Makefile target
  if _has_makefile_target test; then
    TEST_CMD="make test"
    export TEST_CMD; return
  fi

  # 2. npm script
  if [ "$PROJECT_TYPE" = "node" ] && _has_npm_script test; then
    TEST_CMD="npm test"
    export TEST_CMD; return
  fi

  # 3. Tool existence by project type
  local runner
  runner=$(_python_runner)

  case "$PROJECT_TYPE" in
    python)
      if _cmd_exists pytest; then
        TEST_CMD="${runner:+$runner }pytest -q"
      elif [ -d tests ] || [ -d test ]; then
        TEST_CMD="${runner:+$runner }python -m unittest discover"
      else
        TEST_CMD=""
      fi
      ;;
    node)
      if _cmd_exists jest; then
        TEST_CMD="npx jest"
      elif _cmd_exists vitest; then
        TEST_CMD="npx vitest run"
      else
        TEST_CMD=""
      fi
      ;;
    rust)
      TEST_CMD="cargo test"
      ;;
    go)
      TEST_CMD="go test ./..."
      ;;
    *)
      TEST_CMD=""
      ;;
  esac
  export TEST_CMD
}

# ---------- detect_security_cmd ----------

detect_security_cmd() {
  if [ -n "${SECURITY_CMD+x}" ]; then return; fi  # allow empty override to skip

  detect_project_type
  detect_src_dirs

  # 1. semgrep (works for most languages)
  if _cmd_exists semgrep; then
    SECURITY_CMD="semgrep scan --config auto --quiet $SRC_DIRS"
    export SECURITY_CMD; return
  fi

  # 2. Language-specific fallbacks
  case "$PROJECT_TYPE" in
    python)
      if _cmd_exists bandit; then
        SECURITY_CMD="bandit -r $SRC_DIRS -q"
      else
        SECURITY_CMD=""
      fi
      ;;
    node)
      SECURITY_CMD="npm audit --audit-level=high"
      ;;
    rust)
      if _cmd_exists cargo-audit; then
        SECURITY_CMD="cargo audit"
      else
        SECURITY_CMD=""
      fi
      ;;
    go)
      if _cmd_exists gosec; then
        SECURITY_CMD="gosec ./..."
      else
        SECURITY_CMD=""
      fi
      ;;
    *)
      SECURITY_CMD=""
      ;;
  esac
  export SECURITY_CMD
}

# ---------- detect_src_dirs ----------

detect_src_dirs() {
  if [ -n "${SRC_DIRS:-}" ]; then return; fi

  local dirs=()
  for d in src app lib pkg; do
    [ -d "$d" ] && dirs+=("$d/")
  done

  if [ ${#dirs[@]} -gt 0 ]; then
    SRC_DIRS="${dirs[*]}"
  else
    SRC_DIRS="."
  fi
  export SRC_DIRS
}

# ---------- detect_instruction_files ----------

detect_instruction_files() {
  if [ -n "${INSTRUCTION_FILES:-}" ]; then return; fi

  local files=()
  local seen=""

  # Static candidates (safe — no glob)
  for f in CLAUDE.md convention.md CONTRIBUTING.md; do
    if [ -f "$f" ] && [[ "$seen" != *"|$f|"* ]]; then
      files+=("$f")
      seen="${seen}|$f|"
    fi
  done

  # Glob only if the directory exists (avoids zsh "no matches found" crash)
  if [ -d .claude/rules ]; then
    for match in .claude/rules/*.md; do
      if [ -f "$match" ] && [[ "$seen" != *"|$match|"* ]]; then
        files+=("$match")
        seen="${seen}|$match|"
      fi
    done
  fi

  INSTRUCTION_FILES="${files[*]}"
  export INSTRUCTION_FILES
}

# ---------- detect_design_docs ----------

detect_design_docs() {
  if [ -n "${DESIGN_DOCS:-}" ]; then return; fi

  local files=()
  for f in docs/design-doc.md docs/architecture.md docs/design.md ARCHITECTURE.md; do
    [ -f "$f" ] && files+=("$f")
  done

  DESIGN_DOCS="${files[*]}"
  export DESIGN_DOCS
}

# ---------- detect_changed_files ----------

detect_changed_files() {
  if [ -n "${CHANGED_FILES:-}" ]; then return; fi

  local base="${BASE_BRANCH:-main}"
  detect_project_type

  # Collect from ALL sources: committed diff + staged + unstaged + untracked
  local committed staged unstaged untracked

  # 1. Committed changes on branch (vs base)
  committed=$(git diff --name-only "$base"..HEAD 2>/dev/null | head -200) || true

  # 2. Staged changes (git add'd but not committed — Agent A's work)
  staged=$(git diff --name-only --cached 2>/dev/null | head -200) || true

  # 3. Unstaged modifications to tracked files
  unstaged=$(git diff --name-only HEAD 2>/dev/null | head -200) || true

  # 4. Untracked new files (Agent A often creates new files)
  untracked=$(git ls-files --others --exclude-standard 2>/dev/null | head -200) || true

  # Merge all sources and deduplicate
  CHANGED_FILES=$(printf "%s\n%s\n%s\n%s" "$committed" "$staged" "$unstaged" "$untracked" \
    | grep -v '^$' | sort -u)

  # Final fallback: find source files by extension
  if [ -z "$CHANGED_FILES" ]; then
    local ext_pattern
    case "$PROJECT_TYPE" in
      python) ext_pattern="-name '*.py'" ;;
      node)   ext_pattern="-name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx'" ;;
      rust)   ext_pattern="-name '*.rs'" ;;
      go)     ext_pattern="-name '*.go'" ;;
      *)      ext_pattern="-name '*.py' -o -name '*.ts' -o -name '*.js' -o -name '*.rs' -o -name '*.go'" ;;
    esac
    CHANGED_FILES=$(eval "find . -maxdepth 5 -type f \\( $ext_pattern \\) -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/target/*' -not -path '*/__pycache__/*'" 2>/dev/null | sort | head -200) || true
  fi

  if [ -z "$CHANGED_FILES" ]; then
    CHANGED_FILES="No changed files detected"
  fi
  export CHANGED_FILES
}

# ---------- print_detected_config ----------

print_detected_config() {
  detect_project_type
  detect_lint_cmd
  detect_test_cmd
  detect_security_cmd
  detect_src_dirs
  detect_instruction_files
  detect_design_docs

  echo "=== Detected Project Configuration ==="
  echo "  PROJECT_TYPE:      $PROJECT_TYPE"
  echo "  SRC_DIRS:          $SRC_DIRS"
  echo "  LINT_CMD:          ${LINT_CMD:-<none — will skip>}"
  echo "  TEST_CMD:          ${TEST_CMD:-<none — will skip>}"
  echo "  SECURITY_CMD:      ${SECURITY_CMD:-<none — will skip>}"
  echo "  INSTRUCTION_FILES: ${INSTRUCTION_FILES:-<none>}"
  echo "  DESIGN_DOCS:       ${DESIGN_DOCS:-<none>}"
  echo "  BASE_BRANCH:       ${BASE_BRANCH:-main}"
  echo "  OUTPUT_DIR:        ${OUTPUT_DIR:-.self-correcting-loop}"
  echo "======================================="
}
