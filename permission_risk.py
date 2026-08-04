"""Flags permission-risk conditions per item 7: access granted to All Users, broad
download/export capabilities, direct user permissions, unexpected project access
(against an optional approved baseline), and same-resource Allow/Deny conflicts.

Detection only - returns candidate findings for findings_engine.py to merge and
store, plus a per-resource risk score for health_scoring.py and the permissions
page's Risk column. Never changes a single permission.

Conflict detection is intentionally conservative (design note 5 in the governance
plan): it flags a flat Allow-vs-Deny disagreement between grantees on the same
resource for human review, not a computed final verdict - Tableau's actual
effective-permission precedence depends on group membership and role in ways this
check does not attempt to fully resolve.
"""
import json
from collections import defaultdict

import db
from governance_config import governance_settings

_DOWNLOAD_CAPABILITIES = {"Download", "ExportData", "ExportXml"}

_SEVERITY_POINTS = {"critical": 40, "high": 25, "medium": 15, "low": 5}


def _load_capabilities(grant: dict) -> dict:
    raw = grant.get("capabilities_json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return {}


def _allowed_capabilities(caps: dict) -> list:
    return [c for c, mode in caps.items() if str(mode).lower() == "allow"]


def _resource_id_lookup(site):
    projects_by_name = {p["name"]: p["id"] for p in db.fetch_projects(site)}
    workbooks_by_name = {w["name"]: w["id"] for w in db.fetch_workbooks(site)}

    def lookup(resource_type, resource_name):
        if resource_type in ("project", "project_default_workbook"):
            return projects_by_name.get(resource_name)
        if resource_type == "workbook":
            return workbooks_by_name.get(resource_name)
        return None

    return lookup


def _finding(resource_type, resource_id, resource_name, project_name, severity, title,
             description, evidence, recommended_action):
    return {
        "resource_type": resource_type,
        "resource_id": resource_id or resource_name,
        "resource_name": resource_name,
        "project_name": project_name,
        "owner_name": None,
        "category": "permission_risk",
        "severity": severity,
        "title": title,
        "description": description,
        "evidence_json": json.dumps(evidence),
        "recommended_action": recommended_action,
    }


def compute(site: str, errors: list) -> list:
    """Returns a list of candidate finding dicts (category 'permission_risk').
    Does not write to the database - findings_engine.py merges this with other
    sources and calls db.reconcile_findings() once."""
    try:
        grants = db.fetch_permissions(site)
        lookup_id = _resource_id_lookup(site)
        all_users_name = governance_settings.all_users_group_name
        high_risk_caps = set(governance_settings.high_risk_capabilities)
        baseline = governance_settings.approved_baseline

        by_resource = defaultdict(list)
        for grant in grants:
            by_resource[(grant["resource_type"], grant["resource_name"])].append(grant)

        findings = []
        for (resource_type, resource_name), resource_grants in by_resource.items():
            project_name = resource_grants[0].get("project_name")
            resource_id = lookup_id(resource_type, resource_name)

            allow_by_capability = defaultdict(list)
            deny_by_capability = defaultdict(list)

            for grant in resource_grants:
                caps = _load_capabilities(grant)
                grantee_desc = f"{grant['grantee_type']}:{grant['grantee_name']}"

                for capability, mode in caps.items():
                    mode_lower = str(mode).lower()
                    if mode_lower == "allow":
                        allow_by_capability[capability].append(grantee_desc)
                    elif mode_lower == "deny":
                        deny_by_capability[capability].append(grantee_desc)

                allowed_here = _allowed_capabilities(caps)

                if grant["grantee_type"] == "group" and grant["grantee_name"] == all_users_name and allowed_here:
                    risky = sorted(set(allowed_here) & high_risk_caps)
                    findings.append(_finding(
                        resource_type, resource_id, resource_name, project_name,
                        "high" if risky else "medium",
                        "All-Users group has been granted access",
                        f"The '{all_users_name}' group has Allow on: {', '.join(sorted(allowed_here))}.",
                        {"grantee": all_users_name, "allowed_capabilities": sorted(allowed_here)},
                        "Review whether every capability granted to All-Users is intentional; "
                        "narrow to a specific group if not. No permissions are changed automatically.",
                    ))

                if grant["grantee_type"] == "group":
                    download_allowed = sorted(c for c in allowed_here if c in _DOWNLOAD_CAPABILITIES)
                    if download_allowed:
                        findings.append(_finding(
                            resource_type, resource_id, resource_name, project_name,
                            "medium",
                            "Broad download/export capability granted",
                            f"Group '{grant['grantee_name']}' has Allow on: {', '.join(download_allowed)}.",
                            {"grantee": grant["grantee_name"], "capabilities": download_allowed},
                            "Confirm this group's membership is appropriate for extracting data "
                            "from this asset.",
                        ))

                if grant["grantee_type"] == "user" and allowed_here:
                    findings.append(_finding(
                        resource_type, resource_id, resource_name, project_name,
                        "medium",
                        "Direct user permission grant",
                        f"User '{grant['grantee_name']}' has a direct grant (Allow on: "
                        f"{', '.join(sorted(allowed_here))}) instead of access via a group.",
                        {"grantee": grant["grantee_name"], "allowed_capabilities": sorted(allowed_here)},
                        "Direct user grants are harder to audit at scale; consider moving this "
                        "user into a group with equivalent access instead.",
                    ))

                if resource_type == "project" and project_name in baseline and allowed_here:
                    if grant["grantee_name"] not in baseline[project_name]:
                        findings.append(_finding(
                            resource_type, resource_id, resource_name, project_name,
                            "medium",
                            "Project access outside the approved baseline",
                            f"'{grant['grantee_name']}' has access to project '{project_name}' but "
                            "is not on the configured approved_baseline list for this project.",
                            {"grantee": grant["grantee_name"], "project": project_name},
                            "Confirm this access is intended, or remove it directly in Tableau; "
                            "update governance.yaml's approved_baseline if this should be allowed.",
                        ))

            for capability in set(allow_by_capability) & set(deny_by_capability):
                findings.append(_finding(
                    resource_type, resource_id, resource_name, project_name,
                    "medium",
                    f"Conflicting {capability} rule on this resource",
                    f"{capability} is Allow for {', '.join(allow_by_capability[capability])} and "
                    f"Deny for {', '.join(deny_by_capability[capability])} on the same resource.",
                    {
                        "capability": capability,
                        "allow_grantees": allow_by_capability[capability],
                        "deny_grantees": deny_by_capability[capability],
                    },
                    "Review Tableau's actual effective permission for affected users - Allow/Deny "
                    "precedence depends on group membership and role, which this check does not "
                    "fully resolve. Presented for human review only.",
                ))

        return findings
    except Exception as exc:
        errors.append(f"permission_risk: {exc}")
        return []


def risk_scores_by_resource(findings: list) -> dict:
    """Aggregates permission_risk findings into a 0-100 score per
    (resource_type, resource_name), for health_scoring.py's permission_risk factor
    and the permissions page's Risk column. Higher = riskier."""
    scores = defaultdict(int)
    for finding in findings:
        key = (finding["resource_type"], finding["resource_name"])
        scores[key] += _SEVERITY_POINTS.get(finding["severity"], 5)
    return {key: min(100, points) for key, points in scores.items()}
