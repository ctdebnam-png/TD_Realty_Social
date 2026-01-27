"""ROI tracking and cost attribution for lead sources."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


@dataclass
class LeadCost:
    """Cost associated with acquiring a lead."""

    source: str  # "instagram_ads", "facebook_ads", "google_ads", etc.
    campaign: str
    cost: float
    date: datetime

    # Optional granular tracking
    impressions: int = 0
    clicks: int = 0
    leads_generated: int = 1

    @property
    def cost_per_lead(self) -> float:
        """Calculate cost per lead."""
        return self.cost / self.leads_generated if self.leads_generated > 0 else self.cost

    @property
    def cost_per_click(self) -> float:
        """Calculate cost per click."""
        return self.cost / self.clicks if self.clicks > 0 else 0

    @property
    def click_through_rate(self) -> float:
        """Calculate click through rate."""
        return (self.clicks / self.impressions * 100) if self.impressions > 0 else 0


@dataclass
class ConversionEvent:
    """A conversion event (lead becomes client, transaction closes)."""

    id: str
    lead_id: str
    lead_source: str
    event_type: str  # "client_signed", "under_contract", "closed"

    # Financial
    transaction_value: float  # Sale price
    commission_rate: float  # e.g., 0.03 for 3%
    gross_commission: float
    net_commission: float  # After splits

    # Attribution
    campaign: str = ""
    first_touch_source: str = ""
    last_touch_source: str = ""

    # Timing
    lead_created_at: datetime = None
    converted_at: datetime = field(default_factory=datetime.now)

    @property
    def days_to_convert(self) -> int:
        """Days from lead creation to conversion."""
        if self.lead_created_at:
            return (self.converted_at - self.lead_created_at).days
        return 0


class ROITracker:
    """Track ROI across lead sources and campaigns."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize ROI tracker."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "roi_data.json"
        self.costs: List[LeadCost] = []
        self.conversions: List[ConversionEvent] = []
        self._load_data()

    def _load_data(self):
        """Load historical data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for cost_data in data.get("costs", []):
                        self.costs.append(LeadCost(
                            source=cost_data["source"],
                            campaign=cost_data["campaign"],
                            cost=cost_data["cost"],
                            date=datetime.fromisoformat(cost_data["date"]),
                            impressions=cost_data.get("impressions", 0),
                            clicks=cost_data.get("clicks", 0),
                            leads_generated=cost_data.get("leads_generated", 1)
                        ))

                    for conv_data in data.get("conversions", []):
                        self.conversions.append(ConversionEvent(
                            id=conv_data["id"],
                            lead_id=conv_data["lead_id"],
                            lead_source=conv_data["lead_source"],
                            event_type=conv_data["event_type"],
                            transaction_value=conv_data["transaction_value"],
                            commission_rate=conv_data["commission_rate"],
                            gross_commission=conv_data["gross_commission"],
                            net_commission=conv_data["net_commission"],
                            campaign=conv_data.get("campaign", ""),
                            first_touch_source=conv_data.get("first_touch_source", ""),
                            last_touch_source=conv_data.get("last_touch_source", ""),
                            lead_created_at=datetime.fromisoformat(conv_data["lead_created_at"]) if conv_data.get("lead_created_at") else None,
                            converted_at=datetime.fromisoformat(conv_data["converted_at"])
                        ))

            except Exception as e:
                logger.error(f"Error loading ROI data: {e}")

    def _save_data(self):
        """Save data to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "costs": [
                {
                    "source": c.source,
                    "campaign": c.campaign,
                    "cost": c.cost,
                    "date": c.date.isoformat(),
                    "impressions": c.impressions,
                    "clicks": c.clicks,
                    "leads_generated": c.leads_generated
                }
                for c in self.costs
            ],
            "conversions": [
                {
                    "id": c.id,
                    "lead_id": c.lead_id,
                    "lead_source": c.lead_source,
                    "event_type": c.event_type,
                    "transaction_value": c.transaction_value,
                    "commission_rate": c.commission_rate,
                    "gross_commission": c.gross_commission,
                    "net_commission": c.net_commission,
                    "campaign": c.campaign,
                    "first_touch_source": c.first_touch_source,
                    "last_touch_source": c.last_touch_source,
                    "lead_created_at": c.lead_created_at.isoformat() if c.lead_created_at else None,
                    "converted_at": c.converted_at.isoformat()
                }
                for c in self.conversions
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def record_cost(
        self,
        source: str,
        campaign: str,
        cost: float,
        date: Optional[datetime] = None,
        impressions: int = 0,
        clicks: int = 0,
        leads_generated: int = 1
    ) -> LeadCost:
        """Record advertising/marketing cost."""
        lead_cost = LeadCost(
            source=source,
            campaign=campaign,
            cost=cost,
            date=date or datetime.now(),
            impressions=impressions,
            clicks=clicks,
            leads_generated=leads_generated
        )

        self.costs.append(lead_cost)
        self._save_data()

        return lead_cost

    def record_conversion(
        self,
        lead_id: str,
        lead_source: str,
        event_type: str,
        transaction_value: float,
        commission_rate: float = 0.03,
        split_rate: float = 0.7,
        campaign: str = "",
        lead_created_at: Optional[datetime] = None
    ) -> ConversionEvent:
        """Record a conversion event."""
        gross_commission = transaction_value * commission_rate
        net_commission = gross_commission * split_rate

        conversion = ConversionEvent(
            id=str(uuid.uuid4())[:8],
            lead_id=lead_id,
            lead_source=lead_source,
            event_type=event_type,
            transaction_value=transaction_value,
            commission_rate=commission_rate,
            gross_commission=gross_commission,
            net_commission=net_commission,
            campaign=campaign,
            first_touch_source=lead_source,
            last_touch_source=lead_source,
            lead_created_at=lead_created_at
        )

        self.conversions.append(conversion)
        self._save_data()

        return conversion

    def get_roi_by_source(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate ROI by lead source."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        # Aggregate costs by source
        costs_by_source: Dict[str, float] = {}
        leads_by_source: Dict[str, int] = {}

        for cost in self.costs:
            if start_date <= cost.date <= end_date:
                costs_by_source[cost.source] = costs_by_source.get(cost.source, 0) + cost.cost
                leads_by_source[cost.source] = leads_by_source.get(cost.source, 0) + cost.leads_generated

        # Aggregate revenue by source
        revenue_by_source: Dict[str, float] = {}
        conversions_by_source: Dict[str, int] = {}

        for conv in self.conversions:
            if start_date <= conv.converted_at <= end_date:
                revenue_by_source[conv.lead_source] = revenue_by_source.get(conv.lead_source, 0) + conv.net_commission
                conversions_by_source[conv.lead_source] = conversions_by_source.get(conv.lead_source, 0) + 1

        # Calculate ROI for each source
        all_sources = set(costs_by_source.keys()) | set(revenue_by_source.keys())
        results = {}

        for source in all_sources:
            cost = costs_by_source.get(source, 0)
            revenue = revenue_by_source.get(source, 0)
            leads = leads_by_source.get(source, 0)
            conversions = conversions_by_source.get(source, 0)

            roi = ((revenue - cost) / cost * 100) if cost > 0 else (100 if revenue > 0 else 0)
            conversion_rate = (conversions / leads * 100) if leads > 0 else 0
            cost_per_conversion = cost / conversions if conversions > 0 else cost

            results[source] = {
                "total_cost": cost,
                "total_revenue": revenue,
                "net_profit": revenue - cost,
                "roi_percent": round(roi, 1),
                "leads_generated": leads,
                "conversions": conversions,
                "conversion_rate": round(conversion_rate, 1),
                "cost_per_lead": round(cost / leads, 2) if leads > 0 else 0,
                "cost_per_conversion": round(cost_per_conversion, 2),
                "revenue_per_lead": round(revenue / leads, 2) if leads > 0 else 0,
                "profitable": revenue > cost
            }

        return results

    def get_roi_by_campaign(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate ROI by campaign."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        # Filter by source if specified
        filtered_costs = [
            c for c in self.costs
            if start_date <= c.date <= end_date and (not source or c.source == source)
        ]

        filtered_conversions = [
            c for c in self.conversions
            if start_date <= c.converted_at <= end_date and (not source or c.lead_source == source)
        ]

        # Aggregate by campaign
        costs_by_campaign: Dict[str, float] = {}
        leads_by_campaign: Dict[str, int] = {}

        for cost in filtered_costs:
            costs_by_campaign[cost.campaign] = costs_by_campaign.get(cost.campaign, 0) + cost.cost
            leads_by_campaign[cost.campaign] = leads_by_campaign.get(cost.campaign, 0) + cost.leads_generated

        revenue_by_campaign: Dict[str, float] = {}
        conversions_by_campaign: Dict[str, int] = {}

        for conv in filtered_conversions:
            revenue_by_campaign[conv.campaign] = revenue_by_campaign.get(conv.campaign, 0) + conv.net_commission
            conversions_by_campaign[conv.campaign] = conversions_by_campaign.get(conv.campaign, 0) + 1

        # Calculate ROI
        all_campaigns = set(costs_by_campaign.keys()) | set(revenue_by_campaign.keys())
        results = {}

        for campaign in all_campaigns:
            if not campaign:
                continue

            cost = costs_by_campaign.get(campaign, 0)
            revenue = revenue_by_campaign.get(campaign, 0)
            leads = leads_by_campaign.get(campaign, 0)
            conversions = conversions_by_campaign.get(campaign, 0)

            roi = ((revenue - cost) / cost * 100) if cost > 0 else (100 if revenue > 0 else 0)

            results[campaign] = {
                "total_cost": cost,
                "total_revenue": revenue,
                "roi_percent": round(roi, 1),
                "leads": leads,
                "conversions": conversions,
                "profitable": revenue > cost
            }

        return results

    def get_summary(self, period_days: int = 365) -> Dict[str, Any]:
        """Get overall ROI summary."""
        start_date = datetime.now() - timedelta(days=period_days)

        total_cost = sum(c.cost for c in self.costs if c.date >= start_date)
        total_leads = sum(c.leads_generated for c in self.costs if c.date >= start_date)
        total_revenue = sum(c.net_commission for c in self.conversions if c.converted_at >= start_date)
        total_conversions = len([c for c in self.conversions if c.converted_at >= start_date])
        total_volume = sum(c.transaction_value for c in self.conversions if c.converted_at >= start_date)

        roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0
        conversion_rate = (total_conversions / total_leads * 100) if total_leads > 0 else 0

        # Best performing source
        roi_by_source = self.get_roi_by_source(start_date)
        best_source = max(roi_by_source.items(), key=lambda x: x[1]["roi_percent"])[0] if roi_by_source else None

        # Average days to close
        days_to_close = [c.days_to_convert for c in self.conversions if c.converted_at >= start_date and c.days_to_convert > 0]
        avg_days = sum(days_to_close) / len(days_to_close) if days_to_close else 0

        return {
            "period_days": period_days,
            "total_cost": total_cost,
            "total_leads": total_leads,
            "total_conversions": total_conversions,
            "total_revenue": total_revenue,
            "total_volume": total_volume,
            "net_profit": total_revenue - total_cost,
            "roi_percent": round(roi, 1),
            "conversion_rate": round(conversion_rate, 2),
            "cost_per_lead": round(total_cost / total_leads, 2) if total_leads > 0 else 0,
            "cost_per_conversion": round(total_cost / total_conversions, 2) if total_conversions > 0 else 0,
            "avg_commission": round(total_revenue / total_conversions, 2) if total_conversions > 0 else 0,
            "avg_days_to_close": round(avg_days, 1),
            "best_performing_source": best_source
        }

    def get_monthly_trends(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly ROI trends."""
        trends = []

        for i in range(months, 0, -1):
            end_date = datetime.now() - timedelta(days=(i - 1) * 30)
            start_date = end_date - timedelta(days=30)

            month_costs = sum(c.cost for c in self.costs if start_date <= c.date <= end_date)
            month_leads = sum(c.leads_generated for c in self.costs if start_date <= c.date <= end_date)
            month_revenue = sum(c.net_commission for c in self.conversions if start_date <= c.converted_at <= end_date)
            month_conversions = len([c for c in self.conversions if start_date <= c.converted_at <= end_date])

            roi = ((month_revenue - month_costs) / month_costs * 100) if month_costs > 0 else 0

            trends.append({
                "month": start_date.strftime("%Y-%m"),
                "cost": month_costs,
                "revenue": month_revenue,
                "leads": month_leads,
                "conversions": month_conversions,
                "roi_percent": round(roi, 1)
            })

        return trends

    def recommend_budget_allocation(self, total_budget: float) -> Dict[str, float]:
        """Recommend budget allocation based on historical performance."""
        roi_by_source = self.get_roi_by_source()

        if not roi_by_source:
            # Default allocation if no history
            return {
                "instagram_ads": total_budget * 0.25,
                "facebook_ads": total_budget * 0.25,
                "google_ads": total_budget * 0.30,
                "content_marketing": total_budget * 0.10,
                "referral_program": total_budget * 0.10
            }

        # Weight by ROI, but cap any single source at 40%
        total_roi = sum(max(0, data["roi_percent"]) for data in roi_by_source.values())

        if total_roi == 0:
            # Even distribution if no positive ROI
            equal_share = total_budget / len(roi_by_source)
            return {source: equal_share for source in roi_by_source}

        allocation = {}
        for source, data in roi_by_source.items():
            if data["roi_percent"] > 0:
                share = data["roi_percent"] / total_roi
                share = min(share, 0.40)  # Cap at 40%
                allocation[source] = total_budget * share
            else:
                allocation[source] = total_budget * 0.05  # Minimum 5% to test

        # Normalize to total budget
        current_total = sum(allocation.values())
        if current_total > 0:
            factor = total_budget / current_total
            allocation = {source: amount * factor for source, amount in allocation.items()}

        return allocation
