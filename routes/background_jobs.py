from flask import Blueprint, render_template, redirect, url_for, flash

import audit
import crypto
import db
import site_context
import tableau_client
from auth import login_required
from config import settings

bp = Blueprint("background_jobs", __name__)


def _credentials():
    pat_name = db.get_config("pat_name")
    pat_encrypted = db.get_config("pat_encrypted")
    if not pat_name or not pat_encrypted:
        raise RuntimeError("No PAT configured - complete /setup first.")
    return pat_name, crypto.decrypt_value(pat_encrypted)


@bp.route("/background-jobs")
@login_required
def list_background_jobs():
    site = site_context.get_current_site()
    jobs, error = [], None
    try:
        pat_name, pat_secret = _credentials()
        with tableau_client.signed_in_server(settings.server_url, site, pat_name, pat_secret) as server:
            jobs = tableau_client.list_background_jobs(server)
    except Exception as exc:
        error = str(exc)
    return render_template("background_jobs.html", jobs=jobs, error=error)


@bp.route("/background-jobs/<job_id>/cancel", methods=["POST"])
@login_required
def cancel_background_job(job_id):
    site = site_context.get_current_site()
    try:
        pat_name, pat_secret = _credentials()
        with tableau_client.signed_in_server(settings.server_url, site, pat_name, pat_secret) as server:
            tableau_client.cancel_job(server, job_id)
        audit.log_action("admin", "background_job_cancelled", resource_type="job", resource_id=job_id)
        flash(f"Job {job_id} cancelled.", "success")
    except Exception as exc:
        flash(f"Could not cancel job {job_id}: {exc}", "error")
    return redirect(url_for("background_jobs.list_background_jobs"))
