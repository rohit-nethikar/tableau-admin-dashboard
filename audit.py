"""Append-only audit trail. Every administrative action taken from within this app
(finding status changes today; remediation approvals in a later phase) is recorded
here and is never deleted or edited by the app itself - this is the record the "any
remediation action must require explicit administrator approval and must be recorded
in an audit log" requirement points at.
"""
from datetime import datetime, timezone

import db


def log_action(actor: str, action: str, resource_type: str = None, resource_id: str = None, details: str = None):
    db.add_audit_log(
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
    )
