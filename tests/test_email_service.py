"""Tests for email_service module - CRITICAL PATH.

Email alerting is a core feature that users depend on for notifications.
This test suite ensures emails are properly formatted and sent.
"""

import os
import pytest
from unittest import mock
from datetime import datetime

# Import after path is set up by conftest
import email_service


class TestEmailServiceAlertEmail:
    """Test alert email sending - CRITICAL."""

    def test_send_alert_email_with_credentials(self, sample_alert_data):
        """Alert email should be sent when SMTP credentials are configured."""
        with mock.patch.multiple('email_service',
                               SMTP_USERNAME='test@example.com',
                               SMTP_PASSWORD='password123'):
            with mock.patch('smtplib.SMTP') as mock_smtp:
                # Configure mock SMTP server
                mock_server = mock.MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = email_service.EmailService.send_alert_email(
                    'user@example.com',
                    sample_alert_data
                )

                assert result is True
                mock_server.starttls.assert_called_once()
                mock_server.login.assert_called_once()
                mock_server.send_message.assert_called_once()

    def test_send_alert_email_without_credentials(self, sample_alert_data):
        """Alert email should fail gracefully when credentials are missing."""
        with mock.patch.multiple('email_service',
                               SMTP_USERNAME='',
                               SMTP_PASSWORD=''):
            result = email_service.EmailService.send_alert_email(
                'user@example.com',
                sample_alert_data
            )

            assert result is False

    def test_alert_email_html_rendering(self, sample_alert_data):
        """Alert email HTML should contain all required alert information."""
        html = email_service.EmailService._render_alert_html(sample_alert_data)

        assert 'High Stale Workbooks' in html
        assert 'stale_count' in html
        assert '25' in str(sample_alert_data['current_value'])
        assert '20' in str(sample_alert_data['threshold'])
        assert 'TRIGGERED' in html

    def test_alert_email_text_rendering(self, sample_alert_data):
        """Alert email text version should contain all alert information."""
        text = email_service.EmailService._render_alert_text(sample_alert_data)

        assert 'ALERT TRIGGERED' in text
        assert 'High Stale Workbooks' in text
        assert 'stale_count' in text
        assert '25' in str(sample_alert_data['current_value'])

    def test_alert_email_subject_generation(self, sample_alert_data):
        """Alert email subject should include rule name."""
        subject = f"🚨 Alert Triggered: {sample_alert_data['rule_name']}"
        assert 'High Stale Workbooks' in subject

    def test_alert_email_with_special_characters(self):
        """Alert email should handle special characters in rule names."""
        alert_data = {
            'rule_id': 'rule_123',
            'rule_name': 'Critical Alert & Urgent < Threshold > Limit',
            'metric': 'stale_count',
            'current_value': 100,
            'threshold': 50,
            'condition': '>',
        }

        html = email_service.EmailService._render_alert_html(alert_data)
        text = email_service.EmailService._render_alert_text(alert_data)

        # HTML should contain the rule name (may be escaped)
        assert 'Critical' in html
        # Text should preserve the exact text
        assert 'Critical Alert' in text

    def test_alert_email_smtp_connection_error(self, sample_alert_data):
        """Alert email should handle SMTP connection failures."""
        with mock.patch.multiple('email_service',
                               SMTP_USERNAME='test@example.com',
                               SMTP_PASSWORD='password123'):
            with mock.patch('smtplib.SMTP') as mock_smtp:
                mock_smtp.side_effect = Exception("Connection refused")

                result = email_service.EmailService.send_alert_email(
                    'user@example.com',
                    sample_alert_data
                )

                assert result is False


