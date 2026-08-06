"""
Phase 4 Advanced Features API Routes
Handles preferences, dashboards, alerts, and export functionality
"""

from flask import Blueprint, request, jsonify, session, send_file
from functools import wraps
import db
import json
import uuid
import io
from datetime import datetime
from export_service import export_metrics_to_csv, export_to_excel, export_findings_to_csv
from alerts_engine import create_alert_rule, update_alert_rule, delete_alert_rule

phase4_bp = Blueprint('phase4_api', __name__, url_prefix='/api')


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authed'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


# --- User Preferences -------

@phase4_bp.route('/preferences', methods=['GET'])
@require_auth
def get_preferences():
    """Get current user's preferences"""
    user_id = session.get('authed')
    prefs = db.get_user_preferences(user_id)
    if prefs:
        return jsonify(prefs), 200
    return jsonify({'error': 'No preferences found'}), 404


@phase4_bp.route('/preferences', methods=['POST'])
@require_auth
def save_preferences():
    """Save user preferences"""
    user_id = session.get('authed')
    data = request.get_json()

    db.upsert_user_preferences(
        user_id,
        dark_mode=data.get('dark_mode'),
        default_filters=json.dumps(data.get('default_filters', {})) if data.get('default_filters') else None,
        layout_settings=json.dumps(data.get('layout_settings', {})) if data.get('layout_settings') else None,
        notification_email=data.get('notification_email'),
        notifications_enabled=data.get('notifications_enabled', 1)
    )

    return jsonify({'status': 'saved'}), 200


@phase4_bp.route('/preferences/dark-mode', methods=['POST'])
@require_auth
def set_dark_mode():
    """Toggle dark mode"""
    user_id = session.get('authed')
    data = request.get_json()
    db.set_dark_mode(user_id, data.get('enabled', False))
    return jsonify({'status': 'updated'}), 200


# --- Export Routes -------

