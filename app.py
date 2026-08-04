import os

from flask import Flask, redirect, render_template, session, url_for

import db
import refresh_watch
import scheduler
import site_context
from config import INSTANCE_DIR, settings
from routes import (
    auth_routes,
    connected_apps,
    custom_views,
    data_alerts,
    datasources,
    findings,
    health,
    lineage,
    overview,
    permissions,
    refresh,
    refresh_health,
    setup,
    site_settings,
    sites,
    subscriptions,
    users,
    webhooks,
    workbooks,
)

FLASK_SECRET_PATH = os.path.join(INSTANCE_DIR, "flask_secret.key")


def _load_or_create_flask_secret() -> bytes:
    if os.path.exists(FLASK_SECRET_PATH):
        with open(FLASK_SECRET_PATH, "rb") as f:
            return f.read()
    secret = os.urandom(32)
    with open(FLASK_SECRET_PATH, "wb") as f:
        f.write(secret)
    return secret


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or _load_or_create_flask_secret()

    db.init_db()

    app.register_blueprint(setup.bp)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(overview.bp)
    app.register_blueprint(workbooks.bp)
    app.register_blueprint(datasources.bp)
    app.register_blueprint(permissions.bp)
    app.register_blueprint(lineage.bp)
    app.register_blueprint(health.bp)
    app.register_blueprint(findings.bp)
    app.register_blueprint(refresh_health.bp)
    app.register_blueprint(refresh.bp)
    app.register_blueprint(custom_views.bp)
    app.register_blueprint(subscriptions.bp)
    app.register_blueprint(connected_apps.bp)
    app.register_blueprint(data_alerts.bp)
    app.register_blueprint(webhooks.bp)
    app.register_blueprint(site_settings.bp)
    app.register_blueprint(sites.bp)
    app.register_blueprint(users.bp)

    @app.template_filter("format_duration")
    def format_duration(seconds):
        if seconds is None:
            return ""
        seconds = int(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes}m"
        if minutes:
            return f"{minutes}m {secs}s"
        return f"{secs}s"

    @app.context_processor
    def inject_site_context():
        current_site = site_context.get_current_site()
        return {
            "current_site": current_site,
            "available_sites": settings.sites,
            "site_refresh_status": {s: db.latest_refresh(s) for s in settings.sites},
            "refresh_pending": session.get("authed", False) and refresh_watch.is_pending(current_site),
        }

    @app.route("/")
    def index():
        if session.get("authed"):
            return redirect(url_for("overview.show_overview"))
        return render_template("landing.html", already_configured=db.is_setup_complete())

    scheduler.start()

    return app


app = create_app()

if __name__ == "__main__":
    # Waitress instead of Flask's dev server - the dev server logs a warning on every
    # startup that it's not meant for anything but local single-user debugging, and
    # its single-threaded default would serialize teammates' requests behind each
    # other. Also sidesteps Flask's reloader, which would start the BackgroundScheduler
    # twice by re-running this module in a subprocess.
    from waitress import serve

    serve(app, host=settings.host, port=settings.port)
