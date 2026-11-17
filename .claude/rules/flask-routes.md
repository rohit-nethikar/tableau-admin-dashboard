---
name: flask-routes
description: Flask blueprint routes and HTTP handlers
paths:
  - routes/*.py
---

## Routes Structure

All HTTP handlers are in `routes/` as standalone blueprint modules. Each route file typically:
- Imports necessary services/db functions
- Defines a blueprint with `@bp.route()` decorators
- Keeps handlers thin, delegates to service layer
- Uses `session` for site/user context

## Common Patterns

**Error responses:**
- Return `jsonify({"error": "message"})` with appropriate status code
- Check session for site context: `session.get("site")`

**Database access:**
- All via `db.fetch_*()` or `db.update_*()` functions
- No direct SQL; use the wrapper functions

**Service calls:**
- Import from root-level modules (email_service, caching_service, etc.)
- Services are pre-initialized; just call functions

## Common Issues to Check

- Missing site context check (should validate session["site"] exists)
- Not handling missing data gracefully (NoneType errors)
- Circular imports (avoid importing app.py into route files)
