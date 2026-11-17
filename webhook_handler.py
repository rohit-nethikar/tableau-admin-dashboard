"""Processes incoming Tableau Server webhook events for real-time notifications.
When a content event (workbook published, project renamed, datasource deleted, etc.)
arrives via webhook, this module logs it to content_change_log and sends an immediate
email alert. Webhooks are registered manually in Tableau Server; this handler is the
recipient endpoint."""
import datetime as dt
import json

import db
import email_notifier
import audit
from config import settings


def _utcnow_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def handle_webhook_event(site: str, event_type: str, resource_id: str, resource_name: str, payload: dict):
    """Process a webhook event and log it as a content change + send alert.

    Args:
        site: Tableau site name
        event_type: e.g. 'WorkbookPublished', 'ProjectDeleted', 'DatasourceUpdated'
        resource_id: Tableau resource ID (workbook_id, project_id, datasource_id)
        resource_name: Human-readable name (workbook name, project name, etc.)
        payload: Full webhook payload for context logging
    """
    now_iso = _utcnow_iso()
    entity_type = None
    change_type = None
    details = None

    if event_type in ("WorkbookPublished", "DatasourcePublished", "ProjectCreated"):
        entity_type = "workbook" if "Workbook" in event_type else "datasource" if "Datasource" in event_type else "project"
        change_type = "added"
        details = f"Created via webhook: {event_type}"

    elif event_type in ("WorkbookUnpublished", "DatasourceUnpublished", "ProjectDeleted"):
        entity_type = "workbook" if "Workbook" in event_type else "datasource" if "Datasource" in event_type else "project"
        change_type = "removed"
        details = f"Deleted via webhook: {event_type}"

    elif event_type in ("WorkbookUpdated", "DatasourceUpdated", "ProjectUpdated"):
        entity_type = "workbook" if "Workbook" in event_type else "datasource" if "Datasource" in event_type else "project"
        change_type = "modified"
        details = f"Modified via webhook: {event_type}"

    else:
        details = f"Webhook event: {event_type}"
        change_type = "webhook_event"

    if entity_type and change_type:
        db.add_content_change(
            site,
            now_iso,
            entity_type,
            resource_id,
            resource_name,
            change_type,
            details,
        )
        audit.log_action(
            "system",
            f"webhook_{event_type.lower()}",
            resource_type=entity_type,
            resource_id=resource_id,
            details=f"{entity_type} '{resource_name}' {change_type} via webhook",
        )

        change_event = {
            "entity_type": entity_type,
            "entity_name": resource_name,
            "change_type": change_type,
            "details": details,
        }

        try:
            error_logs = db.fetch_error_log_recent(site, hours=1, limit=20)
            email_notifier.send_content_change_alert(site, [change_event], error_logs)
        except Exception as exc:
            print(f"[WEBHOOK] Failed to send alert: {exc}")
            audit.log_action(
                "system",
                "webhook_alert_failed",
                details=f"Failed to send webhook alert: {exc}",
            )
