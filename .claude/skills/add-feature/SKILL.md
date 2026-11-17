---
name: add-feature
type: skill
description: Implement a new feature following existing patterns
---

# Add Feature Skill

Implement a new feature by reusing existing patterns and touching the fewest necessary files.

## When to Use

- You need to add new functionality
- You want to follow the project's existing architecture and patterns
- You want to avoid creating unnecessary new files or abstractions
- You want focused tests for the new code

## How to Invoke

```
/add-feature
```

Then describe what you want to build:
- What the feature is
- What problem it solves
- Any constraints or requirements
- Any specific files or patterns you want to follow

## What This Skill Does

1. **Finds existing patterns** — Searches for similar features already in the codebase
2. **Locates the architecture** — Determines which files to modify (routes/, db.py, services)
3. **Minimizes scope** — Reuses existing modules; creates new files only when unavoidable
4. **Implements the feature** — Adds code following the existing style and patterns
5. **Adds focused tests** — Creates tests for the new feature only
6. **Validates end-to-end** — Tests both the golden path and error cases

## Code Architecture (for this project)

```
HTTP Request → Routes (Flask blueprints) → Services (business logic) → DB (SQLite)

routes/        # Flask route handlers, thin layer
services/      # Business logic, named service functions
db.py          # All database access, single source of truth
config.yaml    # User settings (server_url, sites, etc.)
governance.yaml # Tunable weights (health factors, risk thresholds)
scheduler.py   # Background jobs (APScheduler)
```

## Where Code Belongs

| Feature Type | Location | Pattern |
|---|---|---|
| New HTTP endpoint | routes/ (existing file or new blueprint) | `@bp.route()` decorated function |
| New database query | db.py | `fetch_*()` or `update_*()` function with parameterized SQL |
| New business logic | Root-level service file | Standalone function called from routes or scheduler |
| New scheduled job | scheduler.py | Add to `schedule_jobs()` with APScheduler |
| New config setting | config.yaml + config.py | Add YAML key, add @property to Settings class |
| New governance weight | governance.yaml + governance_config.py | Add YAML key, load in config |

## Implementation Pattern: New Route

```python
# In routes/new_feature.py or add to existing routes/something.py
from flask import Blueprint, jsonify, session
import db

bp = Blueprint('new_feature', __name__)

@bp.route('/new-endpoint', methods=['GET'])
def get_new_data():
    # Validate site context
    site = session.get('site')
    if not site:
        return jsonify({'error': 'Site not selected'}), 400
    
    # Call service/db layer
    data = db.fetch_new_data(site)
    if data is None:
        return jsonify({'error': 'Data not available'}), 503
    
    return jsonify(data)

# In app.py, add to imports and register:
from routes import new_feature
app.register_blueprint(new_feature.bp)
```

## Implementation Pattern: New Database Function

```python
# In db.py
def fetch_new_data(site, filters=None):
    """Fetch new data for a site, optionally filtered."""
    query = """
        SELECT id, name, created_at FROM new_table
        WHERE site = ?
    """
    params = [site]
    
    if filters and filters.get('status'):
        query += " AND status = ?"
        params.append(filters['status'])
    
    query += " ORDER BY created_at DESC"
    return cursor.execute(query, tuple(params)).fetchall()
```

## Implementation Pattern: New Service Function

```python
# In new_service.py or add to existing service file
def compute_metric(items):
    """Compute a metric from a list of items."""
    if not items:
        return 0
    
    total = sum(item.get('value', 0) for item in items)
    return total / len(items)  # or whatever logic makes sense
```

## Testing Pattern

```python
# In tests/test_new_feature.py
import pytest
from new_feature import compute_metric

def test_compute_metric_empty():
    assert compute_metric([]) == 0

def test_compute_metric_single():
    assert compute_metric([{'value': 10}]) == 10

def test_compute_metric_multiple():
    items = [{'value': 10}, {'value': 20}, {'value': 30}]
    assert compute_metric(items) == 20  # average

def test_route_returns_data(client):
    response = client.get('/new-endpoint')
    assert response.status_code in [200, 503]  # either data or graceful error
```

## Validation Checklist

- [ ] Feature works end-to-end (golden path, happy case)
- [ ] Error cases handled gracefully (None, empty, missing data)
- [ ] Related features still work (no regressions)
- [ ] Code follows existing patterns (style, structure, naming)
- [ ] Tests pass (specific test → file → directory)
- [ ] Syntax valid: `python -m py_compile file.py`
- [ ] No unrelated refactoring or cleanup
- [ ] Config or governance changes documented if needed

## Common Pitfalls

- ❌ Creating new service files when you could reuse existing ones
- ❌ Forgetting to register a new blueprint in app.py
- ❌ Not validating site context in routes
- ❌ Assuming cache is fresh without checking timestamp
- ❌ Not handling None/missing data gracefully
- ❌ Adding new abstractions or helper classes unnecessarily
- ❌ Creating a new routes file when adding to an existing one would work

## Reuse Checklist

Before creating a new file:
- [ ] Check if there's a similar feature already (use `rg` to search)
- [ ] Can I add to an existing routes/ file?
- [ ] Can I add to an existing service file?
- [ ] Can I add the database function to db.py?
- [ ] Does this really need a new file, or am I over-engineering?

If you need 3+ new files, reconsider the design.

## Example: Add a "Recent Activity" View

**Search:** Find similar features (health scores, orphan detection)  
**Decide:** Use existing routes/analytics.py, add to db.py, service logic minimal  
**Implement:**
1. Add `fetch_recent_activity(site, limit=50)` to db.py
2. Add route `GET /activity` in routes/analytics.py
3. Add test for the query and route
4. Verify existing analytics features still work

**Result:** 2 files modified (db.py, routes/analytics.py), 1 test file, no new abstractions.

## Next Steps

After the feature is implemented and tested:
1. Create a PR with the feature + tests
2. Request review for correctness and regressions
3. Or request review with `/code-review` before opening a PR

## What This Skill Does NOT Do

- ❌ Design the feature (that's your job; this implements your design)
- ❌ Make architectural decisions (follow existing patterns instead)
- ❌ Create unnecessary abstractions
- ❌ Refactor existing code (unless needed for the feature)
- ❌ Add optional improvements or future-proofing
