# Test Suite for Tableau Admin Dashboard

This document explains the test suite, what it covers, and how to run it.

## Overview

The Tableau Admin Dashboard has **4 focused test modules** covering the highest-risk areas:

1. **Email Service Tests** (`tests/test_email_service.py`)
   - Tests alert email sending (SMTP, credential handling)
   - Tests digest email generation
   - Tests preference confirmation emails
   - **Why critical:** Email alerting is a core feature; failures here mean users miss notifications

2. **Alerts Engine Tests** (`tests/test_alerts_engine.py`)
   - Tests alert rule evaluation (condition logic: >, <, ==, !=)
   - Tests metric extraction from dashboard data
   - Tests alert deduplication logic (prevents duplicate notifications)
   - Tests alert action execution (email, notification, badge)
   - **Why critical:** Alert deduplication is a data governance feature; failures could flood users with duplicate emails

3. **BigQuery Sync Tests** (`tests/test_bigquery_sync.py`)
   - Tests account number fetching from BigQuery
   - Tests data integrity (email normalization, null handling)
   - Tests database sync operations
   - Tests placeholder user creation for custom view owners
   - **Why critical:** Data integrity depends on correct email-to-account mapping; sync failures mean lost account numbers

4. **Account Number Sync Tests** (`tests/test_account_sync.py`)
   - Tests lock mechanism to prevent duplicate syncs
   - Tests database operations and counting
   - Tests threading and cleanup
   - Tests integration with watchdog error handling
   - **Why critical:** Sync runs on startup; locking prevents race conditions; failures here could corrupt data

## Test Coverage Summary

| Critical Path | Test Module | Test Count | Key Tests |
|---|---|---|---|
| Email Alerting | `test_email_service.py` | 15 | SMTP credentials, HTML/text rendering, connection errors |
| Alert Rules | `test_alerts_engine.py` | 20 | Condition evaluation (>, <, ==, !=), metric extraction, deduplication |
| BigQuery Sync | `test_bigquery_sync.py` | 18 | Client init, account fetch, email normalization, placeholder users |
| Account Sync | `test_account_sync.py` | 13 | Lock mechanism, database ops, threading, error handling |
| **Total** | **4 modules** | **66 tests** | Full coverage of critical paths |

## Installation

### Install Testing Dependencies

```bash
# Install pytest
pip install pytest

# Or use the updated requirements.txt with pytest included:
pip install -r requirements.txt
```

### Verify Installation

```bash
pytest --version
```

## Running the Tests

### Run All Tests

```bash
# Run all tests with verbose output
pytest -v

# Run with coverage report (requires pytest-cov)
pip install pytest-cov
pytest --cov=. --cov-report=term-missing
```

### Run Specific Test Modules

```bash
# Email service tests
pytest tests/test_email_service.py -v

# Alert engine tests (deduplication, condition evaluation)
pytest tests/test_alerts_engine.py -v

# BigQuery sync tests (data integrity)
pytest tests/test_bigquery_sync.py -v

# Account number sync tests (threading, locking)
pytest tests/test_account_sync.py -v
```

### Run Specific Tests

```bash
# Run single test
pytest tests/test_email_service.py::TestEmailServiceAlertEmail::test_send_alert_email_with_credentials -v

# Run all tests matching a pattern
pytest -k "email" -v
pytest -k "deduplication" -v
pytest -k "bigquery" -v
```

### Run with Output

```bash
# Show print statements and logs
pytest -v -s

# Show local variables on failure
pytest -v -l
```

## Test Structure

Each test module follows this pattern:

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── test_email_service.py       # Email alerting tests
├── test_alerts_engine.py       # Alert rules & deduplication
├── test_bigquery_sync.py       # Data sync tests
└── test_account_sync.py        # Account number sync tests
```

## Key Fixtures (conftest.py)

The shared `conftest.py` provides:

### `temp_db`
In-memory SQLite database for testing without touching production DB.

```python
def test_something(temp_db):
    conn = temp_db
    cursor = conn.cursor()
    # Use database
