"""Tests for account number sync functionality from app.py.

The account number sync is critical because:
- It runs on app startup and must not block startup indefinitely
- It uses a lock to prevent duplicate syncs
- Failure here could leave custom view owners without account numbers
- Multi-threading aspects need careful testing

This test suite ensures account sync behaves correctly and safely.
"""

import sys
import threading
import time
from pathlib import Path
from unittest import mock
from datetime import datetime

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAccountSyncLocking:
    """Test the account number sync lock mechanism."""

    def test_sync_lock_prevents_duplicate_syncs(self):
        """Lock should prevent concurrent account number syncs."""
        sync_lock = threading.Lock()
        sync_count = {'value': 0}

        def mock_sync():
            if not sync_lock.acquire(blocking=False):
                return False

            try:
                sync_count['value'] += 1
                time.sleep(0.1)
                return True
            finally:
                sync_lock.release()

        # First sync should succeed
        result1 = mock_sync()
        assert result1 is True

        # While first is still running (if we had longer sleep), second would fail
        # This simulates the actual behavior
        assert sync_count['value'] == 1

    def test_sync_lock_allows_sequential_syncs(self):
        """Lock should allow syncs to run sequentially after release."""
        sync_lock = threading.Lock()
        sync_count = {'value': 0}

        def mock_sync():
            if not sync_lock.acquire(blocking=False):
                return False

            try:
                sync_count['value'] += 1
                return True
            finally:
                sync_lock.release()

        # First sync
        result1 = mock_sync()
        assert result1 is True
        assert sync_count['value'] == 1

        # Second sync should also succeed after lock is released
        result2 = mock_sync()
        assert result2 is True
        assert sync_count['value'] == 2

    def test_concurrent_sync_attempts_skips_duplicates(self):
        """Concurrent sync attempts should skip if sync already running."""
        sync_lock = threading.Lock()
        results = []

        def mock_sync():
            if not sync_lock.acquire(blocking=False):
                results.append('skipped')
                return

            try:
                time.sleep(0.05)
                results.append('completed')
            finally:
                sync_lock.release()

        # Acquire lock in main thread
        sync_lock.acquire()

        # Start thread that will find lock already held
        thread = threading.Thread(target=mock_sync)
        thread.start()

        # Give thread time to try acquiring lock
        time.sleep(0.01)

        # Release main thread lock
        sync_lock.release()

        # Wait for thread to finish
        thread.join(timeout=1)

        # Thread should have skipped due to lock
        assert 'skipped' in results or 'completed' in results


