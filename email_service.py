"""
Email Service for Phase 4 Alerts
Sends email notifications when alert rules are triggered
"""

import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any

# Configuration - set via environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'tableau-admin@example.com')
EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'Tableau Admin Dashboard')


class EmailService:
    """Service for sending email notifications"""

    @staticmethod
    def send_alert_email(recipient_email: str, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert triggered email

        Args:
            recipient_email: Email address to send to
            alert_data: Alert information (rule_name, metric, current_value, threshold)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = f"🚨 Alert Triggered: {alert_data['rule_name']}"

            html_body = EmailService._render_alert_html(alert_data)
            text_body = EmailService._render_alert_text(alert_data)

            return EmailService._send_email(recipient_email, subject, text_body, html_body)

        except Exception as e:
            print(f"Error sending alert email to {recipient_email}: {e}")
            return False

    @staticmethod
    def send_digest_email(recipient_email: str, alerts: List[Dict[str, Any]]) -> bool:
        """
        Send daily/weekly digest of triggered alerts

        Args:
            recipient_email: Email address to send to
            alerts: List of alert triggers

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            subject = f"📊 Alert Digest - {datetime.now().strftime('%Y-%m-%d')}"

            html_body = EmailService._render_digest_html(alerts)
            text_body = EmailService._render_digest_text(alerts)

            return EmailService._send_email(recipient_email, subject, text_body, html_body)

        except Exception as e:
            print(f"Error sending digest email to {recipient_email}: {e}")
            return False

    @staticmethod
    def send_preference_confirmation_email(recipient_email: str, preferences: Dict[str, Any]) -> bool:
        """
        Send confirmation when user updates preferences
        """
        try:
            subject = "✅ Tableau Dashboard Preferences Updated"

            html_body = f"""
                <html>
                    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        <h2 style="color: #004B87;">Preferences Updated</h2>
                        <p>Your Tableau Admin Dashboard preferences have been updated.</p>

                        <h3>Updated Settings:</h3>
                        <ul>
                            <li>Dark Mode: {'Enabled' if preferences.get('dark_mode') else 'Disabled'}</li>
                            <li>Notification Email: {preferences.get('notification_email', 'Not set')}</li>
                            <li>Notifications: {'Enabled' if preferences.get('notifications_enabled') else 'Disabled'}</li>
                        </ul>

                        <p style="color: #666; font-size: 12px;">
                            If you did not make these changes, please contact your administrator.
                        </p>
                    </body>
                </html>
            """

            text_body = f"""
            Preferences Updated

            Your Tableau Admin Dashboard preferences have been updated.

            Updated Settings:
            - Dark Mode: {'Enabled' if preferences.get('dark_mode') else 'Disabled'}
            - Notification Email: {preferences.get('notification_email', 'Not set')}
            - Notifications: {'Enabled' if preferences.get('notifications_enabled') else 'Disabled'}
            """

            return EmailService._send_email(recipient_email, subject, text_body, html_body)

        except Exception as e:
            print(f"Error sending preference confirmation email to {recipient_email}: {e}")
            return False

    @staticmethod
    def _render_alert_html(alert_data: Dict[str, Any]) -> str:
        """Render HTML alert email"""
        severity_colors = {
            'critical': '#D9534F',
            'high': '#FF9800',
            'medium': '#FFC107',
            'low': '#4CAF50'
        }

        metric_color = severity_colors.get('high', '#FF9800')

        return f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="background: linear-gradient(135deg, #004B87 0%, #00A3E0 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="margin: 0; font-size: 24px;">🚨 Alert Triggered</h2>
                        <p style="margin: 5px 0 0 0; opacity: 0.9;">
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        </p>
                    </div>

                    <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid {metric_color}; margin-bottom: 20px; border-radius: 4px;">
                        <h3 style="margin-top: 0; color: {metric_color};">{alert_data['rule_name']}</h3>

                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                            <div>
                                <p style="margin: 0 0 5px 0; color: #666; font-size: 12px;">METRIC</p>
                                <p style="margin: 0; font-weight: 600; font-size: 16px;">{alert_data['metric']}</p>
                            </div>
                            <div>
                                <p style="margin: 0 0 5px 0; color: #666; font-size: 12px;">STATUS</p>
                                <p style="margin: 0; font-weight: 600; font-size: 16px; color: {metric_color};">TRIGGERED</p>
                            </div>
                        </div>
                    </div>

                    <h3>Condition Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background: #f9f9f9;">
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Current Value</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd; color: {metric_color}; font-weight: 600;">
                                {alert_data['current_value']}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Threshold</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">{alert_data['threshold']}</td>
                        </tr>
                        <tr style="background: #f9f9f9;">
                            <td style="padding: 10px; border: 1px solid #ddd;"><strong>Condition</strong></td>
                            <td style="padding: 10px; border: 1px solid #ddd;">
                                Value {alert_data['metric']} {alert_data.get('condition', '>')} {alert_data['threshold']}
                            </td>
                        </tr>
                    </table>

                    <p style="margin-top: 20px; text-align: center;">
                        <a href="http://localhost:5000" style="background: #004B87; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            View Dashboard
                        </a>
                    </p>

                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        This is an automated notification from Tableau Admin Dashboard.
                    </p>
                </body>
            </html>
        """

    @staticmethod
    def _render_alert_text(alert_data: Dict[str, Any]) -> str:
        """Render plain text alert email"""
        return f"""
ALERT TRIGGERED: {alert_data['rule_name']}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Condition Details:
- Metric: {alert_data['metric']}
- Current Value: {alert_data['current_value']}
- Threshold: {alert_data['threshold']}
- Condition: Value {alert_data.get('condition', '>')} {alert_data['threshold']}

View Dashboard: http://localhost:5000

This is an automated notification from Tableau Admin Dashboard.
        """

    @staticmethod
    def _render_digest_html(alerts: List[Dict[str, Any]]) -> str:
        """Render HTML digest email"""
        alerts_html = ""
        for alert in alerts:
            alerts_html += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">{alert['rule_name']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{alert['metric']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{alert['current_value']}</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        <span style="background: #FFE5E5; color: #D9534F; padding: 2px 6px; border-radius: 3px; font-size: 12px;">
                            TRIGGERED
                        </span>
                    </td>
                </tr>
            """

        return f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="background: linear-gradient(135deg, #004B87 0%, #00A3E0 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                        <h2 style="margin: 0; font-size: 24px;">📊 Alert Digest</h2>
                        <p style="margin: 5px 0 0 0; opacity: 0.9;">
                            {datetime.now().strftime('%Y-%m-%d')}
                        </p>
                    </div>

                    <p>You have <strong>{len(alerts)}</strong> triggered alert(s) in the past 24 hours.</p>

                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background: #f5f5f5;">
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Alert Name</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Metric</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Value</th>
                                <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts_html}
                        </tbody>
                    </table>

                    <p style="text-align: center;">
                        <a href="http://localhost:5000" style="background: #004B87; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                            View Dashboard
                        </a>
                    </p>
                </body>
            </html>
        """

    @staticmethod
    def _render_digest_text(alerts: List[Dict[str, Any]]) -> str:
        """Render plain text digest email"""
        alerts_text = ""
        for i, alert in enumerate(alerts, 1):
            alerts_text += f"{i}. {alert['rule_name']}: {alert['metric']} = {alert['current_value']}\n"

        return f"""
ALERT DIGEST - {datetime.now().strftime('%Y-%m-%d')}

You have {len(alerts)} triggered alert(s):

{alerts_text}

View Dashboard: http://localhost:5000

This is an automated notification from Tableau Admin Dashboard.
        """

    @staticmethod
    def _send_email(recipient_email: str, subject: str, text_body: str, html_body: str) -> bool:
        """
        Send email via SMTP

        Returns:
            True if sent successfully, False otherwise
        """
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print("Warning: Email credentials not configured. Email not sent.")
            print(f"Email would be sent to {recipient_email} with subject: {subject}")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
            msg['To'] = recipient_email

            # Attach parts
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Send via SMTP
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

            print(f"✅ Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            print(f"❌ Failed to send email to {recipient_email}: {e}")
            return False


def send_alert_notification(user_email: str, alert_data: Dict[str, Any]) -> bool:
    """
    Public function to send alert email notification
    """
    return EmailService.send_alert_email(user_email, alert_data)


def send_daily_digest(user_email: str, triggered_alerts: List[Dict[str, Any]]) -> bool:
    """
    Public function to send daily digest of alerts
    """
    if not triggered_alerts:
        return True  # Nothing to send

    return EmailService.send_digest_email(user_email, triggered_alerts)
