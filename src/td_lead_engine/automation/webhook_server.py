"""Webhook receiver server for inbound integrations."""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature (supports multiple formats)."""
    if not secret:
        return True  # No secret configured, skip verification

    # Try various signature formats
    expected_signatures = [
        # HMAC-SHA256 hex
        hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest(),
        # HMAC-SHA256 with prefix
        f"sha256={hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()}",
        # HMAC-SHA1 (legacy)
        hmac.new(secret.encode(), payload, hashlib.sha1).hexdigest(),
    ]

    return signature in expected_signatures


def process_lead_data(data: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Process incoming lead data and add to database."""
    from ..storage.database import LeadDatabase
    from ..models.lead import Lead

    db = LeadDatabase()

    # Map common field names
    lead_data = {
        "source": source,
        "name": data.get("name") or data.get("full_name") or data.get("contact_name"),
        "email": data.get("email") or data.get("email_address"),
        "phone": data.get("phone") or data.get("phone_number") or data.get("mobile"),
        "bio": data.get("message") or data.get("notes") or data.get("description"),
        "raw_data": data,
    }

    # Remove None values
    lead_data = {k: v for k, v in lead_data.items() if v is not None}

    lead = Lead(**lead_data)
    result = db.upsert_lead(lead)

    return {
        "lead_id": result.id if result else None,
        "status": "created" if result else "duplicate",
    }


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@app.route("/webhook/generic", methods=["POST"])
def generic_webhook():
    """Generic webhook endpoint for any source."""
    try:
        # Verify signature if provided
        signature = request.headers.get("X-Webhook-Signature", "")
        if WEBHOOK_SECRET and signature:
            if not verify_signature(request.data, signature, WEBHOOK_SECRET):
                return jsonify({"error": "Invalid signature"}), 401

        data = request.get_json() or {}
        source = request.args.get("source", "webhook")

        result = process_lead_data(data, source)

        logger.info(f"Processed webhook from {source}: {result}")
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/google-forms", methods=["POST"])
def google_forms_webhook():
    """Handle Google Forms submissions via Apps Script."""
    try:
        data = request.get_json() or {}

        # Google Forms typically sends data as form responses
        lead_data = {
            "name": data.get("Name") or data.get("name"),
            "email": data.get("Email") or data.get("email") or data.get("Email Address"),
            "phone": data.get("Phone") or data.get("phone") or data.get("Phone Number"),
            "message": data.get("Message") or data.get("message") or data.get("Comments"),
            "address": data.get("Address") or data.get("Property Address"),
        }

        # Build bio from address and message
        bio_parts = []
        if lead_data.get("address"):
            bio_parts.append(f"Property: {lead_data['address']}")
        if lead_data.get("message"):
            bio_parts.append(lead_data["message"])

        process_data = {
            "name": lead_data["name"],
            "email": lead_data["email"],
            "phone": lead_data["phone"],
            "message": " | ".join(bio_parts) if bio_parts else None,
        }

        result = process_lead_data(process_data, "google_forms")

        logger.info(f"Processed Google Forms submission: {result}")
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.error(f"Google Forms webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/zapier", methods=["POST"])
def zapier_webhook():
    """Handle Zapier webhook triggers."""
    try:
        data = request.get_json() or {}

        # Zapier sends data in various formats depending on the trigger
        result = process_lead_data(data, "zapier")

        logger.info(f"Processed Zapier webhook: {result}")
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.error(f"Zapier webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/typeform", methods=["POST"])
def typeform_webhook():
    """Handle Typeform submissions."""
    try:
        # Verify Typeform signature
        signature = request.headers.get("Typeform-Signature", "")
        if WEBHOOK_SECRET and signature:
            if not verify_signature(request.data, signature, WEBHOOK_SECRET):
                return jsonify({"error": "Invalid signature"}), 401

        data = request.get_json() or {}

        # Typeform sends answers in a specific format
        form_response = data.get("form_response", {})
        answers = form_response.get("answers", [])

        # Map answers to fields (basic mapping, customize as needed)
        lead_data = {}
        for answer in answers:
            field = answer.get("field", {})
            field_ref = field.get("ref", "")

            if "name" in field_ref.lower():
                lead_data["name"] = answer.get("text")
            elif "email" in field_ref.lower():
                lead_data["email"] = answer.get("email")
            elif "phone" in field_ref.lower():
                lead_data["phone"] = answer.get("phone_number")

        result = process_lead_data(lead_data, "typeform")

        logger.info(f"Processed Typeform submission: {result}")
        return jsonify({"success": True, **result})

    except Exception as e:
        logger.error(f"Typeform webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/facebook-lead", methods=["POST", "GET"])
def facebook_lead_webhook():
    """Handle Facebook Lead Ads webhooks."""
    # Verification challenge for Facebook
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        verify_token = os.environ.get("FB_VERIFY_TOKEN", WEBHOOK_SECRET)

        if mode == "subscribe" and token == verify_token:
            return challenge, 200
        return "Verification failed", 403

    try:
        # Verify Facebook signature
        signature = request.headers.get("X-Hub-Signature-256", "")
        fb_secret = os.environ.get("FB_APP_SECRET", WEBHOOK_SECRET)

        if fb_secret and signature:
            expected = f"sha256={hmac.new(fb_secret.encode(), request.data, hashlib.sha256).hexdigest()}"
            if signature != expected:
                return jsonify({"error": "Invalid signature"}), 401

        data = request.get_json() or {}

        # Process Facebook lead data
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "leadgen":
                    lead_info = change.get("value", {})

                    # You'll need to fetch full lead data using Facebook Graph API
                    # This just stores the lead ID for now
                    lead_data = {
                        "source_id": lead_info.get("leadgen_id"),
                        "name": "Facebook Lead",  # Fetch from Graph API
                        "notes": f"Form ID: {lead_info.get('form_id')}",
                    }

                    process_lead_data(lead_data, "facebook_ads")

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"Facebook webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/calendly", methods=["POST"])
def calendly_webhook():
    """Handle Calendly booking webhooks."""
    try:
        data = request.get_json() or {}

        event = data.get("event", "")
        payload = data.get("payload", {})

        if event == "invitee.created":
            invitee = payload.get("invitee", {})

            lead_data = {
                "name": invitee.get("name"),
                "email": invitee.get("email"),
                "message": f"Calendly booking: {payload.get('event_type', {}).get('name', 'Meeting')}",
            }

            # Add answers from questions
            questions = invitee.get("questions_and_answers", [])
            for qa in questions:
                if "phone" in qa.get("question", "").lower():
                    lead_data["phone"] = qa.get("answer")

            result = process_lead_data(lead_data, "calendly")

            logger.info(f"Processed Calendly booking: {result}")
            return jsonify({"success": True, **result})

        return jsonify({"success": True, "message": "Event ignored"})

    except Exception as e:
        logger.error(f"Calendly webhook error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/hubspot", methods=["POST"])
def hubspot_webhook():
    """Handle HubSpot contact webhooks."""
    try:
        # HubSpot sends an array of events
        events = request.get_json() or []

        for event in events:
            if event.get("subscriptionType") == "contact.creation":
                # Fetch contact details from HubSpot API
                # For now, just log the event
                object_id = event.get("objectId")
                logger.info(f"HubSpot contact created: {object_id}")

        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"HubSpot webhook error: {e}")
        return jsonify({"error": str(e)}), 500


def run_server(host: str = "0.0.0.0", port: int = 5001, debug: bool = False):
    """Run the webhook server."""
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TD Lead Engine Webhook Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5001, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting webhook server on {args.host}:{args.port}")

    run_server(args.host, args.port, args.debug)
