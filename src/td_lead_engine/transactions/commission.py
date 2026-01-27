"""Commission calculation and tracking."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class SplitType(Enum):
    """Commission split types."""
    PERCENTAGE = "percentage"  # e.g., 70/30 split
    FLAT_FEE = "flat_fee"      # Agent pays flat fee to broker
    CAP = "cap"                # Percentage until cap, then 100%
    GRADUATED = "graduated"    # Different rates at different thresholds


@dataclass
class CommissionSplit:
    """Commission split configuration."""

    split_type: SplitType = SplitType.PERCENTAGE
    agent_percentage: float = 70.0  # Agent keeps 70%

    # For CAP model
    annual_cap: float = 21000.0  # Cap amount
    cap_split_before: float = 70.0
    cap_split_after: float = 100.0

    # For FLAT_FEE model
    flat_fee_per_transaction: float = 500.0

    # For GRADUATED model
    tiers: List[Dict[str, float]] = field(default_factory=list)
    # e.g., [{"threshold": 50000, "rate": 60}, {"threshold": 100000, "rate": 70}, {"threshold": None, "rate": 80}]


class CommissionCalculator:
    """Calculate commissions with various split models."""

    def __init__(self, split_config: Optional[CommissionSplit] = None):
        """Initialize calculator."""
        self.split_config = split_config or CommissionSplit()
        self.ytd_gross: float = 0.0  # For cap tracking

    def calculate(
        self,
        sale_price: int,
        commission_rate: float = 0.03,
        referral_fee: float = 0.0,
        referral_percentage: float = 0.0,
        transaction_fee: float = 0.0
    ) -> Dict[str, float]:
        """Calculate commission breakdown.

        Args:
            sale_price: Property sale price
            commission_rate: Commission rate (e.g., 0.03 for 3%)
            referral_fee: Fixed referral fee to pay out
            referral_percentage: Referral as percentage of gross (e.g., 0.25 for 25%)
            transaction_fee: Any transaction/admin fee

        Returns:
            Dictionary with commission breakdown
        """
        gross_commission = sale_price * commission_rate

        # Calculate referral
        if referral_percentage > 0:
            referral = gross_commission * referral_percentage
        else:
            referral = referral_fee

        # Commission after referral
        after_referral = gross_commission - referral

        # Calculate split based on model
        if self.split_config.split_type == SplitType.PERCENTAGE:
            agent_commission = after_referral * (self.split_config.agent_percentage / 100)
            broker_commission = after_referral - agent_commission

        elif self.split_config.split_type == SplitType.FLAT_FEE:
            broker_commission = self.split_config.flat_fee_per_transaction
            agent_commission = after_referral - broker_commission

        elif self.split_config.split_type == SplitType.CAP:
            # Check if cap is reached
            if self.ytd_gross >= self.split_config.annual_cap:
                # Agent keeps 100% (already capped)
                agent_commission = after_referral
                broker_commission = 0
            else:
                # Calculate with normal split
                agent_rate = self.split_config.cap_split_before / 100
                agent_commission = after_referral * agent_rate
                broker_commission = after_referral - agent_commission

                # Check if this transaction hits the cap
                potential_ytd = self.ytd_gross + broker_commission
                if potential_ytd > self.split_config.annual_cap:
                    # Partial cap hit
                    broker_to_cap = self.split_config.annual_cap - self.ytd_gross
                    remaining = broker_commission - broker_to_cap
                    agent_commission += remaining
                    broker_commission = broker_to_cap

        elif self.split_config.split_type == SplitType.GRADUATED:
            # Find applicable tier based on YTD
            agent_rate = 50.0  # Default
            for tier in self.split_config.tiers:
                if tier.get("threshold") is None or self.ytd_gross < tier["threshold"]:
                    agent_rate = tier["rate"]
                    break

            agent_commission = after_referral * (agent_rate / 100)
            broker_commission = after_referral - agent_commission

        else:
            # Default percentage split
            agent_commission = after_referral * 0.70
            broker_commission = after_referral * 0.30

        # Subtract transaction fee from agent
        net_to_agent = agent_commission - transaction_fee

        return {
            "sale_price": sale_price,
            "commission_rate": commission_rate,
            "gross_commission": round(gross_commission, 2),
            "referral_out": round(referral, 2),
            "after_referral": round(after_referral, 2),
            "broker_split": round(broker_commission, 2),
            "agent_gross": round(agent_commission, 2),
            "transaction_fee": transaction_fee,
            "agent_net": round(net_to_agent, 2),
            "effective_rate": round(net_to_agent / sale_price * 100, 3) if sale_price > 0 else 0
        }

    def estimate_annual_income(
        self,
        projected_transactions: int,
        avg_sale_price: int,
        commission_rate: float = 0.03,
        avg_referral_rate: float = 0.05  # 5% of deals have referral
    ) -> Dict[str, Any]:
        """Estimate annual income based on projected activity."""
        total_gross = 0
        total_net = 0

        # Reset YTD for projection
        original_ytd = self.ytd_gross
        self.ytd_gross = 0

        for i in range(projected_transactions):
            # Some deals have referrals
            referral = 0.25 if (i % int(1 / avg_referral_rate) == 0 and avg_referral_rate > 0) else 0

            result = self.calculate(
                sale_price=avg_sale_price,
                commission_rate=commission_rate,
                referral_percentage=referral
            )

            total_gross += result["gross_commission"]
            total_net += result["agent_net"]

            # Track for cap
            self.ytd_gross += result["broker_split"]

        # Restore original YTD
        self.ytd_gross = original_ytd

        return {
            "projected_transactions": projected_transactions,
            "avg_sale_price": avg_sale_price,
            "total_volume": projected_transactions * avg_sale_price,
            "total_gross_commission": round(total_gross, 2),
            "total_net_to_agent": round(total_net, 2),
            "avg_net_per_deal": round(total_net / projected_transactions, 2) if projected_transactions > 0 else 0,
            "effective_split": round(total_net / total_gross * 100, 1) if total_gross > 0 else 0
        }

    def compare_brokerages(
        self,
        sale_price: int,
        commission_rate: float,
        splits: Dict[str, CommissionSplit]
    ) -> Dict[str, Dict[str, float]]:
        """Compare commission across different brokerage models."""
        results = {}

        for brokerage_name, split_config in splits.items():
            calculator = CommissionCalculator(split_config)
            result = calculator.calculate(sale_price, commission_rate)
            results[brokerage_name] = result

        return results


def create_common_split_models() -> Dict[str, CommissionSplit]:
    """Create common brokerage split models for comparison."""
    return {
        "Traditional 70/30": CommissionSplit(
            split_type=SplitType.PERCENTAGE,
            agent_percentage=70.0
        ),
        "Traditional 80/20": CommissionSplit(
            split_type=SplitType.PERCENTAGE,
            agent_percentage=80.0
        ),
        "Keller Williams (70/30 + Cap)": CommissionSplit(
            split_type=SplitType.CAP,
            cap_split_before=70.0,
            cap_split_after=100.0,
            annual_cap=21000.0
        ),
        "eXp Realty (80/20 + Cap)": CommissionSplit(
            split_type=SplitType.CAP,
            cap_split_before=80.0,
            cap_split_after=100.0,
            annual_cap=16000.0
        ),
        "Flat Fee ($500/transaction)": CommissionSplit(
            split_type=SplitType.FLAT_FEE,
            flat_fee_per_transaction=500.0
        ),
        "100% Commission ($1000/mo + $250/txn)": CommissionSplit(
            split_type=SplitType.FLAT_FEE,
            flat_fee_per_transaction=250.0  # Plus monthly desk fee not included
        )
    }


class CommissionTracker:
    """Track commission income over time."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize tracker."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "commissions.json"
        self.records: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        """Load commission records."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    self.records = data.get("records", [])
            except Exception as e:
                logger.error(f"Error loading commissions: {e}")

    def _save_data(self):
        """Save commission records."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump({"records": self.records, "updated_at": datetime.now().isoformat()}, f, indent=2)

    def record_commission(
        self,
        transaction_id: str,
        close_date: datetime,
        gross_commission: float,
        net_commission: float,
        client_name: str,
        property_address: str,
        side: str
    ):
        """Record a commission payment."""
        self.records.append({
            "id": str(len(self.records) + 1),
            "transaction_id": transaction_id,
            "close_date": close_date.isoformat(),
            "gross_commission": gross_commission,
            "net_commission": net_commission,
            "client_name": client_name,
            "property_address": property_address,
            "side": side,
            "recorded_at": datetime.now().isoformat()
        })
        self._save_data()

    def get_ytd_income(self) -> Dict[str, Any]:
        """Get year-to-date income summary."""
        year_start = datetime.now().replace(month=1, day=1)

        ytd_records = [
            r for r in self.records
            if datetime.fromisoformat(r["close_date"]) >= year_start
        ]

        total_gross = sum(r["gross_commission"] for r in ytd_records)
        total_net = sum(r["net_commission"] for r in ytd_records)

        by_month = {}
        for r in ytd_records:
            month = datetime.fromisoformat(r["close_date"]).strftime("%Y-%m")
            if month not in by_month:
                by_month[month] = {"gross": 0, "net": 0, "count": 0}
            by_month[month]["gross"] += r["gross_commission"]
            by_month[month]["net"] += r["net_commission"]
            by_month[month]["count"] += 1

        return {
            "year": datetime.now().year,
            "total_transactions": len(ytd_records),
            "total_gross": total_gross,
            "total_net": total_net,
            "avg_per_deal": total_net / len(ytd_records) if ytd_records else 0,
            "by_month": by_month
        }

    def get_monthly_trend(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly commission trend."""
        from datetime import timedelta

        trends = []
        now = datetime.now()

        for i in range(months - 1, -1, -1):
            # Calculate month start/end
            month_date = now - timedelta(days=i * 30)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)

            month_records = [
                r for r in self.records
                if month_start <= datetime.fromisoformat(r["close_date"]) < month_end
            ]

            trends.append({
                "month": month_start.strftime("%Y-%m"),
                "transactions": len(month_records),
                "gross": sum(r["gross_commission"] for r in month_records),
                "net": sum(r["net_commission"] for r in month_records)
            })

        return trends
