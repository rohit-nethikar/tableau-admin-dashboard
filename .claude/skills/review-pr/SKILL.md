---
name: review-pr
type: skill
description: Review code changes for correctness, security, and regressions
---

# Review PR Skill

Review code changes on the current branch for correctness, security, data integrity, and regressions.

## When to Use

- You have changes committed on a branch and want a code review
- You want to verify the changes are safe before merging
- You want to catch correctness bugs, security issues, and regressions
- You want feedback on missing tests

## How to Invoke

```
/review-pr
```

The skill will automatically examine your git diff and review the changes.

Optionally, provide context:
- What the changes are trying to accomplish
- Any known risks or edge cases
- Parts of the diff you're uncertain about

## What This Skill Does

1. **Reviews git diff** — Examines only changed lines and directly affected code
2. **Checks correctness** — Logic, edge cases, error handling
3. **Verifies regressions** — Function signature changes, import updates, breaking changes
4. **Audits security** — SQL injection, input validation, credential exposure, file safety
5. **Validates data integrity** — Database changes, atomicity, audit logging
6. **Checks Flask/project patterns** — Site context validation, service layer usage, config access
7. **Identifies missing tests** — For new features or critical bug fixes

## Review Focus (in priority order)

### 1. Correctness
- [ ] Does the logic implement the intended behavior?
- [ ] Are there off-by-one errors or typos?
- [ ] Do variables match their usage?
- [ ] Is control flow clear and correct?
- [ ] Are return values consistent with their type?

### 2. Error Handling
- [ ] Are exceptions caught appropriately?
- [ ] Is error context logged?
- [ ] Are edge cases handled (None, empty, missing keys)?
- [ ] Are HTTP responses appropriate status codes?
- [ ] Are API/database errors handled?

### 3. Regressions
- [ ] Could this change break existing features?
- [ ] Are function signatures updated everywhere they're called?
- [ ] Are imports updated (no missing imports, no stale ones)?
- [ ] Are schema changes backward-compatible?
- [ ] Are dependent tests updated?

### 4. Security
- [ ] Are SQL queries parameterized (? placeholders, no string concat)?
- [ ] Is user input validated before use?
- [ ] Are secrets/credentials logged or exposed?
- [ ] Are file operations safe (no directory traversal, path validation)?
- [ ] Are session/site contexts validated?
- [ ] Are permission checks in place if needed?

### 5. Data Integrity
- [ ] Are database writes atomic and consistent?
- [ ] Is the audit log updated for state-changing operations?
- [ ] Could the change cause data loss or corruption?
- [ ] Are transactions used where needed?
- [ ] Is cache consistency maintained?

### 6. Flask/Project-Specific Patterns
- [ ] Is site context validated in route handlers?
- [ ] Are database calls made only through db.py functions?
- [ ] Is config accessed via `settings.key` not hardcoded?
- [ ] Are blueprints registered in app.py?
- [ ] Are service functions reused, not duplicated?
- [ ] Is the service layer thin (routes) vs. thick (logic)?

### 7. Missing Tests
- [ ] New features have tests?
- [ ] Critical bug fixes have regression tests?
- [ ] Tests verify the actual behavior, not just coverage?

## Example Review

```
## Correctness ✓
Logic is sound. Permission check is correct.

## Error Handling ⚠️
Line 42: db.fetch_user() can return None, but .get() is called without checking.
→ Add: if user is None: return jsonify(...), 503

## Regressions ✓
Function signature unchanged. Imports complete. No breaking changes.

## Security ✓
SQL uses parameterized query. Input validated. No credentials logged.

## Data Integrity ✓
Audit log updated for permission change. Good.

## Pattern Adherence ✓
Uses db.fetch_* functions. Site context validated. Config accessed correctly.

## Tests ✓
Added test_permission_change(). Covers happy path and missing user case.

## Overall
Ready to merge after addressing the error handling on line 42.
```

## What to IGNORE (Not Review)

- ❌ Whitespace, indentation (unless it masks a logic error)
- ❌ Naming conventions (unless they're misleading)
- ❌ Comments (unless they're wrong or misleading)
- ❌ "Better" approaches (unless current code is incorrect)
- ❌ Code style preferences
- ❌ Performance micro-optimizations

**Only flag:**
- ✓ Bugs, logic errors, edge cases
- ✓ Security vulnerabilities
- ✓ Data integrity risks
- ✓ Breaking changes / regressions
- ✓ Missing error handling
- ✓ Missing tests for new/critical code
- ✓ Pattern violations (db access, site validation, etc.)

## Review Return Format

**If no issues:**
```
✓ Diff is correct. No issues detected.
```

**If issues found:**
```
## 🔴 CRITICAL: SQL Injection Risk
File: db.py:250
Line contains: f"WHERE status = '{status}'"
This allows injection. Use parameterized query with ? placeholder.

## 🟡 WARNING: Missing Error Handling
File: routes/findings.py:120
session["site"] access without None check.
Verify: Is session guaranteed to have 'site', or should we handle None?

## 🟢 SUGGESTION: Missing Test
Recommend: Add test for the new report export feature.
```

## How to Use the Review

1. Read the findings (critical issues first)
2. Fix each issue or explain why it's not an issue
3. Re-run `/review-pr` after fixing critical items
4. Merge once all critical and warning items are addressed

## Common Issues in This Repository

- Missing site context validation (`session.get('site')` without checking)
- Forgetting parameterized queries (string interpolation in SQL)
- Not logging to audit log on state changes
- Assuming cache data is fresh (should check timestamp)
- Missing error handling on Tableau API calls
- Not checking for None after db.fetch_* calls

## Next Steps

After review:
1. Address critical and warning findings
2. Re-run `/review-pr` if major changes made
3. Merge when all critical items are resolved
4. Or escalate to human review if uncertain

## What This Skill Does NOT Do

- ❌ Suggest refactoring or architecture changes
- ❌ Make style preferences
- ❌ Suggest performance optimizations unrelated to correctness
- ❌ Request documentation or comments
- ❌ Judge code taste or elegance
