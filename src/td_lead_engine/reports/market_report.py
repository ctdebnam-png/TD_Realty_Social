"""Market report generation."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..enrichment.market import MarketDataProvider

logger = logging.getLogger(__name__)


class MarketReportGenerator:
    """Generate market reports for clients and marketing."""

    def __init__(self):
        """Initialize report generator."""
        self.market_data = MarketDataProvider()

    def generate_area_report(
        self,
        area: str,
        agent_name: str = "",
        agent_phone: str = "",
        agent_email: str = ""
    ) -> Dict[str, Any]:
        """Generate a market report for an area."""
        stats = self.market_data.get_market_stats(area)

        if not stats:
            return {"error": f"No data available for {area}"}

        trends = self.market_data.get_price_trends(area, months=12)
        summary = self.market_data.get_market_summary()

        report = {
            "title": f"{stats.area} Real Estate Market Report",
            "generated_at": datetime.now().isoformat(),
            "period": stats.period,

            "agent": {
                "name": agent_name,
                "phone": agent_phone,
                "email": agent_email
            },

            "executive_summary": self._generate_summary(stats),

            "market_snapshot": {
                "median_price": f"${stats.median_price:,}",
                "avg_price": f"${stats.average_price:,}",
                "price_per_sqft": f"${stats.price_per_sqft}",
                "yoy_change": f"{stats.price_change_yoy:+.1f}%",
                "days_on_market": stats.avg_days_on_market,
                "list_to_sale_ratio": f"{stats.list_to_sale_ratio * 100:.1f}%",
                "months_inventory": stats.months_of_inventory,
                "market_type": stats.market_type.upper()
            },

            "market_analysis": {
                "inventory_analysis": self._analyze_inventory(stats),
                "price_analysis": self._analyze_prices(stats),
                "speed_analysis": self._analyze_market_speed(stats)
            },

            "price_trends": trends,

            "buyer_insights": self._generate_buyer_insights(stats),
            "seller_insights": self._generate_seller_insights(stats),

            "metro_comparison": {
                "this_area": {
                    "median": stats.median_price,
                    "yoy_change": stats.price_change_yoy
                },
                "metro_median": summary.get("metro_stats", {}).get("median_price", 0),
                "vs_metro": f"{((stats.median_price / summary.get('metro_stats', {}).get('median_price', 1)) - 1) * 100:+.1f}%"
            },

            "forecast": trends.get("forecast", {}),

            "call_to_action": self._generate_cta(stats, agent_name)
        }

        return report

    def _generate_summary(self, stats) -> str:
        """Generate executive summary."""
        market_descriptor = {
            "seller": "a strong seller's market with high demand and limited inventory",
            "buyer": "a buyer's market with more negotiating power for purchasers",
            "balanced": "a balanced market with opportunities for both buyers and sellers"
        }

        price_trend = "appreciation" if stats.price_change_yoy > 0 else "softening"

        return (
            f"The {stats.area} real estate market is currently {market_descriptor.get(stats.market_type, 'active')}. "
            f"Home prices have shown {stats.price_change_yoy:+.1f}% {price_trend} over the past year, "
            f"with the median home price now at ${stats.median_price:,}. "
            f"Homes are selling in an average of {stats.avg_days_on_market} days, "
            f"and sellers are receiving {stats.list_to_sale_ratio * 100:.0f}% of their asking price."
        )

    def _analyze_inventory(self, stats) -> Dict[str, str]:
        """Analyze inventory levels."""
        if stats.months_of_inventory < 2:
            level = "critically low"
            impact = "Strong upward pressure on prices. Multiple offers are common."
            advice = "Buyers should be prepared to act quickly with strong offers."
        elif stats.months_of_inventory < 4:
            level = "low"
            impact = "Moderate upward pressure on prices. Competition among buyers."
            advice = "Buyers should have financing pre-approved and be ready to move fast."
        elif stats.months_of_inventory < 6:
            level = "balanced"
            impact = "Stable prices with fair negotiating power for both parties."
            advice = "Good time for both buyers and sellers to achieve fair deals."
        else:
            level = "elevated"
            impact = "Downward pressure on prices. More choices for buyers."
            advice = "Buyers have negotiating leverage. Sellers should price competitively."

        return {
            "level": level,
            "months": f"{stats.months_of_inventory:.1f}",
            "impact": impact,
            "advice": advice
        }

    def _analyze_prices(self, stats) -> Dict[str, str]:
        """Analyze price trends."""
        if stats.price_change_yoy > 8:
            trend = "rapid appreciation"
            outlook = "Strong growth may moderate as affordability becomes a factor."
        elif stats.price_change_yoy > 4:
            trend = "healthy appreciation"
            outlook = "Sustainable growth indicates a healthy market."
        elif stats.price_change_yoy > 0:
            trend = "modest appreciation"
            outlook = "Stable growth provides a balanced environment."
        elif stats.price_change_yoy > -3:
            trend = "stable to slightly declining"
            outlook = "Minor corrections are normal and may present buying opportunities."
        else:
            trend = "declining"
            outlook = "Market correction underway. Good opportunities for patient buyers."

        return {
            "trend": trend,
            "yoy_change": f"{stats.price_change_yoy:+.1f}%",
            "median": f"${stats.median_price:,}",
            "price_per_sqft": f"${stats.price_per_sqft}/sqft",
            "outlook": outlook
        }

    def _analyze_market_speed(self, stats) -> Dict[str, str]:
        """Analyze how fast homes are selling."""
        if stats.avg_days_on_market < 14:
            speed = "very fast"
            description = "Homes are selling within two weeks of listing."
        elif stats.avg_days_on_market < 30:
            speed = "fast"
            description = "Most homes sell within the first month."
        elif stats.avg_days_on_market < 60:
            speed = "moderate"
            description = "Homes typically sell within 1-2 months."
        else:
            speed = "slow"
            description = "Extended time on market is common."

        return {
            "speed": speed,
            "days_on_market": stats.avg_days_on_market,
            "description": description,
            "list_to_sale": f"{stats.list_to_sale_ratio * 100:.1f}%"
        }

    def _generate_buyer_insights(self, stats) -> List[str]:
        """Generate insights for buyers."""
        insights = []

        if stats.market_type == "seller":
            insights.extend([
                "Get pre-approved for a mortgage before starting your search",
                "Be prepared to make strong offers quickly",
                "Consider offering above asking price in competitive situations",
                "Limit contingencies where possible to strengthen your offer",
                "Work with an experienced agent who knows the market"
            ])
        else:
            insights.extend([
                "Take your time to find the right home",
                "You have room to negotiate on price",
                "Request repairs and seller concessions",
                "Consider homes that have been on the market longer",
                "Don't rush - you have leverage as a buyer"
            ])

        # Price-specific insights
        if stats.price_change_yoy > 5:
            insights.append("Buying now locks in current prices before further appreciation")
        elif stats.price_change_yoy < 0:
            insights.append("Declining prices may present buying opportunities")

        return insights

    def _generate_seller_insights(self, stats) -> List[str]:
        """Generate insights for sellers."""
        insights = []

        if stats.market_type == "seller":
            insights.extend([
                "You're in a strong position with limited competition",
                "Price at or slightly above market value",
                "You may receive multiple offers",
                "Be selective about which contingencies to accept",
                "Consider setting an offer deadline to create urgency"
            ])
        else:
            insights.extend([
                "Price your home competitively from the start",
                "Invest in staging and professional photography",
                "Be flexible on terms and closing dates",
                "Consider offering buyer incentives",
                "Ensure your home is in move-in ready condition"
            ])

        # Market-specific insights
        if stats.avg_days_on_market < 21:
            insights.append(f"Homes in {stats.area} are selling quickly - prepare for a fast sale")

        return insights

    def _generate_cta(self, stats, agent_name: str) -> str:
        """Generate call to action."""
        if stats.market_type == "seller":
            action = f"find out what your {stats.area} home is worth"
        else:
            action = f"explore homes for sale in {stats.area}"

        if agent_name:
            return f"Ready to {action}? Contact {agent_name} today for a free consultation."
        else:
            return f"Ready to {action}? Contact us today for a free consultation."

    def generate_text_report(self, area: str, agent_name: str = "") -> str:
        """Generate a plain text market report."""
        report = self.generate_area_report(area, agent_name)

        if "error" in report:
            return report["error"]

        lines = [
            "=" * 60,
            report["title"].upper(),
            f"Generated: {datetime.now().strftime('%B %d, %Y')}",
            "=" * 60,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            report["executive_summary"],
            "",
            "MARKET SNAPSHOT",
            "-" * 40,
        ]

        snapshot = report["market_snapshot"]
        for key, value in snapshot.items():
            label = key.replace("_", " ").title()
            lines.append(f"  {label}: {value}")

        lines.extend([
            "",
            "MARKET ANALYSIS",
            "-" * 40,
            f"Inventory: {report['market_analysis']['inventory_analysis']['level'].upper()}",
            f"  {report['market_analysis']['inventory_analysis']['impact']}",
            "",
            f"Price Trend: {report['market_analysis']['price_analysis']['trend'].upper()}",
            f"  {report['market_analysis']['price_analysis']['outlook']}",
            "",
            f"Market Speed: {report['market_analysis']['speed_analysis']['speed'].upper()}",
            f"  {report['market_analysis']['speed_analysis']['description']}",
            "",
            "BUYER INSIGHTS",
            "-" * 40,
        ])

        for insight in report["buyer_insights"][:5]:
            lines.append(f"  • {insight}")

        lines.extend([
            "",
            "SELLER INSIGHTS",
            "-" * 40,
        ])

        for insight in report["seller_insights"][:5]:
            lines.append(f"  • {insight}")

        lines.extend([
            "",
            "=" * 60,
            report["call_to_action"],
            "=" * 60,
        ])

        if agent_name:
            lines.extend([
                "",
                f"Report prepared by: {agent_name}",
            ])

        return "\n".join(lines)

    def generate_email_report(self, area: str, agent_name: str, recipient_name: str = "") -> Dict[str, str]:
        """Generate email-friendly market report."""
        report = self.generate_area_report(area, agent_name)

        if "error" in report:
            return {"error": report["error"]}

        greeting = f"Hi {recipient_name}," if recipient_name else "Hello,"

        subject = f"{report['market_snapshot']['market_type']} Market: {area} Real Estate Update"

        body = f"""
{greeting}

Here's your {area} real estate market update:

{report['executive_summary']}

📊 QUICK STATS:
• Median Price: {report['market_snapshot']['median_price']}
• Year-over-Year: {report['market_snapshot']['yoy_change']}
• Days on Market: {report['market_snapshot']['days_on_market']}
• Market Type: {report['market_snapshot']['market_type']}

"""

        if recipient_name:
            body += f"🏠 WHAT THIS MEANS FOR YOU:\n"
            # Add personalized insights based on context

        body += f"""
{report['call_to_action']}

Best regards,
{agent_name}
"""

        return {
            "subject": subject,
            "body": body.strip(),
            "report_data": report
        }
