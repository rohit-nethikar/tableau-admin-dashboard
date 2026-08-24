from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("overview", __name__)


@bp.route("/overview")
@login_required
def show_overview():
    site = site_context.get_current_site()

    # Get aggregated stats (optimized with SQL aggregations instead of fetching all rows)
    workbook_count = db.count_workbooks(site)
    datasource_count = db.count_datasources(site)
    stale_workbooks = db.count_stale_workbooks(site)
    stale_datasources = db.count_stale_datasources(site)
    custom_view_count = db.count_custom_views(site)
    subscription_count = db.count_subscriptions(site)
    user_count = db.count_users(site)
    project_count = db.count_projects(site)

    # Health scores stats (single SQL query instead of fetching all rows)
    health_stats = db.get_health_score_stats(site)
    avg_score = round(health_stats["avg_score"], 1) if health_stats["avg_score"] else None
    score_buckets = {
        "good": health_stats["good_count"],
        "warning": health_stats["warning_count"],
        "critical": health_stats["critical_count"]
    }

    # Severity counts (single SQL query instead of fetching all rows)
    severity_counts = db.get_severity_counts(site)

    # User roles distribution (single SQL query instead of fetching all users)
    user_roles = db.get_user_role_distribution(site)

    # Extract stats (single SQL query instead of fetching all workbooks)
    extract_stats = db.get_extract_stats(site)

    # Only fetch what we actually need for display
    refresh_log = db.fetch_refresh_log(site, limit=20)
    audit_log = db.fetch_audit_log(limit=10)
    top_findings = db.fetch_top_findings(site, limit=5)

    content_by_type = {
        "Workbooks": workbook_count,
        "Data Sources": datasource_count,
        "Custom Views": custom_view_count,
        "Projects": project_count,
    }

    return render_template(
        "overview.html",
        workbook_count=workbook_count,
        datasource_count=datasource_count,
        stale_count=stale_workbooks + stale_datasources,
        custom_view_count=custom_view_count,
        subscription_count=subscription_count,
        user_count=user_count,
        avg_score=avg_score,
        score_buckets=score_buckets,
        severity_counts=severity_counts,
        user_roles=user_roles,
        content_by_type=content_by_type,
        extract_stats=extract_stats,
        top_findings=top_findings,
        recent_activity=audit_log[:5],
        refresh_log=refresh_log[:5],
        last_refresh=db.latest_refresh(site),
    )
