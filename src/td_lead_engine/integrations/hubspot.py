"""HubSpot CRM integration for lead sync."""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HubSpotConfig:
    """HubSpot configuration."""

    api_key: str
    portal_id: Optional[str] = None
    sync_enabled: bool = True
    sync_direction: str = "bidirectional"  # "to_hubspot", "from_hubspot", "bidirectional"

    # Field mappings: TD Lead Engine -> HubSpot property
    field_mappings: Dict[str, str] = None

    def __post_init__(self):
        if self.field_mappings is None:
            self.field_mappings = {
                "name": "firstname",  # HubSpot splits first/last
                "email": "email",
                "phone": "phone",
                "notes": "hs_lead_status",
                "score": "leadscore",  # Custom property
                "tier": "td_tier",  # Custom property
                "source": "hs_analytics_source",
            }


class HubSpotIntegration:
    """Sync leads with HubSpot CRM."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self, config: HubSpotConfig):
        """Initialize HubSpot integration."""
        self.config = config
        self._headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an API request to HubSpot."""
        url = f"{self.BASE_URL}{endpoint}"

        request_data = json.dumps(data).encode() if data else None

        req = urllib.request.Request(
            url,
            data=request_data,
            headers=self._headers,
            method=method
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ""
            logger.error(f"HubSpot API error: {e.code} - {error_body}")
            raise
        except Exception as e:
            logger.error(f"HubSpot request failed: {e}")
            raise

    def test_connection(self) -> bool:
        """Test the HubSpot API connection."""
        try:
            self._request("GET", "/crm/v3/objects/contacts?limit=1")
            return True
        except Exception:
            return False

    def sync_lead_to_hubspot(self, lead) -> Optional[str]:
        """Sync a lead to HubSpot. Returns HubSpot contact ID."""
        # Prepare properties
        properties = {}

        # Map fields
        if lead.name:
            # Split name into first/last
            parts = lead.name.split(" ", 1)
            properties["firstname"] = parts[0]
            if len(parts) > 1:
                properties["lastname"] = parts[1]

        if lead.email:
            properties["email"] = lead.email
        if lead.phone:
            properties["phone"] = lead.phone

        # Custom properties (need to be created in HubSpot first)
        properties["td_score"] = str(lead.score)
        properties["td_tier"] = lead.tier
        properties["td_source"] = lead.source

        # Check if contact exists
        existing_id = self._find_contact(lead.email) if lead.email else None

        if existing_id:
            # Update existing contact
            self._request(
                "PATCH",
                f"/crm/v3/objects/contacts/{existing_id}",
                {"properties": properties}
            )
            logger.info(f"Updated HubSpot contact: {existing_id}")
            return existing_id
        else:
            # Create new contact
            result = self._request(
                "POST",
                "/crm/v3/objects/contacts",
                {"properties": properties}
            )
            contact_id = result.get("id")
            logger.info(f"Created HubSpot contact: {contact_id}")
            return contact_id

    def _find_contact(self, email: str) -> Optional[str]:
        """Find a HubSpot contact by email."""
        try:
            result = self._request(
                "POST",
                "/crm/v3/objects/contacts/search",
                {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email
                        }]
                    }]
                }
            )
            results = result.get("results", [])
            if results:
                return results[0].get("id")
        except Exception:
            pass
        return None

    def get_contacts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get contacts from HubSpot."""
        result = self._request(
            "GET",
            f"/crm/v3/objects/contacts?limit={limit}&properties=firstname,lastname,email,phone"
        )
        return result.get("results", [])

    def sync_from_hubspot(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get contacts from HubSpot to import as leads."""
        contacts = self.get_contacts(limit)

        leads_data = []
        for contact in contacts:
            props = contact.get("properties", {})
            leads_data.append({
                "hubspot_id": contact.get("id"),
                "name": f"{props.get('firstname', '')} {props.get('lastname', '')}".strip(),
                "email": props.get("email"),
                "phone": props.get("phone"),
            })

        return leads_data

    def create_custom_properties(self):
        """Create custom properties in HubSpot for TD Lead Engine fields."""
        custom_props = [
            {
                "name": "td_score",
                "label": "TD Lead Score",
                "type": "number",
                "fieldType": "number",
                "groupName": "contactinformation",
            },
            {
                "name": "td_tier",
                "label": "TD Lead Tier",
                "type": "enumeration",
                "fieldType": "select",
                "groupName": "contactinformation",
                "options": [
                    {"label": "Hot", "value": "hot"},
                    {"label": "Warm", "value": "warm"},
                    {"label": "Lukewarm", "value": "lukewarm"},
                    {"label": "Cold", "value": "cold"},
                    {"label": "Negative", "value": "negative"},
                ]
            },
            {
                "name": "td_source",
                "label": "TD Lead Source",
                "type": "string",
                "fieldType": "text",
                "groupName": "contactinformation",
            },
        ]

        for prop in custom_props:
            try:
                self._request(
                    "POST",
                    "/crm/v3/properties/contacts",
                    prop
                )
                logger.info(f"Created HubSpot property: {prop['name']}")
            except urllib.error.HTTPError as e:
                if e.code == 409:  # Conflict - already exists
                    logger.info(f"HubSpot property already exists: {prop['name']}")
                else:
                    raise


def setup_hubspot(api_key: str) -> HubSpotIntegration:
    """Quick setup for HubSpot integration."""
    config = HubSpotConfig(api_key=api_key)
    integration = HubSpotIntegration(config)

    if integration.test_connection():
        logger.info("HubSpot connection successful")
        # Create custom properties
        try:
            integration.create_custom_properties()
        except Exception as e:
            logger.warning(f"Could not create custom properties: {e}")
        return integration
    else:
        raise ConnectionError("Could not connect to HubSpot API")
