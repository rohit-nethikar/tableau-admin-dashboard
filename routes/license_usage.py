from flask import Blueprint, render_template

import db
import site_context
from auth import login_required
from config import settings

bp = Blueprint("license_usage", __name__)


@bp.route("/license-usage")
@login_required
def show_license_usage():
    site = site_context.get_current_site()
    history = db.fetch_license_usage_history(site, limit=500)
    by_tier = {}
    for row in reversed(history):  # oldest -> newest, for the trend chart
        by_tier.setdefault(row["tier"], []).append(row)

    return render_template(
        "license_usage.html",
        current=db.latest_license_usage(site),
        history_by_tier=by_tier,
        threshold_pct=settings.license_alert_threshold_pct,
        last_refresh=db.latest_refresh(site),
    )
