import os

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
    connected_apps,
    custom_views,
    data_alerts,
    datasources,
    findings,
    health,
    lineage,
    overview,
    permissions,
    phase4_api,
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

    # Sync account numbers from BigQuery BEFORE app starts (synchronous, blocking)
    try:
        print("Syncing account numbers from BigQuery...")
        import bigquery_sync
        import uuid
        import sqlite3

        # First, add missing custom view owners to users table
        with db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT owner_name FROM custom_views')
            custom_view_owners = [row[0] for row in cursor.fetchall()]

            added_count = 0
            for owner in custom_view_owners:
                cursor.execute('SELECT id FROM users WHERE LOWER(email) = LOWER(?)', (owner,))
                if not cursor.fetchone():
                    # Get site for this owner
                    cursor.execute('SELECT site FROM custom_views WHERE owner_name = ? LIMIT 1', (owner,))
                    site_row = cursor.fetchone()
                    if site_row:
                        site = site_row[0]
                        user_id = str(uuid.uuid4())
                        name_part = owner.split('@')[0]
                        try:
                            cursor.execute('''
                            INSERT INTO users (id, name, email, site, site_role, fetched_at, account_number)
                            VALUES (?, ?, ?, ?, ?, datetime('now'), NULL)
                            ''', (user_id, name_part, owner, site, 'Unknown'))
                            added_count += 1
                        except sqlite3.IntegrityError:
                            pass
            if added_count > 0:
                # Don't just commit - explicitly ensure the connection commits
                conn.commit()
                print(f"Added {added_count} custom view owners to users table")

        # Now sync account numbers from BigQuery
        result = bigquery_sync.sync_account_numbers_to_database(db)
        print(f"Account number sync: {result['message']} (Updated: {result['updated_count']})")

        # Verify sync worked
        with db.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users WHERE account_number IS NOT NULL AND account_number != ''")
            count = cursor.fetchone()[0]
            print(f"Verification: {count} users now have account numbers")

    except Exception as e:
        print(f"WARNING: Account number sync failed: {e}")
        import traceback
        traceback.print_exc()

    # Account Number Protection: Verify on startup
    try:
        from account_number_watchdog import get_watchdog
        watchdog = get_watchdog()
        if not watchdog.verify_accounts():
            print("WARNING: Account numbers were lost and have been auto-restored from backup")
    except Exception as e:
        print(f"WARNING: Account watchdog error: {e}")

    app.register_blueprint(setup.bp)
    app.register_blueprint(auth_routes.bp)
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

    scheduler.start()

    return app


app = create_app()

if __name__ == "__main__":
    print("Starting Tableau Admin Dashboard (HTTP-only mode)")
    serve(app, host=settings.host, port=settings.port)
