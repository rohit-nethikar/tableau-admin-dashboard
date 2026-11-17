"""Lightweight polling daemon that runs every 5-10 minutes to detect real-time
changes (background job failures and content changes) without waiting for the full
60-minute sync cycle. Sends immediate alerts on detection. Separate from the main
sync_service to keep polling overhead low and enable future webhook integration.
"""
import datetime as dt
import traceback

import db
import email_notifier
import tableau_client
import content_change_detector
import job_failure_tracker
from config import settings
import audit


def _utcnow_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def poll_site(site: str, server):
    """Lightweight poll: check for new job failures and content changes.
    Much faster than full sync (no permissions, lineage, health scores, etc.).
    Sends immediate alerts on detection. Errors are logged but don't stop the poll."""
    try:
        import tableauserverclient as TSC

        job_failures = []
        content_changes = []
        errors = []

        try:
            workbooks = list(TSC.Pager(server.workbooks))
            datasources = list(TSC.Pager(server.datasources))

            workbooks_by_id = {wb.id: wb.name for wb in workbooks}
            datasources_by_id = {ds.id: ds.name for ds in datasources}

            jobs = tableau_client.list_background_jobs(
                server, workbooks_by_id, datasources_by_id
            )
            job_failures.extend(
                job_failure_tracker.detect_new_failures(site, jobs, _utcnow_iso())
            )
        except Exception as exc:
            errors.append(f"background_jobs_poll: {exc}")
            traceback.print_exc()

        try:
            previous_workbooks = db.fetch_workbooks(site)
            workbooks_list = list(TSC.Pager(server.workbooks))
            new_wb_dicts = [
                {
                    "id": wb.id,
                    "name": wb.name,
                    "project_name": wb.project_name,
                    "owner_name": wb.owner.name if hasattr(wb, "owner") and wb.owner else None,
                    "sheet_count": getattr(wb, "sheet_count", 0),
                }
                for wb in workbooks_list
            ]
            content_changes.extend(
                content_change_detector.diff_entities(
                    site,
                    "workbook",
                    previous_workbooks,
                    new_wb_dicts,
                    _utcnow_iso(),
                    content_change_detector._WORKBOOK_FIELDS,
                )
            )
            content_changes.extend(
                content_change_detector.diff_schedules(
                    site, previous_workbooks, new_wb_dicts, _utcnow_iso(), "workbook"
                )
            )
        except Exception as exc:
            errors.append(f"workbooks_poll: {exc}")
            traceback.print_exc()

        try:
            previous_datasources = db.fetch_datasources(site)
            datasources_list = list(TSC.Pager(server.datasources))
            new_ds_dicts = [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "project_name": ds.project_name,
                    "owner_name": ds.owner.name if hasattr(ds, "owner") and ds.owner else None,
                    "is_certified": getattr(ds, "certified", False) and 1 or 0,
                }
                for ds in datasources_list
            ]
            content_changes.extend(
                content_change_detector.diff_entities(
                    site,
                    "datasource",
                    previous_datasources,
                    new_ds_dicts,
                    _utcnow_iso(),
                    content_change_detector._DATASOURCE_FIELDS,
                )
            )
            content_changes.extend(
                content_change_detector.diff_schedules(
                    site,
                    previous_datasources,
                    new_ds_dicts,
                    _utcnow_iso(),
                    "datasource",
                )
            )
        except Exception as exc:
            errors.append(f"datasources_poll: {exc}")
            traceback.print_exc()

        if job_failures:
            try:
                error_logs = db.fetch_error_log_recent(site, hours=1, limit=20)
                email_notifier.send_job_failure_alert(job_failures, error_logs)
                audit.log_action(
                    "system",
                    "job_failure_alert_sent_realtime",
                    details=f"Emailed {settings.alert_email_to} about {len(job_failures)} failed job(s) (real-time)",
                )
            except Exception as exc:
                errors.append(f"job_failure_alert_email: {exc}")

        if content_changes:
            try:
                error_logs = db.fetch_error_log_recent(site, hours=1, limit=20)
                email_notifier.send_content_change_alert(site, content_changes, error_logs)
                audit.log_action(
                    "system",
                    "content_change_alert_sent_realtime",
                    details=f"Emailed {settings.alert_email_to} about {len(content_changes)} content change(s) (real-time)",
                )
            except Exception as exc:
                errors.append(f"content_change_alert_email: {exc}")

        if errors:
            for error in errors:
                print(f"[POLLER] {error}")

    except Exception as exc:
        print(f"[POLLER] Fatal error in poll_site: {exc}")
        traceback.print_exc()
