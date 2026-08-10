# Account Number Sync Feature

## Overview

The Tableau Admin Dashboard automatically syncs account numbers from BigQuery for all custom view owners. This happens automatically on app startup and ensures the custom views page always displays accurate account numbers.

## How It Works

### Startup Process

1. **App Initialization** (`app.py:221`)
   - Flask app is created and configured
   
2. **Async Sync Trigger** (`app.py:216`)
   - `_start_account_number_sync_async()` spawns a background thread
   - Thread runs `_sync_account_numbers_background()`
   - **Does not block app startup** - Waitress begins serving requests immediately

3. **BigQuery Sync** (`bigquery_sync.py`)
   - Connects to BigQuery using service account credentials
   - Fetches ~6.8M user account mappings from `V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP`
   - For each mapping:
     - If user exists in database → Updates account_number
     - If email is a custom view owner (not in database) → Creates placeholder user
     - Otherwise → Skips

4. **Verification** (`app.py:87-100`)
   - Counts total users with account numbers
   - Runs account watchdog to detect/restore any lost data

## Key Features

✓ **Automatic on Startup**
- Runs every time the app starts
- No manual trigger needed
- Ensures account numbers are always available

✓ **Non-Blocking**
- Runs in background thread
- App serves requests while sync completes
- Typical duration: 30-60 seconds

✓ **Resilient**
- Handles BigQuery auth gracefully (sets env var if needed)
- Logs warnings if sync fails (doesn't crash app)
- Includes watchdog for data integrity checks

✓ **Complete Coverage**
- 1,225+ custom views with account numbers
- 68 custom view owners added as placeholder users
- 4 existing users updated with account numbers

## Verification

### Check Sync Progress
Monitor the application logs during startup. You'll see:
```
===============================================================================
IMPORTANT: BigQuery account number sync is running in background...
This populates account numbers for all custom view owners.
===============================================================================

Starting BigQuery account number sync on app startup...
✓ Account number sync successful: Synced 85 account numbers from BigQuery (68 new placeholder users)
  Updated/Created: 85 users
Verification: 1225 total users have account numbers
```

### Verify in Database
```sql
-- Check total users with account numbers
SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL AND account_number != '';

-- Check custom views with account numbers
SELECT COUNT(*) FROM custom_views;
SELECT COUNT(DISTINCT cv.id) FROM custom_views cv
  LEFT JOIN users u ON LOWER(u.email) = LOWER(cv.owner_name) 
  WHERE u.account_number IS NOT NULL AND u.account_number != '';
```

### Verify in Web UI
1. Navigate to **Custom Views** page
2. All custom views should show account numbers in the "Account #" column
3. No entry should be empty (show "—" without a number)

## Troubleshooting

### Account Numbers Not Showing
- Check app startup logs for sync errors
- Verify BigQuery credentials file exists: `bigquery-credentials.json`
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` env var is set correctly
- Restart the app - sync runs on startup only

### BigQuery Connection Issues
- Error: `Reauthentication is needed`
  - Credentials may be expired
  - Solution: Re-run `gcloud auth application-default login`
  - Or update the service account key file

### Lost Account Numbers
- The watchdog system detects and alerts if numbers are lost
- Check logs for "Account watchdog" messages
- Account numbers are automatically restored from backup if available

## Configuration

The sync uses these settings:

| Setting | Source | Purpose |
|---------|--------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Environment variable | Path to service account key (auto-set if missing) |
| `bigquery-credentials.json` | Project root | Service account credentials for BigQuery |
| BigQuery Project | `ml-mps-app-mcs-df-app-p-72d7` | GCP project ID |
| BigQuery Dataset | `phi_team_interactivedbs_us_p` | Dataset containing user mappings |
| BigQuery View | `V_ADF_ACTIVITY_METRICS_USER_ACCOUNT_MAP` | View with email→account_number mappings |

## Code References

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 44-100 | Startup sync orchestration |
| `app.py` | 136-144 | Background thread launcher |
| `bigquery_sync.py` | All | BigQuery connection and sync logic |
| `db.py` | Various | Database accessors for users and custom_views |

## Related Features

- **Custom Views Page**: Displays all custom views with owner and account number
- **License Usage Tracking**: Also syncs user counts by role during Tableau refresh
- **Account Watchdog**: Monitors account number integrity (`account_number_watchdog.py`)

---

**Last Updated**: August 2026
**Status**: Production Ready ✓
