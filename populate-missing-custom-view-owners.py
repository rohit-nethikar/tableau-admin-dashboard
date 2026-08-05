#!/usr/bin/env python3
"""Add missing custom view owners to the users table."""
import sqlite3
import uuid

DB_PATH = "instance/cache.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get all unique custom view owners
cursor.execute('SELECT DISTINCT owner_name FROM custom_views')
custom_view_owners = [row[0] for row in cursor.fetchall()]
print(f"Found {len(custom_view_owners)} unique custom view owners")

# Check which ones are already in the users table
missing_owners = []
for owner in custom_view_owners:
    cursor.execute('SELECT id FROM users WHERE LOWER(email) = LOWER(?)', (owner,))
    if not cursor.fetchone():
        missing_owners.append(owner)

print(f"Found {len(missing_owners)} missing from users table")

# Add missing owners to users table
# We need to figure out which site they belong to - let's use the site from custom_views
added_count = 0
for owner in missing_owners:
    # Get a sample site for this owner from custom_views
    cursor.execute('SELECT site FROM custom_views WHERE owner_name = ? LIMIT 1', (owner,))
    site_row = cursor.fetchone()
    if not site_row:
        continue

    site = site_row[0]

    # Create user record
    user_id = str(uuid.uuid4())
    # Use the email as the name since we don't know the actual name
    name_part = owner.split('@')[0]  # e.g., "shore.robin" from "shore.robin@mayo.edu"

    try:
        cursor.execute('''
        INSERT INTO users (id, name, email, site, site_role, fetched_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (user_id, name_part, owner, site, 'Unknown'))
        added_count += 1
        if added_count % 100 == 0:
            print(f"Added {added_count} users...")
    except sqlite3.IntegrityError:
        # User already exists, skip
        pass

conn.commit()
print(f"\nTotal users added: {added_count}")

# Now run the BigQuery sync
print("\nRunning BigQuery sync...")
import bigquery_sync
import db

result = bigquery_sync.sync_account_numbers_to_database(db)
print(f"Sync result:")
print(f"  Status: {result['status']}")
print(f"  Updated: {result['updated_count']}")
print(f"  Skipped: {result['skipped_count']}")

# Check how many custom views now have account numbers
cursor.execute('''
SELECT COUNT(*)
FROM custom_views cv
LEFT JOIN users u ON LOWER(cv.owner_name) = LOWER(u.email)
WHERE u.account_number IS NOT NULL
''')
count = cursor.fetchone()[0]
print(f"\nCustom views with account numbers: {count}")

conn.close()
