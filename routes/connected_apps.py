from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("connected_apps", __name__)


@bp.route("/connected-apps")
@login_required
def list_connected_apps():
    site = site_context.get_current_site()
    return render_template(
        "connected_apps.html",
        connected_apps=db.fetch_connected_apps(site),
        last_refresh=db.latest_refresh(site),
    )
