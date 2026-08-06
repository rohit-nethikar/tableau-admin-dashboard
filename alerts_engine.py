"""
Alert Engine for Phase 4
Manages alert rules, evaluates conditions, and triggers notifications
"""

import db
import json
from datetime import datetime
from typing import List, Dict, Any
from email_service import send_alert_notification


class AlertRule:
    """Represents an alert rule"""
    def __init__(self, rule_id: str, user_id: str, name: str, metric: str,
                 condition: str, threshold: float, action: str, enabled: bool = True):
        self.rule_id = rule_id
        self.user_id = user_id
        self.name = name
        self.metric = metric  # workbook_count, stale_count, critical_issues, health_score
        self.condition = condition  # '>', '<', '==', '!='
        self.threshold = threshold
        self.action = action  # 'email', 'notification', 'badge'
        self.enabled = enabled

    def evaluate(self, current_value: float) -> bool:
        """Check if the alert should trigger"""
        if not self.enabled:
            return False

        if self.condition == '>':
            return current_value > self.threshold
        elif self.condition == '<':
            return current_value < self.threshold
        elif self.condition == '==':
            return current_value == self.threshold
        elif self.condition == '!=':
            return current_value != self.threshold
        return False


class AlertEngine:
    """Main alert engine for evaluating and triggering alerts"""

    @staticmethod
    def evaluate_metrics(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate all enabled alerts against current metrics
        Returns list of triggered alerts
        """
        triggered_alerts = []

        try:
            # Get all enabled alert rules
            rules = db.get_alert_rules(enabled_only=True)

            for rule in rules:
                # Extract the current metric value
                current_value = AlertEngine._get_metric_value(metrics, rule['metric'])

                if current_value is None:
                    continue

                # Create rule object and evaluate
                alert_rule = AlertRule(
                    rule_id=rule['rule_id'],
                    user_id=rule['user_id'],
                    name=rule['name'],
                    metric=rule['metric'],
                    condition=rule['condition'],
                    threshold=rule['threshold'],
                    action=rule['action'],
                    enabled=rule['enabled']
                )

                # Check if alert should trigger
                if alert_rule.evaluate(current_value):
                    triggered_alerts.append({
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['name'],
                        'user_id': rule['user_id'],
                        'metric': rule['metric'],
                        'current_value': current_value,
                        'threshold': rule['threshold'],
                        'action': rule['action'],
                        'triggered_at': datetime.now().isoformat()
                    })

                    # Log the alert trigger
                    db.log_alert_trigger(rule['rule_id'], current_value, rule['threshold'])

                    # Execute alert action
                    AlertEngine._execute_alert_action(rule['action'], triggered_alerts[-1])

        except Exception as e:
            print(f"Error in AlertEngine.evaluate_metrics: {e}")

        return triggered_alerts

    @staticmethod
    def _get_metric_value(metrics: Dict[str, Any], metric_key: str) -> float:
        """Extract metric value from metrics dict"""
        metric_mapping = {
            'workbook_count': 'workbook_count',
            'datasource_count': 'datasource_count',
            'stale_count': 'stale_count',
            'custom_view_count': 'custom_view_count',
            'subscription_count': 'subscription_count',
            'user_count': 'user_count',
            'critical_issues': lambda m: m.get('severity_counts', {}).get('critical', 0) + m.get('severity_counts', {}).get('high', 0),
            'health_score': 'avg_score'
        }

        if metric_key in metric_mapping:
            mapping = metric_mapping[metric_key]
            if callable(mapping):
                return mapping(metrics)
            return metrics.get(mapping)

        return None

    @staticmethod
    def _execute_alert_action(action: str, alert_data: Dict[str, Any]):
        """Execute the alert action (email, notification, badge, etc.)"""
        try:
            if action == 'email':
                AlertEngine._send_email_alert(alert_data)
            elif action == 'notification':
                AlertEngine._send_notification_alert(alert_data)
            elif action == 'badge':
                AlertEngine._add_badge_alert(alert_data)
        except Exception as e:
            print(f"Error executing alert action {action}: {e}")

    @staticmethod
    def _send_email_alert(alert_data: Dict[str, Any]):
        """Send email alert notification"""
        try:
            # Get user's email from preferences
            user_prefs = db.get_user_preferences(alert_data['user_id'])
            if user_prefs and user_prefs.get('notification_email'):
                email = user_prefs['notification_email']
                success = send_alert_notification(email, alert_data)
                if success:
                    print(f"✅ Email alert sent to {email}: {alert_data['rule_name']}")
                else:
                    print(f"⚠️ Failed to send email alert to {email}")
            else:
                print(f"⚠️ No notification email configured for user {alert_data['user_id']}")
        except Exception as e:
            print(f"❌ Error sending email alert: {e}")

    @staticmethod
    def _send_notification_alert(alert_data: Dict[str, Any]):
        """Send browser notification (via WebSocket)"""
        print(f"Notification alert: {alert_data['rule_name']} triggered")
        # TODO: Broadcast via WebSocket to user's dashboard

    @staticmethod
    def _add_badge_alert(alert_data: Dict[str, Any]):
        """Add badge/badge to dashboard"""
        print(f"Badge alert: {alert_data['rule_name']} - show badge on dashboard")
        # TODO: Store in cache for dashboard display


def create_alert_rule(user_id: str, name: str, metric: str, condition: str,
                     threshold: float, action: str) -> bool:
    """Create a new alert rule"""
    rule_id = f"rule_{user_id}_{metric}_{int(datetime.now().timestamp())}"
    return db.insert_alert_rule(rule_id, user_id, name, metric, condition, threshold, action)


def update_alert_rule(rule_id: str, **kwargs) -> bool:
    """Update an alert rule"""
    return db.update_alert_rule(rule_id, **kwargs)


def delete_alert_rule(rule_id: str) -> bool:
    """Delete an alert rule"""
    return db.delete_alert_rule(rule_id)


def get_user_alert_rules(user_id: str) -> List[Dict[str, Any]]:
    """Get all alert rules for a user"""
    return db.get_alert_rules(user_id=user_id)


def get_alert_history(rule_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get alert trigger history for a rule"""
    return db.get_alert_history(rule_id, limit)


def get_active_alerts(user_id: str) -> List[Dict[str, Any]]:
    """Get currently active alerts for a user"""
    return db.get_active_alerts(user_id)
