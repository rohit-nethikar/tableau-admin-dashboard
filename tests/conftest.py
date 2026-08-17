"""Pytest configuration and shared fixtures for test suite."""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest import mock
from datetime import datetime

import pytest

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing.

    Yields the database connection and cleans up after the test.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def mock_db_module(temp_db):
    """Create a mock db module with in-memory database.

    This fixture replaces the real db module with one backed by a test database.
    """

    class MockDbModule:
        """Mock database module for testing."""

        def __init__(self, conn):
            self.conn = conn
            self.initialized = False

        def init_db(self):
            """Initialize database schema for testing."""
            cursor = self.conn.cursor()

            # Create minimal schema for tests
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    site_role TEXT,
                    account_number TEXT,
                    site TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    rule_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    threshold REAL NOT NULL,
                    action TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alert_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    current_value REAL,
                    threshold REAL,
                    triggered_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_views (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    owner_name TEXT,
                    site TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    notification_email TEXT,
                    dark_mode INTEGER DEFAULT 0,
                    notifications_enabled INTEGER DEFAULT 1
                )
            """)

            self.conn.commit()
            self.initialized = True

        def get_conn(self):
            """Context manager for database connections."""
            return DatabaseConnection(self.conn)

        def get_alert_rules(self, user_id=None, enabled_only=False):
            """Get alert rules from database."""
            cursor = self.conn.cursor()
            query = "SELECT rule_id, user_id, name, metric, condition, threshold, action, enabled FROM alert_rules"
            params = []

            if user_id:
                query += " WHERE user_id = ?"
                params.append(user_id)

            if enabled_only:
                if user_id:
                    query += " AND enabled = 1"
                else:
                    query += " WHERE enabled = 1"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        def get_user_preferences(self, user_id):
            """Get user preferences from database."""
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT user_id, notification_email, dark_mode, notifications_enabled FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

        def insert_alert_rule(self, rule_id, user_id, name, metric, condition, threshold, action):
            """Insert an alert rule."""
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO alert_rules (rule_id, user_id, name, metric, condition, threshold, action, enabled)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (rule_id, user_id, name, metric, condition, threshold, action)
            )
            self.conn.commit()
            return True

        def update_alert_rule(self, rule_id, **kwargs):
            """Update an alert rule."""
            cursor = self.conn.cursor()
            if not kwargs:
                return False

            set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [rule_id]
            cursor.execute(f"UPDATE alert_rules SET {set_clause} WHERE rule_id = ?", values)
            self.conn.commit()
            return True

        def delete_alert_rule(self, rule_id):
            """Delete an alert rule."""
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM alert_rules WHERE rule_id = ?", (rule_id,))
            self.conn.commit()
            return True

        def log_alert_trigger(self, rule_id, current_value, threshold):
            """Log an alert trigger."""
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO alert_triggers (rule_id, current_value, threshold, triggered_at) VALUES (?, ?, ?, ?)",
                (rule_id, current_value, threshold, datetime.now().isoformat())
            )
            self.conn.commit()

        def get_alert_history(self, rule_id, limit=50):
            """Get alert trigger history."""
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT rule_id, current_value, threshold, triggered_at FROM alert_triggers WHERE rule_id = ? LIMIT ?",
                (rule_id, limit)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        def get_active_alerts(self, user_id):
            """Get active alerts for a user."""
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT rule_id FROM alert_rules WHERE user_id = ? AND enabled = 1",
                (user_id,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    class DatabaseConnection:
        """Context manager for database connections."""

        def __init__(self, conn):
            self.conn = conn

        def __enter__(self):
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_db = MockDbModule(temp_db)
    mock_db.init_db()
    return mock_db


@pytest.fixture
def mock_email_service():
    """Mock the email service for testing without sending real emails."""
    with mock.patch('email_service.EmailService') as mock_email:
        # Configure the mock to return True (success) by default
        mock_email.send_alert_email.return_value = True
        mock_email.send_digest_email.return_value = True
        mock_email.send_preference_confirmation_email.return_value = True
        yield mock_email


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing."""
    with mock.patch('bigquery_sync.get_bigquery_client') as mock_client:
        client = mock.MagicMock()
        mock_client.return_value = client
        yield mock_client


@pytest.fixture
def sample_metrics():
    """Sample metrics for alert testing."""
    return {
        'workbook_count': 150,
        'datasource_count': 45,
        'stale_count': 12,
        'custom_view_count': 8,
        'subscription_count': 25,
        'user_count': 89,
        'avg_score': 78.5,
        'severity_counts': {
            'critical': 3,
            'high': 5,
            'medium': 10,
            'low': 20
        }
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data for email testing."""
    return {
        'rule_id': 'rule_test_123',
        'rule_name': 'High Stale Workbooks',
        'user_id': 'user_456',
        'metric': 'stale_count',
        'current_value': 25,
        'threshold': 20,
        'condition': '>',
        'action': 'email',
        'triggered_at': datetime.now().isoformat()
    }


@pytest.fixture
def monkeypatch_env():
    """Fixture to safely set environment variables for tests."""
    original_env = os.environ.copy()

    def _set_env(**kwargs):
        for key, value in kwargs.items():
            os.environ[key] = value

    yield _set_env

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
