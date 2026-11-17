"""Flags orphaned content per item 3: assets owned by inactive or deleted users,
assets owned by service accounts, or assets with no designated business/technical
owner. Detection only - returns candidate findings for findings_engine.py to merge
and store; never changes ownership, permissions, or content.

Tableau has no native concept of a "business owner" separate from whoever
created/was assigned the asset. To honor item 3's distinction, an admin can record a
business/technical owner in asset_owner_overrides (see db.upsert_owner_override); if
one is recorded, that's treated as a human-confirmed designation and suppresses the
owner-issue finding below even if the underlying Tableau owner is stale/deleted/a
service account.
"""
import json
from datetime import datetime, timezone

import db
from governance_config import governance_settings


def _is_inactive(user: dict) -> bool:
    if not user:
        return False
    if (user.get("site_role") or "").lower() == "unlicensed":
        return True
    last_login = user.get("last_login_at")
    if not last_login:
        return True
    try:
        last_login_dt = datetime.fromisoformat(last_login)
    except ValueError:
        return False
    if last_login_dt.tzinfo is None:
        last_login_dt = last_login_dt.replace(tzinfo=timezone.utc)
    age_days = (datetime.now(timezone.utc) - last_login_dt).days
    return age_days > governance_settings.inactive_user_days


def _owner_issue(owner_id, owner_name, users_by_id):
    """Returns (issue_key, title, severity, evidence_text) describing the problem
    with this asset's owner, or None if the owner looks fine."""
    if owner_id and owner_id not in users_by_id:
        return (
            "deleted_owner",
            "Owned by a deleted user account",
            "high",
            f"Owner id {owner_id} ({owner_name or 'unknown name'}) no longer resolves "
            "against the current user roster.",
        )

    user = users_by_id.get(owner_id) if owner_id else None

    if user and governance_settings.is_service_account(user.get("name"), user.get("email")):
        return (
            "service_account_owner",
            "Owned by a service/system account",
            "medium",
            f"Owner '{user.get('name')}' matches a configured service-account pattern.",
        )

    if user and _is_inactive(user):
        return (
            "inactive_owner",
            "Owned by an inactive user",
            "medium",
            f"Owner '{user.get('name')}' has site role '{user.get('site_role')}' and last login "
            f"{user.get('last_login_at') or 'never recorded'} "
            f"(inactive threshold: {governance_settings.inactive_user_days} days).",
        )

    if not owner_id:
        return (
            "no_owner",
            "No owner recorded on this asset",
            "medium",
            "Tableau has no owner_id recorded for this asset.",
        )

    return None


def _findings_for_assets(resource_type, assets, users_by_id, overrides):
    findings = []
    for asset in assets:
        override = overrides.get((resource_type, asset["id"]))
        has_designated_owner = bool(
            override and (override.get("business_owner") or override.get("technical_owner"))
        )
        if has_designated_owner:
            continue

        issue = _owner_issue(asset.get("owner_id"), asset.get("owner_name"), users_by_id)
        if not issue:
            continue
        issue_key, title, severity, evidence_text = issue

        findings.append(
            {
                "resource_type": resource_type,
                "resource_id": asset["id"],
                "resource_name": asset["name"],
                "project_name": asset.get("project_name"),
                "owner_name": asset.get("owner_name"),
                "category": "orphaned_content",
                "severity": severity,
                "title": title,
                "description": (
                    f"{title} and no business/technical owner override has been recorded for "
                    f"this {resource_type}. Assign an owner override, or update ownership "
                    "directly in Tableau, so someone is accountable for it."
                ),
                "evidence_json": json.dumps(
                    {
                        "issue": issue_key,
                        "owner_id": asset.get("owner_id"),
                        "owner_name": asset.get("owner_name"),
                        "detail": evidence_text,
                    }
                ),
                "recommended_action": (
                    "Assign a business/technical owner override in this app, or reassign "
                    "ownership in Tableau Server if the current owner is no longer appropriate. "
                    "No action is taken automatically."
                ),
            }
        )
    return findings


def compute(site: str, errors: list) -> list:
    """Returns a list of candidate finding dicts (category 'orphaned_content').
    Does not write to the database - findings_engine.py merges this with other
    sources and calls db.reconcile_findings() once."""
    try:
        users_by_id = db.fetch_users_by_id(site)
        overrides = db.fetch_owner_overrides(site)

        findings = []
        findings += _findings_for_assets("workbook", db.fetch_workbooks(site), users_by_id, overrides)
        findings += _findings_for_assets("datasource", db.fetch_datasources(site), users_by_id, overrides)
        return findings
    except Exception as exc:
        errors.append(f"orphan_detection: {exc}")
        return []
