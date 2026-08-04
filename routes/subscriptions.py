from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("subscriptions", __name__)


@bp.route("/subscriptions")
@login_required
def list_subscriptions():
    site = site_context.get_current_site()
    return render_template(
        "subscriptions.html",
        subscriptions=db.fetch_subscriptions(site),
        last_refresh=db.latest_refresh(site),
    )