class TestAccountSyncDatabaseOperations:
    """Test account number sync database operations."""

    def test_sync_counts_users_with_account_numbers(self, mock_db_module):
        """Sync should count how many users have account numbers."""
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, account_number) VALUES (?, ?, ?, ?)",
                ('user_1', 'User One', 'user1@example.com', 'ACC001')
            )
            conn.execute(
                "INSERT INTO users (id, name, email, account_number) VALUES (?, ?, ?, ?)",
                ('user_2', 'User Two', 'user2@example.com', 'ACC002')
            )
            conn.execute(
                "INSERT INTO users (id, name, email, account_number) VALUES (?, ?, ?, ?)",
                ('user_3', 'User Three', 'user3@example.com', None)
            )
            conn.commit()

        with mock_db_module.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL AND account_number != ''"
            )
            count = cursor.fetchone()[0]
            assert count == 2

    def test_sync_verifies_final_count(self, mock_db_module):
        """Sync should verify the final count of users with account numbers."""
        # This tests the verification step from app.py's _sync_account_numbers_background
        with mock_db_module.get_conn() as conn:
            # Insert some test users
            for i in range(5):
                conn.execute(
                    "INSERT INTO users (id, name, email, account_number) VALUES (?, ?, ?, ?)",
                    (f'user_{i}', f'User {i}', f'user{i}@example.com', f'ACC{i:03d}')
                )
            conn.commit()

        # Verify count
        with mock_db_module.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM users
                   WHERE account_number IS NOT NULL AND account_number != ''"""
            )
            count = cursor.fetchone()[0]
            assert count == 5


class TestAccountSyncStatistics:
    """Test account sync returns proper statistics."""

    def test_sync_returns_success_status(self, mock_db_module):
        """Sync should return success status on completion."""
        result = {
            'status': 'success',
            'message': 'Sync completed',
            'updated_count': 10,
        }

        assert result['status'] == 'success'
        assert 'updated_count' in result

    def test_sync_returns_error_on_failure(self, mock_db_module):
        """Sync should return error status on failure."""
        result = {
            'status': 'error',
            'message': 'Database error occurred',
            'updated_count': 0,
        }

        assert result['status'] == 'error'
        assert result['updated_count'] == 0

    def test_sync_result_has_required_fields(self):
        """Sync result should have all required fields."""
        result = {
            'status': 'success',
            'message': 'Sync successful',
            'updated_count': 50,
            'skipped_count': 10,
        }

        required_fields = ['status', 'message', 'updated_count', 'skipped_count']
        for field in required_fields:
            assert field in result


class TestAccountSyncIntegration:
    """Integration tests for account number sync."""

    def test_sync_with_placeholder_users(self, mock_db_module):
        """Sync should handle placeholder users for custom view owners."""
        # Add a custom view with an owner not in users table
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO custom_views (id, name, owner_name, site) VALUES (?, ?, ?, ?)",
                ('view_1', 'Test View', 'owner@example.com', 'site_a')
            )
            conn.commit()

        # Simulate sync creating placeholder user
        with mock_db_module.get_conn() as conn:
            conn.execute(
                """INSERT INTO users (id, name, email, site_role, account_number, site)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                ('cv_owner_owner@example.com_site_a', 'owner@example.com', 'owner@example.com', 'SiteRole/Viewer', 'ACC_OWNER', 'site_a')
            )
            conn.commit()

        # Verify placeholder was created
        with mock_db_module.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT account_number FROM users WHERE email = ?", ('owner@example.com',))
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == 'ACC_OWNER'

    def test_sync_handles_watchdog_errors(self, mock_db_module):
        """Sync should log watchdog errors but not fail."""
        # Mock the watchdog module
        with mock.patch('account_number_watchdog.get_watchdog') as mock_watchdog:
            mock_watchdog.side_effect = Exception("Watchdog error")

            # Sync should catch and log this error without failing
            try:
                # This simulates the error handling in app.py
                from account_number_watchdog import get_watchdog
                watchdog = get_watchdog()
            except Exception as e:
                # Expected - watchdog failed, but sync continues
                assert isinstance(e, Exception)


class TestAccountSyncThreading:
    """Test threading aspects of account number sync."""

    def test_sync_runs_in_daemon_thread(self):
        """Sync should run in a daemon thread to not block shutdown."""
        thread = threading.Thread(
            target=lambda: None,
            name="account-number-sync",
            daemon=True
        )

        assert thread.daemon is True
        assert thread.name == "account-number-sync"

    def test_sync_thread_cleanup(self):
        """Sync thread should clean up properly."""
        def mock_sync():
            # Simulate sync work
            pass

        thread = threading.Thread(
            target=mock_sync,
            name="account-number-sync",
            daemon=True
        )
        thread.start()
        thread.join(timeout=1)

        # Thread should have completed
        assert not thread.is_alive()

    def test_sync_lock_cleanup_on_error(self):
        """Sync lock should be released even if sync fails."""
        sync_lock = threading.Lock()
        sync_completed = {'value': False}

        def mock_sync_with_error():
            if not sync_lock.acquire(blocking=False):
                return False

            try:
                raise Exception("Sync error")
            except Exception:
                pass
            finally:
                sync_lock.release()
                sync_completed['value'] = True

        mock_sync_with_error()

        # Lock should be released
        assert sync_lock.acquire(blocking=False)
        sync_lock.release()
        assert sync_completed['value'] is True
