"""Computes a configurable, explainable health score (0-100) per workbook and
published data source, per item 1: usage, ownership, refresh status, certification,
documentation, permission-risk, and lineage signals - each stored as a contributing
factor, never folded silently into a single opaque number.

A factor that isn't applicable or available for a given asset (e.g. certification on
a workbook - only data sources can be certified in Tableau - or lineage/usage while
the Metadata API is unreachable) is marked unavailable and its configured weight is
redistributed across that asset's remaining available factors, rather than counting
as a zero (design note 6 in the governance plan). Every factor's raw value and
contribution is stored in health_scores.factors_json so the score is always
explainable.
"""
import json
import math
from datetime import datetime, timezone

import db
import permission_risk
from governance_config import governance_settings

_REFRESH_STATUS_SCORES = {"success": 100, "failed": 0, "cancelled": 50}


def _usage_factor(lifetime_view_count):
    if lifetime_view_count is None:
        return None, "No usage data available (Metadata API unreachable or not yet synced)."
    if lifetime_view_count == 0:
        return 10, "Never viewed (lifetime total)."
    score = min(100, 40 + 15 * math.log2(lifetime_view_count + 1))
    return round(score, 1), f"{lifetime_view_count} lifetime views."


def _ownership_factor(resource_type, resource_id, orphan_by_resource):
    issue = orphan_by_resource.get((resource_type, resource_id))
    if issue is None:
        return 100, "Owner looks active and is not a service account, or a designated owner is on file."
    severity, title = issue
    score = {"high": 0, "medium": 40}.get(severity, 40)
    return score, title


def _refresh_status_factor(extract_status):
    if not extract_status:
        return None, "No extract-refresh history (may be a live connection, not an extract)."
    score = _REFRESH_STATUS_SCORES.get(extract_status.lower())
    if score is None:
        return None, f"Unrecognized extract status '{extract_status}'."
    return score, f"Last extract-refresh job: {extract_status}."


def _certification_factor(resource_type, is_certified):
    if resource_type != "datasource":
        return None, "Certification does not apply to workbooks in Tableau."
    return (100, "Certified.") if is_certified else (50, "Not certified.")


def _documentation_factor(description):
    if description and description.strip():
        return 100, "Has a description."
    return 20, "No description on file."


def _permission_risk_factor(resource_type, resource_name, risk_scores):
    if resource_type == "datasource":
        return None, "Permission sync does not currently cover published data sources directly."
    risk = risk_scores.get((resource_type, resource_name))
    if risk is None:
        return 100, "No permission-risk findings for this resource."
    return max(0, 100 - risk), f"Permission-risk score {risk}/100 (higher = riskier)."


def _lineage_factor(resource_type, resource_name, lineage_available, workbook_names_with_links,
                     datasource_names_with_links):
    if not lineage_available:
        return None, "No lineage data available (Metadata API unreachable or not yet synced)."
    has_link = (
        resource_name in workbook_names_with_links
        if resource_type == "workbook"
        else resource_name in datasource_names_with_links
    )
    return (100, "Has lineage links.") if has_link else (0, "No lineage links found.")


def _score_asset(resource_type, asset, orphan_by_resource, risk_scores, lineage_available,
                  workbook_names_with_links, datasource_names_with_links):
    weights = governance_settings.weights

    raw_factors = {
        "usage": _usage_factor(asset.get("lifetime_view_count")),
        "ownership": _ownership_factor(resource_type, asset["id"], orphan_by_resource),
        "refresh_status": _refresh_status_factor(asset.get("extract_status")),
        "certification": _certification_factor(resource_type, asset.get("is_certified")),
        "documentation": _documentation_factor(asset.get("description")),
        "permission_risk": _permission_risk_factor(resource_type, asset["name"], risk_scores),
        "lineage": _lineage_factor(
            resource_type, asset["name"], lineage_available,
            workbook_names_with_links, datasource_names_with_links,
        ),
    }

    available_names = {name for name, (score, _) in raw_factors.items() if score is not None}
    available_weight_total = sum(weights[name] for name in available_names) or 1.0

    factors = []
    total_score = 0.0
    for name, (score, explanation) in raw_factors.items():
        is_available = name in available_names
        normalized_weight = (weights[name] / available_weight_total) if is_available else 0.0
        contribution = score * normalized_weight if is_available else 0.0
        if is_available:
            total_score += contribution
        factors.append({
            "name": name,
            "configured_weight": round(weights[name], 3),
            "weight_used": round(normalized_weight, 3),
            "available": is_available,
            "raw_score": score,
            "contribution": round(contribution, 1),
            "explanation": explanation,
        })

    return round(total_score, 1), factors


def compute_and_store(site: str, errors: list, permission_risk_findings: list, orphan_findings: list):
    """Writes health_scores for every cached workbook and data source. Takes the
    already-computed permission_risk/orphan_detection findings as input (rather than
    re-querying findings from the database) since findings_engine.py hasn't merged
    and stored them yet at the point this runs in sync_service.refresh_all()."""
    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        orphan_by_resource = {
            (finding["resource_type"], finding["resource_id"]): (finding["severity"], finding["title"])
            for finding in orphan_findings
        }
        risk_scores = permission_risk.risk_scores_by_resource(permission_risk_findings)

        links = db.fetch_lineage(site)
        lineage_available = bool(links)
        workbook_names_with_links = {link["workbook_name"] for link in links}
        datasource_names_with_links = {link["datasource_name"] for link in links}

        rows = []
        for asset in db.fetch_workbooks(site):
            score, factors = _score_asset(
                "workbook", asset, orphan_by_resource, risk_scores, lineage_available,
                workbook_names_with_links, datasource_names_with_links,
            )
            rows.append((
                "workbook", asset["id"], asset["name"], asset.get("project_name"),
                asset.get("owner_name"), score, now_iso, json.dumps(factors),
            ))

        for asset in db.fetch_datasources(site):
            score, factors = _score_asset(
                "datasource", asset, orphan_by_resource, risk_scores, lineage_available,
                workbook_names_with_links, datasource_names_with_links,
            )
            rows.append((
                "datasource", asset["id"], asset["name"], asset.get("project_name"),
                asset.get("owner_name"), score, now_iso, json.dumps(factors),
            ))

        db.replace_health_scores(site, rows)
    except Exception as exc:
        errors.append(f"health_scoring: {exc}")
