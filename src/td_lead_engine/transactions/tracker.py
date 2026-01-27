"""Transaction tracking from contract to close."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TransactionStatus(Enum):
    """Transaction status stages."""
    PENDING = "pending"              # Offer accepted, not yet under contract
    UNDER_CONTRACT = "under_contract"
    INSPECTION_PERIOD = "inspection"
    APPRAISAL = "appraisal"
    FINANCING = "financing"
    TITLE_WORK = "title_work"
    FINAL_WALKTHROUGH = "final_walkthrough"
    CLOSING_SCHEDULED = "closing_scheduled"
    CLOSED = "closed"
    FELL_THROUGH = "fell_through"
    CANCELLED = "cancelled"


class TransactionSide(Enum):
    """Which side of the transaction."""
    BUYER = "buyer"
    SELLER = "seller"
    DUAL = "dual"  # Representing both


@dataclass
class Party:
    """Party involved in transaction."""
    name: str
    email: str = ""
    phone: str = ""
    role: str = ""  # "buyer", "seller", "buyer_agent", "seller_agent", "lender", "title", "attorney"
    company: str = ""


@dataclass
class Transaction:
    """Real estate transaction record."""

    id: str
    lead_id: Optional[str]  # Original lead that converted

    # Property
    property_address: str
    property_city: str
    property_state: str = "OH"
    property_zip: str = ""
    mls_number: str = ""
    property_type: str = ""  # single_family, condo, etc.

    # Pricing
    list_price: int = 0
    contract_price: int = 0
    final_price: int = 0  # After any adjustments

    # Side and representation
    side: TransactionSide = TransactionSide.BUYER
    representing: str = ""  # Client name

    # Dates
    offer_date: Optional[datetime] = None
    contract_date: Optional[datetime] = None
    inspection_deadline: Optional[datetime] = None
    appraisal_deadline: Optional[datetime] = None
    financing_deadline: Optional[datetime] = None
    closing_date: Optional[datetime] = None
    actual_close_date: Optional[datetime] = None

    # Status
    status: TransactionStatus = TransactionStatus.PENDING

    # Commission
    commission_rate: float = 0.03  # 3%
    commission_amount: float = 0.0
    split_rate: float = 0.70  # 70% to agent
    net_commission: float = 0.0
    referral_fee: float = 0.0
    referral_to: str = ""

    # Parties
    parties: List[Party] = field(default_factory=list)

    # Documents and notes
    notes: str = ""
    documents: List[str] = field(default_factory=list)

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def calculate_commission(self):
        """Calculate commission amounts."""
        price = self.final_price or self.contract_price
        self.commission_amount = price * self.commission_rate
        net = self.commission_amount * self.split_rate
        self.net_commission = net - self.referral_fee

    @property
    def days_to_close(self) -> Optional[int]:
        """Days from contract to scheduled close."""
        if self.contract_date and self.closing_date:
            return (self.closing_date - self.contract_date).days
        return None

    @property
    def days_until_close(self) -> Optional[int]:
        """Days remaining until closing."""
        if self.closing_date and self.status not in [TransactionStatus.CLOSED, TransactionStatus.FELL_THROUGH]:
            return (self.closing_date - datetime.now()).days
        return None


class TransactionTracker:
    """Track and manage real estate transactions."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize transaction tracker."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "transactions.json"
        self.transactions: Dict[str, Transaction] = {}
        self._load_data()

    def _load_data(self):
        """Load transactions from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for txn_data in data.get("transactions", []):
                        parties = [
                            Party(**p) for p in txn_data.get("parties", [])
                        ]

                        txn = Transaction(
                            id=txn_data["id"],
                            lead_id=txn_data.get("lead_id"),
                            property_address=txn_data["property_address"],
                            property_city=txn_data["property_city"],
                            property_state=txn_data.get("property_state", "OH"),
                            property_zip=txn_data.get("property_zip", ""),
                            mls_number=txn_data.get("mls_number", ""),
                            property_type=txn_data.get("property_type", ""),
                            list_price=txn_data.get("list_price", 0),
                            contract_price=txn_data.get("contract_price", 0),
                            final_price=txn_data.get("final_price", 0),
                            side=TransactionSide(txn_data.get("side", "buyer")),
                            representing=txn_data.get("representing", ""),
                            status=TransactionStatus(txn_data.get("status", "pending")),
                            commission_rate=txn_data.get("commission_rate", 0.03),
                            commission_amount=txn_data.get("commission_amount", 0),
                            split_rate=txn_data.get("split_rate", 0.70),
                            net_commission=txn_data.get("net_commission", 0),
                            referral_fee=txn_data.get("referral_fee", 0),
                            referral_to=txn_data.get("referral_to", ""),
                            parties=parties,
                            notes=txn_data.get("notes", ""),
                            documents=txn_data.get("documents", []),
                            created_at=datetime.fromisoformat(txn_data["created_at"]),
                            updated_at=datetime.fromisoformat(txn_data["updated_at"])
                        )

                        # Parse dates
                        for date_field in ["offer_date", "contract_date", "inspection_deadline",
                                          "appraisal_deadline", "financing_deadline",
                                          "closing_date", "actual_close_date"]:
                            if txn_data.get(date_field):
                                setattr(txn, date_field, datetime.fromisoformat(txn_data[date_field]))

                        self.transactions[txn.id] = txn

            except Exception as e:
                logger.error(f"Error loading transactions: {e}")

    def _save_data(self):
        """Save transactions to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        def serialize_date(dt):
            return dt.isoformat() if dt else None

        data = {
            "transactions": [
                {
                    "id": t.id,
                    "lead_id": t.lead_id,
                    "property_address": t.property_address,
                    "property_city": t.property_city,
                    "property_state": t.property_state,
                    "property_zip": t.property_zip,
                    "mls_number": t.mls_number,
                    "property_type": t.property_type,
                    "list_price": t.list_price,
                    "contract_price": t.contract_price,
                    "final_price": t.final_price,
                    "side": t.side.value,
                    "representing": t.representing,
                    "offer_date": serialize_date(t.offer_date),
                    "contract_date": serialize_date(t.contract_date),
                    "inspection_deadline": serialize_date(t.inspection_deadline),
                    "appraisal_deadline": serialize_date(t.appraisal_deadline),
                    "financing_deadline": serialize_date(t.financing_deadline),
                    "closing_date": serialize_date(t.closing_date),
                    "actual_close_date": serialize_date(t.actual_close_date),
                    "status": t.status.value,
                    "commission_rate": t.commission_rate,
                    "commission_amount": t.commission_amount,
                    "split_rate": t.split_rate,
                    "net_commission": t.net_commission,
                    "referral_fee": t.referral_fee,
                    "referral_to": t.referral_to,
                    "parties": [
                        {"name": p.name, "email": p.email, "phone": p.phone,
                         "role": p.role, "company": p.company}
                        for p in t.parties
                    ],
                    "notes": t.notes,
                    "documents": t.documents,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat()
                }
                for t in self.transactions.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_transaction(
        self,
        property_address: str,
        property_city: str,
        contract_price: int,
        side: TransactionSide,
        representing: str,
        lead_id: Optional[str] = None,
        closing_date: Optional[datetime] = None,
        commission_rate: float = 0.03
    ) -> Transaction:
        """Create a new transaction."""
        txn_id = str(uuid.uuid4())[:8]

        txn = Transaction(
            id=txn_id,
            lead_id=lead_id,
            property_address=property_address,
            property_city=property_city,
            contract_price=contract_price,
            side=side,
            representing=representing,
            contract_date=datetime.now(),
            closing_date=closing_date,
            commission_rate=commission_rate,
            status=TransactionStatus.UNDER_CONTRACT
        )

        txn.calculate_commission()
        self.transactions[txn_id] = txn
        self._save_data()

        logger.info(f"Created transaction {txn_id}: {property_address}")
        return txn

    def update_status(self, txn_id: str, status: TransactionStatus, notes: str = "") -> bool:
        """Update transaction status."""
        txn = self.transactions.get(txn_id)
        if not txn:
            return False

        old_status = txn.status
        txn.status = status
        txn.updated_at = datetime.now()

        if notes:
            txn.notes = f"{txn.notes}\n[{datetime.now().strftime('%Y-%m-%d')}] Status: {old_status.value} → {status.value}. {notes}".strip()

        if status == TransactionStatus.CLOSED:
            txn.actual_close_date = datetime.now()
            if not txn.final_price:
                txn.final_price = txn.contract_price
            txn.calculate_commission()

        self._save_data()
        return True

    def add_party(self, txn_id: str, party: Party) -> bool:
        """Add a party to a transaction."""
        txn = self.transactions.get(txn_id)
        if not txn:
            return False

        txn.parties.append(party)
        txn.updated_at = datetime.now()
        self._save_data()
        return True

    def get_active_transactions(self) -> List[Transaction]:
        """Get all active (not closed/cancelled) transactions."""
        active_statuses = [
            TransactionStatus.PENDING,
            TransactionStatus.UNDER_CONTRACT,
            TransactionStatus.INSPECTION_PERIOD,
            TransactionStatus.APPRAISAL,
            TransactionStatus.FINANCING,
            TransactionStatus.TITLE_WORK,
            TransactionStatus.FINAL_WALKTHROUGH,
            TransactionStatus.CLOSING_SCHEDULED
        ]

        return [t for t in self.transactions.values() if t.status in active_statuses]

    def get_closing_this_month(self) -> List[Transaction]:
        """Get transactions closing this month."""
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            month_end = month_start.replace(year=now.year + 1, month=1)
        else:
            month_end = month_start.replace(month=now.month + 1)

        return [
            t for t in self.transactions.values()
            if t.closing_date and month_start <= t.closing_date < month_end
            and t.status not in [TransactionStatus.FELL_THROUGH, TransactionStatus.CANCELLED]
        ]

    def get_upcoming_deadlines(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming deadlines across all active transactions."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        deadlines = []

        for txn in self.get_active_transactions():
            deadline_fields = [
                ("inspection_deadline", "Inspection Deadline"),
                ("appraisal_deadline", "Appraisal Deadline"),
                ("financing_deadline", "Financing Deadline"),
                ("closing_date", "Closing Date")
            ]

            for field, label in deadline_fields:
                deadline = getattr(txn, field)
                if deadline and now <= deadline <= cutoff:
                    deadlines.append({
                        "transaction_id": txn.id,
                        "property": txn.property_address,
                        "client": txn.representing,
                        "deadline_type": label,
                        "deadline_date": deadline,
                        "days_until": (deadline - now).days
                    })

        return sorted(deadlines, key=lambda x: x["deadline_date"])

    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get pipeline summary."""
        active = self.get_active_transactions()
        closing_this_month = self.get_closing_this_month()

        total_volume = sum(t.contract_price for t in active)
        total_commission = sum(t.net_commission for t in active)
        month_volume = sum(t.contract_price for t in closing_this_month)
        month_commission = sum(t.net_commission for t in closing_this_month)

        by_status = {}
        for t in active:
            status = t.status.value
            if status not in by_status:
                by_status[status] = {"count": 0, "volume": 0}
            by_status[status]["count"] += 1
            by_status[status]["volume"] += t.contract_price

        by_side = {"buyer": 0, "seller": 0, "dual": 0}
        for t in active:
            by_side[t.side.value] += 1

        return {
            "active_transactions": len(active),
            "closing_this_month": len(closing_this_month),
            "total_pipeline_volume": total_volume,
            "total_pipeline_commission": total_commission,
            "month_projected_volume": month_volume,
            "month_projected_commission": month_commission,
            "by_status": by_status,
            "by_side": by_side,
            "upcoming_deadlines": len(self.get_upcoming_deadlines(7))
        }

    def get_ytd_stats(self) -> Dict[str, Any]:
        """Get year-to-date statistics."""
        year_start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        closed = [
            t for t in self.transactions.values()
            if t.status == TransactionStatus.CLOSED
            and t.actual_close_date and t.actual_close_date >= year_start
        ]

        fell_through = [
            t for t in self.transactions.values()
            if t.status == TransactionStatus.FELL_THROUGH
            and t.updated_at >= year_start
        ]

        total_volume = sum(t.final_price for t in closed)
        total_gross = sum(t.commission_amount for t in closed)
        total_net = sum(t.net_commission for t in closed)
        avg_price = total_volume / len(closed) if closed else 0
        avg_commission = total_net / len(closed) if closed else 0

        buyer_deals = len([t for t in closed if t.side == TransactionSide.BUYER])
        seller_deals = len([t for t in closed if t.side == TransactionSide.SELLER])

        return {
            "year": datetime.now().year,
            "closed_transactions": len(closed),
            "fell_through": len(fell_through),
            "close_rate": len(closed) / (len(closed) + len(fell_through)) * 100 if (closed or fell_through) else 0,
            "total_volume": total_volume,
            "total_gross_commission": total_gross,
            "total_net_commission": total_net,
            "avg_sale_price": avg_price,
            "avg_commission": avg_commission,
            "buyer_side_deals": buyer_deals,
            "seller_side_deals": seller_deals
        }
