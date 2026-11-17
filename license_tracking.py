"""Computes per-tier seat usage vs licensed capacity from the users + site_settings
data sync_service just wrote to the cache (no extra Tableau API calls), snapshots it
for trending, and reports which tiers just crossed settings.license_alert_threshold_pct."""
from collections import Counter

import db
from config import settings

_TIER_CAPACITY_KEYS = {
    "Creator": "tier_creator_capacity",
    "Explorer": "tier_explorer_capacity",
    "Viewer": "tier_viewer_capacity",
}


def _bucket_role(site_role: str) -> str:
    role = (site_role or "").lower()
    if "creator" in role:
        return "Creator"
    if "explorer" in role:
        return "Explorer"
    if "viewer" in role:
        return "Viewer"
    return "Other"


def compute_and_snapshot(site: str, now_iso: str) -> list:
    counts = Counter(_bucket_role(u.get("site_role")) for u in db.fetch_users(site))
    site_settings_row = db.fetch_site_settings(site) or {}

    crossed = []
    for tier, capacity_key in _TIER_CAPACITY_KEYS.items():
        capacity = site_settings_row.get(capacity_key)
        used = counts.get(tier, 0)
        pct_used = round((used / capacity) * 100, 1) if capacity else None
        db.add_license_usage_snapshot(site, now_iso, tier, capacity, used, pct_used)
        if pct_used is not None and pct_used >= settings.license_alert_threshold_pct:
            crossed.append({"tier": tier, "used": used, "capacity": capacity, "pct_used": pct_used})
    return crossed
