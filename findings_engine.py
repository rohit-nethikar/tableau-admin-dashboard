"""Orchestrates every finding source into one reconciled findings table, per item 2:
orphaned-content findings (orphan_detection.py), permission-risk findings
(permission_risk.py), plus two standalone rules computed directly from the cache
(stale content, failed extract refresh). Calls db.reconcile_findings() exactly once
so a human-set status (acknowledged/resolved/dismissed) survives across resyncs -
see db.reconcile_findings for the merge semantics.

"Consecutive failed refreshes" (as named in item 5) isn't tracked here: Tableau's
Jobs REST endpoint only exposes the most recent extract-refresh job per asset in
this app's data model (tableau_client.list_extract_refresh_status), not a history of
past runs, so there's nothing to count consecutive failures against. What IS
available and genuinely reflects reality - the latest job's outcome - is what the
refresh_failure rule below flags.
"""
import json

import db


def _stale_content_findings(site):
    findings = []
    for resource_type, assets in (("workbook", db.fetch_workbooks(site)), ("datasource", db.fetch_datasources(site))):
        for asset in assets:
            if not asset.get("is_stale"):
                continue
            findings.append({
                "resource_type": resource_type,
                "resource_id": asset["id"],
                "resource_name": asset["name"],
                "project_name": asset.get("project_name"),
                "owner_name": asset.get("owner_name"),
                "category": "stale_content",
                "severity": "medium",
                "title": "Content has not been updated recently",
                "description": (
                    "This asset has not been modified within the configured staleness "
                    "threshold. It may be abandoned, or simply stable and still in active use - "
                    "this is a signal for review, not a verdict."
                ),
                "evidence_json": json.dumps({
                    "updated_at": asset.get("updated_at"),
                    "extract_status": asset.get("extract_status"),
                }),
                "recommended_action": (
                    "Confirm with the owner whether this asset is still needed. If not, "
                    "consider archiving it directly in Tableau - this app never deletes content."
                ),
            })
    return findings


def _refresh_failure_findings(site):
    findings = []
    for resource_type, assets in (("workbook", db.fetch_workbooks(site)), ("datasource", db.fetch_datasources(site))):
        for asset in assets:
            if (asset.get("extract_status") or "").lower() != "failed":
                continue
            findings.append({
                "resource_type": resource_type,
                "resource_id": asset["id"],
                "resource_name": asset["name"],
                "project_name": asset.get("project_name"),
                "owner_name": asset.get("owner_name"),
                "category": "refresh_failure",
                "severity": "high",
                "title": "Last extract-refresh attempt failed",
                "description": (
                    "The most recent extract-refresh job Tableau ran for this asset failed. "
                    "Data shown to users may be stale until this is fixed and re-run."
                ),
                "evidence_json": json.dumps({
                    "extract_status": asset.get("extract_status"),
                    "extract_last_run_at": asset.get("extract_last_run_at"),
                }),
                "recommended_action": (
                    "Check the extract-refresh task's schedule and data-source connection in "
                    "Tableau Server, then re-run the refresh."
                ),
            })
    return findings


def run_all_rules(
    site: str,
    errors: list,
    permission_risk_findings: list,
    orphan_findings: list,
    dqw_findings: list,
    now_iso: str,
):
    """Combines all finding sources and reconciles them into the findings table in a
    single call, so the preserve-status-across-resync merge in db.reconcile_findings
    only has to run once per sync."""
    try:
        all_findings = []
        all_findings.extend(orphan_findings)
        all_findings.extend(permission_risk_findings)
        all_findings.extend(dqw_findings)
        all_findings.extend(_stale_content_findings(site))
        all_findings.extend(_refresh_failure_findings(site))
        db.reconcile_findings(site, all_findings, now_iso)
    except Exception as exc:
        errors.append(f"findings_engine: {exc}")
