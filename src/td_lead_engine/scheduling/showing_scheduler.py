"""Showing scheduler for property tours."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ShowingStatus(Enum):
    """Showing request status."""
    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class ShowingType(Enum):
    """Type of showing."""
    BUYER_TOUR = "buyer_tour"
    OPEN_HOUSE = "open_house"
    BROKER_OPEN = "broker_open"
    PRIVATE_SHOWING = "private_showing"
    VIRTUAL_TOUR = "virtual_tour"
    INSPECTION = "inspection"
    APPRAISAL = "appraisal"
    FINAL_WALKTHROUGH = "final_walkthrough"


@dataclass
class TimeSlot:
    """Available time slot."""

    date: datetime
    start_time: time
    end_time: time
    available: bool = True
    booked_by: str = ""


@dataclass
class ShowingRequest:
    """Showing request."""

    id: str
    property_id: str
    property_address: str

    # Requestor info
    buyer_name: str
    buyer_phone: str
    buyer_email: str
    buyer_agent_name: str = ""
    buyer_agent_phone: str = ""

    # Showing details
    showing_type: ShowingType = ShowingType.BUYER_TOUR
    requested_date: Optional[datetime] = None
    requested_time: Optional[time] = None
    alternate_times: List[Tuple[datetime, time]] = field(default_factory=list)

    # Confirmed details
    confirmed_date: Optional[datetime] = None
    confirmed_time: Optional[time] = None
    duration_minutes: int = 30

    # Status
    status: ShowingStatus = ShowingStatus.REQUESTED
    approval_required: bool = True  # Needs seller/listing agent approval

    # Access
    access_type: str = "lockbox"  # "lockbox", "agent_accompanied", "seller_present", "supra"
    lockbox_code: str = ""
    access_instructions: str = ""

    # Notes
    special_requests: str = ""  # "Interested in basement", "Has small children", etc.
    internal_notes: str = ""

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    confirmed_at: Optional[datetime] = None
    reminder_sent: bool = False

    # Feedback
    feedback_received: bool = False
    interest_level: str = ""  # "very_interested", "interested", "maybe", "not_interested"
    feedback_notes: str = ""


class ShowingScheduler:
    """Manage property showings."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize showing scheduler."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "showings.json"
        self.showings: Dict[str, ShowingRequest] = {}  # By showing_id
        self.property_showings: Dict[str, List[str]] = {}  # property_id -> [showing_ids]
        self._load_data()

        # Default settings
        self.default_duration = 30  # minutes
        self.buffer_between_showings = 15  # minutes
        self.advance_notice_hours = 2
        self.max_showings_per_day = 10

    def _load_data(self):
        """Load showing data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for showing_data in data.get("showings", []):
                        showing = ShowingRequest(
                            id=showing_data["id"],
                            property_id=showing_data["property_id"],
                            property_address=showing_data["property_address"],
                            buyer_name=showing_data["buyer_name"],
                            buyer_phone=showing_data.get("buyer_phone", ""),
                            buyer_email=showing_data.get("buyer_email", ""),
                            buyer_agent_name=showing_data.get("buyer_agent_name", ""),
                            showing_type=ShowingType(showing_data.get("showing_type", "buyer_tour")),
                            status=ShowingStatus(showing_data.get("status", "requested")),
                            duration_minutes=showing_data.get("duration_minutes", 30),
                            created_at=datetime.fromisoformat(showing_data["created_at"])
                        )

                        if showing_data.get("confirmed_date"):
                            showing.confirmed_date = datetime.fromisoformat(showing_data["confirmed_date"])
                        if showing_data.get("confirmed_time"):
                            showing.confirmed_time = time.fromisoformat(showing_data["confirmed_time"])

                        self.showings[showing.id] = showing

                        # Index by property
                        if showing.property_id not in self.property_showings:
                            self.property_showings[showing.property_id] = []
                        self.property_showings[showing.property_id].append(showing.id)

            except Exception as e:
                logger.error(f"Error loading showings: {e}")

    def _save_data(self):
        """Save showing data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "showings": [
                {
                    "id": s.id,
                    "property_id": s.property_id,
                    "property_address": s.property_address,
                    "buyer_name": s.buyer_name,
                    "buyer_phone": s.buyer_phone,
                    "buyer_email": s.buyer_email,
                    "buyer_agent_name": s.buyer_agent_name,
                    "showing_type": s.showing_type.value,
                    "status": s.status.value,
                    "confirmed_date": s.confirmed_date.isoformat() if s.confirmed_date else None,
                    "confirmed_time": s.confirmed_time.isoformat() if s.confirmed_time else None,
                    "duration_minutes": s.duration_minutes,
                    "access_type": s.access_type,
                    "special_requests": s.special_requests,
                    "feedback_received": s.feedback_received,
                    "interest_level": s.interest_level,
                    "created_at": s.created_at.isoformat()
                }
                for s in self.showings.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def request_showing(
        self,
        property_id: str,
        property_address: str,
        buyer_name: str,
        buyer_phone: str,
        buyer_email: str,
        requested_datetime: datetime,
        buyer_agent_name: str = "",
        buyer_agent_phone: str = "",
        showing_type: ShowingType = ShowingType.BUYER_TOUR,
        special_requests: str = "",
        alternate_times: List[datetime] = None
    ) -> ShowingRequest:
        """Request a property showing."""
        showing_id = str(uuid.uuid4())[:8]

        showing = ShowingRequest(
            id=showing_id,
            property_id=property_id,
            property_address=property_address,
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            buyer_email=buyer_email,
            buyer_agent_name=buyer_agent_name,
            buyer_agent_phone=buyer_agent_phone,
            showing_type=showing_type,
            requested_date=requested_datetime.date() if hasattr(requested_datetime, 'date') else requested_datetime,
            requested_time=requested_datetime.time() if hasattr(requested_datetime, 'time') else time(10, 0),
            special_requests=special_requests,
            status=ShowingStatus.PENDING_APPROVAL
        )

        if alternate_times:
            showing.alternate_times = [
                (dt.date() if hasattr(dt, 'date') else dt, dt.time() if hasattr(dt, 'time') else time(10, 0))
                for dt in alternate_times
            ]

        self.showings[showing_id] = showing

        if property_id not in self.property_showings:
            self.property_showings[property_id] = []
        self.property_showings[property_id].append(showing_id)

        self._save_data()
        return showing

    def confirm_showing(
        self,
        showing_id: str,
        confirmed_datetime: datetime,
        lockbox_code: str = "",
        access_instructions: str = ""
    ) -> bool:
        """Confirm a showing request."""
        showing = self.showings.get(showing_id)
        if not showing:
            return False

        showing.status = ShowingStatus.CONFIRMED
        showing.confirmed_date = confirmed_datetime
        showing.confirmed_time = confirmed_datetime.time() if hasattr(confirmed_datetime, 'time') else time(10, 0)
        showing.confirmed_at = datetime.now()
        showing.lockbox_code = lockbox_code
        showing.access_instructions = access_instructions

        self._save_data()

        # Would send confirmation notifications here
        logger.info(f"Showing confirmed: {showing.property_address} for {showing.buyer_name}")

        return True

    def reschedule_showing(
        self,
        showing_id: str,
        new_datetime: datetime,
        reason: str = ""
    ) -> bool:
        """Reschedule a showing."""
        showing = self.showings.get(showing_id)
        if not showing:
            return False

        showing.status = ShowingStatus.RESCHEDULED
        showing.confirmed_date = new_datetime
        showing.confirmed_time = new_datetime.time() if hasattr(new_datetime, 'time') else time(10, 0)
        if reason:
            showing.internal_notes += f"\nRescheduled: {reason}"

        self._save_data()
        return True

    def cancel_showing(self, showing_id: str, reason: str = "") -> bool:
        """Cancel a showing."""
        showing = self.showings.get(showing_id)
        if not showing:
            return False

        showing.status = ShowingStatus.CANCELLED
        if reason:
            showing.internal_notes += f"\nCancelled: {reason}"

        self._save_data()
        return True

    def complete_showing(
        self,
        showing_id: str,
        interest_level: str = "",
        feedback: str = ""
    ) -> bool:
        """Mark showing as completed with optional feedback."""
        showing = self.showings.get(showing_id)
        if not showing:
            return False

        showing.status = ShowingStatus.COMPLETED
        if interest_level:
            showing.feedback_received = True
            showing.interest_level = interest_level
            showing.feedback_notes = feedback

        self._save_data()
        return True

    def mark_no_show(self, showing_id: str, notes: str = "") -> bool:
        """Mark showing as no-show."""
        showing = self.showings.get(showing_id)
        if not showing:
            return False

        showing.status = ShowingStatus.NO_SHOW
        if notes:
            showing.internal_notes += f"\nNo-show: {notes}"

        self._save_data()
        return True

    def get_property_showings(
        self,
        property_id: str,
        status: Optional[ShowingStatus] = None,
        from_date: Optional[datetime] = None
    ) -> List[ShowingRequest]:
        """Get showings for a property."""
        showing_ids = self.property_showings.get(property_id, [])
        showings = [self.showings[sid] for sid in showing_ids if sid in self.showings]

        if status:
            showings = [s for s in showings if s.status == status]

        if from_date:
            showings = [s for s in showings if s.confirmed_date and s.confirmed_date >= from_date]

        return sorted(showings, key=lambda x: (x.confirmed_date or datetime.max, x.confirmed_time or time.max))

    def get_upcoming_showings(
        self,
        agent_id: str = "",
        days: int = 7
    ) -> List[ShowingRequest]:
        """Get upcoming confirmed showings."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        upcoming = []
        for showing in self.showings.values():
            if showing.status == ShowingStatus.CONFIRMED and showing.confirmed_date:
                showing_dt = datetime.combine(showing.confirmed_date, showing.confirmed_time or time(0, 0))
                if now <= showing_dt <= cutoff:
                    upcoming.append(showing)

        return sorted(upcoming, key=lambda x: datetime.combine(x.confirmed_date, x.confirmed_time or time(0, 0)))

    def get_pending_approvals(self) -> List[ShowingRequest]:
        """Get showings pending approval."""
        return [
            s for s in self.showings.values()
            if s.status == ShowingStatus.PENDING_APPROVAL
        ]

    def get_todays_showings(self) -> List[ShowingRequest]:
        """Get today's confirmed showings."""
        today = datetime.now().date()
        return [
            s for s in self.showings.values()
            if s.status == ShowingStatus.CONFIRMED
            and s.confirmed_date
            and s.confirmed_date == today
        ]

    def check_availability(
        self,
        property_id: str,
        date: datetime,
        requested_time: time,
        duration: int = 30
    ) -> Dict[str, Any]:
        """Check if a time slot is available."""
        showings = self.get_property_showings(property_id, ShowingStatus.CONFIRMED)

        requested_start = datetime.combine(date, requested_time)
        requested_end = requested_start + timedelta(minutes=duration)

        conflicts = []
        for showing in showings:
            if showing.confirmed_date == date.date():
                showing_start = datetime.combine(showing.confirmed_date, showing.confirmed_time)
                showing_end = showing_start + timedelta(minutes=showing.duration_minutes + self.buffer_between_showings)

                if (requested_start < showing_end and requested_end > showing_start):
                    conflicts.append({
                        "id": showing.id,
                        "time": showing.confirmed_time.isoformat(),
                        "buyer": showing.buyer_agent_name or showing.buyer_name
                    })

        return {
            "available": len(conflicts) == 0,
            "requested_time": requested_time.isoformat(),
            "conflicts": conflicts,
            "next_available": self._find_next_available(property_id, date, duration) if conflicts else None
        }

    def _find_next_available(
        self,
        property_id: str,
        date: datetime,
        duration: int
    ) -> Optional[str]:
        """Find next available time slot."""
        showings = self.get_property_showings(property_id, ShowingStatus.CONFIRMED)
        booked_times = [
            (s.confirmed_time, s.duration_minutes)
            for s in showings
            if s.confirmed_date == date.date()
        ]

        # Check times from 9 AM to 7 PM
        for hour in range(9, 19):
            for minute in [0, 30]:
                check_time = time(hour, minute)
                available = True

                for booked_time, booked_duration in booked_times:
                    booked_start = datetime.combine(date.date(), booked_time)
                    booked_end = booked_start + timedelta(minutes=booked_duration + self.buffer_between_showings)
                    check_start = datetime.combine(date.date(), check_time)
                    check_end = check_start + timedelta(minutes=duration)

                    if check_start < booked_end and check_end > booked_start:
                        available = False
                        break

                if available:
                    return check_time.isoformat()

        return None

    def get_available_slots(
        self,
        property_id: str,
        date: datetime,
        start_hour: int = 9,
        end_hour: int = 19
    ) -> List[TimeSlot]:
        """Get available time slots for a date."""
        showings = self.get_property_showings(property_id, ShowingStatus.CONFIRMED)
        booked = {}

        for s in showings:
            if s.confirmed_date == date.date() and s.confirmed_time:
                key = s.confirmed_time.isoformat()
                booked[key] = s.buyer_agent_name or s.buyer_name

        slots = []
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                slot_time = time(hour, minute)
                slot_key = slot_time.isoformat()

                slots.append(TimeSlot(
                    date=date,
                    start_time=slot_time,
                    end_time=time(hour if minute == 0 else hour + 1, 30 if minute == 0 else 0),
                    available=slot_key not in booked,
                    booked_by=booked.get(slot_key, "")
                ))

        return slots

    def send_reminders(self) -> List[str]:
        """Send reminders for upcoming showings."""
        tomorrow = datetime.now().date() + timedelta(days=1)
        reminders_sent = []

        for showing in self.showings.values():
            if (showing.status == ShowingStatus.CONFIRMED
                and showing.confirmed_date == tomorrow
                and not showing.reminder_sent):

                # Would send actual reminder here
                logger.info(f"Sending reminder for {showing.property_address} to {showing.buyer_email}")
                showing.reminder_sent = True
                reminders_sent.append(showing.id)

        if reminders_sent:
            self._save_data()

        return reminders_sent

    def get_showing_statistics(self, property_id: Optional[str] = None) -> Dict[str, Any]:
        """Get showing statistics."""
        if property_id:
            showings = self.get_property_showings(property_id)
        else:
            showings = list(self.showings.values())

        total = len(showings)
        completed = len([s for s in showings if s.status == ShowingStatus.COMPLETED])
        cancelled = len([s for s in showings if s.status == ShowingStatus.CANCELLED])
        no_shows = len([s for s in showings if s.status == ShowingStatus.NO_SHOW])

        # Feedback analysis
        with_feedback = [s for s in showings if s.feedback_received]
        interest_breakdown = {}
        for s in with_feedback:
            level = s.interest_level or "unknown"
            interest_breakdown[level] = interest_breakdown.get(level, 0) + 1

        return {
            "total_showings": total,
            "completed": completed,
            "cancelled": cancelled,
            "no_shows": no_shows,
            "completion_rate": f"{(completed/total*100):.1f}%" if total > 0 else "N/A",
            "feedback_collected": len(with_feedback),
            "interest_breakdown": interest_breakdown,
            "pending_approval": len([s for s in showings if s.status == ShowingStatus.PENDING_APPROVAL]),
            "upcoming": len([s for s in showings if s.status == ShowingStatus.CONFIRMED])
        }

    def get_daily_schedule(self, date: datetime = None) -> Dict[str, Any]:
        """Get formatted daily schedule."""
        target_date = (date or datetime.now()).date()

        day_showings = [
            s for s in self.showings.values()
            if s.status == ShowingStatus.CONFIRMED
            and s.confirmed_date == target_date
        ]

        day_showings.sort(key=lambda x: x.confirmed_time or time(0, 0))

        schedule = {
            "date": target_date.isoformat(),
            "total_showings": len(day_showings),
            "schedule": [
                {
                    "time": s.confirmed_time.isoformat() if s.confirmed_time else "TBD",
                    "end_time": (datetime.combine(target_date, s.confirmed_time) + timedelta(minutes=s.duration_minutes)).time().isoformat() if s.confirmed_time else "TBD",
                    "property": s.property_address,
                    "buyer": s.buyer_name,
                    "agent": s.buyer_agent_name,
                    "phone": s.buyer_agent_phone or s.buyer_phone,
                    "type": s.showing_type.value,
                    "access": s.access_type,
                    "notes": s.special_requests
                }
                for s in day_showings
            ]
        }

        return schedule
