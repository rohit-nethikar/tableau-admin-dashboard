from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("content_changes", __name__)


@bp.route("/content-changes")
@login_required
def list_content_changes():
    site = site_context.get_current_site()
    return render_template(
        "content_changes.html",
        changes=db.fetch_content_change_log(site, limit=200),
        last_refresh=db.latest_refresh(site),
    )
