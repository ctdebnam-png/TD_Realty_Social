"""Skip tracing and contact enrichment services."""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

import requests

logger = logging.getLogger(__name__)


@dataclass
class SkipTraceResult:
    """Result from skip trace lookup."""

    # Search input
    input_name: str
    input_address: str

    # Contact info found
    phones: List[Dict[str, str]]  # [{"number": "...", "type": "mobile", "carrier": "..."}]
    emails: List[str]

    # Verified addresses
    current_address: Optional[str]
    previous_addresses: List[str]

    # Demographics
    age_range: Optional[str]
    gender: Optional[str]
    marital_status: Optional[str]

    # Financial indicators
    estimated_income: Optional[str]
    home_value: Optional[int]
    length_of_residence: Optional[int]  # years

    # Associated people
    relatives: List[Dict[str, str]]  # [{"name": "...", "relationship": "..."}]
    associates: List[str]

    # Property ownership
    properties_owned: List[Dict[str, Any]]

    # Confidence
    match_score: float
    data_source: str


class BatchSkipTraceConnector:
    """BatchSkipTrace.com API connector.

    Affordable skip tracing for real estate investors and agents.
    Typical cost: $0.15-0.25 per record.
    """

    def __init__(self):
        """Initialize BatchSkipTrace connector."""
        self.api_key = os.environ.get("BATCHSKIPTRACE_API_KEY")
        self.base_url = "https://api.batchskiptrace.com/v1"

    def trace_by_address(self, address: str, city: str, state: str, zip_code: str) -> Optional[SkipTraceResult]:
        """Skip trace by property address."""
        if not self.api_key:
            logger.warning("BatchSkipTrace API key not configured")
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "address": address,
                "city": city,
                "state": state,
                "zip": zip_code
            }

            response = requests.post(
                f"{self.base_url}/search/address",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return self._parse_result(response.json(), address)

        except Exception as e:
            logger.error(f"BatchSkipTrace error: {e}")

        return None

    def trace_by_name(
        self,
        first_name: str,
        last_name: str,
        city: Optional[str] = None,
        state: Optional[str] = None
    ) -> Optional[SkipTraceResult]:
        """Skip trace by name."""
        if not self.api_key:
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "firstName": first_name,
                "lastName": last_name
            }
            if city:
                payload["city"] = city
            if state:
                payload["state"] = state

            response = requests.post(
                f"{self.base_url}/search/name",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return self._parse_result(response.json(), f"{first_name} {last_name}")

        except Exception as e:
            logger.error(f"BatchSkipTrace error: {e}")

        return None

    def batch_trace(self, records: List[Dict[str, str]]) -> List[SkipTraceResult]:
        """Batch skip trace multiple records.

        Each record should have: address, city, state, zip
        or: firstName, lastName, city, state
        """
        if not self.api_key:
            return []

        results = []

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(
                f"{self.base_url}/batch",
                headers=headers,
                json={"records": records},
                timeout=120
            )

            if response.status_code == 200:
                data = response.json()
                for result_data in data.get("results", []):
                    result = self._parse_result(result_data, result_data.get("input", ""))
                    if result:
                        results.append(result)

        except Exception as e:
            logger.error(f"BatchSkipTrace batch error: {e}")

        return results

    def _parse_result(self, data: Dict[str, Any], input_ref: str) -> Optional[SkipTraceResult]:
        """Parse API response into SkipTraceResult."""
        try:
            phones = []
            for phone in data.get("phones", []):
                phones.append({
                    "number": phone.get("number"),
                    "type": phone.get("type", "unknown"),
                    "carrier": phone.get("carrier"),
                    "is_mobile": phone.get("lineType") == "mobile"
                })

            return SkipTraceResult(
                input_name=data.get("name", ""),
                input_address=input_ref,
                phones=phones,
                emails=data.get("emails", []),
                current_address=data.get("currentAddress"),
                previous_addresses=data.get("previousAddresses", []),
                age_range=data.get("ageRange"),
                gender=data.get("gender"),
                marital_status=data.get("maritalStatus"),
                estimated_income=data.get("estimatedIncome"),
                home_value=data.get("homeValue"),
                length_of_residence=data.get("lengthOfResidence"),
                relatives=data.get("relatives", []),
                associates=data.get("associates", []),
                properties_owned=data.get("propertiesOwned", []),
                match_score=data.get("matchScore", 0.0),
                data_source="batchskiptrace"
            )

        except Exception as e:
            logger.error(f"Error parsing skip trace result: {e}")
            return None


class REISkipConnector:
    """REI Skip (REISkip.com) connector.

    Popular skip tracing for real estate investors.
    Includes property data and owner contact info.
    """

    def __init__(self):
        """Initialize REISkip connector."""
        self.api_key = os.environ.get("REISKIP_API_KEY")
        self.base_url = "https://api.reiskip.com/v2"

    def lookup_property(self, address: str, city: str, state: str, zip_code: str) -> Optional[Dict[str, Any]]:
        """Look up property owner info."""
        if not self.api_key:
            logger.warning("REISkip API key not configured")
            return None

        try:
            headers = {"X-API-Key": self.api_key}

            params = {
                "address": address,
                "city": city,
                "state": state,
                "zip": zip_code
            }

            response = requests.get(
                f"{self.base_url}/property",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "owner_name": data.get("ownerName"),
                    "owner_type": data.get("ownerType"),  # individual, trust, llc, etc.
                    "mailing_address": data.get("mailingAddress"),
                    "phones": data.get("phones", []),
                    "emails": data.get("emails", []),
                    "property_value": data.get("estimatedValue"),
                    "equity_estimate": data.get("equityEstimate"),
                    "purchase_date": data.get("purchaseDate"),
                    "purchase_price": data.get("purchasePrice"),
                    "is_owner_occupied": data.get("isOwnerOccupied"),
                    "is_absentee": data.get("isAbsentee"),
                    "mortgage_balance": data.get("mortgageBalance"),
                    "foreclosure_status": data.get("foreclosureStatus")
                }

        except Exception as e:
            logger.error(f"REISkip error: {e}")

        return None


class PropStreamConnector:
    """PropStream property data and skip tracing.

    Comprehensive real estate data platform.
    Includes property data, owner info, and comps.
    """

    def __init__(self):
        """Initialize PropStream connector."""
        self.api_key = os.environ.get("PROPSTREAM_API_KEY")
        self.base_url = "https://api.propstream.com/v1"

    def search_motivated_sellers(
        self,
        city: str,
        state: str,
        criteria: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for motivated seller leads.

        Criteria can include:
        - pre_foreclosure: bool
        - high_equity: bool (50%+)
        - absentee_owner: bool
        - vacant: bool
        - divorce: bool
        - probate: bool
        - tax_lien: bool
        - code_violation: bool
        - tired_landlord: bool (long-term rentals)
        - free_clear: bool (no mortgage)
        """
        if not self.api_key:
            logger.warning("PropStream API key not configured")
            return []

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            payload = {
                "location": {"city": city, "state": state},
                "filters": criteria or {}
            }

            response = requests.post(
                f"{self.base_url}/search/motivated-sellers",
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("properties", [])

        except Exception as e:
            logger.error(f"PropStream search error: {e}")

        return []

    def get_owner_info(self, property_id: str) -> Optional[Dict[str, Any]]:
        """Get owner contact information."""
        if not self.api_key:
            return None

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(
                f"{self.base_url}/property/{property_id}/owner",
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"PropStream owner info error: {e}")

        return None

    def get_comps(self, address: str, city: str, state: str, zip_code: str) -> List[Dict[str, Any]]:
        """Get comparable sales for a property."""
        if not self.api_key:
            return []

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            params = {
                "address": address,
                "city": city,
                "state": state,
                "zip": zip_code,
                "radius_miles": 0.5,
                "months_back": 6,
                "limit": 10
            }

            response = requests.get(
                f"{self.base_url}/comps",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("comparables", [])

        except Exception as e:
            logger.error(f"PropStream comps error: {e}")

        return []
