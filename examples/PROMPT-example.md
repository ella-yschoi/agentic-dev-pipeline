# Feature: User Authentication API

## Context

We're building a Python FastAPI backend for a task management app.
The project uses SQLAlchemy for ORM and Pydantic for validation.

Read the following for project context:
- CLAUDE.md
- docs/architecture.md

## Requirements

Read `docs/requirements-auth.md` for full requirements.

Summary:
1. POST /auth/register — create user with email + hashed password
2. POST /auth/login — return JWT access token
3. GET /auth/me — return current user info (requires valid token)
4. Password must be bcrypt-hashed, never stored in plaintext
5. JWT expiry: 30 minutes

## Existing Patterns to Follow

- Model example: `app/models/task.py`
- Router example: `app/routers/tasks.py`
- Test example: `tests/test_tasks.py`

## Completion Criteria

- [ ] All 3 endpoints implemented and return correct responses
- [ ] Lint passes (0 errors)
- [ ] All tests pass (existing + new auth tests)
- [ ] Security scan passes
- [ ] Passwords are bcrypt-hashed
- [ ] JWT tokens include user_id and have 30-min expiry

## On Failure

- Lint failure: read error output, fix specific issues
- Test failure: read failing test output, fix the implementation
- Security failure: read scan report, fix flagged issues (especially plaintext passwords)
- Triangular verification failure: read discrepancy-report.md, fix each listed issue

## Completion Signal

When ALL criteria met, output exactly:
<promise>LOOP_COMPLETE</promise>
