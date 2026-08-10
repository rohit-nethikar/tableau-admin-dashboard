"""Sends a plain-text email when sync_service detects a new or worsening
extract-refresh failure. Purely a notification - never touches Tableau, never
remediates anything. Disabled (no-op) unless smtp_host and alert_email_to are set in
config.yaml. The caller (sync_service.refresh_all) wraps calls to this module in its
own try/except, the same way every other sync section is isolated, so a mail-relay
outage can't fail the whole sync or lose cached data.
"""
import smtplib
from email.mime.text import MIMEText

from config import settings


def _format_body(alerts: list) -> str:
    lines = [f"{len(alerts)} extract refresh failure(s) detected during the latest sync:", ""]
    for alert in alerts:
        lines.append(
            f"- [{alert['resource_type']}] {alert['name']} "
            f"(project: {alert.get('project_name') or 'n/a'}, owner: {alert.get('owner_name') or 'n/a'})"
        )
        lines.append(
            f"  Status: {alert.get('extract_status') or 'n/a'}  "
            f"Last run: {alert.get('extract_last_run_at') or 'n/a'}  "
            f"Consecutive failures: {alert.get('consecutive_failures')}"
        )
        lines.append(f"  Log: {alert.get('notes') or 'Tableau returned no job notes for this run'}")
        if alert.get("webpage_url"):
            lines.append(f"  Link: {alert['webpage_url']}")
        lines.append("")
    return "\n".join(lines)


def send_extract_failure_alert(alerts: list):
    if not alerts or not settings.smtp_host or not settings.alert_email_to:
        return
    msg = MIMEText(_format_body(alerts))
    msg["Subject"] = f"[Tableau Admin Dashboard] {len(alerts)} extract refresh failure(s)"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())


def _format_config_change_body(site: str, changes: list) -> str:
    lines = [f"{len(changes)} site configuration change(s) detected on site '{site}':", ""]
    for c in changes:
        lines.append(f"- {c['label']}: {c['old']!r} -> {c['new']!r}")
    return "\n".join(lines)


def send_config_change_alert(site: str, changes: list):
    if not changes or not settings.smtp_host or not settings.alert_email_to:
        return
    msg = MIMEText(_format_config_change_body(site, changes))
    msg["Subject"] = f"[Tableau Admin Dashboard] {len(changes)} config change(s) on {site}"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())


def _format_license_body(site: str, crossed: list) -> str:
    lines = [f"Seat usage crossed {settings.license_alert_threshold_pct}% of capacity on site '{site}':", ""]
    for c in crossed:
        lines.append(f"- {c['tier']}: {c['used']}/{c['capacity']} used ({c['pct_used']}%)")
    return "\n".join(lines)


def send_license_threshold_alert(site: str, crossed: list):
    if not crossed or not settings.smtp_host or not settings.alert_email_to:
        return
    msg = MIMEText(_format_license_body(site, crossed))
    msg["Subject"] = f"[Tableau Admin Dashboard] License capacity threshold crossed on {site}"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())
