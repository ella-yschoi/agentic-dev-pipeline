# PROMPT Template — Agentic Dev Pipeline

Copy this file into your project directory and fill in the placeholders.

---

# Feature: [Feature Name]

## Context

[Brief project description. What should the agent read before coding?]

Read the following for project context:
- [instruction file, e.g., CLAUDE.md, convention.md, CONTRIBUTING.md]
- [design doc, e.g., docs/design-doc.md, docs/architecture.md]

## Requirements

Read `[path/to/requirements.md]` for full requirements.

Summary:
1. [Key requirement 1]
2. [Key requirement 2]
3. [Key requirement 3]

## Existing Patterns to Follow

[Point to existing files/modules the agent should use as reference for style and structure.]

- Model example: `[path/to/existing/model.py]`
- Test example: `[path/to/existing/test_file.py]`

## Completion Criteria

- [ ] All functional requirements implemented
- [ ] Lint passes (0 errors)
- [ ] All tests pass (existing + new)
- [ ] Security scan passes (if configured)
- [ ] Project conventions followed

## On Failure

- Lint failure: read error output, fix specific issues
- Test failure: read failing test output, fix the implementation
- Security failure: read scan report, fix flagged issues
- Triangular verification failure: read discrepancy-report.md, fix each listed issue

## Completion Signal

When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
