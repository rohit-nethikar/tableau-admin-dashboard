# Account Numbers Feature for Custom Views

## Overview
This feature adds support for displaying account numbers and email addresses associated with custom view owners in the Tableau Admin Dashboard.

## Changes Made

### 1. Database Schema (db.py)
- Added `account_number` column to the `users` table via ALTER TABLE migration
- This allows storing account number information for each user

### 2. Database Queries (db.py)
- Updated `fetch_custom_views()` to join with the `users` table
- Now returns `owner_email` and `owner_account_number` for each custom view
- Handles NULL values gracefully with COALESCE

### 3. New Database Function (db.py)
- Added `update_user_account_number(site, user_id, account_number)` function
- Allows updating account number for any user

### 4. API Routes (routes/custom_views.py)
- Added `GET /custom-views/account-numbers` - Fetch all users with account numbers
- Added `POST /custom-views/account-numbers` - Update account number for a user
- Both endpoints require login and are scoped to the current site

### 5. UI Template (templates/custom_views.html)
- Added "Owner Email" column - Shows email address with mailto: link
- Added "Account #" column - Shows account number or "—" if not set
- Moved email and account number columns after Owner name for logical flow
- Email is clickable to draft emails to the owner

## How to Use

### Viewing Account Numbers
1. Go to the Custom Views page
2. The "Owner Email" column displays the email address from the users table
3. The "Account #" column displays the associated account number if set

### Setting Account Numbers
The account numbers can be set via:
1. API call: POST `/custom-views/account-numbers` with JSON payload:
   ```json
   {
     "user_id": "<tableau_user_id>",
     "account_number": "<account_number>"
   }
   ```

2. Direct database: Update the users table
   ```sql
   UPDATE users SET account_number = '123456' WHERE name = 'john.doe'
   ```

### Example API Usage
```bash
curl -X POST http://localhost:5000/custom-views/account-numbers \
  -H "Content-Type: application/json" \
  -d '{"user_id": "abc123def", "account_number": "EMP-123456"}'
```

## Data Model

### User Table Extensions
```
users table now includes:
- id: Tableau User ID (existing)
- name: User name (existing)
- email: User email from Tableau (existing)
- site_role: Role (existing)
- account_number: NEW - External account/employee ID
```

### Custom View Enrichment
Each custom view now includes:
- owner_email: Email of the custom view owner
- owner_account_number: Account number of the custom view owner

## SQL Example
```sql
-- View all custom views with owner details
SELECT cv.name, cv.owner_name, u.email, u.account_number
FROM custom_views cv
LEFT JOIN users u ON cv.owner_name = u.name
ORDER BY cv.name;

-- Set account numbers
UPDATE users SET account_number = 'EMP-123456' WHERE name = 'john.doe';
UPDATE users SET account_number = 'EMP-123457' WHERE name = 'jane.smith';
```

## Notes
- Account numbers are optional - if not set, the column displays "—"
- Email addresses come from the Tableau sync (updated during data refresh)
- Account numbers must be set manually or via API
- Changes are visible immediately on page refresh
- All changes are scoped to the current site (multi-site support)
