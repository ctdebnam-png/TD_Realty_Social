"""Comparative Market Analysis (CMA) generation."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from ..enrichment.property import PropertyEnrichment
from ..enrichment.market import MarketDataProvider

logger = logging.getLogger(__name__)


@dataclass
class Comparable:
    """Comparable property for CMA."""

    address: str
    city: str
    sale_price: int
    sale_date: str
    bedrooms: int
    bathrooms: float
    square_feet: int
    year_built: int
    lot_size: int = 0
    days_on_market: int = 0
    distance_miles: float = 0.0
    price_per_sqft: int = 0

    # Adjustments
    adjustment_total: int = 0
    adjusted_price: int = 0

    def __post_init__(self):
        if self.square_feet > 0:
            self.price_per_sqft = int(self.sale_price / self.square_feet)
        self.adjusted_price = self.sale_price + self.adjustment_total


class CMAGenerator:
    """Generate Comparative Market Analysis reports."""

    def __init__(self):
        """Initialize CMA generator."""
        self.property_enrichment = PropertyEnrichment()
        self.market_data = MarketDataProvider()

        # Adjustment values (per unit)
        self.adjustments = {
            "bedroom": 10000,      # Per bedroom difference
            "bathroom": 7500,      # Per bathroom difference
            "sqft": 100,           # Per sqft difference
            "garage": 5000,        # Per garage space
            "pool": 25000,         # Pool present/absent
            "basement": 15000,     # Finished basement
            "age_per_year": 500,   # Per year age difference
            "lot_size_per_acre": 20000,  # Per acre lot size difference
            "condition_good": 10000,
            "condition_poor": -15000,
        }

    def generate_cma(
        self,
        subject_address: str,
        subject_city: str,
        subject_state: str = "OH",
        comparables: Optional[List[Dict[str, Any]]] = None,
        agent_name: str = "",
        agent_phone: str = "",
        purpose: str = "listing"  # "listing" or "buying"
    ) -> Dict[str, Any]:
        """Generate a CMA report.

        Args:
            subject_address: Address of subject property
            subject_city: City of subject property
            subject_state: State (default OH)
            comparables: List of comparable sales (if not provided, will attempt to fetch)
            agent_name: Agent name for report
            purpose: "listing" for sellers, "buying" for buyers
        """
        # Get subject property data
        subject = self.property_enrichment.enrich_by_address(
            subject_address, subject_city, subject_state
        )

        # Get market stats
        market_stats = self.market_data.get_market_stats(subject_city)

        # Process comparables
        processed_comps = []
        if comparables:
            for comp_data in comparables[:6]:  # Max 6 comps
                comp = self._create_comparable(comp_data, subject)
                processed_comps.append(comp)

        # Calculate value range
        value_estimate = self._calculate_value_estimate(subject, processed_comps, market_stats)

        # Generate report
        report = {
            "title": f"Comparative Market Analysis",
            "generated_at": datetime.now().isoformat(),
            "purpose": purpose,

            "agent": {
                "name": agent_name,
                "phone": agent_phone
            },

            "subject_property": {
                "address": subject_address,
                "city": subject_city,
                "state": subject_state,
                "bedrooms": subject.bedrooms,
                "bathrooms": subject.bathrooms,
                "square_feet": subject.square_feet,
                "year_built": subject.year_built,
                "lot_size": subject.lot_size_sqft,
                "property_type": subject.property_type,
                "tax_assessed": subject.tax_assessed_value,
                "last_sale_price": subject.last_sale_price,
                "last_sale_date": subject.last_sale_date
            },

            "market_conditions": {
                "area": subject_city,
                "median_price": market_stats.median_price if market_stats else 0,
                "price_per_sqft": market_stats.price_per_sqft if market_stats else 0,
                "yoy_change": market_stats.price_change_yoy if market_stats else 0,
                "days_on_market": market_stats.avg_days_on_market if market_stats else 0,
                "market_type": market_stats.market_type if market_stats else "unknown",
                "list_to_sale_ratio": market_stats.list_to_sale_ratio if market_stats else 0
            },

            "comparables": [
                {
                    "address": c.address,
                    "city": c.city,
                    "sale_price": c.sale_price,
                    "sale_date": c.sale_date,
                    "bedrooms": c.bedrooms,
                    "bathrooms": c.bathrooms,
                    "square_feet": c.square_feet,
                    "year_built": c.year_built,
                    "price_per_sqft": c.price_per_sqft,
                    "days_on_market": c.days_on_market,
                    "adjustment": c.adjustment_total,
                    "adjusted_price": c.adjusted_price
                }
                for c in processed_comps
            ],

            "value_estimate": value_estimate,

            "pricing_strategy": self._generate_pricing_strategy(
                value_estimate, market_stats, purpose
            ),

            "methodology": self._get_methodology_text()
        }

        return report

    def _create_comparable(self, comp_data: Dict[str, Any], subject) -> Comparable:
        """Create a Comparable from raw data with adjustments."""
        comp = Comparable(
            address=comp_data.get("address", ""),
            city=comp_data.get("city", ""),
            sale_price=comp_data.get("sale_price", 0),
            sale_date=comp_data.get("sale_date", ""),
            bedrooms=comp_data.get("bedrooms", 0),
            bathrooms=comp_data.get("bathrooms", 0),
            square_feet=comp_data.get("square_feet", 0),
            year_built=comp_data.get("year_built", 0),
            lot_size=comp_data.get("lot_size", 0),
            days_on_market=comp_data.get("days_on_market", 0),
            distance_miles=comp_data.get("distance", 0)
        )

        # Calculate adjustments
        adjustments = 0

        # Bedroom adjustment
        if subject.bedrooms and comp.bedrooms:
            bed_diff = subject.bedrooms - comp.bedrooms
            adjustments += bed_diff * self.adjustments["bedroom"]

        # Bathroom adjustment
        if subject.bathrooms and comp.bathrooms:
            bath_diff = subject.bathrooms - comp.bathrooms
            adjustments += int(bath_diff * self.adjustments["bathroom"])

        # Square footage adjustment
        if subject.square_feet and comp.square_feet:
            sqft_diff = subject.square_feet - comp.square_feet
            adjustments += sqft_diff * self.adjustments["sqft"]

        # Age adjustment
        if subject.year_built and comp.year_built:
            age_diff = comp.year_built - subject.year_built  # Newer comp = positive adjustment
            adjustments += age_diff * self.adjustments["age_per_year"]

        comp.adjustment_total = adjustments
        comp.adjusted_price = comp.sale_price + adjustments

        return comp

    def _calculate_value_estimate(
        self,
        subject,
        comparables: List[Comparable],
        market_stats
    ) -> Dict[str, Any]:
        """Calculate value estimate from comparables."""
        if not comparables:
            # Fall back to area price per sqft
            if market_stats and subject.square_feet:
                estimated = subject.square_feet * market_stats.price_per_sqft
                return {
                    "low": int(estimated * 0.90),
                    "mid": int(estimated),
                    "high": int(estimated * 1.10),
                    "confidence": "low",
                    "method": "area_ppsf",
                    "note": "Estimate based on area average - comparable sales recommended"
                }
            return {
                "low": 0,
                "mid": 0,
                "high": 0,
                "confidence": "none",
                "method": "insufficient_data"
            }

        # Calculate from adjusted comparable prices
        adjusted_prices = [c.adjusted_price for c in comparables]

        # Weighted average (more recent sales weighted higher)
        # For now, simple average
        avg_adjusted = sum(adjusted_prices) / len(adjusted_prices)
        min_adjusted = min(adjusted_prices)
        max_adjusted = max(adjusted_prices)

        # Calculate median
        sorted_prices = sorted(adjusted_prices)
        n = len(sorted_prices)
        if n % 2 == 0:
            median = (sorted_prices[n//2 - 1] + sorted_prices[n//2]) / 2
        else:
            median = sorted_prices[n//2]

        # Confidence based on number of comps and adjustment magnitude
        avg_adjustment = sum(abs(c.adjustment_total) for c in comparables) / len(comparables)
        if len(comparables) >= 4 and avg_adjustment < 20000:
            confidence = "high"
        elif len(comparables) >= 3 and avg_adjustment < 40000:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "low": int(min_adjusted),
            "mid": int(median),
            "high": int(max_adjusted),
            "average": int(avg_adjusted),
            "confidence": confidence,
            "method": "comparable_sales",
            "comparables_used": len(comparables),
            "avg_adjustment": int(avg_adjustment)
        }

    def _generate_pricing_strategy(
        self,
        value_estimate: Dict[str, Any],
        market_stats,
        purpose: str
    ) -> Dict[str, Any]:
        """Generate pricing strategy recommendations."""
        mid_value = value_estimate.get("mid", 0)
        low_value = value_estimate.get("low", 0)
        high_value = value_estimate.get("high", 0)

        if not mid_value:
            return {"error": "Insufficient data for pricing strategy"}

        strategy = {}

        if purpose == "listing":
            # Seller pricing strategy
            if market_stats and market_stats.market_type == "seller":
                strategy["recommended_list_price"] = int(mid_value * 1.02)  # 2% above mid
                strategy["strategy"] = "aggressive"
                strategy["rationale"] = (
                    "In this seller's market, pricing slightly above comparable sales "
                    "can maximize your return while still attracting multiple offers."
                )
            elif market_stats and market_stats.market_type == "buyer":
                strategy["recommended_list_price"] = int(mid_value * 0.98)  # 2% below mid
                strategy["strategy"] = "competitive"
                strategy["rationale"] = (
                    "In the current buyer's market, competitive pricing will help "
                    "attract buyers and avoid extended time on market."
                )
            else:
                strategy["recommended_list_price"] = mid_value
                strategy["strategy"] = "market_value"
                strategy["rationale"] = (
                    "Pricing at market value positions your home competitively "
                    "while maximizing your return."
                )

            strategy["price_range"] = {
                "aggressive": int(high_value * 1.02),
                "market": mid_value,
                "competitive": int(low_value * 0.98)
            }

            # Expected outcomes
            if market_stats:
                strategy["expected_days_on_market"] = market_stats.avg_days_on_market
                strategy["expected_sale_ratio"] = f"{market_stats.list_to_sale_ratio * 100:.1f}%"

        else:  # buying
            strategy["fair_value_range"] = {
                "low": low_value,
                "mid": mid_value,
                "high": high_value
            }
            strategy["max_recommended_offer"] = high_value
            strategy["opening_offer_suggestion"] = int(mid_value * 0.95)

            if market_stats and market_stats.market_type == "seller":
                strategy["negotiation_advice"] = (
                    "In this competitive market, be prepared to offer at or near "
                    "asking price for well-priced homes."
                )
            else:
                strategy["negotiation_advice"] = (
                    "You have negotiating room in this market. Consider starting "
                    "below asking and negotiating from there."
                )

        return strategy

    def _get_methodology_text(self) -> str:
        """Get CMA methodology explanation."""
        return """
