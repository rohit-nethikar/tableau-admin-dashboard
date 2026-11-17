#!/usr/bin/env python3
"""
Account Number Watchdog

Continuously monitors account numbers and prevents loss.
- Auto-backup before syncs
- Auto-restore if lost
- Detailed logging
- Recovery verification
"""
import sqlite3
import json
import os
import logging
from datetime import datetime
from config import DB_PATH, INSTANCE_DIR
from account_number_backup import backup_account_numbers, restore_account_numbers

# Setup logging
LOG_DIR = os.path.join(INSTANCE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "account_watchdog.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class AccountNumberWatchdog:
    """Monitors and protects account numbers from loss."""

    def __init__(self):
        self.db_path = DB_PATH
        self.backup_dir = os.path.join(INSTANCE_DIR, "account_backups")
        self.log_file = os.path.join(LOG_DIR, "account_changes.log")

    def get_current_count(self):
        """Get current count of users with account numbers."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Error getting count: {e}")
            return 0

    def verify_accounts(self):
        """
        Verify account numbers are present.
        If lost, automatically restore from latest backup.
        """
        current_count = self.get_current_count()
        logger.info(f"Account number count: {current_count}")

        if current_count == 0:
            logger.warning("⚠️ Account numbers detected as lost! Starting auto-restore...")
            self._auto_restore()
            return False
        return True

    def _auto_restore(self):
        """Automatically restore from latest backup."""
        try:
            logger.info("Searching for latest backup...")
            backups = [
                f
                for f in os.listdir(self.backup_dir)
                if f.startswith("accounts_") and f.endswith(".json")
            ]

            if not backups:
                logger.error("❌ No backup files found! Cannot restore.")
                return False

            latest_backup = sorted(backups)[-1]
            backup_path = os.path.join(self.backup_dir, latest_backup)

            logger.info(f"Restoring from: {latest_backup}")
            restore_account_numbers(backup_path)

            # Verify restoration
            new_count = self.get_current_count()
            logger.info(f"After restore: {new_count} accounts")

            if new_count > 0:
                logger.info("✅ Restore successful!")
                self._log_action("AUTO_RESTORE", f"Restored {new_count} accounts", "SUCCESS")
                return True
            else:
                logger.error("❌ Restore failed - still no accounts")
                self._log_action("AUTO_RESTORE", "Restore failed", "FAILED")
                return False

        except Exception as e:
            logger.error(f"Restore error: {e}")
            self._log_action("AUTO_RESTORE", str(e), "ERROR")
            return False

    def pre_sync_backup(self):
        """Backup before any sync operation."""
        logger.info("Creating pre-sync backup...")
        if backup_account_numbers():
            self._log_action("PRE_SYNC_BACKUP", "Backup created", "SUCCESS")
            return True
        else:
            self._log_action("PRE_SYNC_BACKUP", "Backup failed", "FAILED")
            return False

    def post_sync_verify(self):
        """Verify after sync operation."""
        logger.info("Verifying after sync...")
        count = self.get_current_count()

        if count > 0:
            logger.info(f"✅ Post-sync verification passed: {count} accounts")
            self._log_action("POST_SYNC_VERIFY", f"{count} accounts present", "SUCCESS")
            return True
        else:
            logger.warning("⚠️ Post-sync verification failed - no accounts!")
            self._log_action("POST_SYNC_VERIFY", "No accounts found", "FAILED")
            # Try auto-restore
            return self._auto_restore()

    def protected_sync_wrapper(self, sync_function, *args, **kwargs):
        """
        Safely execute a sync function with account number protection.

        Usage:
            watchdog.protected_sync_wrapper(sync_users, site, rows)
        """
        logger.info("=" * 70)
        logger.info("PROTECTED SYNC STARTED")
        logger.info("=" * 70)

        try:
            # Step 1: Backup
            logger.info("Step 1: Creating pre-sync backup...")
            self.pre_sync_backup()

            # Step 2: Sync
            logger.info(f"Step 2: Running sync function: {sync_function.__name__}")
            sync_function(*args, **kwargs)

            # Step 3: Verify
            logger.info("Step 3: Verifying accounts...")
            if self.post_sync_verify():
                logger.info("✅ PROTECTED SYNC COMPLETED SUCCESSFULLY")
                self._log_action("PROTECTED_SYNC", "Completed successfully", "SUCCESS")
            else:
                logger.warning("⚠️ SYNC COMPLETED WITH ISSUES")
                self._log_action("PROTECTED_SYNC", "Completed with verification issues", "WARNING")

        except Exception as e:
            logger.error(f"❌ SYNC FAILED: {e}")
            self._log_action("PROTECTED_SYNC", str(e), "ERROR")
            # Attempt restore
            self._auto_restore()
            raise

        finally:
            logger.info("=" * 70)

    def _log_action(self, action_type, details, status):
        """Log action to file."""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": action_type,
                "details": details,
                "status": status,
                "account_count": self.get_current_count(),
            }
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Logging error: {e}")

    def full_audit(self):
        """Complete audit of account number status."""
        logger.info("\n" + "=" * 70)
        logger.info("FULL ACCOUNT NUMBER AUDIT")
        logger.info("=" * 70)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # Users with accounts
            cursor.execute("SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL")
            users_with_accounts = cursor.fetchone()[0]

            # Sample accounts
            cursor.execute(
                "SELECT email, account_number FROM users WHERE account_number IS NOT NULL LIMIT 5"
            )
            samples = cursor.fetchall()

            conn.close()

            logger.info(f"Total users: {total_users}")
            logger.info(f"Users with account numbers: {users_with_accounts}")
            logger.info(
                f"Coverage: {(users_with_accounts/total_users*100):.1f}%"
                if total_users > 0
                else "Coverage: N/A"
            )

            if samples:
                logger.info("Sample accounts:")
                for email, account_num in samples:
                    logger.info(f"  {email} -> {account_num}")

            # Check backups
            backups = [
                f
                for f in os.listdir(self.backup_dir)
                if f.startswith("accounts_") and f.endswith(".json")
            ]
            logger.info(f"Available backups: {len(backups)}")

            if backups:
                logger.info(f"Latest backup: {sorted(backups)[-1]}")

            logger.info("=" * 70 + "\n")

        except Exception as e:
            logger.error(f"Audit error: {e}")


# Global instance
_watchdog = None


def get_watchdog():
    """Get or create global watchdog instance."""
    global _watchdog
    if _watchdog is None:
        _watchdog = AccountNumberWatchdog()
    return _watchdog


def verify_accounts():
    """Verify accounts (can be called from anywhere)."""
    watchdog = get_watchdog()
    return watchdog.verify_accounts()


def protected_sync(sync_function, *args, **kwargs):
    """Safely execute sync with protection."""
    watchdog = get_watchdog()
    return watchdog.protected_sync_wrapper(sync_function, *args, **kwargs)


if __name__ == "__main__":
    import sys

    watchdog = get_watchdog()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python account_number_watchdog.py verify  - Check and restore if needed")
        print("  python account_number_watchdog.py audit   - Full audit report")
        sys.exit(1)

    command = sys.argv[1]

    if command == "verify":
        if watchdog.verify_accounts():
            print("✅ Accounts are safe")
        else:
            print("⚠️ Issues found - check log")
    elif command == "audit":
        watchdog.full_audit()
    else:
        print(f"Unknown command: {command}")
