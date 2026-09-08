"""Workbook Compare + Custom View Impact Check.

Strictly read-only: downloads the published workbook's definition WITHOUT its
extract, diffs it against a locally-uploaded candidate .twbx/.twb, and flags which
existing custom views could be affected. Never publishes, overwrites, or deletes
anything on the Tableau Server. See workbook_compare_engine.py for the parsing/diff
logic itself.
"""
import dataclasses
import io
import re
import shutil
import tempfile
import zipfile

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

import crypto
import db
import site_context
import tableau_client
import workbook_compare_pdf
from auth import login_required
from config import settings
from workbook_compare_engine import (
    classify_custom_view_impact,
    classify_view_impact,
    compute_diff,
    parse_workbook,
)

bp = Blueprint("workbook_compare", __name__)

# Sanity cap on the .twb XML itself (not the .twbx/extract) - a legitimate .twb is at
# most a few MB of XML; this only guards against a malformed/hostile upload.
MAX_TWB_BYTES = 200 * 1024 * 1024


def _credentials():
    pat_name = db.get_config("pat_name")
    pat_encrypted = db.get_config("pat_encrypted")
    if not pat_name or not pat_encrypted:
        raise RuntimeError("No PAT configured - complete /setup first.")
    return pat_name, crypto.decrypt_value(pat_encrypted)


def _read_twb_bytes(file_obj, filename: str) -> bytes:
    """Pulls just the .twb XML out of a .twbx/.twb file object, never touching the
    extract. `file_obj` is either an uploaded FileStorage's `.stream` (which Werkzeug
    already spools to a disk-backed temp file for large uploads, so this never loads
    the full multi-GB upload into memory) or a plain file opened from disk."""
    filename_lower = (filename or "").lower()

    if filename_lower.endswith(".twb"):
        file_obj.seek(0)
        data = file_obj.read(MAX_TWB_BYTES + 1)
        if len(data) > MAX_TWB_BYTES:
            raise ValueError("The .twb file exceeds the accepted size limit.")
        return data

    file_obj.seek(0)
    with zipfile.ZipFile(file_obj) as zf:
        twb_names = [n for n in zf.namelist() if n.lower().endswith(".twb")]
        if not twb_names:
            raise ValueError("No .twb file found inside the .twbx archive.")
        info = zf.getinfo(twb_names[0])
        if info.file_size > MAX_TWB_BYTES:
            raise ValueError("The .twb inside the .twbx exceeds the accepted size limit.")
        return zf.read(twb_names[0])


def _severity_for_classification(classification: str) -> str:
    return {
        "directly_impacted": "High",
        "potentially_impacted": "Medium",
        "label_change_only": "Low",
        "no_change": "None",
    }.get(classification, "None")


def _label_for_classification(classification: str) -> str:
    return {
        "directly_impacted": "Directly impacted",
        "potentially_impacted": "Potentially impacted",
        "label_change_only": "Label change only",
        "no_change": "No change detected",
    }.get(classification, "No change detected")


@bp.route("/workbook-compare", methods=["GET"])
@login_required
def show_workbook_compare():
    site = site_context.get_current_site()
    workbooks = sorted(db.fetch_workbooks(site), key=lambda wb: (wb["name"] or "").lower())
    return render_template("workbook_compare.html", workbooks=workbooks, result=None)


@bp.route("/workbook-compare", methods=["POST"])
@login_required
def run_workbook_compare():
    site = site_context.get_current_site()
    workbooks = sorted(db.fetch_workbooks(site), key=lambda wb: (wb["name"] or "").lower())

    workbook_id = request.form.get("workbook_id", "").strip()
    candidate_file = request.files.get("candidate_file")

    if not workbook_id:
        flash("Select a workbook to compare against.", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    if not candidate_file or not candidate_file.filename:
        flash("Upload the candidate .twbx or .twb file.", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    filename_lower = candidate_file.filename.lower()
    if not (filename_lower.endswith(".twbx") or filename_lower.endswith(".twb")):
        flash("Candidate file must be a .twbx or .twb file.", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    workbook_name = next((wb["name"] for wb in workbooks if wb["id"] == workbook_id), None)
    if workbook_name is None:
        flash("Unknown workbook selected.", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    try:
        candidate_twb_bytes = _read_twb_bytes(candidate_file.stream, candidate_file.filename)
    except (ValueError, zipfile.BadZipFile) as exc:
        flash(f"Could not read candidate file: {exc}", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    published_tmp_dir = tempfile.mkdtemp(prefix="wbcompare-")
    try:
        pat_name, pat_secret = _credentials()
        with tableau_client.signed_in_server(settings.server_url, site, pat_name, pat_secret) as server:
            wb_item = tableau_client.find_workbook_by_id_or_name(server, workbook_id)
            if wb_item is None:
                flash(f"Workbook '{workbook_name}' was not found on the server.", "error")
                return redirect(url_for("workbook_compare.show_workbook_compare"))

            published_path = tableau_client.download_workbook_definition(server, wb_item.id, published_tmp_dir)

        with open(published_path, "rb") as f:
            published_twb_bytes = _read_twb_bytes(f, published_path)

    except Exception as exc:
        flash(f"Could not download the published workbook: {exc}", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))
    finally:
        shutil.rmtree(published_tmp_dir, ignore_errors=True)

    try:
        published = parse_workbook(published_twb_bytes)
        candidate = parse_workbook(candidate_twb_bytes)
    except Exception as exc:
        flash(f"Could not parse workbook XML: {exc}", "error")
        return redirect(url_for("workbook_compare.show_workbook_compare"))

    diff = compute_diff(published, candidate)
    impact = classify_custom_view_impact(published, candidate, diff)

    custom_views = db.fetch_custom_views(site, {"workbook_name": workbook_name})
    for cv in custom_views:
        view_classification = classify_view_impact(
            cv.get("view_name"), published, candidate, diff, impact["classification"]
        )
        cv["impact_status"] = _label_for_classification(view_classification)
        cv["impact_severity"] = _severity_for_classification(view_classification)

    result = {
        "workbook_name": workbook_name,
        "diff": diff,
        "diff_json": dataclasses.asdict(diff),
        "impact": impact,
        "custom_views": custom_views,
    }

    return render_template("workbook_compare.html", workbooks=workbooks, result=result)


@bp.route("/workbook-compare/export-pdf", methods=["POST"])
@login_required
def export_pdf():
    """Builds the Workbook Compare PDF report from data the client already has
    (the same compare result rendered on the page) and streams it back
    directly - never written to disk on the server."""
    payload = request.get_json(silent=True) or {}
    workbook_name = payload.get("workbook_name") or "workbook"
    site = payload.get("site") or site_context.get_current_site()

    pdf_bytes = workbook_compare_pdf.build_report_pdf(
        workbook_name=workbook_name,
        site=site,
        diff=payload.get("diff") or {},
        impact=payload.get("impact") or {},
        custom_views=payload.get("custom_views") or [],
    )

    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", workbook_name).strip("_") or "workbook"
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"workbook_compare_{safe_name}.pdf",
    )
