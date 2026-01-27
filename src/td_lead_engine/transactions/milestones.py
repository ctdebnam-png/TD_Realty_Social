"""Transaction milestone tracking."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class MilestoneStatus(Enum):
    """Milestone completion status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    WAIVED = "waived"
    NA = "not_applicable"


@dataclass
class Milestone:
    """Transaction milestone."""

    id: str
    transaction_id: str
    name: str
    description: str = ""

    # Timing
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    reminder_date: Optional[datetime] = None

    # Status
    status: MilestoneStatus = MilestoneStatus.PENDING
    is_critical: bool = False  # Must complete for closing

    # Assignment
    responsible_party: str = ""  # "agent", "buyer", "seller", "lender", "title", etc.

    # Notes
    notes: str = ""

    created_at: datetime = field(default_factory=datetime.now)


# Standard milestone templates
BUYER_MILESTONES = [
    {"name": "Offer Submitted", "days_offset": 0, "responsible": "agent", "critical": True},
    {"name": "Offer Accepted", "days_offset": 1, "responsible": "agent", "critical": True},
    {"name": "Earnest Money Deposited", "days_offset": 3, "responsible": "buyer", "critical": True},
    {"name": "Home Inspection Scheduled", "days_offset": 5, "responsible": "agent", "critical": False},
    {"name": "Home Inspection Complete", "days_offset": 10, "responsible": "agent", "critical": True},
    {"name": "Inspection Response Sent", "days_offset": 12, "responsible": "agent", "critical": True},
    {"name": "Appraisal Ordered", "days_offset": 7, "responsible": "lender", "critical": True},
    {"name": "Appraisal Complete", "days_offset": 21, "responsible": "lender", "critical": True},
    {"name": "Loan Approval", "days_offset": 25, "responsible": "lender", "critical": True},
    {"name": "Clear to Close", "days_offset": 28, "responsible": "lender", "critical": True},
    {"name": "Final Walkthrough Scheduled", "days_offset": 29, "responsible": "agent", "critical": False},
    {"name": "Final Walkthrough Complete", "days_offset": 30, "responsible": "agent", "critical": True},
    {"name": "Closing", "days_offset": 30, "responsible": "agent", "critical": True},
]

SELLER_MILESTONES = [
    {"name": "Listing Agreement Signed", "days_offset": 0, "responsible": "agent", "critical": True},
    {"name": "Photos Scheduled", "days_offset": 2, "responsible": "agent", "critical": False},
    {"name": "Photos Complete", "days_offset": 5, "responsible": "agent", "critical": True},
    {"name": "Listed on MLS", "days_offset": 5, "responsible": "agent", "critical": True},
    {"name": "First Showing", "days_offset": 7, "responsible": "agent", "critical": False},
    {"name": "Offer Received", "days_offset": None, "responsible": "agent", "critical": True},
    {"name": "Offer Accepted", "days_offset": None, "responsible": "seller", "critical": True},
    {"name": "Inspection Complete", "days_offset": None, "responsible": "agent", "critical": True},
    {"name": "Inspection Repairs Complete", "days_offset": None, "responsible": "seller", "critical": False},
    {"name": "Appraisal Complete", "days_offset": None, "responsible": "agent", "critical": True},
    {"name": "Buyer Clear to Close", "days_offset": None, "responsible": "agent", "critical": True},
    {"name": "Closing", "days_offset": None, "responsible": "agent", "critical": True},
]


