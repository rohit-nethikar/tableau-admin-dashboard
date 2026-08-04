import json
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for

import audit
import db
import site_context
from auth import login_required

bp = Blueprint("health", __name__)


@bp.route("/health")
@login_required
def list_health():
    site = site_context.get_current_site()
    scores = db.fetch_health_scores(site)
    overrides = db.fetch_owner_overrides(site)
    for row in scores:
        row["factors"] = json.loads(row["factors_json"]) if row.get("factors_json") else []
        override = overrides.get((row["resource_type"], row["resource_id"]))
        row["business_owner"] = override.get("business_owner") if override else None
        row["technical_owner"] = override.get("technical_owner") if override else None
        row["owner_notes"] = override.get("notes") if override else None

    score_buckets = {"good": 0, "warning": 0, "critical": 0}
    for row in scores:
        score = row["score"] or 0
        bucket = "good" if score >= 80 else ("warning" if score >= 50 else "critical")
        score_buckets[bucket] += 1
    avg_score = round(sum(r["score"] or 0 for r in scores) / len(scores), 1) if scores else None

    return render_template(
        "health.html",
        scores=scores,
        avg_score=avg_score,
        score_buckets=score_buckets,
        last_refresh=db.latest_refresh(site),
    )


@bp.route("/health/<resource_type>/<resource_id>/owner", methods=["POST"])
@login_required
def set_owner_override(resource_type, resource_id):
    site = site_context.get_current_site()
    business_owner = request.form.get("business_owner", "").strip() or None
    technical_owner = request.form.get("technical_owner", "").strip() or None
    notes = request.form.get("notes", "").strip() or None

    db.upsert_owner_override(
        site, resource_type, resource_id, business_owner, technical_owner, notes,
        datetime.now(timezone.utc).isoformat(),
    )
    audit.log_action(
        actor="admin",
        action="set_owner_override",
        resource_type=resource_type,
        resource_id=resource_id,
        details=f"business_owner={business_owner!r} technical_owner={technical_owner!r} notes={notes!r}",
    )
    flash("Owner override saved.", "success")
    return redirect(url_for("health.list_health"))
