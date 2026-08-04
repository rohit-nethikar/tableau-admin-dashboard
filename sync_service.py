"""Orchestrates a full cache refresh: sign in once, pull each data section, write it
into SQLite. Each section is wrapped in its own try/except so one failing API (most
commonly the Metadata API, if it isn't enabled) doesn't block the others - see
metadata_client.py's docstring.

After the Tableau-facing sync sections, a second pass computes governance data
(permission risk, orphaned content, health scores, findings) purely from what's now
in the local cache - no further Tableau API calls needed, so these can't fail due to
connectivity, only due to bugs in their own logic (also individually isolated below).
"""
import datetime as dt

import audit
import crypto
import db
import dqw_detection
import email_notifier
import findings_engine
import health_scoring
import metadata_client
import orphan_detection
import permission_risk
import tableau_client
from config import settings


def _utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _ensure_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


def _is_stale(updated_at: dt.datetime, now: dt.datetime) -> bool:
    if not updated_at:
        return False
    age_days = (now - _ensure_utc(updated_at)).days
    return age_days >= settings.stale_threshold_days


def refresh_all(site: str):
    run_id = db.start_refresh(site, _utcnow_iso())
    errors = []

    pat_name = db.get_config("pat_name")
    pat_encrypted = db.get_config("pat_encrypted")
    if not pat_name or not pat_encrypted:
        db.finish_refresh(run_id, _utcnow_iso(), "failed", "No PAT configured - complete /setup first.")
        return
    pat_secret = crypto.decrypt_value(pat_encrypted)

    alerts = []
    try:
        with tableau_client.signed_in_server(
            settings.server_url, site, pat_name, pat_secret
        ) as server:
            auth_token = server.auth_token
            _sync_projects_and_content(site, server, errors, alerts)
            _sync_lineage_and_usage(site, server, auth_token, errors)
    except Exception as exc:
        db.finish_refresh(run_id, _utcnow_iso(), "failed", f"Sign-in or connection failed: {exc}")
        return

    if alerts:
        try:
            email_notifier.send_extract_failure_alert(alerts)
            audit.log_action(
                "system",
                "extract_failure_alert_sent",
                details=f"Emailed {settings.alert_email_to} about {len(alerts)} failing extract(s)",
            )
        except Exception as exc:
            errors.append(f"email_alert: {exc}")

    permission_risk_findings = permission_risk.compute(site, errors)
    orphan_findings = orphan_detection.compute(site, errors)
    dqw_findings = dqw_detection.compute(site, errors)
    health_scoring.compute_and_store(site, errors, permission_risk_findings, orphan_findings)
    findings_engine.run_all_rules(
        site, errors, permission_risk_findings, orphan_findings, dqw_findings, _utcnow_iso()
    )

    status = "success" if not errors else "partial"
    db.finish_refresh(run_id, _utcnow_iso(), status, "; ".join(errors) if errors else "OK")


def _escalated(previous_failures, new_failures) -> bool:
    """True if a resource just started failing, or its consecutive-failure count
    grew since the last sync - used to avoid re-emailing about an already-known,
    unchanged failure on every sync cycle."""
    if not new_failures:
        return False
    if previous_failures is None:
        return True
    return new_failures > previous_failures


