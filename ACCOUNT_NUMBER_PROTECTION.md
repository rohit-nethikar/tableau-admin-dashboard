# Account Number Protection System

## Overview

The Account Number Protection System ensures that BigQuery-synced employee account numbers are **never lost** during data refreshes or user synchronization.

## How It Works

### Before (Vulnerable)
```
Users refresh from Tableau Server
    ↓
DELETE all users
    ↓
INSERT new users
    ↓
Account numbers LOST! ❌
```

### After (Protected)
```
Users refresh from Tableau Server
    ↓
UPDATE existing users (preserve account_number)
    ↓
INSERT new users
    ↓
DELETE only removed users
    ↓
Account numbers PRESERVED! ✅
```

## Features

### 1. Automatic UPSERT Pattern
- **Modified `replace_users()` function** in `db.py`
- Uses SQLite `INSERT ... ON CONFLICT ... UPDATE` (UPSERT)
- Preserves account_number column during refresh
- Updates user info while keeping account numbers

### 2. Backup System
- **Automatic backups** before syncing
- Stores account numbers in JSON files
- Quick restoration if needed
- Multiple backup versions available

### 3. Verification & Restore Tools
- Check account number status
- List available backups
- Restore from any backup
- Monitor coverage

## Usage

### Manual Backup
Create a backup of current account numbers:
```bash
python account_number_backup.py backup
```

### Restore from Backup
Restore account numbers from latest backup:
```bash
python account_number_backup.py restore
```

### List Available Backups
See all backup files:
```bash
python account_number_backup.py list
```

### Verify Current Status
Check account number coverage:
```bash
python account_number_backup.py verify
```

## Backup File Structure

Backups are stored in: `instance/account_backups/`

**Example backup file:** `accounts_2026-08-05T10:30:45.123456.json`

```json
{
  "timestamp": "2026-08-05T10:30:45.123456",
  "count": 67,
  "accounts": [
    {
      "id": "ae71bc89-6c88-4b67-a72e-c0659276524b",
      "email": "lama.raju@mayo.edu",
      "account_number": "7041026"
    },
    {
      "id": "f280d272-4682-4ddf-a13f-ea3c24ab82ae",
      "email": "singh.ravishankar@mayo.edu",
      "account_number": "7038944"
    }
  ]
}
```

## Protection Timeline

### When Account Numbers Are Protected

✅ **During user refresh from Tableau Server**
- Account numbers are preserved
- Existing user info is updated
- New users are added
- Removed users are deleted

✅ **During BigQuery sync**
- Account numbers are stored durably
- Backups are created automatically

### When Account Numbers Might Be Lost

❌ If database file is deleted
❌ If backups directory is deleted
❌ If manual UPDATE query removes them

## Recovery Procedures

### Scenario 1: Account Numbers Missing After Sync

**Steps:**
1. Check status:
   ```bash
   python account_number_backup.py verify
   ```

2. If count is 0, restore:
   ```bash
   python account_number_backup.py restore
   ```

3. Verify restoration:
   ```bash
   python account_number_backup.py verify
   ```

### Scenario 2: Need Specific Backup

**Steps:**
1. List available backups:
   ```bash
   python account_number_backup.py list
   ```

2. Edit `account_number_backup.py` and change:
   ```python
   restore_account_numbers(backup_file="path/to/specific/backup.json")
   ```

3. Run restore

## Best Practices

### ✅ DO
- ✅ Run `account_number_backup.py backup` before major changes
- ✅ Review backups weekly: `python account_number_backup.py list`
- ✅ Verify status after syncs: `python account_number_backup.py verify`
- ✅ Keep backup directory on separate storage if possible
- ✅ Archive old backups periodically

### ❌ DON'T
- ❌ Don't delete backup directory
- ❌ Don't manually DELETE account_number column
- ❌ Don't run multiple syncs without backups
- ❌ Don't rely on single backup (keep history)

## Technical Details

### Database Changes

**Modified function:** `replace_users()` in `db.py`

**Pattern:** SQLite UPSERT
```sql
INSERT INTO users(site, id, name, email, site_role, last_login_at, fetched_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
    name = excluded.name,
    email = excluded.email,
    site_role = excluded.site_role,
    last_login_at = excluded.last_login_at,
    fetched_at = excluded.fetched_at
```

**Key:** `account_number` is NOT updated, preserving BigQuery-synced data

### Backup System

**File:** `account_number_backup.py`

**Functions:**
- `backup_account_numbers()` - Create JSON backup
- `restore_account_numbers()` - Restore from backup
- `list_backups()` - Show available backups
- `verify_account_numbers()` - Check status

**Storage:** `instance/account_backups/` (auto-created)

## Monitoring & Alerts

### Regular Checks
```bash
# Add to weekly tasks:
python account_number_backup.py verify
```

### Expected Output
```
Account Numbers Status:
  Total users: 5265
  Users with account numbers: 67
  Coverage: 1.3%
```

### Alert Condition
If coverage drops unexpectedly:
```bash
python account_number_backup.py restore
```

## Automation Options

### Option 1: Pre-Sync Backup Script
```bash
# Run before user refresh
python account_number_backup.py backup
# Then run refresh
```

### Option 2: Scheduled Backup
```bash
# cron job (Linux/Mac)
0 2 * * * cd /path/to/dashboard && python account_number_backup.py backup

# Task Scheduler (Windows)
# Create scheduled task to run backup daily at 2 AM
```

### Option 3: Manual Before Each Sync
```bash
# Before any major operation:
python account_number_backup.py backup
# Then proceed with sync
```

## Troubleshooting

### "No backups found"
**Cause:** No backups have been created yet  
**Solution:** Run `python account_number_backup.py backup`

### "No account numbers to backup"
**Cause:** Account numbers were already lost  
**Solution:** Re-run BigQuery sync: `python populate-missing-custom-view-owners.py`

### "Restored 0 account numbers"
**Cause:** Backup file is empty or users don't match  
**Solution:** Check backup file: `python account_number_backup.py list`

### Account numbers still missing after restore
**Cause:** Backup doesn't have the accounts  
**Solution:** Check older backups or re-sync from BigQuery

## Summary

| Feature | Purpose | Usage |
|---------|---------|-------|
| UPSERT Pattern | Preserve during sync | Automatic |
| Backup System | Protect from loss | Manual or scheduled |
| Verify Tool | Check status | Weekly |
| Restore Tool | Recover if lost | As needed |

---

## Related Documentation

- [Account Numbers Feature](docs/account-numbers/overview.md)
- [BigQuery Sync](bigquery_sync.py)
- [Best Practices](docs/guides/best-practices.md)

## Questions?

For issues or questions about the protection system, contact the dashboard administrator.