```

### `mock_db_module`
Mock database module with test schema and basic operations.

```python
def test_something(mock_db_module):
    mock_db_module.insert_alert_rule(...)
    rules = mock_db_module.get_alert_rules()
```

### `mock_email_service`
Mocked email service to avoid real SMTP calls.

```python
def test_something(mock_email_service):
    # EmailService.send_alert_email() won't actually send emails
```

### `sample_metrics` & `sample_alert_data`
Pre-built test data for consistency.

```python
def test_something(sample_metrics, sample_alert_data):
    # Use realistic test data
```

## Common Test Patterns

### Testing Email Sending

```python
def test_alert_email(monkeypatch_env):
    monkeypatch_env(SMTP_USERNAME='test@example.com', SMTP_PASSWORD='pass123')
    
    with mock.patch('smtplib.SMTP') as mock_smtp:
        result = email_service.send_alert_email('user@example.com', alert_data)
        assert result is True
        mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()
```

### Testing Alert Rules

```python
def test_alert_condition(mock_db_module, sample_metrics):
    rule = AlertRule(..., condition='>', threshold=20, ...)
    
    # Should trigger
    assert rule.evaluate(25) is True
    
    # Should not trigger
    assert rule.evaluate(15) is False
```

### Testing Database Operations

```python
def test_sync_updates_users(mock_db_module):
    with mock_db_module.get_conn() as conn:
        conn.execute("INSERT INTO users ...")
        conn.commit()
    
    # Test operation
    result = bigquery_sync.sync_account_numbers_to_database(mock_db_module)
    assert result['status'] == 'success'
```

## Understanding Test Names

Test names follow a pattern that describes what they test:

- `test_send_alert_email_with_credentials` → Email sending when SMTP is configured
- `test_alert_rule_greater_than_condition` → Condition evaluation (> operator)
- `test_fetch_account_numbers_normalizes_email` → Email normalization in BigQuery fetch
- `test_sync_lock_prevents_duplicate_syncs` → Lock mechanism in account sync

## Troubleshooting

### Tests Fail with "ModuleNotFoundError"

```bash
# Make sure you're in the project root directory
cd tableau-admin-dashboard

# Check that tests directory exists
ls tests/

# Try with explicit PYTHONPATH
PYTHONPATH=. pytest tests/
```

### Tests Fail with Database Errors

All tests use in-memory SQLite databases created in `conftest.py`. If you see database errors:

1. Check that `conftest.py` exists in `tests/` directory
2. Run a single test to see detailed error: `pytest tests/test_email_service.py::TestEmailServiceAlertEmail::test_send_alert_email_with_credentials -v -s`
3. Check that mock fixtures are properly imported

### Tests Slow or Hanging

1. Default timeout is reasonable; if tests hang, check for unmocked external calls
2. Reduce scope: `pytest tests/test_email_service.py::TestEmailServiceAlertEmail -v`
3. Run with `-s` to see print statements: `pytest -v -s`

## CI/CD Integration

To run tests in CI/CD:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests and fail if any fail
pytest --tb=short --strict-markers -q

# Generate JUnit XML for CI systems
pip install pytest-junit
pytest --junit-xml=test-results.xml
```

## Future Enhancements

The test suite provides a foundation for:

1. **Route-level integration tests** - Test Flask routes end-to-end
2. **Scheduler tests** - Test background job scheduling
3. **Permissions tests** - Test access control logic
4. **Integration tests** - Test real Tableau API calls with mocking

## Maintenance

When making changes to critical paths:

1. **Email changes** → Update `test_email_service.py`
2. **Alert logic changes** → Update `test_alerts_engine.py`
3. **BigQuery sync changes** → Update `test_bigquery_sync.py`
4. **Startup sync changes** → Update `test_account_sync.py`

Add tests for:
- Happy path (normal operation)
- Error paths (failures, missing data)
- Edge cases (null values, special characters)
- Security aspects (credential handling, data protection)

## References

- **pytest documentation:** https://docs.pytest.org
- **unittest.mock documentation:** https://docs.python.org/3/library/unittest.mock.html
- **SQLite in Python:** https://docs.python.org/3/library/sqlite3.html
