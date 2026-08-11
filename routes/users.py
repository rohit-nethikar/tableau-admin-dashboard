from datetime import datetime, timezone
from flask import Blueprint, render_template, request

import db
import site_context
from auth import login_required
from config import settings

bp = Blueprint("users", __name__)


@bp.route("/users")
@login_required
def list_users():
    site = site_context.get_current_site()
    now = datetime.now(timezone.utc)
    threshold_days = settings.stale_threshold_days
    status_filter = request.args.get("status") or None

    users = db.fetch_users(site)
    inactive_count = 0
    active_count = 0
    for user in users:
        last_login_at = user.get("last_login_at")
        days_since_login = None
        if last_login_at:
            try:
                last_login = datetime.fromisoformat(last_login_at)
                if last_login.tzinfo is None:
                    last_login = last_login.replace(tzinfo=timezone.utc)
                days_since_login = (now - last_login).days
            except ValueError:
                days_since_login = None
        user["days_since_login"] = days_since_login
        user["is_inactive"] = days_since_login is None or days_since_login >= threshold_days
        if user["is_inactive"]:
            inactive_count += 1
        else:
            active_count += 1

    # Filter users by status if specified
    filtered_users = users
    if status_filter == "inactive":
        filtered_users = [u for u in users if u["is_inactive"]]
    elif status_filter == "active":
        filtered_users = [u for u in users if not u["is_inactive"]]

    return render_template(
        "users.html",
        users=filtered_users,
        all_users=users,
        inactive_count=inactive_count,
        active_count=active_count,
        stale_threshold_days=threshold_days,
        status_filter=status_filter,
        last_refresh=db.latest_refresh(site),
    )
