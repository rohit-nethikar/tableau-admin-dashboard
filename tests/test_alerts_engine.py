"""Tests for alerts_engine module - CRITICAL PATH.

The alert engine is critical because:
- It evaluates all alerts and triggers notifications
- Alert deduplication logic prevents duplicate emails
- Incorrect logic could lead to missing or excessive alerts

This test suite ensures alert rules are correctly evaluated and triggered.
"""

import sys
from pathlib import Path
from datetime import datetime
from unittest import mock

import pytest

# Import alerting modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import alerts_engine
from alerts_engine import AlertRule, AlertEngine


class TestAlertRuleEvaluation:
    """Test AlertRule condition evaluation - CRITICAL."""

    def test_alert_rule_greater_than_condition(self):
        """Alert should trigger when current_value > threshold."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='High Stale Count',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        # Should trigger: 25 > 20
        assert rule.evaluate(25) is True
        # Should not trigger: 20 > 20
        assert rule.evaluate(20) is False
        # Should not trigger: 15 > 20
        assert rule.evaluate(15) is False

    def test_alert_rule_less_than_condition(self):
        """Alert should trigger when current_value < threshold."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='Low Health Score',
            metric='health_score',
            condition='<',
            threshold=50,
            action='email'
        )

        # Should trigger: 40 < 50
        assert rule.evaluate(40) is True
        # Should not trigger: 50 < 50
        assert rule.evaluate(50) is False
        # Should not trigger: 60 < 50
        assert rule.evaluate(60) is False

    def test_alert_rule_equal_condition(self):
        """Alert should trigger when current_value == threshold."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='Exact Count',
            metric='workbook_count',
            condition='==',
            threshold=100,
            action='email'
        )

        # Should trigger: 100 == 100
        assert rule.evaluate(100) is True
        # Should not trigger: 99 == 100
        assert rule.evaluate(99) is False
        # Should not trigger: 101 == 100
        assert rule.evaluate(101) is False

    def test_alert_rule_not_equal_condition(self):
        """Alert should trigger when current_value != threshold."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='Change Detected',
            metric='status',
            condition='!=',
            threshold=0,
            action='email'
        )

        # Should trigger: 1 != 0
        assert rule.evaluate(1) is True
        # Should trigger: -1 != 0
        assert rule.evaluate(-1) is True
        # Should not trigger: 0 != 0
        assert rule.evaluate(0) is False

    def test_alert_rule_disabled_never_triggers(self):
        """Disabled alert rules should never trigger regardless of condition."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='Disabled Rule',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email',
            enabled=False
        )

        # Should never trigger even though 25 > 20
        assert rule.evaluate(25) is False

    def test_alert_rule_invalid_condition(self):
        """Alert rule with invalid condition should not trigger."""
        rule = AlertRule(
            rule_id='rule_1',
            user_id='user_1',
            name='Invalid Rule',
            metric='stale_count',
            condition='invalid',
            threshold=20,
            action='email'
        )

        # Should not trigger for invalid condition
        assert rule.evaluate(25) is False


class TestAlertEngineMetricEvaluation:
    """Test AlertEngine metric extraction and evaluation."""

    def test_extract_simple_metric(self, sample_metrics):
        """Engine should extract simple metrics from metrics dict."""
        assert AlertEngine._get_metric_value(sample_metrics, 'workbook_count') == 150
        assert AlertEngine._get_metric_value(sample_metrics, 'stale_count') == 12
        assert AlertEngine._get_metric_value(sample_metrics, 'user_count') == 89

    def test_extract_health_score_metric(self, sample_metrics):
        """Engine should extract health score from avg_score."""
        assert AlertEngine._get_metric_value(sample_metrics, 'health_score') == 78.5

    def test_extract_critical_issues_metric(self, sample_metrics):
        """Engine should calculate critical issues from severity counts."""
        # critical (3) + high (5) = 8
        value = AlertEngine._get_metric_value(sample_metrics, 'critical_issues')
        assert value == 8

    def test_extract_unknown_metric(self, sample_metrics):
        """Engine should return None for unknown metrics."""
        assert AlertEngine._get_metric_value(sample_metrics, 'unknown_metric') is None

    def test_extract_metric_with_missing_field(self):
        """Engine should handle missing fields gracefully."""
        metrics = {'workbook_count': 100}
        assert AlertEngine._get_metric_value(metrics, 'stale_count') is None


class TestAlertEngineTriggering:
    """Test alert triggering and execution - CRITICAL DEDUPLICATION."""

    def test_evaluate_metrics_triggers_matching_alerts(self, mock_db_module, sample_metrics):
        """AlertEngine should trigger alerts that match their conditions."""
        # Set up test data
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='High Stale Count',
            metric='stale_count',
            condition='>',
            threshold=10,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            with mock.patch.object(AlertEngine, '_execute_alert_action'):
                triggered = AlertEngine.evaluate_metrics(sample_metrics)

                assert len(triggered) > 0
                assert triggered[0]['rule_id'] == 'rule_1'
                assert triggered[0]['current_value'] == 12
                assert triggered[0]['threshold'] == 10

    def test_evaluate_metrics_skips_non_matching_alerts(self, mock_db_module, sample_metrics):
        """AlertEngine should not trigger alerts that don't match conditions."""
        # Create alert that should NOT trigger (12 is not > 20)
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Very High Stale Count',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            with mock.patch.object(AlertEngine, '_execute_alert_action'):
                triggered = AlertEngine.evaluate_metrics(sample_metrics)

                # Filter to just rule_1
                rule_1_alerts = [a for a in triggered if a['rule_id'] == 'rule_1']
                assert len(rule_1_alerts) == 0

    def test_evaluate_metrics_logs_triggers(self, mock_db_module, sample_metrics):
        """AlertEngine should log all triggered alerts."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Test Alert',
            metric='stale_count',
            condition='>',
            threshold=10,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            with mock.patch.object(AlertEngine, '_execute_alert_action'):
                AlertEngine.evaluate_metrics(sample_metrics)

                # Check that trigger was logged
                history = mock_db_module.get_alert_history('rule_1')
                assert len(history) > 0

    def test_evaluate_metrics_executes_alert_actions(self, mock_db_module, sample_metrics):
        """AlertEngine should execute the alert action (email, notification, etc)."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Test Alert',
            metric='stale_count',
            condition='>',
            threshold=10,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            with mock.patch.object(AlertEngine, '_execute_alert_action') as mock_execute:
                AlertEngine.evaluate_metrics(sample_metrics)

                # Verify execute was called
                assert mock_execute.called

    def test_evaluate_metrics_handles_exceptions(self, sample_metrics):
        """AlertEngine should handle exceptions without crashing."""
        with mock.patch('alerts_engine.db') as mock_db:
            mock_db.get_alert_rules.side_effect = Exception("Database error")

            # Should not raise exception
            triggered = AlertEngine.evaluate_metrics(sample_metrics)
            assert triggered == []

    def test_alert_action_email_execution(self, mock_db_module):
        """AlertEngine should send email for email action alerts."""
        # Set up user preferences
        with mock_db_module.get_conn() as conn:
            conn.execute(
                "INSERT INTO user_preferences (user_id, notification_email) VALUES (?, ?)",
                ('user_1', 'user@example.com')
            )
            conn.commit()

        alert_data = {
            'rule_id': 'rule_1',
            'rule_name': 'Test Alert',
            'user_id': 'user_1',
            'metric': 'stale_count',
            'current_value': 15,
            'threshold': 10,
            'action': 'email'
        }

        with mock.patch('alerts_engine.db', mock_db_module):
            with mock.patch('alerts_engine.send_alert_notification') as mock_send:
                AlertEngine._execute_alert_action('email', alert_data)

                mock_send.assert_called_once()


