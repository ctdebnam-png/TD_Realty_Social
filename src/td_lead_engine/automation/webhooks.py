"""Webhook system for real-time lead notifications and integrations."""

import json
import hmac
import hashlib
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class WebhookEvent(Enum):
    """Events that can trigger webhooks."""

    # Lead events
    LEAD_CREATED = "lead.created"
    LEAD_UPDATED = "lead.updated"
    LEAD_SCORED = "lead.scored"
    LEAD_HOT = "lead.hot"  # When lead becomes hot tier
    LEAD_STATUS_CHANGED = "lead.status_changed"

    # Import events
    IMPORT_STARTED = "import.started"
    IMPORT_COMPLETED = "import.completed"
    IMPORT_FAILED = "import.failed"

    # Scoring events
    SCORING_COMPLETED = "scoring.completed"

    # System events
    DAILY_DIGEST = "system.daily_digest"
    WEEKLY_REPORT = "system.weekly_report"


@dataclass
class WebhookConfig:
    """Configuration for a webhook endpoint."""

    id: str
    url: str
    events: List[WebhookEvent]
    secret: Optional[str] = None  # For HMAC signature
    enabled: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 60


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt."""

    webhook_id: str
    event: WebhookEvent
    payload: Dict[str, Any]
    status_code: Optional[int] = None
    response: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    delivered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class WebhookManager:
    """Manages webhook registrations and deliveries."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize webhook manager."""
        self.config_path = config_path or Path.home() / ".td-lead-engine" / "webhooks.json"
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.delivery_history: List[WebhookDelivery] = []
        self._load_config()

    def _load_config(self):
        """Load webhook configurations from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for wh_data in data.get("webhooks", []):
                        wh = WebhookConfig(
                            id=wh_data["id"],
                            url=wh_data["url"],
                            events=[WebhookEvent(e) for e in wh_data["events"]],
                            secret=wh_data.get("secret"),
                            enabled=wh_data.get("enabled", True),
                            headers=wh_data.get("headers", {}),
                        )
                        self.webhooks[wh.id] = wh
            except Exception as e:
                logger.error(f"Error loading webhook config: {e}")

    def _save_config(self):
        """Save webhook configurations to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "webhooks": [
                {
                    "id": wh.id,
                    "url": wh.url,
                    "events": [e.value for e in wh.events],
                    "secret": wh.secret,
                    "enabled": wh.enabled,
                    "headers": wh.headers,
                }
                for wh in self.webhooks.values()
            ]
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def register(
        self,
        webhook_id: str,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> WebhookConfig:
        """Register a new webhook endpoint."""
        webhook = WebhookConfig(
            id=webhook_id,
            url=url,
            events=events,
            secret=secret,
            headers=headers or {},
        )
        self.webhooks[webhook_id] = webhook
        self._save_config()
        logger.info(f"Registered webhook: {webhook_id} -> {url}")
        return webhook

    def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook endpoint."""
        if webhook_id in self.webhooks:
            del self.webhooks[webhook_id]
            self._save_config()
            logger.info(f"Unregistered webhook: {webhook_id}")
            return True
        return False

    def get_webhook(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Get a webhook by ID."""
        return self.webhooks.get(webhook_id)

    def list_webhooks(self) -> List[WebhookConfig]:
        """List all registered webhooks."""
        return list(self.webhooks.values())

    def trigger(
        self,
        event: WebhookEvent,
        payload: Dict[str, Any],
        async_delivery: bool = True
    ) -> List[WebhookDelivery]:
        """Trigger webhooks for an event."""
        deliveries = []

        for webhook in self.webhooks.values():
            if not webhook.enabled:
                continue
            if event not in webhook.events:
                continue

            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event=event,
                payload=payload,
            )

            if async_delivery:
                thread = threading.Thread(
                    target=self._deliver,
                    args=(webhook, delivery)
                )
                thread.daemon = True
                thread.start()
            else:
                self._deliver(webhook, delivery)

            deliveries.append(delivery)
            self.delivery_history.append(delivery)

        return deliveries

    def _deliver(self, webhook: WebhookConfig, delivery: WebhookDelivery):
        """Deliver a webhook payload."""
        payload_json = json.dumps({
            "event": delivery.event.value,
            "data": delivery.payload,
            "timestamp": datetime.now().isoformat(),
        })

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TD-Lead-Engine/1.0",
            "X-Webhook-Event": delivery.event.value,
            **webhook.headers,
        }

        # Add HMAC signature if secret is configured
        if webhook.secret:
            signature = hmac.new(
                webhook.secret.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        for attempt in range(webhook.max_retries):
            delivery.attempts = attempt + 1
            try:
                req = urllib.request.Request(
                    webhook.url,
                    data=payload_json.encode(),
                    headers=headers,
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=30) as resp:
                    delivery.status_code = resp.status
                    delivery.response = resp.read().decode()[:1000]
                    delivery.delivered_at = datetime.now()
                    logger.info(
                        f"Webhook delivered: {webhook.id} -> {delivery.event.value} "
                        f"(status: {delivery.status_code})"
                    )
                    return

            except urllib.error.HTTPError as e:
                delivery.status_code = e.code
                delivery.error = str(e)
                logger.warning(
                    f"Webhook failed: {webhook.id} (attempt {attempt + 1}): {e}"
                )

            except Exception as e:
                delivery.error = str(e)
                logger.error(
                    f"Webhook error: {webhook.id} (attempt {attempt + 1}): {e}"
                )

            # Wait before retry
            if attempt < webhook.max_retries - 1:
                import time
                time.sleep(webhook.retry_delay_seconds)

    # === Convenience methods for common events ===

    def trigger_lead_created(self, lead_data: Dict[str, Any]):
        """Trigger lead.created event."""
        self.trigger(WebhookEvent.LEAD_CREATED, lead_data)

    def trigger_lead_scored(self, lead_data: Dict[str, Any]):
        """Trigger lead.scored event."""
        self.trigger(WebhookEvent.LEAD_SCORED, lead_data)

        # Also trigger hot lead event if applicable
        if lead_data.get("tier") == "hot":
            self.trigger(WebhookEvent.LEAD_HOT, lead_data)

    def trigger_import_completed(self, import_data: Dict[str, Any]):
        """Trigger import.completed event."""
        self.trigger(WebhookEvent.IMPORT_COMPLETED, import_data)


# === Webhook Templates for Common Services ===

def create_slack_webhook(
    manager: WebhookManager,
    slack_webhook_url: str,
    events: Optional[List[WebhookEvent]] = None
) -> WebhookConfig:
    """Create a Slack webhook for lead notifications."""
    if events is None:
        events = [WebhookEvent.LEAD_HOT, WebhookEvent.DAILY_DIGEST]

    return manager.register(
        webhook_id="slack_notifications",
        url=slack_webhook_url,
        events=events,
    )


def create_zapier_webhook(
    manager: WebhookManager,
    zapier_webhook_url: str,
    events: Optional[List[WebhookEvent]] = None
) -> WebhookConfig:
    """Create a Zapier webhook for automation."""
    if events is None:
        events = [WebhookEvent.LEAD_CREATED, WebhookEvent.LEAD_HOT]

    return manager.register(
        webhook_id="zapier_automation",
        url=zapier_webhook_url,
        events=events,
    )


def create_hubspot_webhook(
    manager: WebhookManager,
    hubspot_webhook_url: str,
    api_key: str
) -> WebhookConfig:
    """Create a HubSpot webhook for CRM sync."""
    return manager.register(
        webhook_id="hubspot_crm",
        url=hubspot_webhook_url,
        events=[
            WebhookEvent.LEAD_CREATED,
            WebhookEvent.LEAD_SCORED,
            WebhookEvent.LEAD_STATUS_CHANGED,
        ],
        headers={"Authorization": f"Bearer {api_key}"},
    )
