"""Property data enrichment from multiple sources."""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


@dataclass
class PropertyData:
    """Enriched property information."""

    # Address
    address: str
    city: str
    state: str = "OH"
    zip_code: str = ""
    county: str = ""

    # Property details
    property_type: str = ""  # single_family, condo, townhouse, multi_family
    bedrooms: int = 0
    bathrooms: float = 0
    square_feet: int = 0
    lot_size_sqft: int = 0
    year_built: int = 0
    stories: int = 0
    garage_spaces: int = 0

    # Valuation
    estimated_value: int = 0
    value_low: int = 0
    value_high: int = 0
    last_sale_price: int = 0
    last_sale_date: Optional[str] = None
    price_per_sqft: int = 0

    # Tax info
    tax_assessed_value: int = 0
    annual_taxes: int = 0
    tax_year: int = 0

    # Mortgage info
    mortgage_amount: Optional[int] = None
    mortgage_date: Optional[str] = None
    estimated_equity: Optional[int] = None

    # Owner info
    owner_name: Optional[str] = None
    owner_occupied: bool = True
    ownership_length_years: Optional[int] = None

    # Features
    features: List[str] = field(default_factory=list)
    pool: bool = False
    basement: bool = False
    fireplace: bool = False

    # School info
    school_district: str = ""
    elementary_school: str = ""
    middle_school: str = ""
    high_school: str = ""
    school_rating: Optional[float] = None

    # Neighborhood
    neighborhood: str = ""
    walk_score: Optional[int] = None
    transit_score: Optional[int] = None
    crime_rating: Optional[str] = None

    # Market context
    days_on_market_avg: Optional[int] = None
    list_to_sale_ratio: Optional[float] = None

    # Metadata
    data_source: str = ""
    enriched_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 0.0


