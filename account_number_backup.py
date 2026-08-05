#!/usr/bin/env python3
"""
Account Number Backup & Restore

Protects BigQuery-synced account numbers from being lost during data refreshes.
Automatically backs up before sync and can restore if needed.
"""
import sqlite3
import json
import os
from datetime import datetime
from config import DB_PATH, INSTANCE_DIR

BACKUP_DIR = os.path.join(INSTANCE_DIR, "account_backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_account_numbers():
    """
    Backup all account numbers before syncing users.
    Preserves the BigQuery-synced data in case of accidental loss.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get all users with account numbers
        cursor.execute(
            "SELECT id, email, account_number FROM users WHERE account_number IS NOT NULL"
        )
        accounts = cursor.fetchall()
        conn.close()

        if not accounts:
            print("No account numbers to backup")
            return False

        # Create backup file
        timestamp = datetime.now().isoformat()
        backup_file = os.path.join(BACKUP_DIR, f"accounts_{timestamp}.json")

        backup_data = {
            "timestamp": timestamp,
            "count": len(accounts),
            "accounts": [
                {"id": row[0], "email": row[1], "account_number": row[2]}
                for row in accounts
            ],
        }

        with open(backup_file, "w") as f:
            json.dump(backup_data, f, indent=2)

        print(f"✓ Backed up {len(accounts)} account numbers to {backup_file}")
        return True

    except Exception as e:
        print(f"✗ Backup failed: {e}")
        return False


def restore_account_numbers(backup_file=None):
    """
    Restore account numbers from backup file.

    Args:
        backup_file: Path to backup JSON file. If None, uses most recent.
    """
    try:
        # Find most recent backup if not specified
        if backup_file is None:
            backups = [
                f
                for f in os.listdir(BACKUP_DIR)
                if f.startswith("accounts_") and f.endswith(".json")
            ]
            if not backups:
                print("No backup files found!")
                return False
            backup_file = os.path.join(BACKUP_DIR, sorted(backups)[-1])

        # Load backup
        with open(backup_file, "r") as f:
            backup_data = json.load(f)

        # Restore to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        restored_count = 0
        for account in backup_data["accounts"]:
            cursor.execute(
                "UPDATE users SET account_number = ? WHERE id = ?",
                (account["account_number"], account["id"]),
            )
            if cursor.rowcount > 0:
                restored_count += 1

        conn.commit()
        conn.close()

        print(
            f"✓ Restored {restored_count} account numbers from {os.path.basename(backup_file)}"
        )
        return True

    except Exception as e:
        print(f"✗ Restore failed: {e}")
        return False


def list_backups():
    """List all available backup files."""
    try:
        backups = [
            f
            for f in os.listdir(BACKUP_DIR)
            if f.startswith("accounts_") and f.endswith(".json")
        ]
        if not backups:
            print("No backups found")
            return

        print("\nAvailable backups:")
        print("-" * 60)
        for backup in sorted(backups, reverse=True):
            filepath = os.path.join(BACKUP_DIR, backup)
            with open(filepath, "r") as f:
                data = json.load(f)
            timestamp = data.get("timestamp", "unknown")
            count = data.get("count", 0)
            print(f"  {backup}: {count} accounts ({timestamp})")
        print("-" * 60)

    except Exception as e:
        print(f"Error listing backups: {e}")


def verify_account_numbers():
    """Check current account number status."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL")
        count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]

        conn.close()

        print(f"\nAccount Numbers Status:")
        print(f"  Total users: {total}")
        print(f"  Users with account numbers: {count}")
        print(f"  Coverage: {(count/total*100):.1f}%" if total > 0 else "  Coverage: N/A")

        if count == 0:
            print("  ⚠️  WARNING: No account numbers found! Use restore_account_numbers()")

    except Exception as e:
        print(f"Error verifying: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python account_number_backup.py backup  - Backup current accounts")
        print("  python account_number_backup.py restore - Restore from latest backup")
        print("  python account_number_backup.py list    - List all backups")
        print("  python account_number_backup.py verify  - Check current status")
        sys.exit(1)

    command = sys.argv[1]

    if command == "backup":
        backup_account_numbers()
    elif command == "restore":
        restore_account_numbers()
    elif command == "list":
        list_backups()
    elif command == "verify":
        verify_account_numbers()
    else:
        print(f"Unknown command: {command}")
