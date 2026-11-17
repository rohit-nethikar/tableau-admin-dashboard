"""Tests for bigquery_sync module - CRITICAL PATH.

BigQuery sync is critical because:
- It syncs account numbers from BigQuery to the database
- Data integrity depends on correct email-to-account-number mapping
- Failure here means custom view owners lose their account numbers
- Placeholder user creation must not break custom view tracking

This test suite ensures BigQuery data is correctly fetched and synced.
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import bigquery_sync


class TestBigQueryClientInitialization:
    """Test BigQuery client setup and authentication."""

    def test_get_bigquery_client_with_credentials_file(self, monkeypatch):
        """Client should initialize with service account credentials file."""
        mock_creds = mock.MagicMock()
        with mock.patch('bigquery_sync.service_account.Credentials.from_service_account_file') as mock_from_file:
            with mock.patch('bigquery_sync.bigquery.Client') as mock_client_class:
                mock_from_file.return_value = mock_creds

                monkeypatch.setenv('GOOGLE_APPLICATION_CREDENTIALS', '/path/to/creds.json')
                monkeypatch.setattr('os.path.exists', lambda x: True)

                client = bigquery_sync.get_bigquery_client()

                mock_from_file.assert_called_once()
                mock_client_class.assert_called_once()

    def test_get_bigquery_client_with_adc(self):
        """Client should fallback to Application Default Credentials."""
        with mock.patch('bigquery_sync.bigquery.Client') as mock_client_class:
            mock_client = mock.MagicMock()
            mock_client_class.return_value = mock_client

            client = bigquery_sync.get_bigquery_client()

            assert client is not None

    def test_get_bigquery_client_initialization_error(self):
        """Client initialization should return None on error."""
        with mock.patch('bigquery_sync.bigquery.Client') as mock_client_class:
            mock_client_class.side_effect = Exception("Auth error")

            client = bigquery_sync.get_bigquery_client()

            assert client is None


class TestBigQueryFetch:
    """Test fetching account numbers from BigQuery - CRITICAL DATA INTEGRITY."""

    def test_fetch_account_numbers_success(self):
        """Should fetch account mappings from BigQuery."""
        # Create mock Row and Results objects
        class MockRow:
            def __init__(self, email, account):
                self.USERNAME = email
                self.CLIENT_ACCOUNT_NUMBER = account

        class MockResults:
            def __init__(self, rows):
                self.rows = rows
                self.total_rows = len(rows)

            def __iter__(self):
                return iter(self.rows)

        mock_client = mock.MagicMock()
        rows = [
            MockRow('user1@example.com', 'ACC001'),
            MockRow('user2@example.com', 'ACC002'),
            MockRow('user3@example.com', 'ACC003'),
        ]
        mock_results = MockResults(rows)

        # Configure mock job to return the results
        mock_job = mock.MagicMock()
        mock_job.result.return_value = mock_results

        mock_client.query.return_value = mock_job

        with mock.patch('bigquery_sync.get_bigquery_client', return_value=mock_client):
            account_map = bigquery_sync.fetch_account_numbers_from_bigquery()

            assert len(account_map) == 3
            assert account_map['user1@example.com'] == 'ACC001'
            assert account_map['user2@example.com'] == 'ACC002'
            assert account_map['user3@example.com'] == 'ACC003'

    def test_fetch_account_numbers_normalizes_email(self):
        """Should normalize emails to lowercase."""
        class MockRow:
            def __init__(self, email, account):
                self.USERNAME = email
                self.CLIENT_ACCOUNT_NUMBER = account

        class MockResults:
            def __init__(self, rows):
                self.rows = rows
                self.total_rows = len(rows)

            def __iter__(self):
                return iter(self.rows)

        mock_client = mock.MagicMock()
        rows = [
            MockRow('User1@Example.COM', 'ACC001'),
            MockRow('USER2@EXAMPLE.COM', 'ACC002'),
        ]
        mock_results = MockResults(rows)

        mock_job = mock.MagicMock()
        mock_job.result.return_value = mock_results
        mock_client.query.return_value = mock_job

        with mock.patch('bigquery_sync.get_bigquery_client', return_value=mock_client):
            account_map = bigquery_sync.fetch_account_numbers_from_bigquery()

            assert 'user1@example.com' in account_map
            assert 'user2@example.com' in account_map

    def test_fetch_account_numbers_skips_null_values(self):
        """Should skip rows with missing email or account number."""
        class MockRow:
            def __init__(self, email, account):
                self.USERNAME = email
                self.CLIENT_ACCOUNT_NUMBER = account

        class MockResults:
            def __init__(self, rows):
                self.rows = rows
                self.total_rows = len(rows)

            def __iter__(self):
                return iter(self.rows)

        mock_client = mock.MagicMock()
        rows = [
            MockRow('user1@example.com', 'ACC001'),
            MockRow(None, 'ACC002'),  # Missing email
            MockRow('user3@example.com', None),  # Missing account
            MockRow('user4@example.com', 'ACC004'),
        ]
        mock_results = MockResults(rows)

        mock_job = mock.MagicMock()
        mock_job.result.return_value = mock_results
        mock_client.query.return_value = mock_job

        with mock.patch('bigquery_sync.get_bigquery_client', return_value=mock_client):
            account_map = bigquery_sync.fetch_account_numbers_from_bigquery()

            assert len(account_map) == 2
            assert 'user1@example.com' in account_map
            assert 'user4@example.com' in account_map

    def test_fetch_account_numbers_no_client_error(self):
        """Should return empty dict if BigQuery client fails."""
        with mock.patch('bigquery_sync.get_bigquery_client', return_value=None):
            account_map = bigquery_sync.fetch_account_numbers_from_bigquery()

            assert account_map == {}

    def test_fetch_account_numbers_query_error(self):
        """Should return empty dict on query error."""
        mock_client = mock.MagicMock()
        mock_client.query.side_effect = Exception("Query error")

        with mock.patch('bigquery_sync.get_bigquery_client', return_value=mock_client):
            account_map = bigquery_sync.fetch_account_numbers_from_bigquery()

            assert account_map == {}


class TestBigQuerySync:
    """Test syncing account numbers to database - CRITICAL."""

    def test_sync_account_numbers_updates_existing_users(self, mock_db_module):
        """Should update existing users with account numbers."""
        # Set up test user
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, site) VALUES (?, ?, ?, ?)",
                ('user_1', 'User One', 'user1@example.com', 'site_a')
            )
            conn.commit()

        # Mock BigQuery data
        bq_account_map = {
            'user1@example.com': 'ACC001',
            'user2@example.com': 'ACC002'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'success'
            assert result['updated_count'] > 0

    def test_sync_account_numbers_creates_placeholder_users(self, mock_db_module):
        """Should create placeholder users for custom view owners."""
        # Set up custom view owner
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO custom_views (id, name, owner_name, site) VALUES (?, ?, ?, ?)",
                ('view_1', 'My View', 'newuser@example.com', 'site_a')
            )
            conn.commit()

        # Mock BigQuery data with user not in DB
        bq_account_map = {
            'newuser@example.com': 'ACC_NEW'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'success'
            # Check that placeholder was created
            with mock_db_module.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE email = ?", ('newuser@example.com',))
                count = cursor.fetchone()[0]
                assert count > 0

    def test_sync_account_numbers_handles_no_bigquery_data(self, mock_db_module):
        """Should handle case where BigQuery returns no data."""
        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value={}):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'error'
            assert 'No account mappings' in result['message']

    def test_sync_account_numbers_database_error(self, mock_db_module):
        """Should handle database errors gracefully."""
        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value={'user@example.com': 'ACC001'}):
            # Simulate database error by creating a mock that raises an exception
            mock_bad_db = mock.MagicMock()
            mock_bad_db.get_conn.side_effect = Exception("Database error")

            result = bigquery_sync.sync_account_numbers_to_database(mock_bad_db)

            assert result['status'] == 'error'

    def test_sync_returns_statistics(self, mock_db_module):
        """Sync should return update statistics."""
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, site) VALUES (?, ?, ?, ?)",
                ('user_1', 'User One', 'user1@example.com', 'site_a')
            )
            conn.commit()

        bq_account_map = {
            'user1@example.com': 'ACC001'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert 'status' in result
            assert 'message' in result
            assert 'updated_count' in result
            assert 'skipped_count' in result
            assert isinstance(result['updated_count'], int)
            assert isinstance(result['skipped_count'], int)

    def test_sync_updates_multiple_users_same_email(self, mock_db_module):
        """Should update all users with same email across multiple sites."""
        # Set up users with same email on different sites
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, site) VALUES (?, ?, ?, ?)",
                ('user_1_site_a', 'User One', 'user1@example.com', 'site_a')
            )
            conn.execute(
                "INSERT INTO users (id, name, email, site) VALUES (?, ?, ?, ?)",
                ('user_1_site_b', 'User One', 'user1@example.com', 'site_b')
            )
            conn.commit()

        bq_account_map = {
            'user1@example.com': 'ACC001'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'success'
            # Should update 2 users (one per site)
            assert result['updated_count'] >= 2


class TestBigQuerySyncEdgeCases:
    """Test edge cases and error handling."""

    def test_sync_with_whitespace_in_email(self, mock_db_module):
        """Should handle emails with leading/trailing whitespace."""
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, site) VALUES (?, ?, ?, ?)",
                ('user_1', 'User One', ' user1@example.com ', 'site_a')
            )
            conn.commit()

        bq_account_map = {
            'user1@example.com': 'ACC001'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'success'

    def test_sync_preserves_existing_account_numbers(self, mock_db_module):
        """Should not lose account numbers during sync."""
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO users (id, name, email, site, account_number) VALUES (?, ?, ?, ?, ?)",
                ('user_1', 'User One', 'user1@example.com', 'site_a', 'ACC_OLD')
            )
            conn.commit()

        bq_account_map = {
            'user1@example.com': 'ACC_NEW'
        }

        with mock.patch('bigquery_sync.fetch_account_numbers_from_bigquery', return_value=bq_account_map):
            result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)

            assert result['status'] == 'success'
            # Verify the new account number was set
            with mock_db_module.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT account_number FROM users WHERE id = ?", ('user_1',))
                account = cursor.fetchone()[0]
                assert account == 'ACC_NEW'
