# Claude Code Configuration

## Project Summary

Tableau Server governance dashboard: Flask app with modular routes, service layer (email, caching, sync), BigQuery integration, and SQLite cache. No auto-remediation; all writes are manual and audited.

**Key files:** app.py (Flask factory), db.py (cache + audit), routes/ (blueprints), services (tableau_client, email_service, caching_service), config.yaml (settings), governance.yaml (scoring weights).

## Search Before Reading

Before opening any file:
1. Use `rg` to find symbols, patterns, or context
2. Narrow glob patterns to specific directories
3. If searching across the whole codebase is tempting, use the `/explore` skill instead

## File Reading Rules

**DO:**
- Read only the sections you need (use `limit` parameter)
- Reuse recent diff/status output instead of re-reading unchanged files
- Check git history (`git log -p file.py`) for context before reading
- Use `rg -n` to jump to specific lines/functions before opening files

**DON'T:**
- `cat` large files (db.py is 1247 lines; tableau_client.py is 747)
- Load README.md or docs unless directly needed for the task
- Re-read files you just edited (Edit tool verifies)
- Search the whole repo with bare `rg` patterns — use exclusions or path limits

## Code Changes

- **Preserve architecture:** Flask app-factory, blueprint routes, service layer separation
- **Minimal scope:** Fix the issue, don't refactor adjacent code
- **No unrelated cleanup:** Leave dead code, style issues, and stale comments
- **Follow existing patterns:** Use the same error handling, logging, config access as surrounding code

## Flask-Specific Guidance

- **Blueprints:** Routes live in `routes/*.py` as standalone modules; import in `app.py`
- **Error handling:** Check for try/except patterns in route handlers and service methods
- **Database:** All DB access via `db.py` (functions, not ORM); SQLite cache, not app datastore
- **Config:** Use `config.settings.key` or load from `governance.yaml` via `governance_config.py`
- **Extensions:** Tableau client (TSC), BigQuery client pre-initialized; no circular imports
- **Scheduled tasks:** APScheduler in `scheduler.py`; define jobs there, not in routes

## Testing

The project has no existing test suite. When adding tests:
1. Create `tests/` directory at root if needed
2. Use pytest (`pip install pytest`)
3. Run narrow tests first: `pytest tests/test_name.py::test_func -q`
4. Never run the full suite without a specific reason

## Token Optimization

**Prefer:**
- `rg --count` to validate pattern matches before opening files
- `git diff HEAD~1` to see recent changes
- `git status` to avoid re-reading unchanged code
- `/explore quick` for targeted lookups
- `/explore medium` for multi-file patterns

**Avoid:**
- Broad recursive searches (`find . -name "*.py"` without limits)
- Loading large logs or debug output
- Speculative MCP tool calls (BigQuery, Tableau API) without scope

## Common Tasks

**Investigating a bug:**
1. Reproduce or locate failure
2. Use `/investigate` skill (or `/explore quick` if not available)
3. Read only the failing function/route
4. Check git history for recent changes
5. Confirm fix target before editing

**Adding a feature:**
1. Find the closest existing implementation (search for similar patterns)
2. Locate the handler/service layer responsible
3. Add code to the same module (no new files unless unavoidable)
4. Test the golden path

**Reviewing a PR:**
1. Use `/review-pr` skill or `git diff origin/main...HEAD`
2. Check only changed lines and directly related code
3. Focus on: correctness, regressions, security, error handling, data integrity
4. Ignore style/whitespace unless it masks logic errors

## Architecture Notes

- **Entry point:** `app.py` → `create_app()` → registers blueprints from `routes/`
- **Database:** `db.py` functions are the boundary; SQLite cache only (not source of truth)
- **Tableau integration:** `tableau_client.py` wraps TSC client; singleton per session
- **Email/alerts:** `email_service.py`, `alerts_engine.py` (scheduled via APScheduler)
- **BigQuery sync:** `bigquery_sync.py` runs on schedule, populates cache
- **Service layer:** caching_service, export_service, health_scoring, etc. — call from routes or scheduler
- **Config sources:** YAML files (config.yaml, governance.yaml), loaded at startup

## Context Management

Between unrelated tasks:
```
/clear
```

For long tasks:
```
/compact Preserve current objective, root cause, decisions, relevant files, changed files, failed approaches worth avoiding, test status, and remaining tasks.
```

Check context usage:
```
/context
```

## Custom Skills

This project includes four custom skills for common development workflows:

### Investigation (diagnose, don't fix)
```
/investigate
```
Diagnose a bug or understand a problem without modifying code. Returns root cause, relevant files, evidence, and the minimal fix (not implemented).

**Use when:** You've found a bug and need to understand why it's happening.

### Bug Fixes (minimal, tested)
```
/fix-bug
```
Fix a bug with the smallest possible change and appropriate regression tests. Follows the fix-then-test workflow.

**Use when:** You know what's broken and need to fix it safely.

### New Features (follow patterns)
```
/add-feature
```
Implement a feature by reusing existing patterns and touching the fewest necessary files. No unnecessary abstractions.

**Use when:** You need to build new functionality following the project's architecture.

### Code Review (correctness, security, regressions)

**Option A — Project skill:**
```
/review-pr
```
Reviews your current branch's diff for correctness, security, data integrity, and regressions. Custom for this repo.

**Option B — Built-in skill:**
```
/code-review
```
The standard Claude Code skill (more general-purpose).

**Use when:** You want to verify changes before merging.

## Final Verification

After making changes:
1. **Syntax check:** `python -m py_compile path/to/file.py`
2. **Type awareness:** Don't trust types without checking; Python is dynamically typed
3. **Imports:** Verify new imports are in requirements.txt
4. **Config changes:** Restart the app if config.yaml or governance.yaml was touched
5. **Database:** Check if migrations are needed; this project uses manual schema evolution in db.py

## Project-Specific Support

**Fully Supported:**
- ✅ Custom project-local Skills (`.claude/skills/`) — `/investigate`, `/fix-bug`, `/add-feature`, `/review-pr`
- ✅ Custom agents (`.claude/agents/`) — for specialized investigation and review
- ✅ Path-scoped rules (`.claude/rules/`) — auto-loaded for matching files
- ✅ Built-in skills (e.g., `/code-review`, `/simplify`, `/security-review`)
- ✅ Context management (`/clear`, `/compact`, `/context`)

**Not in this setup:**
- CI/CD hooks (no .gitlab-ci.yml or GitHub Actions configured)
- External databases or migration tools
- MCP integrations (local-first, no remote data sources required)

**Local-only, safe:**
- SQLite cache (no migrations needed, schema is in db.py)
- YAML config files (no external secrets stored)
- BigQuery optional (offline-first, only when credentials present)
