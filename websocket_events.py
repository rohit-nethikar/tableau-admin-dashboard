"""
WebSocket event handlers for real-time dashboard updates
"""
from flask import session
from flask_socketio import emit, join_room, leave_room
import db
import site_context
import threading
import time
from datetime import datetime

# Store active connections
active_connections = {}

def get_dashboard_metrics(site):
    """Fetch current dashboard metrics"""
    try:
        workbooks = db.fetch_workbooks(site)
        datasources = db.fetch_datasources(site)
        health_scores = db.fetch_health_scores(site)
        open_findings = db.fetch_findings(site, {"status": "open"})
        users = db.fetch_users(site)
        audit_log = db.fetch_audit_log(limit=10)

        # Calculate metrics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in open_findings:
            severity_counts[f["severity"]] = severity_counts.get(f["severity"], 0) + 1

        stale_count = sum(1 for w in workbooks if w["is_stale"]) + sum(1 for d in datasources if d["is_stale"])

        avg_score = (
            round(sum(r["score"] or 0 for r in health_scores) / len(health_scores), 1)
            if health_scores
            else None
        )

        # Extract status
        extract_stats = {
            "success": sum(1 for w in workbooks if w.get("extract_status") == "Success"),
            "failed": sum(1 for w in workbooks if w.get("extract_status") == "Failed"),
            "running": sum(1 for w in workbooks if w.get("extract_status") == "Running"),
            "total": len([w for w in workbooks if w.get("extract_status")]),
        }

        # User roles
        user_roles = {}
        for u in users:
            role = u.get("site_role", "Unknown")
            user_roles[role] = user_roles.get(role, 0) + 1

        # Content types
        content_by_type = {
            "Workbooks": len(workbooks),
            "Data Sources": len(datasources),
            "Custom Views": len(db.fetch_custom_views(site)),
            "Projects": len(db.fetch_projects(site)),
        }

        return {
            "timestamp": datetime.now().isoformat(),
            "workbook_count": len(workbooks),
            "datasource_count": len(datasources),
            "stale_count": stale_count,
            "custom_view_count": len(db.fetch_custom_views(site)),
            "subscription_count": len(db.fetch_subscriptions(site)),
            "user_count": len(users),
            "avg_score": avg_score,
            "severity_counts": severity_counts,
            "extract_stats": extract_stats,
            "user_roles": user_roles,
            "content_by_type": content_by_type,
            "recent_activity": audit_log[:3] if audit_log else [],
        }
    except Exception as e:
        print(f"Error fetching dashboard metrics: {e}")
        return None


def init_websocket(socketio):
    """Initialize WebSocket event handlers"""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        if 'user_id' not in session:
            return False

        user_id = session.get('user_id')
        active_connections[user_id] = True
        print(f"Client connected: {user_id}")
        emit('connection_response', {'data': 'Connected to live updates'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        user_id = session.get('user_id')
        if user_id in active_connections:
            del active_connections[user_id]
        print(f"Client disconnected: {user_id}")

    @socketio.on('request_metrics')
    def handle_metrics_request():
        """Handle metrics request from client"""
        site = site_context.get_current_site()
        metrics = get_dashboard_metrics(site)
        if metrics:
            emit('metrics_update', metrics)

    return socketio


def broadcast_metrics_update(socketio, site):
    """Broadcast updated metrics to all connected clients"""
    metrics = get_dashboard_metrics(site)
    if metrics:
        socketio.emit('metrics_update', metrics, broadcast=True)


def start_metrics_updater(app, socketio):
    """Start background thread that updates metrics periodically"""
    def update_loop():
        with app.app_context():
            while True:
                try:
                    # Update metrics every 30 seconds
                    time.sleep(30)

                    # Get the current site (from all active sessions)
                    # For now, we'll just use the default site
                    site = site_context.get_current_site()
                    if site:
                        broadcast_metrics_update(socketio, site)
                except Exception as e:
                    print(f"Error in metrics update loop: {e}")

    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
    return thread
