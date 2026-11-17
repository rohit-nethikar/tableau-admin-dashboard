#!/usr/bin/env python3
"""Sync account numbers from BigQuery and verify results."""
import db
import bigquery_sync

db.init_db()

print("=== BigQuery Account Number Sync ===\n")
print("Running sync...")

result = bigquery_sync.sync_account_numbers_to_database(db)

print(f"\nStatus: {result['status']}")
print(f"Message: {result['message']}")
print(f"Updated: {result['updated_count']}")
print(f"Skipped: {result['skipped_count']}")

with db.get_conn() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL AND account_number != ''")
    total_with_accounts = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT cv.owner_name)
        FROM custom_views cv
        LEFT JOIN users u ON LOWER(cv.owner_name) = LOWER(u.email)
        WHERE u.account_number IS NOT NULL AND u.account_number != ''
    """)
    custom_view_owners_with_accounts = cursor.fetchone()[0]

print(f"\n=== Verification ===")
print(f"Users with account numbers: {total_with_accounts}")
print(f"Custom view owners with account numbers: {custom_view_owners_with_accounts}/63")
print("\nSync complete!")