This Comparative Market Analysis (CMA) provides an estimated market value based on:

1. COMPARABLE SALES ANALYSIS: Recent sales of similar properties in the area,
   adjusted for differences in features, size, and condition.

2. MARKET CONDITIONS: Current supply and demand dynamics, average days on market,
   and price trends in the local area.

3. ADJUSTMENTS: Dollar adjustments are made for differences between the subject
   property and comparables, including bedrooms, bathrooms, square footage, age,
   and special features.

This CMA is not an appraisal and should not be used as such. For financing or
legal purposes, a licensed appraisal is recommended. Market conditions can change,
and this analysis reflects data available at the time of preparation.
"""

    def generate_text_cma(
        self,
        subject_address: str,
        subject_city: str,
        comparables: List[Dict[str, Any]],
        agent_name: str = ""
    ) -> str:
        """Generate a plain text CMA report."""
        report = self.generate_cma(
            subject_address, subject_city, comparables=comparables, agent_name=agent_name
        )

        lines = [
            "=" * 70,
            "COMPARATIVE MARKET ANALYSIS",
            f"Prepared: {datetime.now().strftime('%B %d, %Y')}",
            "=" * 70,
            "",
            "SUBJECT PROPERTY",
            "-" * 40,
            f"Address: {report['subject_property']['address']}",
            f"         {report['subject_property']['city']}, {report['subject_property']['state']}",
            f"Beds: {report['subject_property']['bedrooms']}  |  Baths: {report['subject_property']['bathrooms']}  |  Sqft: {report['subject_property']['square_feet']:,}",
            f"Year Built: {report['subject_property']['year_built']}",
            "",
            "MARKET CONDITIONS",
            "-" * 40,
            f"Area: {report['market_conditions']['area']}",
            f"Median Price: ${report['market_conditions']['median_price']:,}",
            f"Price/Sqft: ${report['market_conditions']['price_per_sqft']}",
            f"Market Type: {report['market_conditions']['market_type'].upper()}",
            f"Avg Days on Market: {report['market_conditions']['days_on_market']}",
            "",
            "COMPARABLE SALES",
            "-" * 40,
        ]

        for i, comp in enumerate(report["comparables"], 1):
            lines.extend([
                f"\n{i}. {comp['address']}",
                f"   Sale Price: ${comp['sale_price']:,}  ({comp['sale_date']})",
                f"   {comp['bedrooms']} bed / {comp['bathrooms']} bath / {comp['square_feet']:,} sqft",
                f"   Adjustment: ${comp['adjustment']:+,}  →  Adjusted: ${comp['adjusted_price']:,}",
            ])

        lines.extend([
            "",
            "VALUE ESTIMATE",
            "-" * 40,
            f"Low:  ${report['value_estimate']['low']:,}",
            f"Mid:  ${report['value_estimate']['mid']:,}",
            f"High: ${report['value_estimate']['high']:,}",
            f"Confidence: {report['value_estimate']['confidence'].upper()}",
            "",
            "PRICING RECOMMENDATION",
            "-" * 40,
        ])

        if "recommended_list_price" in report["pricing_strategy"]:
            lines.append(f"Recommended List Price: ${report['pricing_strategy']['recommended_list_price']:,}")
            lines.append(f"Strategy: {report['pricing_strategy']['strategy'].upper()}")
            lines.append(f"\n{report['pricing_strategy']['rationale']}")

        lines.extend([
            "",
            "=" * 70,
            report["methodology"],
            "=" * 70,
        ])

        if agent_name:
            lines.append(f"\nPrepared by: {agent_name}")

        return "\n".join(lines)
