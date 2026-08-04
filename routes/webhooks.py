from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("webhooks", __name__)


@bp.route("/webhooks")
@login_required
def list_webhooks():
    site = site_context.get_current_site()
    return render_template(
        "webhooks.html",
        webhooks=db.fetch_webhooks(site),
        last_refresh=db.latest_refresh(site),
    )