class PropertyEnrichment:
    """Enrich property data from multiple sources."""

    def __init__(self):
        """Initialize property enrichment."""
        self.attom_api_key = os.environ.get("ATTOM_API_KEY")
        self.google_api_key = os.environ.get("GOOGLE_API_KEY")
        self.walkscore_api_key = os.environ.get("WALKSCORE_API_KEY")

        # Central Ohio specific data
        self.ohio_counties = {
            "franklin": ["Columbus", "Dublin", "Westerville", "Gahanna", "Reynoldsburg",
                        "Grove City", "Hilliard", "Upper Arlington", "Grandview Heights",
                        "Bexley", "Whitehall", "Worthington"],
            "delaware": ["Delaware", "Powell", "Lewis Center", "Sunbury", "Galena"],
            "licking": ["Newark", "Granville", "Heath", "Pataskala", "Johnstown"],
            "fairfield": ["Lancaster", "Pickerington", "Canal Winchester"],
            "union": ["Marysville", "Dublin"],
            "madison": ["London", "Plain City"],
            "pickaway": ["Circleville", "Ashville"],
        }

        self.school_districts = {
            "dublin": {"rating": 9.2, "district": "Dublin City Schools"},
            "powell": {"rating": 9.0, "district": "Olentangy Local Schools"},
            "westerville": {"rating": 8.5, "district": "Westerville City Schools"},
            "new albany": {"rating": 9.5, "district": "New Albany-Plain Local"},
            "upper arlington": {"rating": 9.3, "district": "Upper Arlington City Schools"},
            "grandview heights": {"rating": 8.8, "district": "Grandview Heights City Schools"},
            "bexley": {"rating": 9.1, "district": "Bexley City Schools"},
            "worthington": {"rating": 8.7, "district": "Worthington City Schools"},
            "hilliard": {"rating": 8.4, "district": "Hilliard City Schools"},
            "gahanna": {"rating": 8.2, "district": "Gahanna-Jefferson City Schools"},
            "pickerington": {"rating": 8.3, "district": "Pickerington Local Schools"},
            "grove city": {"rating": 7.5, "district": "South-Western City Schools"},
            "lewis center": {"rating": 9.0, "district": "Olentangy Local Schools"},
        }

    def enrich_by_address(self, address: str, city: str, state: str = "OH") -> PropertyData:
        """Enrich property data by address."""
        property_data = PropertyData(address=address, city=city, state=state)

        # Determine county
        city_lower = city.lower()
        for county, cities in self.ohio_counties.items():
            if any(c.lower() == city_lower for c in cities):
                property_data.county = county.title()
                break

        # Add school district info
        if city_lower in self.school_districts:
            sd = self.school_districts[city_lower]
            property_data.school_district = sd["district"]
            property_data.school_rating = sd["rating"]

        # Try ATTOM API if available
        if self.attom_api_key:
            attom_data = self._fetch_attom_data(address, city, state)
            if attom_data:
                property_data = self._merge_attom_data(property_data, attom_data)

        # Try Franklin County Auditor (free public data)
        if property_data.county.lower() == "franklin":
            auditor_data = self._fetch_franklin_county_data(address)
            if auditor_data:
                property_data = self._merge_auditor_data(property_data, auditor_data)

        # Add Walk Score if available
        if self.walkscore_api_key:
            walk_data = self._fetch_walk_score(address, city, state)
            if walk_data:
                property_data.walk_score = walk_data.get("walkscore")
                property_data.transit_score = walk_data.get("transit", {}).get("score")

        # Calculate confidence based on data completeness
        property_data.confidence_score = self._calculate_confidence(property_data)

        return property_data

    def estimate_value(self, property_data: PropertyData) -> Dict[str, Any]:
        """Estimate property value using available data."""
        # Base estimate using price per sqft for area
        area_ppsf = self._get_area_price_per_sqft(property_data.city)

        base_value = property_data.square_feet * area_ppsf if property_data.square_feet else 0

        # Adjustments
        adjustments = []

        # Age adjustment
        if property_data.year_built:
            age = datetime.now().year - property_data.year_built
            if age < 5:
                adjustment = 1.05
                adjustments.append(("New construction", "+5%"))
            elif age < 20:
                adjustment = 1.02
                adjustments.append(("Modern home", "+2%"))
            elif age > 50:
                adjustment = 0.95
                adjustments.append(("Older home", "-5%"))
            else:
                adjustment = 1.0
            base_value *= adjustment

        # Bedroom adjustment
        if property_data.bedrooms >= 4:
            base_value *= 1.03
            adjustments.append(("4+ bedrooms", "+3%"))
        elif property_data.bedrooms < 3:
            base_value *= 0.97
            adjustments.append(("Under 3 bedrooms", "-3%"))

        # Features
        if property_data.pool:
            base_value += 25000
            adjustments.append(("Pool", "+$25K"))
        if property_data.basement:
            base_value += 15000
            adjustments.append(("Basement", "+$15K"))
        if property_data.garage_spaces >= 2:
            base_value += 10000
            adjustments.append(("2+ car garage", "+$10K"))

        # School district premium
        if property_data.school_rating:
            if property_data.school_rating >= 9.0:
                base_value *= 1.08
                adjustments.append(("Top schools", "+8%"))
            elif property_data.school_rating >= 8.0:
                base_value *= 1.04
                adjustments.append(("Good schools", "+4%"))

        estimated = int(base_value)
        low = int(estimated * 0.92)
        high = int(estimated * 1.08)

        return {
            "estimated_value": estimated,
            "range_low": low,
            "range_high": high,
            "price_per_sqft": area_ppsf,
            "adjustments": adjustments,
            "confidence": "medium" if property_data.square_feet else "low",
            "methodology": "Comparable sales analysis with local adjustments"
        }

    def get_equity_estimate(self, property_data: PropertyData) -> Dict[str, Any]:
        """Estimate owner equity in property."""
        if not property_data.estimated_value:
            valuation = self.estimate_value(property_data)
            current_value = valuation["estimated_value"]
        else:
            current_value = property_data.estimated_value

        # Estimate remaining mortgage
        mortgage_remaining = 0
        if property_data.mortgage_amount and property_data.mortgage_date:
            try:
                mortgage_date = datetime.strptime(property_data.mortgage_date, "%Y-%m-%d")
                years_elapsed = (datetime.now() - mortgage_date).days / 365

                # Assume 30-year mortgage, estimate paydown
                original = property_data.mortgage_amount
                # Rough approximation of mortgage payoff
                payoff_ratio = min(1.0, years_elapsed / 30 * 1.5)  # Accelerated early years
                mortgage_remaining = int(original * (1 - payoff_ratio))
            except Exception:
                mortgage_remaining = property_data.mortgage_amount
        elif property_data.last_sale_price and property_data.last_sale_date:
            # Estimate based on purchase
            try:
                sale_date = datetime.strptime(property_data.last_sale_date, "%Y-%m-%d")
                years_owned = (datetime.now() - sale_date).days / 365

                # Assume 80% LTV at purchase
                original_mortgage = int(property_data.last_sale_price * 0.8)
                payoff_ratio = min(1.0, years_owned / 30 * 1.5)
                mortgage_remaining = int(original_mortgage * (1 - payoff_ratio))
            except Exception:
                pass

        equity = current_value - mortgage_remaining
        ltv = (mortgage_remaining / current_value * 100) if current_value else 0

        return {
            "estimated_value": current_value,
            "estimated_mortgage": mortgage_remaining,
            "estimated_equity": equity,
            "equity_percentage": round((equity / current_value * 100) if current_value else 0, 1),
            "loan_to_value": round(ltv, 1),
            "heloc_potential": max(0, int(current_value * 0.8 - mortgage_remaining)),
            "refinance_potential": ltv > 80 and current_value > property_data.last_sale_price if property_data.last_sale_price else None
        }

    def _get_area_price_per_sqft(self, city: str) -> int:
        """Get average price per sqft for area."""
        # Central Ohio 2024 market data (approximate)
        ppsf_by_city = {
            "dublin": 245,
            "powell": 265,
            "new albany": 285,
            "upper arlington": 295,
            "bexley": 275,
            "grandview heights": 285,
            "westerville": 195,
            "worthington": 225,
            "hilliard": 185,
            "grove city": 165,
            "gahanna": 195,
            "pickerington": 175,
            "lewis center": 225,
            "delaware": 185,
            "pataskala": 155,
            "columbus": 175,
            "reynoldsburg": 165,
            "canal winchester": 170,
            "granville": 235,
            "newark": 145,
        }

        return ppsf_by_city.get(city.lower(), 180)  # Default Columbus metro

    def _fetch_attom_data(self, address: str, city: str, state: str) -> Optional[Dict]:
        """Fetch property data from ATTOM API."""
        try:
            url = "https://api.gateway.attomdata.com/propertyapi/v1.0.0/property/detail"
            params = {
                "address1": address,
                "address2": f"{city}, {state}"
            }
            headers = {
                "apikey": self.attom_api_key,
                "Accept": "application/json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"ATTOM API error: {e}")

        return None

    def _fetch_franklin_county_data(self, address: str) -> Optional[Dict]:
        """Fetch from Franklin County Auditor public records."""
        # This would integrate with Franklin County's public API
        # For now, return None - would need actual API integration
        return None

    def _fetch_walk_score(self, address: str, city: str, state: str) -> Optional[Dict]:
        """Fetch Walk Score data."""
        try:
            full_address = f"{address}, {city}, {state}"
            url = f"https://api.walkscore.com/score"
            params = {
                "format": "json",
                "address": full_address,
                "wsapikey": self.walkscore_api_key,
                "transit": 1,
                "bike": 1
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Walk Score API error: {e}")

        return None

    def _merge_attom_data(self, prop: PropertyData, attom: Dict) -> PropertyData:
        """Merge ATTOM API data into property data."""
        try:
            building = attom.get("property", [{}])[0].get("building", {})
            lot = attom.get("property", [{}])[0].get("lot", {})
            assessment = attom.get("property", [{}])[0].get("assessment", {})
            sale = attom.get("property", [{}])[0].get("sale", {})

            prop.bedrooms = building.get("rooms", {}).get("beds", 0)
            prop.bathrooms = building.get("rooms", {}).get("bathstotal", 0)
            prop.square_feet = building.get("size", {}).get("livingsize", 0)
            prop.lot_size_sqft = lot.get("lotsize2", 0)
            prop.year_built = building.get("yearbuilt", 0)

            prop.tax_assessed_value = assessment.get("assessed", {}).get("assdttlvalue", 0)
            prop.annual_taxes = assessment.get("tax", {}).get("taxtotal", 0)

            prop.last_sale_price = sale.get("amount", {}).get("saleamt", 0)
            prop.last_sale_date = sale.get("salerecdate")

            prop.data_source = "ATTOM"

        except Exception as e:
            logger.error(f"Error merging ATTOM data: {e}")

        return prop

    def _merge_auditor_data(self, prop: PropertyData, auditor: Dict) -> PropertyData:
        """Merge county auditor data."""
        # Would merge public records data
        return prop

    def _calculate_confidence(self, prop: PropertyData) -> float:
        """Calculate confidence score based on data completeness."""
        fields = [
            prop.square_feet > 0,
            prop.bedrooms > 0,
            prop.year_built > 0,
            prop.estimated_value > 0 or prop.tax_assessed_value > 0,
            bool(prop.school_district),
            prop.lot_size_sqft > 0,
            bool(prop.last_sale_date),
        ]

        return sum(fields) / len(fields)


class PropertySearchService:
    """Search for properties matching criteria."""

    def __init__(self):
        """Initialize search service."""
        self.enrichment = PropertyEnrichment()

    def find_likely_sellers(
        self,
        city: str,
        min_equity_percent: float = 30,
        min_ownership_years: int = 5
    ) -> List[Dict[str, Any]]:
        """Find homeowners likely to sell based on criteria.

        This would integrate with public records APIs to find:
        - High equity homeowners
        - Long-term owners (potential downsizers)
        - Pre-foreclosure
        - Inherited properties
        - Divorce filings
        - Empty nesters (based on property size + ownership length)
        """
        # This is a placeholder - would need county records API access
        likely_sellers = []

        # Example criteria that indicate selling potential:
        seller_signals = [
            "High equity (30%+)",
            "Owned 7+ years",
            "Property larger than typical for area",
            "Tax mailing address different from property",
            "Recent life events (public records)",
        ]

        return {
            "search_criteria": {
                "city": city,
                "min_equity_percent": min_equity_percent,
                "min_ownership_years": min_ownership_years
            },
            "signals_checked": seller_signals,
            "results": likely_sellers,
            "note": "Requires county records API integration for actual results"
        }

    def find_investment_opportunities(
        self,
        city: str,
        max_price: int,
        min_cap_rate: float = 6.0
    ) -> List[Dict[str, Any]]:
        """Find potential investment properties."""
        # Placeholder - would integrate with MLS and rental data
        return {
            "search_criteria": {
                "city": city,
                "max_price": max_price,
                "min_cap_rate": min_cap_rate
            },
            "results": [],
            "note": "Requires MLS and rental data API integration"
        }
