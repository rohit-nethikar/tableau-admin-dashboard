from flask import Blueprint, flash, jsonify, redirect, request, url_for

import refresh_watch
import scheduler
import site_context
from auth import login_required
from config import settings

bp = Blueprint("refresh", __name__)


@bp.route("/refresh", methods=["POST"])
@login_required
def trigger_refresh():
    site = site_context.get_current_site()
    refresh_watch.start_watching(site)
    started = scheduler.trigger_refresh_async(site)
    if started:
        message = "Cache refresh started in the background."
    else:
        message = "A refresh is already running - this one is queued and will run right after."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"message": message})
    flash(message, "success")
    return redirect(request.referrer or url_for("workbooks.list_workbooks"))


@bp.route("/refresh-status")
@login_required
def refresh_status():
    site = site_context.get_current_site()
    return jsonify({"pending": refresh_watch.is_pending(site)})


@bp.route("/refresh-all-sites", methods=["POST"])
@login_required
def trigger_refresh_all_sites():
    started = scheduler.trigger_refresh_all_sites_async()
    if started:
        flash(f"Refreshing all {len(settings.sites)} sites in the background.", "success")
    else:
        flash("A refresh is already running - the all-sites refresh is queued and will run right after.", "success")
    return redirect(request.referrer or url_for("refresh_health.refresh_health"))