@phase4_bp.route('/export/csv', methods=['POST'])
@require_auth
def export_csv():
    """Export overview metrics to CSV"""
    data = request.get_json()
    metrics = data.get('metrics', {})
    filters = data.get('filters')

    csv_content = export_metrics_to_csv(metrics, filters)
    return send_file(
        io.BytesIO(csv_content.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'tableau_dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@phase4_bp.route('/export/excel', methods=['POST'])
@require_auth
def export_excel():
    """Export to Excel with formatting"""
    data = request.get_json()
    metrics = data.get('metrics', {})
    findings = data.get('findings', [])

    excel_bytes = export_to_excel(metrics, findings)
    return send_file(
        io.BytesIO(excel_bytes),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'tableau_dashboard_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )


@phase4_bp.route('/export/findings', methods=['POST'])
@require_auth
def export_findings():
    """Export findings to CSV"""
    data = request.get_json()
    findings = data.get('findings', [])

    csv_content = export_findings_to_csv(findings)
    return send_file(
        io.BytesIO(csv_content.encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'findings_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


# --- Dashboard Routes -------

@phase4_bp.route('/dashboards', methods=['GET'])
@require_auth
def list_dashboards():
    """Get all dashboards for current user"""
    user_id = session.get('authed')
    dashboards = db.get_user_dashboards(user_id)
    return jsonify(dashboards), 200


@phase4_bp.route('/dashboards', methods=['POST'])
@require_auth
def create_dashboard():
    """Create a new dashboard"""
    user_id = session.get('authed')
    data = request.get_json()
    config_id = f"dashboard_{user_id}_{uuid.uuid4().hex[:8]}"

    db.create_dashboard_config(
        config_id,
        user_id,
        data.get('name', 'Untitled Dashboard'),
        json.dumps(data.get('filters', {})),
        json.dumps(data.get('metric_selection', [])),
        json.dumps(data.get('layout', {})),
        data.get('is_shared', False)
    )

    return jsonify({'config_id': config_id}), 201


@phase4_bp.route('/dashboards/<config_id>', methods=['GET'])
@require_auth
def get_dashboard(config_id):
    """Get a specific dashboard"""
    dashboard = db.get_dashboard_config(config_id)
    if not dashboard:
        return jsonify({'error': 'Dashboard not found'}), 404
    return jsonify(dashboard), 200


@phase4_bp.route('/dashboards/<config_id>', methods=['PUT'])
@require_auth
def update_dashboard(config_id):
    """Update a dashboard"""
    data = request.get_json()
    updates = {}

    if 'name' in data:
        updates['name'] = data['name']
    if 'filters' in data:
        updates['filters'] = json.dumps(data['filters'])
    if 'metric_selection' in data:
        updates['metric_selection'] = json.dumps(data['metric_selection'])
    if 'layout' in data:
        updates['layout'] = json.dumps(data['layout'])
    if 'is_shared' in data:
        updates['is_shared'] = data['is_shared']

    db.update_dashboard_config(config_id, **updates)
    return jsonify({'status': 'updated'}), 200


@phase4_bp.route('/dashboards/<config_id>', methods=['DELETE'])
@require_auth
def delete_dashboard(config_id):
    """Delete a dashboard"""
    db.delete_dashboard_config(config_id)
    return jsonify({'status': 'deleted'}), 200


@phase4_bp.route('/dashboards/<config_id>/set-default', methods=['POST'])
@require_auth
def set_default_dashboard(config_id):
    """Set a dashboard as default"""
    user_id = session.get('authed')
    db.set_default_dashboard(user_id, config_id)
    return jsonify({'status': 'default set'}), 200


# --- Alert Routes -------

@phase4_bp.route('/alerts/rules', methods=['GET'])
@require_auth
def get_alert_rules():
    """Get all alert rules for current user"""
    user_id = session.get('authed')
    rules = db.get_alert_rules(user_id=user_id)
    return jsonify(rules), 200


@phase4_bp.route('/alerts/rules', methods=['POST'])
@require_auth
def create_alert():
    """Create a new alert rule"""
    user_id = session.get('authed')
    data = request.get_json()
    rule_id = f"rule_{user_id}_{uuid.uuid4().hex[:8]}"

    create_alert_rule(
        user_id,
        data.get('name'),
        data.get('metric'),
        data.get('condition'),
        float(data.get('threshold')),
        data.get('action')
    )

    return jsonify({'rule_id': rule_id}), 201


@phase4_bp.route('/alerts/rules/<rule_id>', methods=['PUT'])
@require_auth
def update_alert(rule_id):
    """Update an alert rule"""
    data = request.get_json()
    update_alert_rule(rule_id, **data)
    return jsonify({'status': 'updated'}), 200


@phase4_bp.route('/alerts/rules/<rule_id>', methods=['DELETE'])
@require_auth
def delete_alert(rule_id):
    """Delete an alert rule"""
    delete_alert_rule(rule_id)
    return jsonify({'status': 'deleted'}), 200


@phase4_bp.route('/alerts/rules/<rule_id>/enable', methods=['POST'])
@require_auth
def enable_alert(rule_id):
    """Enable an alert rule"""
    db.enable_alert_rule(rule_id)
    return jsonify({'status': 'enabled'}), 200


@phase4_bp.route('/alerts/rules/<rule_id>/disable', methods=['POST'])
@require_auth
def disable_alert(rule_id):
    """Disable an alert rule"""
    db.disable_alert_rule(rule_id)
    return jsonify({'status': 'disabled'}), 200


@phase4_bp.route('/alerts/history/<rule_id>', methods=['GET'])
@require_auth
def get_alert_history(rule_id):
    """Get alert trigger history"""
    limit = request.args.get('limit', 50, type=int)
    history = db.get_alert_history(rule_id, limit)
    return jsonify(history), 200


@phase4_bp.route('/alerts/active', methods=['GET'])
@require_auth
def get_active_alerts():
    """Get active/recent alerts for user"""
    user_id = session.get('authed')
    alerts = db.get_active_alerts(user_id)
    return jsonify(alerts), 200


# --- Filter Presets Routes -------

@phase4_bp.route('/filters/presets', methods=['GET'])
@require_auth
def list_filter_presets():
    """Get all filter presets for current user"""
    user_id = session.get('authed')
    presets = db.get_filter_presets(user_id)
    return jsonify(presets), 200


@phase4_bp.route('/filters/presets', methods=['POST'])
@require_auth
def create_filter_preset():
    """Save current filters as a named preset"""
    user_id = session.get('authed')
    data = request.get_json()
    preset_id = f"preset_{user_id}_{uuid.uuid4().hex[:8]}"

    db.create_filter_preset(
        preset_id,
        user_id,
        data.get('name', 'Unnamed Preset'),
        json.dumps(data.get('filters', {}))
    )

    return jsonify({'preset_id': preset_id}), 201


@phase4_bp.route('/filters/presets/<preset_id>', methods=['GET'])
@require_auth
def get_filter_preset(preset_id):
    """Get a specific filter preset"""
    preset = db.get_filter_preset(preset_id)
    if not preset:
        return jsonify({'error': 'Preset not found'}), 404
    return jsonify(preset), 200


@phase4_bp.route('/filters/presets/<preset_id>', methods=['DELETE'])
@require_auth
def delete_filter_preset(preset_id):
    """Delete a filter preset"""
    db.delete_filter_preset(preset_id)
    return jsonify({'status': 'deleted'}), 200
