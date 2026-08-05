from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("overview", __name__)


@bp.route("/overview")
@login_required
def show_overview():
    site = site_context.get_current_site()
    workbooks = db.fetch_workbooks(site)
    datasources = db.fetch_datasources(site)
    health_scores = db.fetch_health_scores(site)
    open_findings = db.fetch_findings(site, {"status": "open"})
    users = db.fetch_users(site)
    refresh_log = db.fetch_refresh_log(site, limit=20)
    audit_log = db.fetch_audit_log(limit=10)

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in open_findings:
        severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

    score_buckets = {"good": 0, "warning": 0, "critical": 0}
    for row in health_scores:
        score = row["score"] or 0
        bucket = "good" if score >= 80 else ("warning" if score >= 50 else "critical")
        score_buckets[bucket] += 1
    avg_score = (
        round(sum(r["score"] or 0 for r in health_scores) / len(health_scores), 1)
        if health_scores
        else None
    )

    # Count users by site role for User Distribution chart
    user_roles = {}
    for u in users:
        role = u.get("site_role", "Unknown")
        user_roles[role] = user_roles.get(role, 0) + 1

    # Count content by type for Content Type Breakdown chart
    content_by_type = {
        "Workbooks": len(workbooks),
        "Data Sources": len(datasources),
        "Custom Views": len(db.fetch_custom_views(site)),
        "Projects": len(db.fetch_projects(site)),
    }

    # Calculate refresh status for Extract Refresh tracker
    extract_stats = {
        "success": sum(1 for w in workbooks if w.get("extract_status") == "Success"),
        "failed": sum(1 for w in workbooks if w.get("extract_status") == "Failed"),
        "running": sum(1 for w in workbooks if w.get("extract_status") == "Running"),
        "total": len([w for w in workbooks if w.get("extract_status")]),
    }

    return render_template(
        "overview.html",
        workbook_count=len(workbooks),
        datasource_count=len(datasources),
        stale_count=sum(1 for w in workbooks if w["is_stale"]) + sum(1 for d in datasources if d["is_stale"]),
        custom_view_count=len(db.fetch_custom_views(site)),
        subscription_count=len(db.fetch_subscriptions(site)),
        user_count=len(users),
        avg_score=avg_score,
        score_buckets=score_buckets,
        severity_counts=severity_counts,
        user_roles=user_roles,
        content_by_type=content_by_type,
        extract_stats=extract_stats,
        top_findings=open_findings[:5],
        recent_activity=audit_log[:5],
        refresh_log=refresh_log[:5],
        last_refresh=db.latest_refresh(site),
    )