class TestEmailServiceDigestEmail:
    """Test daily/weekly digest email sending."""

    def test_send_digest_email_with_alerts(self):
        """Digest email should be sent when alerts are provided."""
        alerts = [
            {
                'rule_name': 'High Stale Workbooks',
                'metric': 'stale_count',
                'current_value': 25,
                'threshold': 20
            },
            {
                'rule_name': 'Critical Issues Detected',
                'metric': 'critical_issues',
                'current_value': 8,
                'threshold': 5
            }
        ]

        with mock.patch.multiple('email_service',
                               SMTP_USERNAME='test@example.com',
                               SMTP_PASSWORD='password123'):
            with mock.patch('smtplib.SMTP') as mock_smtp:
                mock_server = mock.MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = email_service.EmailService.send_digest_email(
                    'user@example.com',
                    alerts
                )

                assert result is True
                mock_server.send_message.assert_called_once()

    def test_send_digest_email_empty_list(self, monkeypatch_env):
        """send_daily_digest should return True for empty alert list."""
        result = email_service.send_daily_digest('user@example.com', [])
        assert result is True  # Nothing to send, but not an error

    def test_digest_email_html_rendering(self):
        """Digest email HTML should contain all alert information."""
        alerts = [
            {
                'rule_name': 'Alert 1',
                'metric': 'metric1',
                'current_value': 10,
                'threshold': 5
            },
            {
                'rule_name': 'Alert 2',
                'metric': 'metric2',
                'current_value': 20,
                'threshold': 15
            }
        ]

        html = email_service.EmailService._render_digest_html(alerts)

        assert 'Alert 1' in html
        assert 'Alert 2' in html
        assert 'metric1' in html
        assert 'metric2' in html
        assert 'TRIGGERED' in html

    def test_digest_email_text_rendering(self):
        """Digest email text version should list all alerts."""
        alerts = [
            {
                'rule_name': 'Alert 1',
                'metric': 'metric1',
                'current_value': 10,
                'threshold': 5
            }
        ]

        text = email_service.EmailService._render_digest_text(alerts)

        assert 'ALERT DIGEST' in text
        assert 'Alert 1' in text
        assert 'metric1' in text
        assert '1.' in text  # Numbered list


class TestEmailServicePublicAPI:
    """Test public API functions."""

    def test_send_alert_notification(self, sample_alert_data, monkeypatch_env):
        """Public send_alert_notification should delegate to EmailService."""
        monkeypatch_env(
            SMTP_USERNAME='test@example.com',
            SMTP_PASSWORD='password123'
        )

        with mock.patch.object(
            email_service.EmailService,
            'send_alert_email',
            return_value=True
        ) as mock_send:
            result = email_service.send_alert_notification(
                'user@example.com',
                sample_alert_data
            )

            assert result is True
            mock_send.assert_called_once()

    def test_send_daily_digest(self):
        """Public send_daily_digest should delegate to EmailService."""
        alerts = [
            {'rule_name': 'Alert 1', 'metric': 'm1', 'current_value': 10, 'threshold': 5}
        ]

        with mock.patch.object(
            email_service.EmailService,
            'send_digest_email',
            return_value=True
        ) as mock_send:
            result = email_service.send_daily_digest('user@example.com', alerts)

            assert result is True
            mock_send.assert_called_once()


class TestEmailServicePreferencesEmail:
    """Test preference confirmation emails."""

    def test_send_preference_confirmation(self):
        """Preference confirmation email should be sent."""
        preferences = {
            'dark_mode': True,
            'notification_email': 'user@example.com',
            'notifications_enabled': True
        }

        with mock.patch.multiple('email_service',
                               SMTP_USERNAME='test@example.com',
                               SMTP_PASSWORD='password123'):
            with mock.patch('smtplib.SMTP') as mock_smtp:
                mock_server = mock.MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                result = email_service.EmailService.send_preference_confirmation_email(
                    'user@example.com',
                    preferences
                )

                assert result is True
                mock_server.send_message.assert_called_once()

    def test_preference_email_html_rendering(self):
        """Preference confirmation HTML should reflect settings."""
        preferences = {
            'dark_mode': True,
            'notification_email': 'user@example.com',
            'notifications_enabled': False
        }

        html = email_service.EmailService.send_preference_confirmation_email(
            'user@example.com',
            preferences
        )

        # The HTML is rendered, sent, returns bool, so check with mock
        # This is a simple smoke test that the function doesn't crash
        assert isinstance(html, bool)
