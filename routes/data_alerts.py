from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("data_alerts", __name__)


@bp.route("/data-alerts")
@login_required
def list_data_alerts():
    site = site_context.get_current_site()
    return render_template(
        "data_alerts.html",
        data_alerts=db.fetch_data_alerts(site),
        last_refresh=db.latest_refresh(site),
    )
