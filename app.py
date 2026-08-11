import os
import threading
from flask import Flask, redirect, render_template, session, url_for
from waitress import serve

import db
import refresh_watch
import scheduler
import site_context
from config import INSTANCE_DIR, settings
from routes import (
    analytics,
    auth_routes,
    background_jobs,
    config_audit,
    connected_apps,
    custom_views,
    data_alerts,
    datasources,
    findings,
    health,
    help,
    license_usage,
    lineage,
    overview,
    permissions,
    phase4_api,
    refresh,
    refresh_health,
    security_certs,
    setup,
    site_settings,
    sites,
    subscriptions,
    users,
    webhooks,
    workbooks,
)

FLASK_SECRET_PATH = os.path.join(INSTANCE_DIR, "flask_secret.key")
# Prevent duplicate account-number syncs inside this process.
_account_sync_lock = threading.Lock()


def _sync_account_numbers_background():
    """Sync account numbers from BigQuery on app startup.

    This runs in a background thread to avoid blocking Waitress startup.
    The bigquery_sync module handles both:
    - Creating placeholder users for custom view owners found in BigQuery
    - Updating all users (new and existing) with account numbers from BigQuery

    This ensures the custom views page always shows accurate account numbers.
    """
    if not _account_sync_lock.acquire(blocking=False):
        print("Account number sync is already running; skipping duplicate trigger")
        return

    try:
        print("Starting BigQuery account number sync on app startup...")
        import bigquery_sync

        # Run the main BigQuery sync - handles placeholder creation and account number updates
        result = bigquery_sync.sync_account_numbers_to_database(db)

        if result['status'] == 'success':
            print(f"✓ Account number sync successful: {result['message']}")
            print(f"  Updated/Created: {result['updated_count']} users")
        else:
            print(f"✗ Account number sync failed: {result['message']}")

        # Verify final count
        with db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM users
                WHERE account_number IS NOT NULL
                  AND account_number != ''
                """
            )
            count = cursor.fetchone()[0]
            print(f"Verification: {count} total users have account numbers")

        # Check for account number backup/restore issues
        try:
            from account_number_watchdog import get_watchdog

            watchdog = get_watchdog()
            if not watchdog.verify_accounts():
                print(
                    "WARNING: Account numbers were lost and have been "
                    "auto-restored from backup"
                )
        except Exception as watchdog_error:
            print(f"WARNING: Account watchdog error: {watchdog_error}")

    except Exception as error:
        print(f"WARNING: Background account number sync failed: {error}")
        import traceback
        traceback.print_exc()
    finally:
        _account_sync_lock.release()


def _start_account_number_sync_async():
    """Start account-number synchronization in a daemon thread."""
    thread = threading.Thread(
        target=_sync_account_numbers_background,
        name="account-number-sync",
        daemon=True,
    )
    thread.start()
    return thread


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
    app.register_blueprint(help.bp)
    app.register_blueprint(analytics.bp)
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
    app.register_blueprint(security_certs.bp)
    app.register_blueprint(config_audit.bp)
    app.register_blueprint(license_usage.bp)
    app.register_blueprint(background_jobs.bp)
    app.register_blueprint(sites.bp)
    app.register_blueprint(users.bp)
    app.register_blueprint(phase4_api.phase4_bp)

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

    # DEPLOYMENT_HEALTH_ROUTE

    # Register a dependency-free liveness route only if /health does not already exist.

    if not any(rule.rule == "/health" for rule in app.url_map.iter_rules()):

        @app.get("/health")

        def deployment_health():

            return {"status": "ok"}, 200


    # DEPLOYMENT_LIVENESS_ROUTE


    @app.get("/healthz")


    def deployment_liveness():


        return {"status": "ok"}, 200



    scheduler.start()

    # Start BigQuery account number sync in background thread to populate custom view account numbers.
    # Does not block app startup since it runs asynchronously.
    # This ensures account numbers are populated before any user accesses the custom views page.
    print("\n" + "="*70)
    print("IMPORTANT: BigQuery account number sync is running in background...")
    print("This populates account numbers for all custom view owners.")
    print("="*70 + "\n")
    _start_account_number_sync_async()

    return app


app = create_app()

if __name__ == "__main__":
    print("Starting Tableau Admin Dashboard (HTTP-only mode)")
    serve(app, host=settings.host, port=settings.port)




