"""Zapier integration for connecting to 5000+ apps."""

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ZapierConfig:
    """Zapier webhook configuration."""

    # Zapier "Catch Hook" URLs for different triggers
    new_lead_hook: Optional[str] = None
    hot_lead_hook: Optional[str] = None
    status_change_hook: Optional[str] = None
    daily_digest_hook: Optional[str] = None

    enabled: bool = True


class ZapierIntegration:
    """Send data to Zapier webhooks to trigger Zaps.

    Setup instructions:
    1. Create a Zap in Zapier
    2. Choose "Webhooks by Zapier" as the trigger
    3. Select "Catch Hook"
    4. Copy the webhook URL and configure it here
    5. Send a test event to define the data structure
    6. Connect to any of 5000+ apps as actions
    """

    def __init__(self, config: ZapierConfig):
        """Initialize Zapier integration."""
        self.config = config

    def _send_to_webhook(self, url: str, data: Dict[str, Any]) -> bool:
        """Send data to a Zapier webhook."""
        if not url:
            logger.warning("No Zapier webhook URL configured")
            return False

        try:
            payload = json.dumps(data).encode()
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                logger.info(f"Zapier webhook sent successfully: {response.status}")
                return True

        except Exception as e:
            logger.error(f"Zapier webhook failed: {e}")
            return False

    def send_new_lead(self, lead) -> bool:
        """Send new lead to Zapier."""
        if not self.config.enabled or not self.config.new_lead_hook:
            return False

        data = {
            "event": "new_lead",
            "timestamp": datetime.now().isoformat(),
            "lead": {
                "id": lead.id,
                "name": lead.display_name,
                "email": lead.email,
                "phone": lead.phone,
                "score": lead.score,
                "tier": lead.tier,
                "source": lead.source,
                "notes": lead.notes,
            }
        }

        return self._send_to_webhook(self.config.new_lead_hook, data)

    def send_hot_lead(self, lead) -> bool:
        """Send hot lead alert to Zapier."""
        if not self.config.enabled or not self.config.hot_lead_hook:
            return False

        data = {
            "event": "hot_lead",
            "timestamp": datetime.now().isoformat(),
            "priority": "high",
            "lead": {
                "id": lead.id,
                "name": lead.display_name,
                "email": lead.email,
                "phone": lead.phone,
                "score": lead.score,
                "tier": lead.tier,
                "source": lead.source,
                "notes": lead.notes,
                "profile_url": lead.profile_url,
            }
        }

        return self._send_to_webhook(self.config.hot_lead_hook, data)

    def send_status_change(self, lead, old_status: str, new_status: str) -> bool:
        """Send status change to Zapier."""
        if not self.config.enabled or not self.config.status_change_hook:
            return False

        data = {
            "event": "status_change",
            "timestamp": datetime.now().isoformat(),
            "old_status": old_status,
            "new_status": new_status,
            "lead": {
                "id": lead.id,
                "name": lead.display_name,
                "email": lead.email,
                "phone": lead.phone,
                "score": lead.score,
            }
        }

        return self._send_to_webhook(self.config.status_change_hook, data)

    def send_daily_digest(self, stats: Dict[str, Any], hot_leads: List) -> bool:
        """Send daily digest to Zapier."""
        if not self.config.enabled or not self.config.daily_digest_hook:
            return False

        data = {
            "event": "daily_digest",
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stats": stats,
            "hot_leads": [
                {
                    "name": lead.display_name,
                    "score": lead.score,
                    "source": lead.source,
                }
                for lead in hot_leads[:10]
            ],
        }

        return self._send_to_webhook(self.config.daily_digest_hook, data)


# === Zapier Recipe Examples ===

ZAPIER_RECIPES = """
# Recommended Zapier Recipes for TD Lead Engine

## 1. Hot Lead SMS Alert
Trigger: TD Lead Engine -> Hot Lead Webhook
Action: Twilio -> Send SMS
- Sends you an SMS immediately when a hot lead is detected

## 2. New Lead to Google Sheets
Trigger: TD Lead Engine -> New Lead Webhook
Action: Google Sheets -> Add Row
- Logs all new leads to a Google Sheet for backup/reporting

## 3. Hot Lead to Slack
Trigger: TD Lead Engine -> Hot Lead Webhook
Action: Slack -> Send Channel Message
- Posts hot lead alerts to your team Slack channel

## 4. New Lead to Gmail
Trigger: TD Lead Engine -> New Lead Webhook
Action: Gmail -> Send Email
- Sends yourself an email with new lead details

## 5. Lead to Follow Up Boss
Trigger: TD Lead Engine -> New Lead Webhook
Action: Follow Up Boss -> Create Contact
- Automatically adds leads to Follow Up Boss CRM

## 6. Lead to Google Calendar
Trigger: TD Lead Engine -> Hot Lead Webhook
Action: Google Calendar -> Create Event
- Creates a follow-up reminder on your calendar

## 7. Daily Digest to Email
Trigger: TD Lead Engine -> Daily Digest Webhook
Action: Gmail -> Send Email
- Sends daily lead summary email

## 8. Lead to Mailchimp
Trigger: TD Lead Engine -> New Lead Webhook
Action: Mailchimp -> Add Subscriber
- Adds leads to your Mailchimp nurturing list

## 9. Status Change to Airtable
Trigger: TD Lead Engine -> Status Change Webhook
Action: Airtable -> Update Record
- Keeps Airtable database in sync with lead status

## 10. Hot Lead to Calendly
Trigger: TD Lead Engine -> Hot Lead Webhook
Action: Calendly -> Send Scheduling Link
- Automatically sends scheduling link to hot leads
"""


def print_zapier_setup_guide():
    """Print Zapier setup instructions."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           ZAPIER INTEGRATION SETUP GUIDE                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Step 1: Create Zaps in Zapier                               ║
║  ─────────────────────────────                               ║
║  1. Go to zapier.com and log in                              ║
║  2. Click "Create Zap"                                       ║
║  3. For trigger, search "Webhooks by Zapier"                 ║
║  4. Select "Catch Hook"                                      ║
║  5. Copy the webhook URL provided                            ║
║                                                               ║
║  Step 2: Configure TD Lead Engine                            ║
║  ─────────────────────────────                               ║
║  Run: socialops config zapier                                ║
║  Enter your webhook URLs when prompted                       ║
║                                                               ║
║  Step 3: Test the Integration                                ║
║  ─────────────────────────────                               ║
║  Run: socialops test-zapier                                  ║
║  This sends test data to your webhooks                       ║
║                                                               ║
║  Step 4: Complete Your Zaps                                  ║
║  ─────────────────────────────                               ║
║  Back in Zapier:                                             ║
║  1. Click "Test Trigger" to see your data                    ║
║  2. Add actions (email, SMS, CRM, etc.)                      ║
║  3. Turn on the Zap                                          ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
    print(ZAPIER_RECIPES)
