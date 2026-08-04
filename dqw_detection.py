"""Flags active Data Quality Warnings on published data sources. Detection only -
returns candidate findings for findings_engine.py to merge and store; never changes
or clears a warning in Tableau.

DQW only exists on datasource/database/table/flow in TSC 0.32 - not workbooks - so
this reads db.fetch_dqw_warnings(site), which tableau_client.list_data_quality_warnings
populates for datasources only each sync. Severity comes from the configurable
dqw_severity_map (governance.yaml); severe (a boolean Tableau sets per-warning) does
not change the severity, it's surfaced in the evidence instead.
"""
import json

import db
from governance_config import governance_settings

_DEFAULT_SEVERITY = "medium"


def compute(site: str, errors: list) -> list:
    """Returns a list of candidate finding dicts (category 'data_quality_warning').
    Does not write to the database - findings_engine.py merges this with other
    sources and calls db.reconcile_findings() once."""
    try:
        findings = []
        for warning in db.fetch_dqw_warnings(site):
            warning_type = warning.get("warning_type") or "WARNING"
            severity = governance_settings.dqw_severity_map.get(warning_type, _DEFAULT_SEVERITY)
            findings.append(
                {
                    "resource_type": warning["resource_type"],
                    "resource_id": warning["resource_id"],
                    "resource_name": warning.get("resource_name"),
                    "project_name": None,
                    "owner_name": None,
                    "category": "data_quality_warning",
                    "severity": severity,
                    "title": f"Data Quality Warning: {warning_type}",
                    "description": warning.get("message") or "Tableau has an active Data Quality Warning on this data source.",
                    "evidence_json": json.dumps(
                        {
                            "warning_type": warning_type,
                            "severe": bool(warning.get("severe")),
                            "created_at": warning.get("created_at"),
                        }
                    ),
                    "recommended_action": (
                        "Review and, if resolved, clear this warning directly in Tableau Server. "
                        "No action is taken automatically."
                    ),
                }
            )
        return findings
    except Exception as exc:
        errors.append(f"dqw_detection: {exc}")
        return []
