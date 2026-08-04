import csv
import io
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, url_for

import audit
import db
import site_context
from auth import login_required

bp = Blueprint("findings", __name__)

_VALID_STATUSES = ("open", "acknowledged", "resolved", "dismissed")


def _filters_from_args(args):
    return {
        "severity": args.get("severity") or None,
        "category": args.get("category") or None,
        "project_name": args.get("project_name") or None,
        "owner_name": args.get("owner_name") or None,
        "status": args.get("status") or None,
    }


@bp.route("/findings")
@login_required
def list_findings():
    site = site_context.get_current_site()
    filters = _filters_from_args(request.args)
    findings = db.fetch_findings(site, filters)
    all_findings = db.fetch_findings(site)  # unfiltered - populates the filter dropdowns

    active_filters = {k: v for k, v in filters.items() if v}
    export_qs = urlencode(active_filters)
    export_url = url_for("findings.export_findings_csv") + (f"?{export_qs}" if export_qs else "")

    status_counts = Counter(f["status"] for f in findings)
    severity_counts = Counter(f["severity"] for f in findings)

    return render_template(
        "findings.html",
        findings=findings,
        filters=filters,
        severities=sorted({f["severity"] for f in all_findings}),
        categories=sorted({f["category"] for f in all_findings}),
        statuses=sorted({f["status"] for f in all_findings}),
        export_url=export_url,
        total_count=len(findings),
        open_count=status_counts.get("open", 0),
        critical_count=severity_counts.get("critical", 0),
        high_count=severity_counts.get("high", 0),
        last_refresh=db.latest_refresh(site),
    )


@bp.route("/findings/export.csv")
@login_required
def export_findings_csv():
    site = site_context.get_current_site()
    filters = _filters_from_args(request.args)
    findings = db.fetch_findings(site, filters)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id", "resource_type", "resource_name", "project_name", "owner_name",
        "category", "severity", "title", "description", "recommended_action",
        "status", "status_note", "first_detected_at", "last_seen_at",
    ])
    for f in findings:
        writer.writerow([
            f["id"], f["resource_type"], f["resource_name"], f["project_name"], f["owner_name"],
            f["category"], f["severity"], f["title"], f["description"], f["recommended_action"],
            f["status"], f["status_note"], f["first_detected_at"], f["last_seen_at"],
        ])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=findings.csv"},
    )


@bp.route("/findings/<int:finding_id>/status", methods=["POST"])
@login_required
def update_status(finding_id):
    new_status = request.form.get("status")
    note = request.form.get("note", "").strip() or None
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if new_status not in _VALID_STATUSES:
        if is_ajax:
            return jsonify({"error": "Invalid status."}), 400
        flash("Invalid status.", "error")
        return redirect(request.referrer or url_for("findings.list_findings"))

    finding = db.get_finding(finding_id)
    if not finding:
        if is_ajax:
            return jsonify({"error": "Finding not found."}), 404
        flash("Finding not found.", "error")
        return redirect(request.referrer or url_for("findings.list_findings"))

    now_iso = datetime.now(timezone.utc).isoformat()
    db.set_finding_status(finding_id, new_status, note, "admin", now_iso)
    audit.log_action(
        actor="admin",
        action=f"finding_status:{new_status}",
        resource_type=finding["resource_type"],
        resource_id=finding["resource_id"],
        details=f"finding_id={finding_id} title={finding['title']!r} note={note!r}",
    )

    if is_ajax:
        return jsonify({"message": "Finding status updated.", "status": new_status, "note": note})
    flash("Finding status updated.", "success")
    return redirect(request.referrer or url_for("findings.list_findings"))
