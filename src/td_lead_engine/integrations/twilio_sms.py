"""Twilio SMS integration for lead notifications and outreach."""

import json
import logging
import base64
import urllib.request
import urllib.error
import urllib.parse
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TwilioConfig:
    """Twilio configuration."""

    account_sid: str
    auth_token: str
    from_number: str  # Your Twilio phone number
    enabled: bool = True

    # Optional settings
    notify_numbers: List[str] = None  # Numbers to receive alerts
    templates: Dict[str, str] = None  # SMS templates

    def __post_init__(self):
        if self.notify_numbers is None:
            self.notify_numbers = []
        if self.templates is None:
            self.templates = {
                "hot_lead_alert": (
                    "🔥 HOT LEAD: {name}\n"
                    "Score: {score}\n"
                    "Contact: {contact}\n"
                    "Source: {source}"
                ),
                "new_lead": (
                    "New lead: {name}\n"
                    "Score: {score} ({tier})\n"
                    "Source: {source}"
                ),
                "daily_digest": (
                    "Daily Lead Summary:\n"
                    "Total: {total}\n"
                    "Hot: {hot}\n"
                    "Warm: {warm}\n"
                    "Top lead: {top_lead}"
                ),
            }


class TwilioSMSIntegration:
    """Send SMS notifications via Twilio."""

    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self, config: TwilioConfig):
        """Initialize Twilio integration."""
        self.config = config
        self._auth = base64.b64encode(
            f"{config.account_sid}:{config.auth_token}".encode()
        ).decode()

    def _send_sms(self, to: str, body: str) -> Dict[str, Any]:
        """Send an SMS message."""
        url = f"{self.BASE_URL}/Accounts/{self.config.account_sid}/Messages.json"

        data = urllib.parse.urlencode({
            "To": to,
            "From": self.config.from_number,
            "Body": body,
        }).encode()

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Basic {self._auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                logger.info(f"SMS sent to {to}: {result.get('sid')}")
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            logger.error(f"Twilio API error: {e.code} - {error_body}")
            raise
        except Exception as e:
            logger.error(f"Twilio request failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Test Twilio connection by checking account."""
        url = f"{self.BASE_URL}/Accounts/{self.config.account_sid}.json"

        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Basic {self._auth}"},
            method="GET"
        )

        try:
            with urllib.request.urlopen(req, timeout=30):
                return True
        except Exception:
            return False

    def send_hot_lead_alert(self, lead) -> List[Dict[str, Any]]:
        """Send hot lead alert to all notify numbers."""
        if not self.config.enabled:
            return []

        template = self.config.templates.get("hot_lead_alert", "Hot lead: {name}")
        contact = lead.phone or lead.email or "No contact"

        message = template.format(
            name=lead.display_name,
            score=lead.score,
            contact=contact,
            source=lead.source,
            tier=lead.tier,
        )

        results = []
        for number in self.config.notify_numbers:
            try:
                result = self._send_sms(number, message)
                results.append({"number": number, "success": True, "sid": result.get("sid")})
            except Exception as e:
                results.append({"number": number, "success": False, "error": str(e)})

        return results

    def send_new_lead_alert(self, lead) -> List[Dict[str, Any]]:
        """Send new lead notification."""
        if not self.config.enabled:
            return []

        template = self.config.templates.get("new_lead", "New lead: {name}")

        message = template.format(
            name=lead.display_name,
            score=lead.score,
            tier=lead.tier,
            source=lead.source,
        )

        results = []
        for number in self.config.notify_numbers:
            try:
                result = self._send_sms(number, message)
                results.append({"number": number, "success": True, "sid": result.get("sid")})
            except Exception as e:
                results.append({"number": number, "success": False, "error": str(e)})

        return results

    def send_daily_digest(self, stats: Dict[str, Any], top_lead_name: str) -> List[Dict[str, Any]]:
        """Send daily digest SMS."""
        if not self.config.enabled:
            return []

        template = self.config.templates.get("daily_digest", "Daily: {total} leads")

        message = template.format(
            total=stats.get("total_leads", 0),
            hot=stats.get("by_tier", {}).get("hot", 0),
            warm=stats.get("by_tier", {}).get("warm", 0),
            top_lead=top_lead_name,
        )

        results = []
        for number in self.config.notify_numbers:
            try:
                result = self._send_sms(number, message)
                results.append({"number": number, "success": True, "sid": result.get("sid")})
            except Exception as e:
                results.append({"number": number, "success": False, "error": str(e)})

        return results

    def send_custom_sms(self, to: str, message: str) -> Dict[str, Any]:
        """Send a custom SMS to a specific number."""
        if not self.config.enabled:
            return {"error": "SMS disabled"}

        return self._send_sms(to, message)

    def send_to_lead(self, lead, template_name: str) -> Optional[Dict[str, Any]]:
        """Send SMS to a lead using a template."""
        if not self.config.enabled:
            return None

        if not lead.phone:
            logger.warning(f"Lead {lead.id} has no phone number")
            return None

        template = self.config.templates.get(template_name)
        if not template:
            logger.warning(f"Template not found: {template_name}")
            return None

        message = template.format(
            name=lead.name or "there",
            score=lead.score,
            tier=lead.tier,
        )

        return self._send_sms(lead.phone, message)


def setup_twilio(
    account_sid: str,
    auth_token: str,
    from_number: str,
    notify_numbers: List[str]
) -> TwilioSMSIntegration:
    """Quick setup for Twilio integration."""
    config = TwilioConfig(
        account_sid=account_sid,
        auth_token=auth_token,
        from_number=from_number,
        notify_numbers=notify_numbers,
    )

    integration = TwilioSMSIntegration(config)

    if integration.test_connection():
        logger.info("Twilio connection successful")
        return integration
    else:
        raise ConnectionError("Could not connect to Twilio API")


def print_twilio_setup_guide():
    """Print Twilio setup instructions."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              TWILIO SMS SETUP GUIDE                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Step 1: Create Twilio Account                               ║
║  ─────────────────────────────                               ║
║  1. Go to twilio.com and sign up                             ║
║  2. Free trial includes $15 credit                           ║
║  3. Verify your phone number                                 ║
║                                                               ║
║  Step 2: Get Your Credentials                                ║
║  ─────────────────────────────                               ║
║  From your Twilio Console:                                   ║
║  • Account SID (starts with AC...)                           ║
║  • Auth Token                                                ║
║  • Phone Number (your Twilio number)                         ║
║                                                               ║
║  Step 3: Configure TD Lead Engine                            ║
║  ─────────────────────────────                               ║
║  Run: socialops config twilio                                ║
║  Enter your credentials when prompted                        ║
║                                                               ║
║  Step 4: Add Alert Numbers                                   ║
║  ─────────────────────────────                               ║
║  Add numbers to receive hot lead alerts:                     ║
║  socialops config twilio --add-number +16145551234           ║
║                                                               ║
║  Pricing:                                                    ║
║  ─────────────────────────────                               ║
║  • ~$0.0075 per SMS sent                                     ║
║  • ~$1/month for phone number                                ║
║  • Free trial: $15 credit (≈2000 messages)                   ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
