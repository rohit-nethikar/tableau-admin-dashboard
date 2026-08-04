from flask import Blueprint, render_template, request

import db
import site_context
from auth import login_required

bp = Blueprint("custom_views", __name__)


def _filters_from_args(args):
    shared = args.get("shared")
    return {
        "workbook_name": args.get("workbook_name") or None,
        "owner_name": args.get("owner_name") or None,
        "view_name": args.get("view_name") or None,
        "shared": int(shared) if shared in ("0", "1") else None,
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

    return render_template(
        "custom_views.html",
        custom_views=db.fetch_custom_views(site, filters),
        workbook_names=workbook_names,
        owner_names=owner_names,
        view_names=view_names,
        workbooks_by_name=workbooks_by_name,
        filters=filters,
        last_refresh=db.latest_refresh(site),
    )
