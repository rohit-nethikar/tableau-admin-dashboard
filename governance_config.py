"""Loads tunable governance settings (health-score weights, risk thresholds, regex
patterns) from governance.yaml. Same load-once-at-import pattern as config.py - edit
the file and restart the app to pick up changes. Every field is optional; anything
missing from governance.yaml (or the file itself missing) falls back to the defaults
below so the app runs out of the box.
"""
import os
import re

import yaml

from config import BASE_DIR

GOVERNANCE_CONFIG_PATH = os.path.join(BASE_DIR, "governance.yaml")

DEFAULT_WEIGHTS = {
    "usage": 0.20,
    "ownership": 0.15,
    "refresh_status": 0.20,
    "certification": 0.10,
    "documentation": 0.10,
    "permission_risk": 0.15,
    "lineage": 0.10,
}

DEFAULT_HIGH_RISK_CAPABILITIES = [
    "Download",
    "ExportData",
    "ExportXml",
    "Delete",
    "ChangePermissions",
    "ChangeHierarchy",
]

DEFAULT_SERVICE_ACCOUNT_PATTERNS = [
    r"(?i)^svc[-_.]",
    r"(?i)service[-_.]?account",
    r"(?i)^sa[-_.]",
    r"(?i)^bot[-_.]",
    r"(?i)noreply",
    r"(?i)no-reply",
]

DEFAULT_DQW_SEVERITY_MAP = {
    "SENSITIVE_DATA": "critical",
    "STALE": "high",
    "DEPRECATED": "medium",
    "WARNING": "medium",
    "MAINTENANCE": "low",
}


class GovernanceSettings:
    def __init__(self, data):
        data = data or {}
        self.weights = self._normalized_weights(data.get("weights"))
        self.inactive_user_days = int(data.get("inactive_user_days", 180))
        self.all_users_group_name = data.get("all_users_group_name", "All Users")
        self.high_risk_capabilities = list(
            data.get("high_risk_capabilities", DEFAULT_HIGH_RISK_CAPABILITIES)
        )
        raw_patterns = data.get("service_account_patterns", DEFAULT_SERVICE_ACCOUNT_PATTERNS)
        self.service_account_patterns = [re.compile(p) for p in raw_patterns]
        # {project_name: [grantee_name, ...]} - empty by default so the
        # unexpected-project-access check is skipped rather than firing false
        # positives against an undefined baseline.
        self.approved_baseline = data.get("approved_baseline") or {}
        # Maps a Data Quality Warning's warning_type to a finding severity.
        self.dqw_severity_map = dict(
            data.get("dqw_severity_map") or DEFAULT_DQW_SEVERITY_MAP
        )

    @staticmethod
    def _normalized_weights(raw):
        """Weights in governance.yaml don't need to sum to 1 - they're normalized
        here. Per-asset redistribution across only the *available* factors happens
        in health_scoring.py, not here."""
        weights = dict(DEFAULT_WEIGHTS)
        if raw:
            weights.update(raw)
        total = sum(weights.values()) or 1.0
        return {k: v / total for k, v in weights.items()}

    def is_service_account(self, name: str, email: str = None) -> bool:
        candidates = [c for c in (name, email) if c]
        return any(pattern.search(c) for c in candidates for pattern in self.service_account_patterns)


def load_governance_settings() -> GovernanceSettings:
    if not os.path.exists(GOVERNANCE_CONFIG_PATH):
        return GovernanceSettings({})
    with open(GOVERNANCE_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return GovernanceSettings(data)


governance_settings = load_governance_settings()
