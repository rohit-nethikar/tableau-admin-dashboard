---
name: fix-bug
type: skill
description: Fix a bug with minimal changes and regression tests
---

# Fix Bug Skill

Fix a bug you've identified with the smallest safe change and appropriate tests.

## When to Use

- You know what's broken and where
- You want to fix it with the smallest possible change
- You want to avoid unrelated refactoring
- You want a regression test added

## How to Invoke

```
/fix-bug
```

Then provide context about the bug:
- What's broken and where
- Root cause (from investigation, or your own analysis)
- Expected behavior vs. actual behavior
- Any specific constraints or patterns to follow

## What This Skill Does

1. **Confirms the bug** — Locates and reproduces the exact failure
2. **Verifies root cause** — Reads only the failing code section (narrow reads)
3. **Makes minimal change** — Smallest fix, no refactoring or cleanup
4. **Adds regression test** — If test suite exists, creates a test that would fail before the fix
5. **Runs targeted tests** — Tests specific failure first, then related code
6. **Validates** — Ensures fix works and doesn't break nearby code

## Example Invocation

```
/fix-bug

Bug: The /findings endpoint crashes with NoneType error at routes/findings.py:123.
Root cause: db.fetch_findings() returns None when cache is empty; 
           the handler calls .get() on None without checking.
Expected: Handle missing data gracefully, return empty list.
Actual: TypeError: 'NoneType' object has no attribute 'get'
```

**Response would:**
1. Verify the bug location and reproduce the error
2. Make a minimal fix (add None check)
3. Add a test that fails before the fix, passes after
4. Run the test and related tests
5. Confirm no new errors in nearby code

## Code Quality Principles

**DO:**
- ✓ Make the smallest change that fixes the bug
- ✓ Follow existing code style in that function
- ✓ Add only necessary validation (None checks, input validation)
- ✓ Add a focused regression test
- ✓ Run tests: specific test → file → directory

**DON'T:**
- ❌ Refactor surrounding code
- ❌ Clean up style issues unrelated to the bug
- ❌ Add "while you're at it" improvements
- ❌ Change function signatures or abstractions
- ❌ Add new dependencies

## Testing Strategy

```
First:   pytest path/to/test.py::test_name -q       (the specific test)
Then:    pytest path/to/test.py -q                   (the whole test file)
Then:    pytest path/to/related_tests/ -q            (related test directory)
Last:    pytest -q                                   (full suite, only if above passes)
```

If no test suite exists, verify the fix manually with clear reproduction steps.

## Verification Checklist

Before marking the fix complete:
- [ ] Bug is fixed (error gone or behavior correct)
- [ ] No new errors in related code paths
- [ ] Syntax is valid: `python -m py_compile file.py`
- [ ] Regression test added (if test suite exists)
- [ ] Targeted tests pass
- [ ] No unrelated changes in the diff

## Common Bug-Fix Patterns

**Missing None check:**
```python
# Before: crashes on None
value = db.fetch_something(site)
return value.get('key')

# After: handles None gracefully
value = db.fetch_something(site)
if value is None:
    return default_value
return value.get('key')
```

**Missing validation:**
```python
# Before: assumes valid input
index = request.args.get('index')
return items[index]

# After: validates input
index = request.args.get('index')
try:
    index = int(index)
except (ValueError, TypeError):
    return jsonify({'error': 'Invalid index'}), 400
if index < 0 or index >= len(items):
    return jsonify({'error': 'Index out of bounds'}), 400
return items[index]
```

**Missing error handling:**
```python
# Before: crashes on API error
response = tableau_client.query(site)
return response['data']

# After: handles errors gracefully
try:
    response = tableau_client.query(site)
except Exception as e:
    logger.error(f"Tableau API error: {e}")
    return jsonify({'error': 'Failed to query Tableau'}), 503
return response.get('data', [])
```

## Next Steps

After the fix is verified:
1. Create a PR with the minimal change + test
2. Or close the issue if all problems are resolved
3. Or investigate further if the fix doesn't resolve the symptom

## What This Skill Does NOT Do

- ❌ Design new features
- ❌ Refactor code architecturally
- ❌ Clean up style or naming
- ❌ Change unrelated code
- ❌ Make speculative improvements
