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

    return render_template(
        "overview.html",
        workbook_count=len(workbooks),
        datasource_count=len(datasources),
        stale_count=sum(1 for w in workbooks if w["is_stale"]) + sum(1 for d in datasources if d["is_stale"]),
        custom_view_count=len(db.fetch_custom_views(site)),
        subscription_count=len(db.fetch_subscriptions(site)),
        avg_score=avg_score,
        score_buckets=score_buckets,
        severity_counts=severity_counts,
        top_findings=open_findings[:5],
        last_refresh=db.latest_refresh(site),
    )
