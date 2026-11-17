"""Diffs each sync's freshly fetched site settings against the previous cache before
it gets overwritten, and logs any changes to config_change_log plus the shared
audit_log (audit.py). Purely derived from the dicts sync_service already has -
no extra Tableau API calls."""
import db
import audit

_TRACKED_FIELDS = {
    "extract_encryption_mode": "Extract Encryption Mode",
    "guest_access_enabled": "Guest Access Enabled",
    "disable_subscriptions": "Subscriptions Disabled",
    "revision_history_enabled": "Revision History Enabled",
    "revision_limit": "Revision History Limit",
    "ask_data_mode": "Ask Data Mode",
    "tier_creator_capacity": "Creator Capacity",
    "tier_explorer_capacity": "Explorer Capacity",
    "tier_viewer_capacity": "Viewer Capacity",
}


def diff_and_log(site: str, previous: dict, new: dict, now_iso: str) -> list:
    """previous = db.fetch_site_settings(site) captured BEFORE the sync overwrites it.
    None on a site's first-ever sync (nothing to diff against). Returns list of
    changes detected."""
    if not previous:
        return []
    changes = []
    for key, label in _TRACKED_FIELDS.items():
        old_value, new_value = previous.get(key), new.get(key)
        if old_value != new_value:
            changes.append({"key": key, "label": label, "old": old_value, "new": new_value})
            db.add_config_change(site, now_iso, key, label, old_value, new_value)
            audit.log_action(
                "system", "config_setting_changed",
                resource_type="site_settings", resource_id=key,
                details=f"{label} changed from {old_value!r} to {new_value!r} (site: {site})",
            )
    return changes
