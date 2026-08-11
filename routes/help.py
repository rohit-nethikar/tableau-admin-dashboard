from flask import Blueprint, render_template

from auth import login_required

bp = Blueprint("help", __name__)


@bp.route("/help")
@login_required
def show_help():
    """Help and dashboard guide page."""
    return render_template("help.html")
