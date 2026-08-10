---
name: database
description: SQLite cache database, schema, and access patterns
paths:
  - db.py
  - instance/cache.db
---

## Database Layer

`db.py` is the ONLY interface to the SQLite cache. It contains:
- Schema initialization (CREATE TABLE)
- Query functions (fetch_*, update_*, insert_*)
- Audit log functions (fetch_audit_log, insert_audit_log)
- No ORM; raw SQL with parameterized queries

Database location: `instance/cache.db` (created on first run).

## Adding New Queries

When adding database access:
1. Add function to `db.py`, NOT to route files
2. Use parameterized queries (? placeholders, tuple args)
3. Handle None results gracefully
4. Log important changes to audit log if they affect state

## Schema Changes

Schema changes are not migrations; they're inline in `db.py`:
- Check if table exists before CREATE TABLE
- Add columns with ALTER TABLE if table already exists
- No downtime; just restart the app

## Key Tables

- `workbooks`, `datasources`, `projects`, `users`, `sites` — cached Tableau objects
- `findings` — remediation queue (status, owner, notes)
- `health_checks` — refresh reliability tracking
- `audit_log` — all manual state changes (owner overrides, status updates)
- `custom_views`, `account_numbers` — custom metadata

Inspect with: `sqlite3 instance/cache.db ".schema"`

## Common Mistakes

- Hardcoding site context (use parameter passing instead)
- Not checking for NULL values (SQLite returns None, not 0 or "")
- Assuming fresh data (cache is stale until next refresh; check timestamp)