class MilestoneTracker:
    """Track milestones for transactions."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize milestone tracker."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "milestones.json"
        self.milestones: Dict[str, List[Milestone]] = {}  # By transaction_id
        self._load_data()

    def _load_data(self):
        """Load milestones from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for txn_id, milestone_list in data.get("milestones", {}).items():
                        self.milestones[txn_id] = []
                        for m_data in milestone_list:
                            milestone = Milestone(
                                id=m_data["id"],
                                transaction_id=m_data["transaction_id"],
                                name=m_data["name"],
                                description=m_data.get("description", ""),
                                due_date=datetime.fromisoformat(m_data["due_date"]) if m_data.get("due_date") else None,
                                completed_date=datetime.fromisoformat(m_data["completed_date"]) if m_data.get("completed_date") else None,
                                status=MilestoneStatus(m_data.get("status", "pending")),
                                is_critical=m_data.get("is_critical", False),
                                responsible_party=m_data.get("responsible_party", ""),
                                notes=m_data.get("notes", "")
                            )
                            self.milestones[txn_id].append(milestone)

            except Exception as e:
                logger.error(f"Error loading milestones: {e}")

    def _save_data(self):
        """Save milestones to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "milestones": {
                txn_id: [
                    {
                        "id": m.id,
                        "transaction_id": m.transaction_id,
                        "name": m.name,
                        "description": m.description,
                        "due_date": m.due_date.isoformat() if m.due_date else None,
                        "completed_date": m.completed_date.isoformat() if m.completed_date else None,
                        "status": m.status.value,
                        "is_critical": m.is_critical,
                        "responsible_party": m.responsible_party,
                        "notes": m.notes
                    }
                    for m in milestones
                ]
                for txn_id, milestones in self.milestones.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_buyer_milestones(
        self,
        transaction_id: str,
        contract_date: datetime,
        closing_date: datetime
    ) -> List[Milestone]:
        """Create standard buyer transaction milestones."""
        milestones = []
        days_to_close = (closing_date - contract_date).days

        for template in BUYER_MILESTONES:
            if template["days_offset"] is not None:
                # Scale days based on actual closing timeline
                scaled_days = int(template["days_offset"] * days_to_close / 30)
                due_date = contract_date + timedelta(days=scaled_days)
            else:
                due_date = None

            milestone = Milestone(
                id=str(uuid.uuid4())[:8],
                transaction_id=transaction_id,
                name=template["name"],
                due_date=due_date,
                is_critical=template["critical"],
                responsible_party=template["responsible"]
            )
            milestones.append(milestone)

        self.milestones[transaction_id] = milestones
        self._save_data()

        return milestones

    def create_seller_milestones(
        self,
        transaction_id: str,
        listing_date: datetime
    ) -> List[Milestone]:
        """Create standard seller/listing milestones."""
        milestones = []

        for template in SELLER_MILESTONES:
            if template["days_offset"] is not None:
                due_date = listing_date + timedelta(days=template["days_offset"])
            else:
                due_date = None

            milestone = Milestone(
                id=str(uuid.uuid4())[:8],
                transaction_id=transaction_id,
                name=template["name"],
                due_date=due_date,
                is_critical=template["critical"],
                responsible_party=template["responsible"]
            )
            milestones.append(milestone)

        self.milestones[transaction_id] = milestones
        self._save_data()

        return milestones

    def complete_milestone(
        self,
        transaction_id: str,
        milestone_id: str,
        notes: str = ""
    ) -> bool:
        """Mark a milestone as complete."""
        if transaction_id not in self.milestones:
            return False

        for milestone in self.milestones[transaction_id]:
            if milestone.id == milestone_id:
                milestone.status = MilestoneStatus.COMPLETED
                milestone.completed_date = datetime.now()
                if notes:
                    milestone.notes = notes
                self._save_data()
                return True

        return False

    def update_milestone_date(
        self,
        transaction_id: str,
        milestone_id: str,
        new_due_date: datetime
    ) -> bool:
        """Update milestone due date."""
        if transaction_id not in self.milestones:
            return False

        for milestone in self.milestones[transaction_id]:
            if milestone.id == milestone_id:
                milestone.due_date = new_due_date
                self._save_data()
                return True

        return False

    def get_transaction_milestones(self, transaction_id: str) -> List[Milestone]:
        """Get all milestones for a transaction."""
        return self.milestones.get(transaction_id, [])

    def get_pending_milestones(self, transaction_id: str) -> List[Milestone]:
        """Get pending milestones for a transaction."""
        return [
            m for m in self.milestones.get(transaction_id, [])
            if m.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]
        ]

    def get_overdue_milestones(self, transaction_id: Optional[str] = None) -> List[Milestone]:
        """Get overdue milestones."""
        now = datetime.now()
        overdue = []

        txn_ids = [transaction_id] if transaction_id else self.milestones.keys()

        for txn_id in txn_ids:
            for milestone in self.milestones.get(txn_id, []):
                if (milestone.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]
                    and milestone.due_date and milestone.due_date < now):
                    milestone.status = MilestoneStatus.OVERDUE
                    overdue.append(milestone)

        if overdue:
            self._save_data()

        return overdue

    def get_upcoming_milestones(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming milestones across all transactions."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        upcoming = []

        for txn_id, milestones in self.milestones.items():
            for m in milestones:
                if (m.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]
                    and m.due_date and now <= m.due_date <= cutoff):
                    upcoming.append({
                        "transaction_id": txn_id,
                        "milestone_id": m.id,
                        "name": m.name,
                        "due_date": m.due_date,
                        "days_until": (m.due_date - now).days,
                        "is_critical": m.is_critical,
                        "responsible": m.responsible_party
                    })

        return sorted(upcoming, key=lambda x: x["due_date"])

    def get_progress_summary(self, transaction_id: str) -> Dict[str, Any]:
        """Get milestone progress summary for a transaction."""
        milestones = self.milestones.get(transaction_id, [])

        if not milestones:
            return {"error": "No milestones found"}

        total = len(milestones)
        completed = len([m for m in milestones if m.status == MilestoneStatus.COMPLETED])
        overdue = len([m for m in milestones if m.status == MilestoneStatus.OVERDUE])
        pending = len([m for m in milestones if m.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]])

        critical_total = len([m for m in milestones if m.is_critical])
        critical_completed = len([m for m in milestones if m.is_critical and m.status == MilestoneStatus.COMPLETED])

        # Find next milestone
        next_milestone = None
        for m in milestones:
            if m.status in [MilestoneStatus.PENDING, MilestoneStatus.IN_PROGRESS]:
                if m.due_date:
                    if not next_milestone or m.due_date < next_milestone.due_date:
                        next_milestone = m

        return {
            "total_milestones": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "progress_percent": round(completed / total * 100, 1) if total > 0 else 0,
            "critical_progress": f"{critical_completed}/{critical_total}",
            "next_milestone": {
                "name": next_milestone.name,
                "due_date": next_milestone.due_date.isoformat() if next_milestone.due_date else None,
                "responsible": next_milestone.responsible_party
            } if next_milestone else None
        }
