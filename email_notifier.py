"""Sends plain-text emails with optional error log attachments when sync_service
detects alerts (extract failures, job failures, content changes). Purely a
notification - never touches Tableau, never remediates anything. Disabled (no-op)
unless smtp_host and alert_email_to are set in config.yaml. The caller
(sync_service.refresh_all) wraps calls to this module in its own try/except, the
same way every other sync section is isolated, so a mail-relay outage can't fail
the whole sync or lose cached data.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64

from config import settings


def _build_error_log_content(error_logs: list) -> str:
    lines = ["[ERROR LOG ATTACHMENT]", "", "Recent errors from sync operations:",""]
    for log in error_logs:
        lines.append(f"[{log.get('logged_at')}] {log.get('operation')}")
        lines.append(f"  Code: {log.get('error_code') or 'N/A'}")
        lines.append(f"  Message: {log.get('error_message') or 'N/A'}")
        if log.get('error_trace'):
            lines.append(f"  Trace:")
            for trace_line in log['error_trace'].split('\n'):
                if trace_line.strip():
                    lines.append(f"    {trace_line}")
        if log.get('context'):
            lines.append(f"  Context: {log['context']}")
        lines.append("")
    return "\n".join(lines)


def _attach_error_log(msg: MIMEMultipart, error_logs: list):
    if not error_logs:
        return
    log_content = _build_error_log_content(error_logs)
    attachment = MIMEBase('application', 'octet-stream')
    attachment.set_payload(log_content.encode('utf-8'))
    encoders.encode_base64(attachment)
    attachment.add_header('Content-Disposition', 'attachment; filename="error_log.txt"')
    msg.attach(attachment)


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


def send_extract_failure_alert(alerts: list, error_logs: list = None):
    if not alerts or not settings.smtp_host or not settings.alert_email_to:
        return
    if error_logs:
        msg = MIMEMultipart()
        msg.attach(MIMEText(_format_body(alerts)))
        _attach_error_log(msg, error_logs)
    else:
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


def send_config_change_alert(site: str, changes: list, error_logs: list = None):
    if not changes or not settings.smtp_host or not settings.alert_email_to:
        return
    if error_logs:
        msg = MIMEMultipart()
        msg.attach(MIMEText(_format_config_change_body(site, changes)))
        _attach_error_log(msg, error_logs)
    else:
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


def send_license_threshold_alert(site: str, crossed: list, error_logs: list = None):
    if not crossed or not settings.smtp_host or not settings.alert_email_to:
        return
    if error_logs:
        msg = MIMEMultipart()
        msg.attach(MIMEText(_format_license_body(site, crossed)))
        _attach_error_log(msg, error_logs)
    else:
        msg = MIMEText(_format_license_body(site, crossed))
    msg["Subject"] = f"[Tableau Admin Dashboard] License capacity threshold crossed on {site}"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())


def _format_job_failure_body(failures: list) -> str:
    lines = [f"{len(failures)} background job failure(s) detected during the latest sync:", ""]
    for job in failures:
        lines.append(f"- [{job.get('type') or 'Job'}] {job.get('job_name') or job.get('id')}")
        if job.get("resource_name"):
            lines.append(f"  Resource: {job['resource_name']}")
        lines.append(f"  Started: {job.get('started_at') or 'n/a'}  Ended: {job.get('ended_at') or 'n/a'}")
        lines.append("")
    return "\n".join(lines)


def send_job_failure_alert(failures: list, error_logs: list = None):
    if not failures or not settings.smtp_host or not settings.alert_email_to:
        return
    if error_logs:
        msg = MIMEMultipart()
        msg.attach(MIMEText(_format_job_failure_body(failures)))
        _attach_error_log(msg, error_logs)
    else:
        msg = MIMEText(_format_job_failure_body(failures))
    msg["Subject"] = f"[Tableau Admin Dashboard] {len(failures)} background job failure(s)"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())


def _format_content_change_body(site: str, changes: list) -> str:
    lines = [f"{len(changes)} content change(s) detected on site '{site}':", ""]
    by_type = {}
    for c in changes:
        by_type.setdefault(c["entity_type"], []).append(c)
    for entity_type, items in sorted(by_type.items()):
        lines.append(f"-- {entity_type.upper()} ({len(items)}) --")
        for c in items:
            lines.append(f"  [{c['change_type']}] {c.get('entity_name') or 'unnamed'}: {c['details']}")
        lines.append("")
    return "\n".join(lines)


def send_content_change_alert(site: str, changes: list, error_logs: list = None):
    if not changes or not settings.smtp_host or not settings.alert_email_to:
        return
    if error_logs:
        msg = MIMEMultipart()
        msg.attach(MIMEText(_format_content_change_body(site, changes)))
        _attach_error_log(msg, error_logs)
    else:
        msg = MIMEText(_format_content_change_body(site, changes))
    msg["Subject"] = f"[Tableau Admin Dashboard] {len(changes)} content change(s) on {site}"
    msg["From"] = settings.alert_email_from
    msg["To"] = settings.alert_email_to
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.sendmail(settings.alert_email_from, [settings.alert_email_to], msg.as_string())
