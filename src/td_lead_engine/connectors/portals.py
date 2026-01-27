"""Real estate portal lead connectors (Realtor.com, Redfin, etc.)."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

from ..storage.models import Lead

logger = logging.getLogger(__name__)


class RealtorDotComConnector:
    """Realtor.com lead connector.

    Realtor.com provides leads through:
    1. Connections Plus (subscription leads)
    2. ReadyConnect Concierge (live transfer)
    3. Listing leads (from your listings)

    This connects to their Partner API.
    """

    def __init__(self):
        """Initialize Realtor.com connector."""
        self.api_key = os.environ.get("REALTOR_API_KEY")
        self.partner_id = os.environ.get("REALTOR_PARTNER_ID")
        self.base_url = "https://api.realtor.com/v1"

    def get_new_leads(self, since: Optional[datetime] = None) -> List[Lead]:
        """Fetch new leads from Realtor.com."""
        if not self.api_key or not self.partner_id:
            logger.warning("Realtor.com credentials not configured")
            return []

        leads = []

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Partner-ID": self.partner_id
            }

            params = {"status": "new", "limit": 50}
            if since:
                params["since"] = since.isoformat()

            response = requests.get(
                f"{self.base_url}/leads",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                for lead_data in data.get("leads", []):
                    lead = self._parse_lead(lead_data)
                    if lead:
                        leads.append(lead)

        except Exception as e:
            logger.error(f"Realtor.com API error: {e}")

        return leads

    def _parse_lead(self, data: Dict[str, Any]) -> Optional[Lead]:
        """Parse Realtor.com lead into Lead object."""
        try:
            name = data.get("name") or f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
            if not name:
                name = "Realtor.com Lead"

            bio_parts = []
            if data.get("propertyAddress"):
                bio_parts.append(f"Interested in: {data['propertyAddress']}")
            if data.get("priceRange"):
                bio_parts.append(f"Budget: {data['priceRange']}")
            if data.get("moveInDate"):
                bio_parts.append(f"Move-in: {data['moveInDate']}")
            if data.get("leadType"):
                bio_parts.append(f"Type: {data['leadType']}")
            if data.get("message"):
                bio_parts.append(f"Message: {data['message']}")

            return Lead(
                name=name,
                email=data.get("email"),
                phone=data.get("phone"),
                bio="\n".join(bio_parts),
                source="realtor.com",
                source_id=data.get("leadId")
            )

        except Exception as e:
            logger.error(f"Error parsing Realtor.com lead: {e}")
            return None


class RedfinConnector:
    """Redfin Partner Agent lead connector.

    Redfin refers leads to partner agents in areas they don't cover directly.
    Leads come via email webhook or partner portal API.
    """

    def __init__(self):
        """Initialize Redfin connector."""
        self.api_key = os.environ.get("REDFIN_PARTNER_KEY")
        self.agent_id = os.environ.get("REDFIN_AGENT_ID")
        self.base_url = "https://partner-api.redfin.com/v1"

    def get_new_leads(self) -> List[Lead]:
        """Fetch new leads from Redfin partner portal."""
        if not self.api_key or not self.agent_id:
            logger.warning("Redfin partner credentials not configured")
            return []

        leads = []

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(
                f"{self.base_url}/agents/{self.agent_id}/leads",
                headers=headers,
                params={"status": "new"},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                for lead_data in data.get("leads", []):
                    lead = self._parse_lead(lead_data)
                    if lead:
                        leads.append(lead)

        except Exception as e:
            logger.error(f"Redfin API error: {e}")

        return leads

    def parse_email_webhook(self, email_content: str) -> Optional[Lead]:
        """Parse Redfin lead email into Lead object.

        Redfin sends lead notifications via email.
        This parses the email content.
        """
        # This would parse the Redfin email format
        # For now, return None as this needs actual email parsing
        return None

    def _parse_lead(self, data: Dict[str, Any]) -> Optional[Lead]:
        """Parse Redfin lead data."""
        try:
            bio_parts = []
            if data.get("searchCriteria"):
                criteria = data["searchCriteria"]
                if criteria.get("locations"):
                    bio_parts.append(f"Looking in: {', '.join(criteria['locations'])}")
                if criteria.get("priceMax"):
                    bio_parts.append(f"Max price: ${criteria['priceMax']:,}")
                if criteria.get("beds"):
                    bio_parts.append(f"Bedrooms: {criteria['beds']}+")

            if data.get("savedHomes"):
                bio_parts.append(f"Saved {len(data['savedHomes'])} homes on Redfin")

            if data.get("tourRequests"):
                bio_parts.append(f"Requested {len(data['tourRequests'])} tours")

            return Lead(
                name=data.get("name", "Redfin Lead"),
                email=data.get("email"),
                phone=data.get("phone"),
                bio="\n".join(bio_parts),
                source="redfin",
                source_id=data.get("id")
            )

        except Exception as e:
            logger.error(f"Error parsing Redfin lead: {e}")
            return None


class HomesDotComConnector:
    """Homes.com lead connector."""

    def __init__(self):
        """Initialize Homes.com connector."""
        self.api_key = os.environ.get("HOMES_API_KEY")
        self.base_url = "https://api.homes.com/v1"

    def get_new_leads(self) -> List[Lead]:
        """Fetch leads from Homes.com."""
        if not self.api_key:
            logger.warning("Homes.com API key not configured")
            return []

        # Implementation would connect to Homes.com API
        return []


class TruliaConnector:
    """Trulia lead connector.

    Note: Trulia is owned by Zillow Group, leads often come
    through Zillow Premier Agent as combined package.
    """

    def __init__(self):
        """Initialize Trulia connector."""
        # Trulia leads typically come through Zillow integration
        pass


class HomeLightConnector:
    """HomeLight referral lead connector.

    HomeLight matches agents with buyers/sellers based on
    performance metrics. Leads are typically pre-qualified.
    """

    def __init__(self):
        """Initialize HomeLight connector."""
        self.api_key = os.environ.get("HOMELIGHT_API_KEY")
        self.agent_id = os.environ.get("HOMELIGHT_AGENT_ID")
        self.base_url = "https://api.homelight.com/v1"

    def get_referrals(self) -> List[Dict[str, Any]]:
        """Get referral leads from HomeLight."""
        if not self.api_key or not self.agent_id:
            logger.warning("HomeLight credentials not configured")
            return []

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(
                f"{self.base_url}/agents/{self.agent_id}/referrals",
                headers=headers,
                params={"status": "active"},
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get("referrals", [])

        except Exception as e:
            logger.error(f"HomeLight API error: {e}")

        return []

    def accept_referral(self, referral_id: str) -> bool:
        """Accept a HomeLight referral."""
        if not self.api_key:
            return False

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.post(
                f"{self.base_url}/referrals/{referral_id}/accept",
                headers=headers,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error accepting HomeLight referral: {e}")
            return False


class OPCityConnector:
    """OPCity (now part of Realtor.com) lead connector.

    OPCity provides AI-qualified leads with live transfer.
    Higher cost but higher quality/intent.
    """

    def __init__(self):
        """Initialize OPCity connector."""
        self.api_key = os.environ.get("OPCITY_API_KEY")
        self.base_url = "https://api.opcity.com/v1"

    def get_leads(self) -> List[Lead]:
        """Get leads from OPCity."""
        if not self.api_key:
            logger.warning("OPCity API key not configured")
            return []

        # Implementation would connect to OPCity API
        return []


class UpNestConnector:
    """UpNest agent matching platform connector.

    UpNest connects buyers/sellers with competing agents.
    Leads are typically high-intent but competitive.
    """

    def __init__(self):
        """Initialize UpNest connector."""
        self.api_key = os.environ.get("UPNEST_API_KEY")
        self.base_url = "https://api.upnest.com/v1"

    def get_opportunities(self) -> List[Dict[str, Any]]:
        """Get matching opportunities from UpNest."""
        if not self.api_key:
            return []

        # Implementation would connect to UpNest API
        return []


class AgentPromoConnector:
    """Agent Promo lead connector.

    Aggregates leads from various sources including
    social media, listing sites, and direct campaigns.
    """

    def __init__(self):
        """Initialize Agent Promo connector."""
        self.api_key = os.environ.get("AGENTPROMO_API_KEY")

    def get_leads(self) -> List[Lead]:
        """Get leads from Agent Promo."""
        if not self.api_key:
            return []

        # Implementation would connect to Agent Promo API
        return []


# Unified portal connector
class PortalLeadAggregator:
    """Aggregate leads from multiple portals."""

    def __init__(self):
        """Initialize all portal connectors."""
        self.connectors = {
            "realtor.com": RealtorDotComConnector(),
            "redfin": RedfinConnector(),
            "homes.com": HomesDotComConnector(),
            "homelight": HomeLightConnector(),
            "opcity": OPCityConnector(),
        }

    def fetch_all_leads(self, since: Optional[datetime] = None) -> Dict[str, List[Lead]]:
        """Fetch leads from all configured portals."""
        all_leads = {}

        for name, connector in self.connectors.items():
            try:
                if hasattr(connector, 'get_new_leads'):
                    leads = connector.get_new_leads()
                else:
                    leads = []

                all_leads[name] = leads
                logger.info(f"Fetched {len(leads)} leads from {name}")

            except Exception as e:
                logger.error(f"Error fetching from {name}: {e}")
                all_leads[name] = []

        return all_leads

    def get_configured_sources(self) -> List[str]:
        """Get list of configured/active sources."""
        configured = []

        for name, connector in self.connectors.items():
            # Check if connector has credentials configured
            if hasattr(connector, 'api_key') and connector.api_key:
                configured.append(name)

        return configured
