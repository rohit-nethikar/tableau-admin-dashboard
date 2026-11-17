from collections import defaultdict

from flask import Blueprint, render_template

import db
import site_context
from auth import login_required

bp = Blueprint("lineage", __name__)


@bp.route("/lineage")
@login_required
def list_lineage():
    site = site_context.get_current_site()
    links = db.fetch_lineage(site)
    by_datasource = defaultdict(list)
    for link in links:
        by_datasource[link["datasource_name"]].append(link["workbook_name"])

    return render_template(
        "lineage.html",
        by_datasource=dict(sorted(by_datasource.items())),
        last_refresh=db.latest_refresh(site),
        has_data=bool(links),
    )
