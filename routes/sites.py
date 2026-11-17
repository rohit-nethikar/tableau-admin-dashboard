from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, request, url_for

import db
import refresh_watch
import scheduler
import site_context
from auth import login_required
from config import settings

bp = Blueprint("sites", __name__)


def _is_fresh(site: str) -> bool:
    latest = db.latest_refresh(site)
    if not latest or latest["status"] not in ("success", "partial") or not latest["finished_at"]:
        return False
    finished = datetime.fromisoformat(latest["finished_at"])
    if finished.tzinfo is None:
        finished = finished.replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - finished
    return age < timedelta(minutes=settings.site_switch_staleness_minutes)


@bp.route("/switch-site", methods=["POST"])
@login_required
def switch_site():
    site = request.form.get("site", "")
    if site in settings.sites:
        site_context.set_current_site(site)
        if _is_fresh(site):
            flash(f"Switched to site: {site}. Data is already up to date.", "success")
        else:
            # Switching sites kicks off a background refresh of the newly active site so
            # the data shown isn't left stale from whenever this site was last refreshed
            # (which may be never, for a site that hasn't been visited yet).
            refresh_watch.start_watching(site)
            if scheduler.trigger_refresh_async(site):
                flash(f"Switched to site: {site}. Refreshing latest data in the background - this page will reload automatically.", "success")
            else:
                flash(f"Switched to site: {site}. A refresh is already running - it's queued and this page will reload automatically.", "success")
    else:
        flash("Unknown site.", "error")
    return redirect(request.referrer or url_for("overview.show_overview"))
