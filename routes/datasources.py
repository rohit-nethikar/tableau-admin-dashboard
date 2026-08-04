from flask import Blueprint, render_template

import db
import site_context
from auth import login_required
from config import settings

bp = Blueprint("datasources", __name__)


@bp.route("/datasources")
@login_required
def list_datasources():
    site = site_context.get_current_site()
    datasources = db.fetch_datasources(site)

    users_by_id = db.fetch_users_by_id(site)
    for ds in datasources:
        user = users_by_id.get(ds["owner_id"], {})
        ds["owner_email"] = user.get("email")
        ds["owner_site_role"] = user.get("site_role")
        ds["owner_last_login_at"] = user.get("last_login_at")

    return render_template(
        "datasources.html",
        datasources=datasources,
        stale_threshold_days=settings.stale_threshold_days,
        last_refresh=db.latest_refresh(site),
    )