def _sync_projects_and_content(site, server, errors, alerts):
    try:
        project_rows, projects_by_id = tableau_client.list_projects(server)
        db.replace_projects(site, project_rows)
    except Exception as exc:
        errors.append(f"projects: {exc}")
        projects_by_id = {}

    users_by_id_name = {}
    try:
        user_rows = tableau_client.list_users_full(server)
        db.replace_users(site, user_rows)
        users_by_id_name = {row[0]: row[1] for row in user_rows}
    except Exception as exc:
        errors.append(f"users: {exc}")

    try:
        extract_status = tableau_client.list_extract_refresh_status(server)
    except Exception as exc:
        errors.append(f"extract_status: {exc}")
        extract_status = {}

    try:
        extract_schedules = tableau_client.list_extract_refresh_schedules(server)
    except Exception as exc:
        errors.append(f"extract_schedules: {exc}")
        extract_schedules = {}

    favorites_lookup = {}
    try:
        favorites_lookup = tableau_client.list_favorites_totals(server)
    except Exception as exc:
        errors.append(f"favorites: {exc}")

    workbooks = []
    try:
        previous_wb_failures = {
            row["id"]: row.get("consecutive_extract_failures") for row in db.fetch_workbooks(site)
        }
        workbooks = tableau_client.list_workbooks(server, users_by_id_name, projects_by_id)
        now = dt.datetime.now(dt.timezone.utc)
        try:
            wb_detail = tableau_client.enrich_workbooks(server, workbooks)
        except Exception as exc:
            errors.append(f"workbook_detail: {exc}")
            wb_detail = {}
        wb_rows = []
        for wb in workbooks:
            updated_at = wb.updated_at
            updated_at_iso = updated_at.isoformat() if updated_at else None
            status_info = extract_status.get(wb.id, {})
            schedule_info = extract_schedules.get(wb.id, {})
            detail = wb_detail.get(wb.id, {})
            created_at = getattr(wb, "created_at", None)
            consecutive_failures = status_info.get("consecutive_failures")
            owner_name = users_by_id_name.get(wb.owner_id, wb.owner_id)
            if _escalated(previous_wb_failures.get(wb.id), consecutive_failures):
                alerts.append(
                    {
                        "resource_type": "workbook",
                        "name": wb.name,
                        "project_name": wb.project_name,
                        "owner_name": owner_name,
                        "extract_status": status_info.get("status"),
                        "extract_last_run_at": status_info.get("last_run_at"),
                        "consecutive_failures": consecutive_failures,
                        "notes": status_info.get("notes"),
                        "webpage_url": getattr(wb, "webpage_url", None),
                    }
                )
            wb_rows.append(
                (
                    wb.id,
                    wb.name,
                    wb.project_name,
                    owner_name,
                    wb.owner_id,
                    getattr(wb, "description", None),
                    updated_at_iso,
                    status_info.get("status"),
                    status_info.get("last_run_at"),
                    1 if _is_stale(updated_at, now) else 0,
                    detail.get("view_count"),
                    getattr(wb, "webpage_url", None),
                    created_at.isoformat() if created_at else None,
                    getattr(wb, "size", None),
                    detail.get("sheet_count"),
                    detail.get("connection_count"),
                    detail.get("revision_count"),
                    consecutive_failures,
                    detail.get("connection_type"),
                    schedule_info.get("schedule_name"),
                    schedule_info.get("frequency"),
                    schedule_info.get("next_run_at"),
                    status_info.get("last_run_duration_seconds"),
                    ", ".join(sorted(getattr(wb, "tags", None) or [])),
                    favorites_lookup.get(wb.id),
                )
            )
        db.replace_workbooks(site, wb_rows)
    except Exception as exc:
        errors.append(f"workbooks: {exc}")

    datasources = []
    try:
        previous_ds_failures = {
            row["id"]: row.get("consecutive_extract_failures") for row in db.fetch_datasources(site)
        }
        datasources = tableau_client.list_datasources(server)
        now = dt.datetime.now(dt.timezone.utc)
        try:
            ds_detail = tableau_client.enrich_datasources(server, datasources)
        except Exception as exc:
            errors.append(f"datasource_detail: {exc}")
            ds_detail = {}
        ds_rows = []
        for ds in datasources:
            updated_at = getattr(ds, "updated_at", None)
            updated_at_iso = updated_at.isoformat() if updated_at else None
            status_info = extract_status.get(ds.id, {})
            schedule_info = extract_schedules.get(ds.id, {})
            has_extracts = getattr(ds, "has_extracts", None)
            detail = ds_detail.get(ds.id, {})
            created_at = getattr(ds, "created_at", None)
            consecutive_failures = status_info.get("consecutive_failures")
            owner_name = users_by_id_name.get(ds.owner_id, ds.owner_id)
            if _escalated(previous_ds_failures.get(ds.id), consecutive_failures):
                alerts.append(
                    {
                        "resource_type": "datasource",
                        "name": ds.name,
                        "project_name": ds.project_name,
                        "owner_name": owner_name,
                        "extract_status": status_info.get("status"),
                        "extract_last_run_at": status_info.get("last_run_at"),
                        "consecutive_failures": consecutive_failures,
                        "notes": status_info.get("notes"),
                        "webpage_url": getattr(ds, "webpage_url", None),
                    }
                )
            ds_rows.append(
                (
                    ds.id,
                    ds.name,
                    ds.project_name,
                    owner_name,
                    ds.owner_id,
                    getattr(ds, "description", None),
                    1 if getattr(ds, "certified", False) else 0,
                    getattr(ds, "certification_note", None),
                    None,  # lifetime_view_count - filled in by _sync_lineage_and_usage (Metadata API only; see README)
                    status_info.get("status"),
                    status_info.get("last_run_at"),
                    updated_at_iso,
                    1 if _is_stale(updated_at, now) else 0,
                    getattr(ds, "webpage_url", None),
                    None if has_extracts is None else (1 if has_extracts else 0),
                    created_at.isoformat() if created_at else None,
                    getattr(ds, "size", None),
                    detail.get("connection_count"),
                    detail.get("revision_count"),
                    consecutive_failures,
                    detail.get("connection_type"),
                    getattr(ds, "datasource_type", None),
                    None if getattr(ds, "encrypt_extracts", None) is None else (1 if ds.encrypt_extracts else 0),
                    schedule_info.get("schedule_name"),
                    schedule_info.get("frequency"),
                    schedule_info.get("next_run_at"),
                    status_info.get("last_run_duration_seconds"),
                    ", ".join(sorted(getattr(ds, "tags", None) or [])),
                    favorites_lookup.get(ds.id),
                    detail.get("underlying_sources"),
                )
            )
        db.replace_datasources(site, ds_rows)
    except Exception as exc:
        errors.append(f"datasources: {exc}")

    try:
        dqw_rows = tableau_client.list_data_quality_warnings(server, datasources)
        db.replace_dqw_warnings(site, dqw_rows)
    except Exception as exc:
        errors.append(f"dqw_warnings: {exc}")

    try:
        group_rows = tableau_client.list_groups_with_members(server)
        db.replace_group_members(site, group_rows)
    except Exception as exc:
        errors.append(f"groups: {exc}")

    try:
        perm_rows = tableau_client.list_permissions(server, projects_by_id, workbooks)
        db.replace_permissions(site, perm_rows)
    except Exception as exc:
        errors.append(f"permissions: {exc}")

    try:
        custom_view_rows = tableau_client.list_custom_views(server)
        db.replace_custom_views(site, custom_view_rows)
    except Exception as exc:
        errors.append(f"custom_views: {exc}")

    try:
        workbook_names_by_id = {wb.id: wb.name for wb in workbooks}
        subscription_rows = tableau_client.list_subscriptions(server, users_by_id_name, workbook_names_by_id)
        db.replace_subscriptions(site, subscription_rows)
    except Exception as exc:
        errors.append(f"subscriptions: {exc}")

    try:
        connected_app_rows = tableau_client.list_connected_apps(server)
        db.replace_connected_apps(site, connected_app_rows)
    except Exception as exc:
        # Expected to fail on Tableau Server older than 2022.3 (REST API < 3.17) or
        # when the PAT's user isn't a server/site admin - see tableau_client.list_connected_apps.
        errors.append(f"connected_apps: {exc}")

    try:
        data_alert_rows = tableau_client.list_data_alerts(server, users_by_id_name)
        db.replace_data_alerts(site, data_alert_rows)
    except Exception as exc:
        errors.append(f"data_alerts: {exc}")

    try:
        webhook_rows = tableau_client.list_webhooks(server, users_by_id_name)
        db.replace_webhooks(site, webhook_rows)
    except Exception as exc:
        errors.append(f"webhooks: {exc}")

    try:
        site_settings_dict = tableau_client.list_site_settings(server)
        db.replace_site_settings(site, site_settings_dict)
    except Exception as exc:
        errors.append(f"site_settings: {exc}")

    try:
        server_info = tableau_client.get_server_info(server)
        db.replace_server_info(server_info)
    except Exception as exc:
        errors.append(f"server_info: {exc}")


def _sync_lineage_and_usage(site, server, auth_token, errors):
    """Datasource usage still depends on the Metadata API's usage.totalViewCount -
    there's no REST equivalent (see tableau_client.list_workbook_view_counts's
    docstring). Workbook usage no longer needs this call: it's populated directly
    from the REST API in _sync_projects_and_content, which also works while the
    Metadata API is blocked - see README.md."""
    try:
        result = metadata_client.fetch_lineage_and_usage(settings.server_url, auth_token)
        db.replace_links(site, result["links"])
        if result["datasource_views"]:
            db.update_datasource_view_counts(site, result["datasource_views"])
    except Exception as exc:
        errors.append(f"lineage: {exc}")
