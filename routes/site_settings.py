from collections import Counter

from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("site_settings", __name__)


@bp.route("/site-settings")
@login_required
def show_site_settings():
    site = site_context.get_current_site()

    role_counts = Counter()
    for user in db.fetch_users(site):
        role = (user.get("site_role") or "").lower()
        if "creator" in role:
            role_counts["Creator"] += 1
        elif "explorer" in role:
            role_counts["Explorer"] += 1
        elif "viewer" in role:
            role_counts["Viewer"] += 1
        else:
            role_counts["Other"] += 1

    return render_template(
        "site_settings.html",
        settings=db.fetch_site_settings(site),
        server_info=db.fetch_server_info(),
        role_counts=dict(role_counts),
        last_refresh=db.latest_refresh(site),
    )
