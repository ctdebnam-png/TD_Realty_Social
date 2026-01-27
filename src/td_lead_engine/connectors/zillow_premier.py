"""Zillow Premier Agent API connector."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

from ..storage.models import Lead

logger = logging.getLogger(__name__)


class ZillowPremierConnector:
    """Connect to Zillow Premier Agent for leads.

    Zillow Premier Agent provides high-intent buyer/seller leads.
    Requires Premier Agent subscription and API access.
    """

    def __init__(self):
        """Initialize Zillow Premier connector."""
        self.api_key = os.environ.get("ZILLOW_PREMIER_API_KEY")
        self.partner_id = os.environ.get("ZILLOW_PARTNER_ID")
        self.base_url = "https://api.zillow.com/webservice"

        # Lead types from Zillow
        self.lead_types = {
            "buyer": "buyer_lead",
            "seller": "seller_lead",
            "renter": "renter_lead",
            "landlord": "landlord_lead"
        }

    def get_new_leads(self, since: Optional[datetime] = None) -> List[Lead]:
        """Fetch new leads from Zillow Premier Agent."""
        if not self.api_key or not self.partner_id:
            logger.warning("Zillow Premier Agent credentials not configured")
            return []

        leads = []

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Partner-ID": self.partner_id
            }

            params = {"status": "new"}
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
            logger.error(f"Zillow Premier Agent error: {e}")

        return leads

    def _parse_lead(self, data: Dict[str, Any]) -> Optional[Lead]:
        """Parse Zillow lead data into Lead object."""
        try:
            name = f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
            if not name:
                name = "Zillow Lead"

            bio_parts = []
            if data.get("leadType"):
                bio_parts.append(f"Lead type: {data['leadType']}")
            if data.get("propertyAddress"):
                bio_parts.append(f"Property interest: {data['propertyAddress']}")
            if data.get("priceRange"):
                bio_parts.append(f"Budget: {data['priceRange']}")
            if data.get("timeline"):
                bio_parts.append(f"Timeline: {data['timeline']}")
            if data.get("comments"):
                bio_parts.append(f"Notes: {data['comments']}")

            return Lead(
                name=name,
                email=data.get("email"),
                phone=data.get("phone"),
                bio="\n".join(bio_parts),
                source="zillow_premier",
                source_id=data.get("leadId"),
                followers=0
            )

        except Exception as e:
            logger.error(f"Error parsing Zillow lead: {e}")
            return None

    def acknowledge_lead(self, lead_id: str) -> bool:
        """Acknowledge receipt of a lead."""
        if not self.api_key:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "X-Partner-ID": self.partner_id
            }

            response = requests.post(
                f"{self.base_url}/leads/{lead_id}/acknowledge",
                headers=headers,
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error acknowledging Zillow lead: {e}")
            return False


class ZillowPropertyAPI:
    """Zillow property data API for enrichment.

    Note: Zillow API (ZWSID) has been deprecated.
    This uses available public data endpoints and scraping alternatives.
    Consider using Bridge API or ATTOM as primary property data sources.
    """

    def __init__(self):
        """Initialize Zillow property connector."""
        self.rapidapi_key = os.environ.get("RAPIDAPI_KEY")  # For Zillow scrapers on RapidAPI

    def get_zestimate(self, address: str, city: str, state: str, zip_code: str) -> Optional[Dict[str, Any]]:
        """Get Zestimate for a property.

        Uses RapidAPI Zillow scrapers since official API is deprecated.
        """
        if not self.rapidapi_key:
            logger.warning("RapidAPI key not configured for Zillow data")
            return None

        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
            }

            params = {
                "address": f"{address}, {city}, {state} {zip_code}"
            }

            response = requests.get(
                "https://zillow-com1.p.rapidapi.com/property",
                headers=headers,
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "zestimate": data.get("zestimate"),
                    "rent_zestimate": data.get("rentZestimate"),
                    "bedrooms": data.get("bedrooms"),
                    "bathrooms": data.get("bathrooms"),
                    "living_area": data.get("livingArea"),
                    "year_built": data.get("yearBuilt"),
                    "lot_size": data.get("lotSize"),
                    "property_type": data.get("propertyType"),
                    "last_sold_price": data.get("lastSoldPrice"),
                    "last_sold_date": data.get("lastSoldDate")
                }

        except Exception as e:
            logger.error(f"Zillow property API error: {e}")

        return None

    def search_properties(
        self,
        city: str,
        state: str,
        min_price: int = 0,
        max_price: int = 10000000,
        beds_min: int = 0,
        status: str = "forSale"
    ) -> List[Dict[str, Any]]:
        """Search for properties on Zillow."""
        if not self.rapidapi_key:
            return []

        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
            }

            params = {
                "location": f"{city}, {state}",
                "status": status,
                "price_min": min_price,
                "price_max": max_price,
                "beds_min": beds_min
            }

            response = requests.get(
                "https://zillow-com1.p.rapidapi.com/propertyExtendedSearch",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("props", [])

        except Exception as e:
            logger.error(f"Zillow search error: {e}")

        return []
