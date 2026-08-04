from collections import defaultdict

from flask import Blueprint, render_template

import db
import site_context
from auth import login_required
from config import settings

bp = Blueprint("workbooks", __name__)


@bp.route("/workbooks")
@login_required
def list_workbooks():
    site = site_context.get_current_site()
    workbooks = db.fetch_workbooks(site)

    users_by_id = db.fetch_users_by_id(site)
    for wb in workbooks:
        user = users_by_id.get(wb["owner_id"], {})
        wb["owner_email"] = user.get("email")
        wb["owner_site_role"] = user.get("site_role")
        wb["owner_last_login_at"] = user.get("last_login_at")

    workbook_datasources = defaultdict(list)
    for link in db.fetch_lineage(site):
        workbook_datasources[link["workbook_name"]].append(link["datasource_name"])

    personal_space_count = sum(1 for wb in workbooks if not wb["project_name"])

    return render_template(
        "workbooks.html",
        workbooks=workbooks,
        workbook_datasources=dict(workbook_datasources),
        stale_threshold_days=settings.stale_threshold_days,
        last_refresh=db.latest_refresh(site),
        personal_space_count=personal_space_count,
    )
