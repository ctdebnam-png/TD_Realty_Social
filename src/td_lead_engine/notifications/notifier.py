"""Notification dispatch for website lead events.

Supports SMTP email, SendGrid, and webhook delivery.
"""

import os
import smtplib
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)


class NotificationConfig:
    def __init__(self):
        self.enabled = os.getenv("TD_NOTIFICATIONS_ENABLED", "false").lower() == "true"
        self.method = os.getenv("TD_NOTIFICATION_METHOD", "smtp")
        self.smtp_host = os.getenv("TD_SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("TD_SMTP_PORT", "587"))
        self.smtp_user = os.getenv("TD_SMTP_USER")
        self.smtp_password = os.getenv("TD_SMTP_PASSWORD")
        self.from_email = os.getenv("TD_FROM_EMAIL", self.smtp_user or "")
        self.to_email = os.getenv("TD_NOTIFY_EMAIL")
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.webhook_url = os.getenv("TD_WEBHOOK_URL")


_config = None


def _get_config() -> NotificationConfig:
    global _config
    if _config is None:
        _config = NotificationConfig()
    return _config


def send_hot_lead_alert(lead: dict, trigger_event: str = None):
    """Send notification when a lead becomes hot."""
    config = _get_config()
    if not config.enabled:
        return

    subject = f"Hot Lead Alert: {lead.get('name', 'Unknown')}"
    body = f"""New hot lead detected!

Name: {lead.get('name', 'Unknown')}
Email: {lead.get('email', 'N/A')}
Phone: {lead.get('phone', 'N/A')}
Score: {lead.get('score', 'N/A')}
Source: {lead.get('lead_source') or lead.get('source', 'unknown')}
{f'Trigger: {trigger_event}' if trigger_event else ''}

---
TD Lead Engine
"""

    if config.method == "smtp":
        _send_smtp(config, subject, body)
    elif config.method == "webhook":
        _send_webhook(config, lead, "hot_lead_alert")


def send_high_intent_event_alert(lead: dict, event: dict):
    """Send notification for high-intent website events."""
    config = _get_config()
    if not config.enabled:
        return

    high_intent = {"contact_submit", "home_value_request", "schedule_showing", "schedule_consultation"}
    event_name = event.get("event_name", "")
    if event_name not in high_intent:
        return

    subject = f"New {event_name.replace('_', ' ').title()}: {lead.get('name', 'Website Visitor')}"
    body = f"""New high-intent website event!

Event: {event_name}
Lead: {lead.get('name', 'Unknown')}
Email: {lead.get('email', 'Not provided')}
Phone: {lead.get('phone', 'Not provided')}
Page: {event.get('page_path', 'Unknown')}
Message: {event.get('message', 'N/A')}
Score: {lead.get('score', 'Not scored')}

---
TD Lead Engine
"""

    if config.method == "smtp":
        _send_smtp(config, subject, body)
    elif config.method == "webhook":
        _send_webhook(config, lead, event_name, event)


def _send_smtp(config: NotificationConfig, subject: str, body: str):
    if not all([config.smtp_user, config.smtp_password, config.to_email]):
        logger.warning("SMTP not fully configured, skipping notification")
        return

    msg = MIMEMultipart()
    msg["From"] = config.from_email
    msg["To"] = config.to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(config.smtp_host, config.smtp_port)
        server.starttls()
        server.login(config.smtp_user, config.smtp_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"Notification sent: {subject}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")


def _send_webhook(config: NotificationConfig, lead: dict, event_type: str, event_data: dict = None):
    if not config.webhook_url:
        return

    import requests

    payload = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "lead": lead,
        "event_data": event_data,
    }

    try:
        requests.post(config.webhook_url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Webhook failed: {e}")
