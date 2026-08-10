from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("config_audit", __name__)


@bp.route("/config-audit")
@login_required
def list_config_audit():
    site = site_context.get_current_site()
    return render_template(
        "config_audit.html",
        changes=db.fetch_config_change_log(site, limit=200),
        current_settings=db.fetch_site_settings(site),
        last_refresh=db.latest_refresh(site),
    )
