from flask import Blueprint, render_template, request, jsonify

import db
import site_context
from auth import login_required
import bigquery_sync

bp = Blueprint("custom_views", __name__)


def _filters_from_args(args):
    shared = args.get("shared")
    return {
        "workbook_name": args.get("workbook_name") or None,
        "owner_name": args.get("owner_name") or None,
        "view_name": args.get("view_name") or None,
        "shared": int(shared) if shared in ("0", "1") else None,
        "account_type": args.get("account_type") or None,
    }


@bp.route("/custom-views")
@login_required
def list_custom_views():
    site = site_context.get_current_site()
    filters = _filters_from_args(request.args)
    all_custom_views = db.fetch_custom_views(site)  # unfiltered - populates the filter dropdowns

    workbook_names = sorted({cv["workbook_name"] for cv in all_custom_views if cv["workbook_name"]})
    owner_names = sorted({cv["owner_name"] for cv in all_custom_views if cv["owner_name"]})
    view_names = sorted({cv["view_name"] for cv in all_custom_views if cv["view_name"]})

    # Joined by name (same pattern as workbook_datasources in routes/workbooks.py) so
    # each custom view can link straight to its parent workbook and show which
    # project it lives in.
    workbooks_by_name = {wb["name"]: wb for wb in db.fetch_workbooks(site)}

    # Fetch filtered views
    filtered_views = db.fetch_custom_views(site, filters)

    # Apply account_type filter (Mayo vs Non-Mayo)
    # Note: owner_name actually contains the email address
    account_type = filters.get("account_type")
    if account_type == "mayo":
        filtered_views = [cv for cv in filtered_views if cv.get("owner_name", "").lower().endswith("@mayo.edu")]
    elif account_type == "non-mayo":
        filtered_views = [cv for cv in filtered_views if cv.get("owner_name", "") and not cv.get("owner_name", "").lower().endswith("@mayo.edu")]

    return render_template(
        "custom_views.html",
        custom_views=filtered_views,
        workbook_names=workbook_names,
        owner_names=owner_names,
        view_names=view_names,
        workbooks_by_name=workbooks_by_name,
        filters=filters,
        last_refresh=db.latest_refresh(site),
    )


@bp.route("/custom-views/account-numbers", methods=["GET"])
@login_required
def get_account_numbers():
    """Fetch all users with their account numbers for the current site."""
    site = site_context.get_current_site()
    users = db.fetch_users(site)
    return jsonify([{
        "id": u["id"],
        "name": u["name"],
        "email": u.get("email", ""),
        "account_number": u.get("account_number", "")
    } for u in users])


@bp.route("/custom-views/account-numbers", methods=["POST"])
@login_required
def update_account_number():
    """Update account number for a user."""
    site = site_context.get_current_site()
    data = request.get_json()
    user_id = data.get("user_id")
    account_number = data.get("account_number")

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    db.update_user_account_number(site, user_id, account_number)
    return jsonify({"status": "ok"})


@bp.route("/custom-views/sync-bigquery-account-numbers", methods=["POST"])
def sync_bigquery_account_numbers():
    """Sync account numbers from BigQuery to the local database."""
    try:
        result = bigquery_sync.sync_account_numbers_to_database(db)
        status_code = 200 if result["status"] == "success" else 500
        return jsonify(result), status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
