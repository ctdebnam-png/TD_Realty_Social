"""Market data and analytics for Central Ohio real estate."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MarketStats:
    """Market statistics for an area."""

    area: str
    period: str  # "monthly", "quarterly", "yearly"
    period_end: datetime

    # Price metrics
    median_price: int = 0
    average_price: int = 0
    price_per_sqft: int = 0
    price_change_yoy: float = 0.0  # Year over year change
    price_change_mom: float = 0.0  # Month over month

    # Inventory
    active_listings: int = 0
    new_listings: int = 0
    pending_sales: int = 0
    closed_sales: int = 0
    months_of_inventory: float = 0.0

    # Market speed
    avg_days_on_market: int = 0
    median_days_on_market: int = 0
    list_to_sale_ratio: float = 0.0  # Sale price / list price

    # By property type
    single_family_median: int = 0
    condo_median: int = 0
    townhouse_median: int = 0

    # By price range
    under_300k_pct: float = 0.0
    range_300k_500k_pct: float = 0.0
    range_500k_750k_pct: float = 0.0
    over_750k_pct: float = 0.0

    # Market type indicator
    market_type: str = ""  # "seller", "buyer", "balanced"


class MarketDataProvider:
    """Provide market data and analytics for Central Ohio."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize market data provider."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "market_data.json"
        self._market_data: Dict[str, MarketStats] = {}
        self._load_baseline_data()

    def _load_baseline_data(self):
        """Load baseline Central Ohio market data."""
        # Current market data (would be updated from MLS feeds)
        # These are approximate Q4 2024 figures for Central Ohio

        areas = {
            "columbus_metro": {
                "median_price": 325000,
                "average_price": 375000,
                "price_per_sqft": 180,
                "price_change_yoy": 5.2,
                "active_listings": 4500,
                "avg_days_on_market": 28,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.8,
                "market_type": "seller"
            },
            "dublin": {
                "median_price": 525000,
                "average_price": 595000,
                "price_per_sqft": 245,
                "price_change_yoy": 4.8,
                "active_listings": 180,
                "avg_days_on_market": 21,
                "list_to_sale_ratio": 0.99,
                "months_of_inventory": 1.2,
                "market_type": "seller"
            },
            "powell": {
                "median_price": 575000,
                "average_price": 650000,
                "price_per_sqft": 265,
                "price_change_yoy": 5.5,
                "active_listings": 95,
                "avg_days_on_market": 18,
                "list_to_sale_ratio": 1.01,
                "months_of_inventory": 1.0,
                "market_type": "seller"
            },
            "westerville": {
                "median_price": 385000,
                "average_price": 425000,
                "price_per_sqft": 195,
                "price_change_yoy": 6.1,
                "active_listings": 145,
                "avg_days_on_market": 24,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.5,
                "market_type": "seller"
            },
            "new_albany": {
                "median_price": 685000,
                "average_price": 825000,
                "price_per_sqft": 285,
                "price_change_yoy": 4.2,
                "active_listings": 65,
                "avg_days_on_market": 25,
                "list_to_sale_ratio": 0.97,
                "months_of_inventory": 1.8,
                "market_type": "seller"
            },
            "upper_arlington": {
                "median_price": 595000,
                "average_price": 725000,
                "price_per_sqft": 295,
                "price_change_yoy": 3.8,
                "active_listings": 55,
                "avg_days_on_market": 22,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.4,
                "market_type": "seller"
            },
            "grandview_heights": {
                "median_price": 485000,
                "average_price": 545000,
                "price_per_sqft": 285,
                "price_change_yoy": 7.2,
                "active_listings": 25,
                "avg_days_on_market": 14,
                "list_to_sale_ratio": 1.02,
                "months_of_inventory": 0.8,
                "market_type": "seller"
            },
            "hilliard": {
                "median_price": 365000,
                "average_price": 395000,
                "price_per_sqft": 185,
                "price_change_yoy": 5.8,
                "active_listings": 120,
                "avg_days_on_market": 26,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.6,
                "market_type": "seller"
            },
            "grove_city": {
                "median_price": 295000,
                "average_price": 315000,
                "price_per_sqft": 165,
                "price_change_yoy": 7.5,
                "active_listings": 135,
                "avg_days_on_market": 22,
                "list_to_sale_ratio": 0.99,
                "months_of_inventory": 1.3,
                "market_type": "seller"
            },
            "gahanna": {
                "median_price": 375000,
                "average_price": 415000,
                "price_per_sqft": 195,
                "price_change_yoy": 5.4,
                "active_listings": 85,
                "avg_days_on_market": 25,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.5,
                "market_type": "seller"
            },
            "pickerington": {
                "median_price": 345000,
                "average_price": 375000,
                "price_per_sqft": 175,
                "price_change_yoy": 6.8,
                "active_listings": 110,
                "avg_days_on_market": 23,
                "list_to_sale_ratio": 0.99,
                "months_of_inventory": 1.4,
                "market_type": "seller"
            },
            "german_village": {
                "median_price": 545000,
                "average_price": 625000,
                "price_per_sqft": 325,
                "price_change_yoy": 4.5,
                "active_listings": 18,
                "avg_days_on_market": 28,
                "list_to_sale_ratio": 0.96,
                "months_of_inventory": 2.0,
                "market_type": "balanced"
            },
            "short_north": {
                "median_price": 425000,
                "average_price": 485000,
                "price_per_sqft": 295,
                "price_change_yoy": 5.1,
                "active_listings": 22,
                "avg_days_on_market": 21,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.5,
                "market_type": "seller"
            },
            "clintonville": {
                "median_price": 395000,
                "average_price": 435000,
                "price_per_sqft": 235,
                "price_change_yoy": 6.2,
                "active_listings": 45,
                "avg_days_on_market": 18,
                "list_to_sale_ratio": 1.01,
                "months_of_inventory": 1.1,
                "market_type": "seller"
            },
            "worthington": {
                "median_price": 445000,
                "average_price": 495000,
                "price_per_sqft": 225,
                "price_change_yoy": 4.9,
                "active_listings": 65,
                "avg_days_on_market": 24,
                "list_to_sale_ratio": 0.98,
                "months_of_inventory": 1.6,
                "market_type": "seller"
            },
            "bexley": {
                "median_price": 535000,
                "average_price": 625000,
                "price_per_sqft": 275,
                "price_change_yoy": 3.5,
                "active_listings": 35,
                "avg_days_on_market": 28,
                "list_to_sale_ratio": 0.97,
                "months_of_inventory": 2.1,
                "market_type": "balanced"
            },
        }

        for area_key, data in areas.items():
            self._market_data[area_key] = MarketStats(
                area=area_key.replace("_", " ").title(),
                period="monthly",
                period_end=datetime.now(),
                **data
            )

    def get_market_stats(self, area: str) -> Optional[MarketStats]:
        """Get market statistics for an area."""
        area_key = area.lower().replace(" ", "_").replace("-", "_")
        return self._market_data.get(area_key)

    def get_all_areas(self) -> List[str]:
        """Get list of all areas with data."""
        return [stats.area for stats in self._market_data.values()]

    def compare_areas(self, areas: List[str]) -> Dict[str, Any]:
        """Compare market stats across multiple areas."""
        comparison = {"areas": {}, "rankings": {}}

        stats_list = []
        for area in areas:
            stats = self.get_market_stats(area)
            if stats:
                stats_list.append(stats)
                comparison["areas"][stats.area] = {
                    "median_price": stats.median_price,
                    "price_per_sqft": stats.price_per_sqft,
                    "price_change_yoy": stats.price_change_yoy,
                    "days_on_market": stats.avg_days_on_market,
                    "months_inventory": stats.months_of_inventory,
                    "market_type": stats.market_type
                }

        if stats_list:
            # Rankings
            by_price = sorted(stats_list, key=lambda x: x.median_price, reverse=True)
            by_appreciation = sorted(stats_list, key=lambda x: x.price_change_yoy, reverse=True)
            by_speed = sorted(stats_list, key=lambda x: x.avg_days_on_market)

            comparison["rankings"] = {
                "most_expensive": [s.area for s in by_price[:3]],
                "fastest_appreciation": [s.area for s in by_appreciation[:3]],
                "fastest_selling": [s.area for s in by_speed[:3]]
            }

        return comparison

    def get_market_summary(self) -> Dict[str, Any]:
        """Get overall Columbus metro market summary."""
        metro = self._market_data.get("columbus_metro")
        if not metro:
            return {}

        # Count market types
        seller_markets = sum(1 for s in self._market_data.values() if s.market_type == "seller")
        balanced_markets = sum(1 for s in self._market_data.values() if s.market_type == "balanced")
        buyer_markets = sum(1 for s in self._market_data.values() if s.market_type == "buyer")

        # Hottest markets (fastest selling + highest appreciation)
        all_stats = list(self._market_data.values())
        hottest = sorted(
            all_stats,
            key=lambda x: (-x.price_change_yoy, x.avg_days_on_market)
        )[:5]

        # Most affordable
        affordable = sorted(all_stats, key=lambda x: x.median_price)[:5]

        return {
            "metro_stats": {
                "median_price": metro.median_price,
                "yoy_change": f"{metro.price_change_yoy:+.1f}%",
                "avg_days_on_market": metro.avg_days_on_market,
                "months_inventory": metro.months_of_inventory,
                "market_type": metro.market_type
            },
            "market_breakdown": {
                "seller_markets": seller_markets,
                "balanced_markets": balanced_markets,
                "buyer_markets": buyer_markets
            },
            "hottest_markets": [
                {"area": s.area, "yoy": f"{s.price_change_yoy:+.1f}%", "dom": s.avg_days_on_market}
                for s in hottest
            ],
            "most_affordable": [
                {"area": s.area, "median": f"${s.median_price:,}"}
                for s in affordable
            ],
            "market_outlook": self._generate_outlook(metro)
        }

    def _generate_outlook(self, stats: MarketStats) -> str:
        """Generate market outlook text."""
        if stats.months_of_inventory < 2:
            inventory_status = "extremely low inventory"
        elif stats.months_of_inventory < 4:
            inventory_status = "low inventory"
        elif stats.months_of_inventory < 6:
            inventory_status = "balanced inventory"
        else:
            inventory_status = "elevated inventory"

        if stats.price_change_yoy > 5:
            price_trend = "strong price appreciation"
        elif stats.price_change_yoy > 2:
            price_trend = "moderate price growth"
        elif stats.price_change_yoy > 0:
            price_trend = "stable prices"
        else:
            price_trend = "softening prices"

        return (
            f"The Columbus metro market continues to show {price_trend} "
            f"with {inventory_status}. Homes are selling in an average of "
            f"{stats.avg_days_on_market} days, and sellers are receiving "
            f"{stats.list_to_sale_ratio * 100:.0f}% of asking price on average."
        )

    def get_price_trends(self, area: str, months: int = 12) -> Dict[str, Any]:
        """Get price trend data for an area."""
        stats = self.get_market_stats(area)
        if not stats:
            return {}

        # Generate simulated historical trend (would come from actual data)
        current_price = stats.median_price
        monthly_change = stats.price_change_yoy / 12 / 100

        trend_data = []
        for i in range(months, 0, -1):
            date = datetime.now() - timedelta(days=i * 30)
            price = int(current_price / ((1 + monthly_change) ** i))
            trend_data.append({
                "date": date.strftime("%Y-%m"),
                "median_price": price
            })

        trend_data.append({
            "date": datetime.now().strftime("%Y-%m"),
            "median_price": current_price
        })

        return {
            "area": stats.area,
            "current_median": current_price,
            "yoy_change": stats.price_change_yoy,
            "trend": trend_data,
            "forecast": self._forecast_prices(stats)
        }

    def _forecast_prices(self, stats: MarketStats) -> Dict[str, Any]:
        """Generate price forecast."""
        # Simple forecast based on current trends
        current = stats.median_price
        annual_rate = stats.price_change_yoy / 100

        # Dampen extreme growth rates
        if annual_rate > 0.08:
            forecast_rate = 0.05
        elif annual_rate > 0.05:
            forecast_rate = annual_rate * 0.8
        elif annual_rate < 0:
            forecast_rate = annual_rate * 0.5
        else:
            forecast_rate = annual_rate

        return {
            "next_6_months": int(current * (1 + forecast_rate / 2)),
            "next_12_months": int(current * (1 + forecast_rate)),
            "confidence": "medium",
            "factors": [
                "Interest rate environment",
                "Local job market strength",
                "Inventory levels",
                "Seasonal patterns"
            ]
        }

    def get_buyer_advice(self, area: str, budget: int) -> Dict[str, Any]:
        """Generate buyer advice for an area and budget."""
        stats = self.get_market_stats(area)
        if not stats:
            return {"error": "Area not found"}

        advice = {
            "area": stats.area,
            "budget": budget,
            "market_conditions": stats.market_type
        }

        # Budget analysis
        if budget >= stats.median_price * 1.2:
            advice["budget_position"] = "above_median"
            advice["budget_advice"] = "Your budget is above the area median, giving you good options."
        elif budget >= stats.median_price * 0.8:
            advice["budget_position"] = "around_median"
            advice["budget_advice"] = "Your budget is near the area median. You'll find options but may face competition."
        else:
            advice["budget_position"] = "below_median"
            advice["budget_advice"] = "Your budget is below the area median. Consider expanding your search area."

        # Strategy based on market type
        if stats.market_type == "seller":
            advice["strategy"] = [
                "Get pre-approved before searching",
                "Be prepared to move quickly on listings",
                "Consider offering above asking in competitive situations",
                "Limit contingencies where possible",
                "Write a personal letter to sellers"
            ]
            advice["timing"] = "Act fast - homes are selling quickly"
        else:
            advice["strategy"] = [
                "Take your time to find the right home",
                "Negotiate on price and terms",
                "Request repairs and credits",
                "Consider homes that have sat on market"
            ]
            advice["timing"] = "You have more negotiating power in this market"

        # Suggested areas if budget is tight
        if budget < stats.median_price:
            affordable_areas = [
                s.area for s in self._market_data.values()
                if s.median_price <= budget * 1.1 and s.area != stats.area
            ]
            advice["alternative_areas"] = affordable_areas[:5]

        return advice

    def get_seller_advice(self, area: str, property_value: int) -> Dict[str, Any]:
        """Generate seller advice for an area."""
        stats = self.get_market_stats(area)
        if not stats:
            return {"error": "Area not found"}

        advice = {
            "area": stats.area,
            "estimated_value": property_value,
            "market_conditions": stats.market_type,
            "expected_days_on_market": stats.avg_days_on_market,
            "expected_sale_ratio": stats.list_to_sale_ratio
        }

        if stats.market_type == "seller":
            advice["pricing_strategy"] = "Price at or slightly above market value"
            advice["negotiation_power"] = "high"
            advice["tips"] = [
                "You may receive multiple offers",
                "Consider setting an offer deadline",
                "Don't underprice - you have leverage",
                "Still invest in staging and photos",
                "Be selective with contingencies you accept"
            ]
        else:
            advice["pricing_strategy"] = "Price competitively to attract buyers"
            advice["negotiation_power"] = "moderate"
            advice["tips"] = [
                "Price accurately from the start",
                "Invest in staging and professional photos",
                "Be flexible on closing dates",
                "Consider offering concessions",
                "Make sure home is in show-ready condition"
            ]

        # Best time to sell
        advice["timing_advice"] = (
            "Spring (March-May) typically sees the highest buyer activity. "
            "Late summer and fall are also strong. Winter tends to be slower "
            "but serious buyers are out year-round."
        )

        return advice
