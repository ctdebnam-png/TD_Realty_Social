"""Slack integration for team notifications."""

import json
import logging
import urllib.request
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Slack configuration."""

    webhook_url: str  # Incoming webhook URL
    channel: Optional[str] = None  # Override channel (optional)
    username: str = "TD Lead Engine"
    icon_emoji: str = ":house:"
    enabled: bool = True


class SlackIntegration:
    """Send notifications to Slack channels."""

    def __init__(self, config: SlackConfig):
        """Initialize Slack integration."""
        self.config = config

    def _send_message(self, payload: Dict[str, Any]) -> bool:
        """Send a message to Slack."""
        if not self.config.enabled:
            return False

        # Add defaults
        payload.setdefault("username", self.config.username)
        payload.setdefault("icon_emoji", self.config.icon_emoji)
        if self.config.channel:
            payload["channel"] = self.config.channel

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Slack message failed: {e}")
            return False

    def send_simple_message(self, text: str) -> bool:
        """Send a simple text message."""
        return self._send_message({"text": text})

    def send_hot_lead_alert(self, lead) -> bool:
        """Send a rich hot lead alert."""
        contact_info = lead.phone or lead.email or "No contact info"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔥 Hot Lead Alert!",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Name:*\n{lead.display_name}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Score:*\n{lead.score} ({lead.tier.upper()})"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Contact:*\n{contact_info}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Source:*\n{lead.source}"
                    }
                ]
            }
        ]

        if lead.notes:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Notes:*\n{lead.notes[:500]}"
                }
            })

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Lead ID: {lead.id} | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                }
            ]
        })

        return self._send_message({"blocks": blocks})

    def send_new_lead_notification(self, lead) -> bool:
        """Send a new lead notification."""
        color = {
            "hot": "#dc2626",
            "warm": "#f59e0b",
            "lukewarm": "#3b82f6",
            "cold": "#6b7280",
            "negative": "#991b1b",
        }.get(lead.tier, "#6b7280")

        attachments = [{
            "color": color,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*New Lead:* {lead.display_name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Score:* {lead.score}"},
                        {"type": "mrkdwn", "text": f"*Tier:* {lead.tier}"},
                        {"type": "mrkdwn", "text": f"*Source:* {lead.source}"},
                    ]
                }
            ]
        }]

        return self._send_message({"attachments": attachments})

    def send_daily_digest(self, stats: Dict[str, Any], hot_leads: List) -> bool:
        """Send daily lead digest."""
        tier_stats = stats.get("by_tier", {})

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📊 Daily Lead Report - {datetime.now().strftime('%B %d, %Y')}",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Total Leads:*\n{stats.get('total_leads', 0)}"},
                    {"type": "mrkdwn", "text": f"*Avg Score:*\n{stats.get('score_avg', 0)}"},
                    {"type": "mrkdwn", "text": f"*🔥 Hot:*\n{tier_stats.get('hot', 0)}"},
                    {"type": "mrkdwn", "text": f"*🌡️ Warm:*\n{tier_stats.get('warm', 0)}"},
                ]
            },
            {"type": "divider"},
        ]

        if hot_leads:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Top Hot Leads:*"
                }
            })

            for lead in hot_leads[:5]:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• *{lead.display_name}* (Score: {lead.score}) - {lead.source}"
                    }
                })

        return self._send_message({"blocks": blocks})

    def send_import_complete(self, source: str, new_count: int, merged_count: int) -> bool:
        """Send import completion notification."""
        return self._send_message({
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"✅ *Import Complete* from `{source}`"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*New Leads:* {new_count}"},
                        {"type": "mrkdwn", "text": f"*Merged:* {merged_count}"},
                    ]
                }
            ]
        })


def setup_slack(webhook_url: str, channel: Optional[str] = None) -> SlackIntegration:
    """Quick setup for Slack integration."""
    config = SlackConfig(
        webhook_url=webhook_url,
        channel=channel,
    )

    integration = SlackIntegration(config)

    # Test with a simple message
    if integration.send_simple_message("🏠 TD Lead Engine connected!"):
        logger.info("Slack integration successful")
        return integration
    else:
        raise ConnectionError("Could not send message to Slack")


def print_slack_setup_guide():
    """Print Slack setup instructions."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              SLACK INTEGRATION SETUP GUIDE                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Step 1: Create Slack App                                    ║
║  ─────────────────────────────                               ║
║  1. Go to api.slack.com/apps                                 ║
║  2. Click "Create New App"                                   ║
║  3. Choose "From scratch"                                    ║
║  4. Name it "TD Lead Engine"                                 ║
║  5. Select your workspace                                    ║
║                                                               ║
║  Step 2: Enable Incoming Webhooks                            ║
║  ─────────────────────────────                               ║
║  1. In app settings, click "Incoming Webhooks"               ║
║  2. Toggle "Activate Incoming Webhooks" ON                   ║
║  3. Click "Add New Webhook to Workspace"                     ║
║  4. Choose a channel for notifications                       ║
║  5. Copy the Webhook URL                                     ║
║                                                               ║
║  Step 3: Configure TD Lead Engine                            ║
║  ─────────────────────────────                               ║
║  Run: socialops config slack                                 ║
║  Paste your webhook URL when prompted                        ║
║                                                               ║
║  Features:                                                   ║
║  ─────────────────────────────                               ║
║  • Hot lead alerts with rich formatting                      ║
║  • Daily digest reports                                      ║
║  • Import completion notifications                           ║
║  • Custom message support                                    ║
║                                                               ║
║  Cost: FREE                                                  ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
