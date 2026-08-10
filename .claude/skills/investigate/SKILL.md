---
name: investigate
type: skill
description: Diagnose bugs without changing code
---

# Investigate Skill

Diagnose a bug or understand a problem without modifying code.

## When to Use

- You've found a failing test, error, or unexpected behavior
- You need to understand the root cause before fixing
- You want to isolate the investigation from the fix

## How to Invoke

```
/investigate
```

Then provide context about the problem:
- Where it's failing (file, function, line number)
- What the error is
- Steps to reproduce (if applicable)
- Recent changes in git history (if applicable)

## What This Skill Does

1. **Searches narrowly** with `rg` (not broad recursion)
2. **Reads only relevant sections** (not entire files like db.py or tableau_client.py)
3. **Checks git history** for recent changes that might be related
4. **Traces the call flow** only as far as needed to understand the failure
5. **Uses explorer subagent** if investigation gets noisy or requires many file reads
6. **Stops at root cause** — does NOT fix the bug

## What You'll Get Back

✓ **Root cause** — What's actually broken and why  
✓ **Relevant files** — Specific file names with line numbers  
✓ **Call flow** — Which functions call what to trigger the failure  
✓ **Evidence** — Error messages, code snippets, git history  
✓ **Minimal fix** — Smallest change that would resolve it (not implemented)  
✓ **Uncertainties** — What needs verification or further investigation

## Example Invocation

```
/investigate

The /findings endpoint is returning a 500 error when I request POST /findings.
I see a NoneType error in the logs at routes/findings.py line 123.
The cache was just refreshed.
No recent changes in the findings routes.
```

**Response would include:**
- Root cause (e.g., "db.fetch_findings() returns None when site not in cache")
- Relevant code location
- Call stack showing how the error happens
- Smallest fix (e.g., "add None check before .get() call")
- Uncertainties (e.g., "verify if cache is guaranteed to be pre-warmed")

## Rules This Skill Follows

1. **Search narrowly** — Use path filters and specific patterns, not bare `rg`
2. **Read minimally** — Open only the failing function, not the whole file
3. **Check git history** — Use `git log -p file.py` to see recent changes
4. **Don't fix yet** — Stop once you know WHERE and WHY
5. **Use explorer agent** — If many file reads are needed, spawn Explore agent to keep context focused

## What This Skill Does NOT Do

- ❌ Modify code
- ❌ Run tests (that's for fix-bug skill)
- ❌ Refactor or clean up
- ❌ Read entire large files unnecessarily
- ❌ Make speculative API calls

## Next Steps

Once you have the root cause:
1. Tell Claude to `/fix-bug` with the diagnosis
2. Or create a new issue/task with the findings
3. Or investigate further with more specific search terms
