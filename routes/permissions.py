from collections import defaultdict

from flask import Blueprint, render_template

import db
import permission_risk
import site_context
from auth import login_required

bp = Blueprint("permissions", __name__)


@bp.route("/permissions")
@login_required
def list_permissions():
    site = site_context.get_current_site()
    grants = db.fetch_permissions(site)
    by_project = defaultdict(list)
    for grant in grants:
        by_project[grant["project_name"] or "(no project)"].append(grant)

    members_by_group = defaultdict(list)
    for row in db.fetch_group_members(site):
        members_by_group[row["group_name"]].append(row["user_name"])

    # Only open/acknowledged permission-risk findings count toward the badge -
    # a resolved or dismissed finding shouldn't keep flagging a resource as risky.
    risk_findings = db.fetch_findings(site, filters={"category": "permission_risk"})
    active_risk_findings = [f for f in risk_findings if f["status"] in ("open", "acknowledged")]
    risk_scores = permission_risk.risk_scores_by_resource(active_risk_findings)

    return render_template(
        "permissions.html",
        by_project=dict(sorted(by_project.items())),
        members_by_group=dict(members_by_group),
        risk_scores=risk_scores,
        total_grants=len(grants),
        project_count=len(by_project),
        risky_resource_count=len(risk_scores),
        group_count=len(members_by_group),
        last_refresh=db.latest_refresh(site),
    )
