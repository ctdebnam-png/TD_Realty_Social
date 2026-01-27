"""Revenue and lead forecasting."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import math

logger = logging.getLogger(__name__)


@dataclass
class LeadForecast:
    """Forecast for lead generation."""

    period: str
    predicted_leads: int
    confidence_low: int
    confidence_high: int
    growth_rate: float


@dataclass
class RevenueForecast:
    """Revenue forecast data."""

    period: str
    predicted_revenue: float
    predicted_transactions: int
    confidence_low: float
    confidence_high: float
    pipeline_contribution: float
    new_lead_contribution: float


class ForecastEngine:
    """Generate forecasts for leads and revenue."""

    def __init__(
        self,
        historical_leads: Optional[List[Dict[str, Any]]] = None,
        historical_revenue: Optional[List[Dict[str, Any]]] = None,
        pipeline_value: float = 0,
        avg_transaction_value: float = 350000,
        commission_rate: float = 0.03
    ):
        """Initialize forecast engine."""
        self.historical_leads = historical_leads or []
        self.historical_revenue = historical_revenue or []
        self.pipeline_value = pipeline_value
        self.avg_transaction_value = avg_transaction_value
        self.commission_rate = commission_rate
        self.avg_commission = avg_transaction_value * commission_rate

    def forecast_leads(self, months_ahead: int = 6) -> List[LeadForecast]:
        """Forecast lead generation for upcoming months."""
        forecasts = []

        # Calculate historical trend
        if len(self.historical_leads) >= 3:
            recent_leads = [d.get("count", 0) for d in self.historical_leads[-6:]]
            avg_leads = sum(recent_leads) / len(recent_leads)

            # Calculate growth rate
            if len(recent_leads) >= 2 and recent_leads[0] > 0:
                growth_rate = (recent_leads[-1] - recent_leads[0]) / recent_leads[0] / len(recent_leads)
            else:
                growth_rate = 0
        else:
            avg_leads = 20  # Default assumption
            growth_rate = 0.05  # 5% monthly growth default

        # Apply seasonality (real estate patterns)
        seasonality = {
            1: 0.7,   # January - slow
            2: 0.8,   # February
            3: 1.0,   # March - spring pickup
            4: 1.2,   # April - peak
            5: 1.3,   # May - peak
            6: 1.2,   # June
            7: 1.0,   # July
            8: 0.9,   # August
            9: 1.0,   # September
            10: 1.0,  # October
            11: 0.8,  # November
            12: 0.6   # December - holiday slow
        }

        current_date = datetime.now()

        for i in range(1, months_ahead + 1):
            future_date = current_date + timedelta(days=30 * i)
            month = future_date.month

            # Base prediction with growth
            base_prediction = avg_leads * ((1 + growth_rate) ** i)

            # Apply seasonality
            seasonal_factor = seasonality.get(month, 1.0)
            predicted = int(base_prediction * seasonal_factor)

            # Confidence interval (widens with time)
            uncertainty = 0.15 + (0.05 * i)
            confidence_low = int(predicted * (1 - uncertainty))
            confidence_high = int(predicted * (1 + uncertainty))

            forecasts.append(LeadForecast(
                period=future_date.strftime("%Y-%m"),
                predicted_leads=predicted,
                confidence_low=confidence_low,
                confidence_high=confidence_high,
                growth_rate=growth_rate
            ))

        return forecasts

    def forecast_revenue(self, months_ahead: int = 6) -> List[RevenueForecast]:
        """Forecast revenue for upcoming months."""
        forecasts = []

        # Get lead forecast
        lead_forecasts = self.forecast_leads(months_ahead)

        # Historical conversion rate
        if self.historical_revenue:
            total_revenue = sum(d.get("revenue", 0) for d in self.historical_revenue)
            total_transactions = sum(d.get("transactions", 0) for d in self.historical_revenue)

            if total_transactions > 0:
                avg_commission = total_revenue / total_transactions
            else:
                avg_commission = self.avg_commission
        else:
            avg_commission = self.avg_commission

        # Conversion rate from leads to closed
        conversion_rate = 0.03  # 3% default, would calculate from actual data

        # Average time to close (months)
        avg_close_time = 3

        for i, lead_forecast in enumerate(lead_forecasts):
            month_num = i + 1

            # Revenue from pipeline (higher probability for near-term)
            if month_num <= 2:
                pipeline_close_rate = 0.3
            elif month_num <= 4:
                pipeline_close_rate = 0.2
            else:
                pipeline_close_rate = 0.1

            pipeline_revenue = self.pipeline_value * pipeline_close_rate / months_ahead

            # Revenue from leads generated earlier (with lag)
            if month_num > avg_close_time and len(lead_forecasts) > month_num - avg_close_time:
                lagged_leads = lead_forecasts[month_num - avg_close_time - 1].predicted_leads
            else:
                lagged_leads = lead_forecast.predicted_leads * 0.5  # Assume some existing leads

            new_lead_revenue = lagged_leads * conversion_rate * avg_commission

            total_revenue = pipeline_revenue + new_lead_revenue
            predicted_transactions = int(total_revenue / avg_commission) if avg_commission > 0 else 0

            # Confidence interval
            uncertainty = 0.2 + (0.05 * month_num)
            confidence_low = total_revenue * (1 - uncertainty)
            confidence_high = total_revenue * (1 + uncertainty)

            forecasts.append(RevenueForecast(
                period=lead_forecast.period,
                predicted_revenue=round(total_revenue, 2),
                predicted_transactions=predicted_transactions,
                confidence_low=round(confidence_low, 2),
                confidence_high=round(confidence_high, 2),
                pipeline_contribution=round(pipeline_revenue, 2),
                new_lead_contribution=round(new_lead_revenue, 2)
            ))

        return forecasts

    def calculate_goal_requirements(
        self,
        annual_revenue_goal: float,
        current_ytd_revenue: float = 0
    ) -> Dict[str, Any]:
        """Calculate what's needed to hit revenue goal."""
        remaining_goal = annual_revenue_goal - current_ytd_revenue

        # Months remaining in year
        current_month = datetime.now().month
        months_remaining = 12 - current_month + 1

        if months_remaining <= 0:
            months_remaining = 12

        monthly_needed = remaining_goal / months_remaining
        transactions_needed = remaining_goal / self.avg_commission

        # Leads needed (assuming 3% conversion)
        conversion_rate = 0.03
        leads_needed = transactions_needed / conversion_rate

        return {
            "annual_goal": annual_revenue_goal,
            "current_ytd": current_ytd_revenue,
            "remaining_goal": remaining_goal,
            "months_remaining": months_remaining,
            "monthly_revenue_needed": round(monthly_needed, 2),
            "transactions_needed": round(transactions_needed, 1),
            "leads_needed": round(leads_needed, 0),
            "leads_per_month": round(leads_needed / months_remaining, 0),
            "assumed_conversion_rate": conversion_rate,
            "assumed_avg_commission": self.avg_commission,
            "on_track": current_ytd_revenue >= (annual_revenue_goal * current_month / 12),
            "recommendations": self._generate_goal_recommendations(
                monthly_needed, leads_needed / months_remaining
            )
        }

    def _generate_goal_recommendations(
        self,
        monthly_revenue_needed: float,
        leads_per_month_needed: float
    ) -> List[str]:
        """Generate recommendations to hit goals."""
        recommendations = []

        if leads_per_month_needed > 50:
            recommendations.append(
                "Consider increasing ad spend - you need significant lead volume"
            )

        if leads_per_month_needed > 30:
            recommendations.append(
                "Focus on improving lead quality over quantity"
            )

        recommendations.extend([
            "Nurture existing pipeline leads - fastest path to revenue",
            "Ask past clients for referrals - higher conversion rate",
            "Speed up response time to new leads - improves conversion 5x",
        ])

        if monthly_revenue_needed > self.avg_commission * 3:
            recommendations.append(
                "Look for higher-value opportunities to hit goals faster"
            )

        return recommendations

    def scenario_analysis(
        self,
        scenarios: Dict[str, Dict[str, float]]
    ) -> Dict[str, Dict[str, Any]]:
        """Run scenario analysis for different assumptions.

        Example scenarios:
        {
            "conservative": {"lead_growth": 0.0, "conversion_rate": 0.02},
            "base": {"lead_growth": 0.05, "conversion_rate": 0.03},
            "optimistic": {"lead_growth": 0.10, "conversion_rate": 0.05}
        }
        """
        results = {}

        for scenario_name, params in scenarios.items():
            lead_growth = params.get("lead_growth", 0.05)
            conversion_rate = params.get("conversion_rate", 0.03)

            # Calculate 12-month projection
            monthly_leads = 25  # Base assumption

            total_leads = 0
            total_revenue = 0

            for month in range(12):
                leads = monthly_leads * ((1 + lead_growth) ** month)
                total_leads += leads

                # Revenue from leads with 3-month lag
                if month >= 3:
                    lagged_leads = monthly_leads * ((1 + lead_growth) ** (month - 3))
                    revenue = lagged_leads * conversion_rate * self.avg_commission
                    total_revenue += revenue

            results[scenario_name] = {
                "total_leads": int(total_leads),
                "total_transactions": int(total_leads * conversion_rate),
                "total_revenue": round(total_revenue, 2),
                "avg_monthly_revenue": round(total_revenue / 12, 2),
                "parameters": params
            }

        return results

    def break_even_analysis(
        self,
        monthly_costs: float,
        ad_spend: float
    ) -> Dict[str, Any]:
        """Calculate break-even requirements."""
        total_monthly_costs = monthly_costs + ad_spend
        annual_costs = total_monthly_costs * 12

        # Transactions needed to break even
        transactions_for_breakeven = annual_costs / self.avg_commission

        # Leads needed
        conversion_rate = 0.03
        leads_for_breakeven = transactions_for_breakeven / conversion_rate

        # Cost per lead allowed
        max_cost_per_lead = ad_spend * 12 / leads_for_breakeven if leads_for_breakeven > 0 else 0

        return {
            "monthly_costs": monthly_costs,
            "monthly_ad_spend": ad_spend,
            "annual_total_costs": annual_costs,
            "transactions_to_breakeven": round(transactions_for_breakeven, 1),
            "leads_needed_annually": round(leads_for_breakeven, 0),
            "leads_needed_monthly": round(leads_for_breakeven / 12, 0),
            "max_cost_per_lead": round(max_cost_per_lead, 2),
            "breakeven_volume": round(transactions_for_breakeven * self.avg_transaction_value, 0),
            "note": "Assumes 3% lead-to-close conversion rate"
        }

    def what_if_analysis(
        self,
        variable: str,
        current_value: float,
        test_values: List[float]
    ) -> List[Dict[str, Any]]:
        """Run what-if analysis on a single variable.

        Variables: "conversion_rate", "avg_transaction", "commission_rate", "lead_volume"
        """
        results = []

        for test_value in test_values:
            if variable == "conversion_rate":
                leads = 25 * 12  # Assume 25 leads/month
                revenue = leads * test_value * self.avg_commission
            elif variable == "avg_transaction":
                transactions = 10  # Assume 10 transactions
                revenue = transactions * test_value * self.commission_rate
            elif variable == "commission_rate":
                transactions = 10
                revenue = transactions * self.avg_transaction_value * test_value
            elif variable == "lead_volume":
                conversion_rate = 0.03
                revenue = test_value * 12 * conversion_rate * self.avg_commission
            else:
                continue

            change = ((test_value - current_value) / current_value * 100) if current_value > 0 else 0

            results.append({
                "variable": variable,
                "value": test_value,
                "change_from_current": f"{change:+.1f}%",
                "projected_annual_revenue": round(revenue, 2)
            })

        return results
