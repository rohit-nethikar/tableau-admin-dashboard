import os

from flask import Flask, redirect, render_template, session, url_for
from flask_socketio import SocketIO

import db
import refresh_watch
import scheduler
import site_context
from config import INSTANCE_DIR, settings
import websocket_events
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

    # Initialize WebSocket support
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    websocket_events.init_websocket(socketio)

    db.init_db()

    # Account Number Protection: Verify on startup
    try:
        from account_number_watchdog import get_watchdog
        watchdog = get_watchdog()
        if not watchdog.verify_accounts():
            print("⚠️ WARNING: Account numbers were lost and have been auto-restored from backup")
    except Exception as e:
        print(f"⚠️ Account watchdog warning: {e}")

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

    # Start background metrics updater for real-time dashboard
    websocket_events.start_metrics_updater(app, socketio)

    # Store socketio for access in routes
    app.socketio = socketio

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    # Use socketio.run instead of waitress for WebSocket support
    socketio.run(app, host=settings.host, port=settings.port, debug=False, allow_unsafe_werkzeug=True)