class TestAlertEnginePublicAPI:
    """Test public API functions for alert management."""

    def test_create_alert_rule(self, mock_db_module):
        """create_alert_rule should insert new rule."""
        with mock.patch('alerts_engine.db', mock_db_module):
            result = alerts_engine.create_alert_rule(
                user_id='user_1',
                name='Test Rule',
                metric='stale_count',
                condition='>',
                threshold=20,
                action='email'
            )

            assert result is True

    def test_get_user_alert_rules(self, mock_db_module):
        """get_user_alert_rules should return user's rules."""
        # Set up test data
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Rule 1',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            rules = alerts_engine.get_user_alert_rules('user_1')
            assert len(rules) == 1
            assert rules[0]['name'] == 'Rule 1'

    def test_update_alert_rule(self, mock_db_module):
        """update_alert_rule should modify existing rule."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Original Name',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            result = alerts_engine.update_alert_rule(
                'rule_1',
                name='Updated Name',
                threshold=30
            )

            assert result is True

    def test_delete_alert_rule(self, mock_db_module):
        """delete_alert_rule should remove rule."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Test Rule',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            result = alerts_engine.delete_alert_rule('rule_1')
            assert result is True

    def test_get_alert_history(self, mock_db_module):
        """get_alert_history should return trigger log."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Test Rule',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            # Log a trigger
            mock_db_module.log_alert_trigger('rule_1', 25, 20)

            history = alerts_engine.get_alert_history('rule_1')
            assert len(history) > 0

    def test_get_active_alerts(self, mock_db_module):
        """get_active_alerts should return enabled rules for user."""
        mock_db_module.insert_alert_rule(
            rule_id='rule_1',
            user_id='user_1',
            name='Active Rule',
            metric='stale_count',
            condition='>',
            threshold=20,
            action='email'
        )

        with mock.patch('alerts_engine.db', mock_db_module):
            alerts = alerts_engine.get_active_alerts('user_1')
            assert len(alerts) > 0
