"""Templates: an admin-curated registry of existing server workbooks that are
good starting points for a new dashboard. Users browse the gallery and
download a workbook definition (no extract/live data included) to build on
locally, instead of starting from a blank canvas. Never publishes/modifies
anything on the Tableau Server - downloads only.
"""
import io
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

import crypto
import db
import site_context
import tableau_client
from auth import login_required
from config import settings

bp = Blueprint("templates", __name__)


def _credentials():
    pat_name = db.get_config("pat_name")
    pat_encrypted = db.get_config("pat_encrypted")
    if not pat_name or not pat_encrypted:
        raise RuntimeError("No PAT configured - complete /setup first.")
    return pat_name, crypto.decrypt_value(pat_encrypted)


@bp.route("/templates", methods=["GET"])
@login_required
def list_templates():
    site = site_context.get_current_site()
    template_rows = db.fetch_templates(site)
    workbooks = sorted(db.fetch_workbooks(site), key=lambda wb: (wb["name"] or "").lower())
    standards_notes = db.get_config("template_standards_notes", "")
    return render_template(
        "templates.html",
        templates=template_rows,
        workbooks=workbooks,
        standards_notes=standards_notes,
    )


@bp.route("/templates/add", methods=["POST"])
@login_required
def add_template():
    site = site_context.get_current_site()
    workbook_id = request.form.get("workbook_id", "").strip()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    standards_notes = request.form.get("standards_notes", "").strip()

    if not workbook_id or not title:
        flash("Select a workbook and provide a title.", "error")
        return redirect(url_for("templates.list_templates"))

    workbooks = db.fetch_workbooks(site)
    workbook_name = next((wb["name"] for wb in workbooks if wb["id"] == workbook_id), None)
    if workbook_name is None:
        flash("Unknown workbook selected.", "error")
        return redirect(url_for("templates.list_templates"))

    try:
        now = datetime.now(timezone.utc).isoformat()
        db.insert_template(site, workbook_id, workbook_name, title, description, category, now, standards_notes)
        flash(f"Template '{title}' added successfully!", "success")
    except Exception as exc:
        flash(f"Error adding template: {exc}", "error")

    return redirect(url_for("templates.list_templates"))


@bp.route("/templates/standards", methods=["POST"])
@login_required
def save_standards_notes():
    notes = request.form.get("notes", "").strip()
    db.set_config("template_standards_notes", notes)
    flash("Developer standards notes saved.", "success")
    return redirect(url_for("templates.list_templates"))


@bp.route("/templates/<int:template_id>/delete", methods=["POST"])
@login_required
def delete_template_route(template_id):
    site = site_context.get_current_site()
    try:
        db.delete_template(template_id, site)
        flash("Template deleted successfully!", "success")
    except Exception as exc:
        flash(f"Error deleting template: {exc}", "error")

    return redirect(url_for("templates.list_templates"))


@bp.route("/templates/<int:template_id>/download", methods=["GET"])
@login_required
def download_template(template_id):
    site = site_context.get_current_site()
    template = db.fetch_template(template_id, site)
    if template is None:
        flash("Template not found.", "error")
        return redirect(url_for("templates.list_templates"))

    tmp_dir = tempfile.mkdtemp(prefix="template-dl-")
    try:
        pat_name, pat_secret = _credentials()
        with tableau_client.signed_in_server(settings.server_url, site, pat_name, pat_secret) as server:
            wb_item = tableau_client.find_workbook_by_id_or_name(server, template["workbook_id"])
            if wb_item is None:
                flash(f"Source workbook '{template['workbook_name']}' was not found on the server.", "error")
                return redirect(url_for("templates.list_templates"))

            downloaded_path = tableau_client.download_workbook_definition(server, wb_item.id, tmp_dir)

        with open(downloaded_path, "rb") as f:
            data = f.read()

        ext = os.path.splitext(downloaded_path)[1] or ".twbx"
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", template["title"]).strip("_") or "template"
        return send_file(
            io.BytesIO(data),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=f"{safe_name}{ext}",
        )
    except Exception as exc:
        flash(f"Could not download template: {exc}", "error")
        return redirect(url_for("templates.list_templates"))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
