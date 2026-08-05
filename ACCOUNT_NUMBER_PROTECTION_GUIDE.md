# Account Number Protection Guide

## Problem Statement

Account numbers were being lost when users were refreshed from Tableau Server. We've implemented **4 layers of protection** to ensure this never happens again.

## 4 Layers of Protection

### Layer 1: Database-Level UPSERT (Automatic)
**File:** `db.py` - `replace_users()` function

**How it works:**
- Changed from `DELETE + INSERT` → to `UPSERT` pattern
- Updates existing users instead of recreating them
- **Preserves account_number column** automatically

**When it runs:**
- Every time users are refreshed from Tableau Server
- Every time you run a data sync

**Example:**
```python
INSERT INTO users(...) VALUES (...)
ON CONFLICT(id) DO UPDATE SET
    -- Update these fields
    name = excluded.name,
    email = excluded.email,
    -- But NOT account_number (preserved!)
```

---

### Layer 2: Automatic Backup (Before Every Sync)
**File:** `account_number_watchdog.py` - Watchdog class

**How it works:**
- Automatically backs up account numbers before any sync
- Stores as JSON in `instance/account_backups/`
- Timestamped files for version history

**When it runs:**
- Automatically when you run `populate-missing-custom-view-owners.py`
- Triggered by `pre_sync_backup()` function
- Creates files like: `accounts_2026-08-05T10_30_45.json`

**Example:**
```json
{
  "timestamp": "2026-08-05T10:30:45",
  "count": 67,
  "accounts": [
    {"id": "...", "email": "user@mayo.edu", "account_number": "7041026"}
  ]
}
```

---

### Layer 3: Automatic Verification & Restore (After Every Sync)
**File:** `account_number_watchdog.py` - `post_sync_verify()`

**How it works:**
- Verifies account numbers are present after sync
- If lost, automatically restores from latest backup
- Reports results in logs

**When it runs:**
- Automatically after every BigQuery sync
- Reports results to console and log files

**Example Output:**
```
Step 3: Verifying accounts...
Account number count: 67
✅ Post-sync verification passed: 67 accounts
✅ Verification passed - accounts are safe!
```

---

### Layer 4: Startup Verification (Automatic)
**File:** `app.py` - `create_app()` function

**How it works:**
- Verifies account numbers when Flask app starts
- Auto-restores from backup if any are missing
- Warns if restoration occurred

**When it runs:**
- Every time Flask app starts (app.py)
- Happens silently if all is well
- Warns only if restoration was needed

**Example Output:**
```
⚠️ WARNING: Account numbers were lost and have been auto-restored from backup
```

---

## Usage

### Automatic (Recommended)
Everything runs automatically:
1. Run sync script
2. Backup created automatically
3. Sync happens
4. Verification and auto-restore if needed
5. Everything logged

```bash
python populate-missing-custom-view-owners.py
# That's it! All protection layers active.
```

### Manual Verification
Check status anytime:

```bash
# Verify now (will restore if needed)
python account_number_watchdog.py verify

# Full audit report
python account_number_watchdog.py audit

# Manual backup
python account_number_backup.py backup

# Manual restore
python account_number_backup.py restore
```

---

## Files & Responsibilities

| File | Purpose | Runs |
|------|---------|------|
| **db.py** | UPSERT pattern to preserve data | Auto (every sync) |
| **account_number_watchdog.py** | Monitor & protect account numbers | Auto (with sync) |
| **account_number_backup.py** | Create/restore backups | Auto (watchdog) + Manual |
| **app.py** | Startup verification | Auto (app launch) |
| **populate-missing-custom-view-owners.py** | Orchestrate sync with protection | On demand |

---

## Protection Flow

### Before (Vulnerable)
```
[Sync] → [Delete all users] → [Insert new users]
              ↓
      Account numbers LOST ❌
```

### After (Protected)
```
[Sync] → [Backup accounts]
              ↓
        [Update existing users]
        (account_number preserved)
              ↓
        [Verify accounts exist]
              ↓
        If missing: [Auto-restore] ✅
              ↓
        [Log everything]
```

---

## Log Files

All activity is logged to `instance/logs/`:

- **account_watchdog.log** - Watchdog actions and verifications
- **account_changes.log** - Detailed JSON log of every action

### Example Log Entry
```json
{
  "timestamp": "2026-08-05T10:30:45.123456",
  "action": "POST_SYNC_VERIFY",
  "details": "67 accounts present",
  "status": "SUCCESS",
  "account_count": 67
}
```

