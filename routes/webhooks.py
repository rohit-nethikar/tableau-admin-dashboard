"""Webhook endpoint for receiving real-time events from Tableau Server.
Webhook events trigger immediate content change logging and email alerts.
"""
from flask import Blueprint, request, jsonify

import webhook_handler
import site_context
import audit


bp = Blueprint("webhooks", __name__)


@bp.route("/webhooks/tableau", methods=["POST"])
def receive_tableau_webhook():
    """Receive webhook events from Tableau Server.

    Expected payload:
    {
        "webhook": {
            "id": "...",
            "event": "WorkbookPublished",
            "resource": {
                "id": "...",
                "name": "...",
                "resourceType": "Workbook"
            },
            "created_at": "...",
            ...
        }
    }
    """
    try:
        data = request.get_json()
        if not data or "webhook" not in data:
            return jsonify({"error": "Invalid payload"}), 400

        webhook = data["webhook"]
        event_type = webhook.get("event")
        resource = webhook.get("resource", {})
        resource_id = resource.get("id")
        resource_name = resource.get("name")

        if not event_type or not resource_id:
            return jsonify({"error": "Missing event or resource id"}), 400

        site = site_context.get_current_site()

        webhook_handler.handle_webhook_event(site, event_type, resource_id, resource_name, data)

        audit.log_action(
            "system",
            "webhook_received",
            details=f"Webhook {event_type} for {resource_name}",
        )

        return jsonify({"status": "ok"}), 200

    except Exception as exc:
        audit.log_action("system", "webhook_error", details=str(exc))
        return jsonify({"error": str(exc)}), 500