---

## Backup Directory Structure

Backups stored in: `instance/account_backups/`

```
account_backups/
├── accounts_2026-08-05T10_30_45.json  (Latest - auto-used for restore)
├── accounts_2026-08-04T14_15_30.json  (Previous)
├── accounts_2026-08-03T09_20_10.json  (Older)
└── ...
```

Each backup contains:
- Timestamp of when backup was created
- Count of accounts backed up
- Full list of email → account_number mappings

---

## Scenarios & Recovery

### Scenario 1: Sync Completes Successfully
✅ **All 4 layers ensure safety:**
1. Backup created before
2. UPSERT preserves data during
3. Verification confirms after
4. Startup check on next run

**You see:** ✅ All green

### Scenario 2: Account Numbers Lost After Sync
⚠️ **Auto-recovery triggered:**
1. Post-sync verification detects loss
2. Auto-restore from latest backup (Layer 3)
3. Verification runs again
4. Results logged

**You see:** ⚠️ Warning → ✅ Auto-restored

### Scenario 3: App Restart After Loss
⚠️ **Startup verification triggers:**
1. Flask app starts
2. Startup check detects missing accounts (Layer 4)
3. Auto-restore from backup
4. App continues normally

**You see:** ⚠️ Warning at startup → ✅ Auto-fixed

### Scenario 4: Multiple Syncs in Session
✅ **Protection stacks:**
1. First sync: Backup → Sync → Verify
2. Second sync: Backup (new) → Sync → Verify
3. Each sync gets its own protection
4. Oldest backup is fallback

**You see:** ✅ Safe multiple times

---

## Best Practices

### ✅ DO
- ✅ Run syncs normally - protection is automatic
- ✅ Check logs regularly: `tail instance/logs/account_watchdog.log`
- ✅ Archive old backups periodically
- ✅ Monitor for warnings in console output
- ✅ Verify on startup: app automatically does this

### ❌ DON'T
- ❌ Don't manually DELETE account_number column
- ❌ Don't delete the `instance/account_backups/` directory
- ❌ Don't ignore WARNING messages
- ❌ Don't skip app restarts (startup verification helps)

---

## Monitoring Commands

### Daily
```bash
# Check logs for any issues
tail -20 instance/logs/account_watchdog.log
```

### Weekly
```bash
# Full audit
python account_number_watchdog.py audit

# Verify status
python account_number_watchdog.py verify
```

### Before Major Operations
```bash
# Manual backup for extra safety
python account_number_backup.py backup
```

---

## Technical Details

### UPSERT Implementation
```sql
INSERT INTO users(site, id, name, email, site_role, last_login_at, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    name = excluded.name,
    email = excluded.email,
    site_role = excluded.site_role,
    last_login_at = excluded.last_login_at,
    fetched_at = excluded.fetched_at
    -- account_number is NOT in UPDATE, so it's preserved
```

### Watchdog Class Methods
```python
# Check status
watchdog.verify_accounts()

# Backup before sync
watchdog.pre_sync_backup()

# Verify after sync
watchdog.post_sync_verify()

# Full report
watchdog.full_audit()

# Protected sync with all layers
watchdog.protected_sync_wrapper(func, *args)
```

---

## Troubleshooting

### "Account numbers still missing?"
1. Check logs: `cat instance/logs/account_watchdog.log`
2. Check backups exist: `ls instance/account_backups/`
3. Try manual restore: `python account_number_backup.py restore`

### "No backup files found"
1. Run sync to create backups: `python populate-missing-custom-view-owners.py`
2. Or manually backup: `python account_number_backup.py backup`

### "Warning on startup"
This is normal! Means accounts were lost and auto-restored.
1. Check logs to see what happened
2. All is now fixed automatically
3. No action needed

---

## Summary

| Layer | Purpose | Automatic | Backup | Restore |
|-------|---------|-----------|--------|---------|
| **1: UPSERT** | Prevent loss during sync | ✅ | N/A | N/A |
| **2: Backup** | Save before every sync | ✅ | ✅ | ✅ |
| **3: Verify** | Check after every sync | ✅ | ✅ | ✅ |
| **4: Startup** | Check on app start | ✅ | ✅ | ✅ |

**Result:** Account numbers are now **permanently protected**! 🛡️

---

## Questions?

See related documentation:
- [Account Numbers Feature](docs/account-numbers/overview.md)
- [Account Number Backup System](ACCOUNT_NUMBER_PROTECTION.md)
- [BigQuery Sync](bigquery_sync.py)
