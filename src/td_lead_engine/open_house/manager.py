"""Open house event management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class OpenHouseStatus(Enum):
    """Open house status."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class OpenHouseAttendee:
    """An open house attendee."""
    id: str
    open_house_id: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    
    # Registration info
    registered_at: datetime = field(default_factory=datetime.now)
    checked_in: bool = False
    checked_in_at: datetime = None
    
    # Lead info
    lead_id: str = ""
    is_new_lead: bool = True
    
    # Interest
    working_with_agent: bool = False
    agent_name: str = ""
    preapproved: bool = False
    interest_level: int = 0  # 1-5
    timeframe: str = ""  # e.g., "1-3 months"
    budget_min: float = 0
    budget_max: float = 0
    
    # Notes
    notes: str = ""
    follow_up_priority: str = "medium"  # low, medium, high, hot
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class OpenHouse:
    """An open house event."""
    id: str
    property_id: str
    property_address: str
    
    # Timing
    date: datetime
    start_time: str  # "2:00 PM"
    end_time: str    # "4:00 PM"
    timezone: str = "America/New_York"
    
    # Status
    status: OpenHouseStatus = OpenHouseStatus.SCHEDULED
    
    # Hosting
    hosted_by: str = ""  # Agent ID
    hosted_by_name: str = ""
    
    # Marketing
    description: str = ""
    featured: bool = False
    syndicate: bool = True  # Post to Zillow, Realtor.com, etc.
    
    # Registration
    require_registration: bool = True
    registration_deadline: datetime = None
    max_capacity: int = 0  # 0 = unlimited
    
    # Attendees
    attendees: List[str] = field(default_factory=list)  # Attendee IDs
    expected_attendance: int = 0
    actual_attendance: int = 0
    
    # Virtual
    is_virtual: bool = False
    virtual_tour_url: str = ""
    
    # Follow-up
    follow_up_sent: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class OpenHouseManager:
    """Manage open house events."""
    
    def __init__(self, storage_path: str = "data/open_houses"):
        self.storage_path = storage_path
        self.open_houses: Dict[str, OpenHouse] = {}
        self.attendees: Dict[str, OpenHouseAttendee] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load open house data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load open houses
        oh_file = f"{self.storage_path}/open_houses.json"
        if os.path.exists(oh_file):
            with open(oh_file, 'r') as f:
                data = json.load(f)
                for oh_data in data:
                    oh = OpenHouse(
                        id=oh_data['id'],
                        property_id=oh_data['property_id'],
                        property_address=oh_data['property_address'],
                        date=datetime.fromisoformat(oh_data['date']),
                        start_time=oh_data['start_time'],
                        end_time=oh_data['end_time'],
                        timezone=oh_data.get('timezone', 'America/New_York'),
                        status=OpenHouseStatus(oh_data.get('status', 'scheduled')),
                        hosted_by=oh_data.get('hosted_by', ''),
                        hosted_by_name=oh_data.get('hosted_by_name', ''),
                        description=oh_data.get('description', ''),
                        featured=oh_data.get('featured', False),
                        syndicate=oh_data.get('syndicate', True),
                        require_registration=oh_data.get('require_registration', True),
                        registration_deadline=datetime.fromisoformat(oh_data['registration_deadline']) if oh_data.get('registration_deadline') else None,
                        max_capacity=oh_data.get('max_capacity', 0),
                        attendees=oh_data.get('attendees', []),
                        expected_attendance=oh_data.get('expected_attendance', 0),
                        actual_attendance=oh_data.get('actual_attendance', 0),
                        is_virtual=oh_data.get('is_virtual', False),
                        virtual_tour_url=oh_data.get('virtual_tour_url', ''),
                        follow_up_sent=oh_data.get('follow_up_sent', False),
                        created_at=datetime.fromisoformat(oh_data['created_at']) if oh_data.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(oh_data['updated_at']) if oh_data.get('updated_at') else datetime.now()
                    )
                    self.open_houses[oh.id] = oh
        
        # Load attendees
        attendees_file = f"{self.storage_path}/attendees.json"
        if os.path.exists(attendees_file):
            with open(attendees_file, 'r') as f:
                data = json.load(f)
                for att_data in data:
                    attendee = OpenHouseAttendee(
                        id=att_data['id'],
                        open_house_id=att_data['open_house_id'],
                        first_name=att_data['first_name'],
                        last_name=att_data['last_name'],
                        email=att_data['email'],
                        phone=att_data.get('phone', ''),
                        registered_at=datetime.fromisoformat(att_data['registered_at']) if att_data.get('registered_at') else datetime.now(),
                        checked_in=att_data.get('checked_in', False),
                        checked_in_at=datetime.fromisoformat(att_data['checked_in_at']) if att_data.get('checked_in_at') else None,
                        lead_id=att_data.get('lead_id', ''),
                        is_new_lead=att_data.get('is_new_lead', True),
                        working_with_agent=att_data.get('working_with_agent', False),
                        agent_name=att_data.get('agent_name', ''),
                        preapproved=att_data.get('preapproved', False),
                        interest_level=att_data.get('interest_level', 0),
                        timeframe=att_data.get('timeframe', ''),
                        budget_min=att_data.get('budget_min', 0),
                        budget_max=att_data.get('budget_max', 0),
                        notes=att_data.get('notes', ''),
                        follow_up_priority=att_data.get('follow_up_priority', 'medium')
                    )
                    self.attendees[attendee.id] = attendee
    
    def _save_data(self):
        """Save open house data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save open houses
        oh_data = [
            {
                'id': oh.id,
                'property_id': oh.property_id,
                'property_address': oh.property_address,
                'date': oh.date.isoformat(),
                'start_time': oh.start_time,
                'end_time': oh.end_time,
                'timezone': oh.timezone,
                'status': oh.status.value,
                'hosted_by': oh.hosted_by,
                'hosted_by_name': oh.hosted_by_name,
                'description': oh.description,
                'featured': oh.featured,
                'syndicate': oh.syndicate,
                'require_registration': oh.require_registration,
                'registration_deadline': oh.registration_deadline.isoformat() if oh.registration_deadline else None,
                'max_capacity': oh.max_capacity,
                'attendees': oh.attendees,
                'expected_attendance': oh.expected_attendance,
                'actual_attendance': oh.actual_attendance,
                'is_virtual': oh.is_virtual,
                'virtual_tour_url': oh.virtual_tour_url,
                'follow_up_sent': oh.follow_up_sent,
                'created_at': oh.created_at.isoformat(),
                'updated_at': oh.updated_at.isoformat()
            }
            for oh in self.open_houses.values()
        ]
        
        with open(f"{self.storage_path}/open_houses.json", 'w') as f:
            json.dump(oh_data, f, indent=2)
        
        # Save attendees
        attendees_data = [
            {
                'id': a.id,
                'open_house_id': a.open_house_id,
                'first_name': a.first_name,
                'last_name': a.last_name,
                'email': a.email,
                'phone': a.phone,
                'registered_at': a.registered_at.isoformat(),
                'checked_in': a.checked_in,
                'checked_in_at': a.checked_in_at.isoformat() if a.checked_in_at else None,
                'lead_id': a.lead_id,
                'is_new_lead': a.is_new_lead,
                'working_with_agent': a.working_with_agent,
                'agent_name': a.agent_name,
                'preapproved': a.preapproved,
                'interest_level': a.interest_level,
                'timeframe': a.timeframe,
                'budget_min': a.budget_min,
                'budget_max': a.budget_max,
                'notes': a.notes,
                'follow_up_priority': a.follow_up_priority
            }
            for a in self.attendees.values()
        ]
        
        with open(f"{self.storage_path}/attendees.json", 'w') as f:
            json.dump(attendees_data, f, indent=2)
    
    def create_open_house(
        self,
        property_id: str,
        property_address: str,
        date: datetime,
        start_time: str,
        end_time: str,
        hosted_by: str = "",
        hosted_by_name: str = "",
        description: str = "",
        require_registration: bool = True,
        max_capacity: int = 0,
        is_virtual: bool = False,
        virtual_tour_url: str = ""
    ) -> OpenHouse:
        """Create a new open house."""
        oh = OpenHouse(
            id=str(uuid.uuid4())[:8],
            property_id=property_id,
            property_address=property_address,
            date=date,
            start_time=start_time,
            end_time=end_time,
            hosted_by=hosted_by,
            hosted_by_name=hosted_by_name,
            description=description,
            require_registration=require_registration,
            max_capacity=max_capacity,
            is_virtual=is_virtual,
            virtual_tour_url=virtual_tour_url
        )
        
        # Set default registration deadline to 2 hours before
        if require_registration:
            oh.registration_deadline = date - timedelta(hours=2)
        
        self.open_houses[oh.id] = oh
        self._save_data()
        return oh
    
    def update_open_house(self, oh_id: str, updates: Dict) -> Optional[OpenHouse]:
        """Update an open house."""
        if oh_id not in self.open_houses:
            return None
        
        oh = self.open_houses[oh_id]
        for key, value in updates.items():
            if hasattr(oh, key):
                if key == 'status' and isinstance(value, str):
                    value = OpenHouseStatus(value)
                elif key in ['date', 'registration_deadline'] and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(oh, key, value)
        
        oh.updated_at = datetime.now()
        self._save_data()
        return oh
    
    def cancel_open_house(self, oh_id: str) -> bool:
        """Cancel an open house."""
        if oh_id in self.open_houses:
            self.open_houses[oh_id].status = OpenHouseStatus.CANCELLED
            self.open_houses[oh_id].updated_at = datetime.now()
            self._save_data()
            return True
        return False
    
    def delete_open_house(self, oh_id: str) -> bool:
        """Delete an open house."""
        if oh_id in self.open_houses:
            # Delete attendees
            attendee_ids = self.open_houses[oh_id].attendees
            for att_id in attendee_ids:
                if att_id in self.attendees:
                    del self.attendees[att_id]
            
            del self.open_houses[oh_id]
            self._save_data()
            return True
        return False
    
    def register_attendee(
        self,
        oh_id: str,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = "",
        working_with_agent: bool = False,
        preapproved: bool = False,
        timeframe: str = "",
        lead_id: str = ""
    ) -> Optional[OpenHouseAttendee]:
        """Register an attendee for an open house."""
        if oh_id not in self.open_houses:
            return None
        
        oh = self.open_houses[oh_id]
        
        # Check capacity
        if oh.max_capacity > 0 and len(oh.attendees) >= oh.max_capacity:
            return None
        
        # Check for existing registration
        for att_id in oh.attendees:
            if att_id in self.attendees:
                if self.attendees[att_id].email.lower() == email.lower():
                    return self.attendees[att_id]  # Already registered
        
        attendee = OpenHouseAttendee(
            id=str(uuid.uuid4())[:8],
            open_house_id=oh_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            working_with_agent=working_with_agent,
            preapproved=preapproved,
            timeframe=timeframe,
            lead_id=lead_id,
            is_new_lead=not bool(lead_id)
        )
        
        self.attendees[attendee.id] = attendee
        oh.attendees.append(attendee.id)
        oh.expected_attendance = len(oh.attendees)
        self._save_data()
        
        return attendee
    
    def check_in_attendee(self, attendee_id: str) -> Optional[OpenHouseAttendee]:
        """Check in an attendee."""
        if attendee_id not in self.attendees:
            return None
        
        attendee = self.attendees[attendee_id]
        attendee.checked_in = True
        attendee.checked_in_at = datetime.now()
        
        # Update actual attendance
        oh = self.open_houses.get(attendee.open_house_id)
        if oh:
            oh.actual_attendance = len([
                a for a in oh.attendees 
                if a in self.attendees and self.attendees[a].checked_in
            ])
        
        self._save_data()
        return attendee
    
    def update_attendee(self, attendee_id: str, updates: Dict) -> Optional[OpenHouseAttendee]:
        """Update an attendee."""
        if attendee_id not in self.attendees:
            return None
        
        attendee = self.attendees[attendee_id]
        for key, value in updates.items():
            if hasattr(attendee, key):
                setattr(attendee, key, value)
        
        self._save_data()
        return attendee
    
    def remove_attendee(self, attendee_id: str) -> bool:
        """Remove an attendee registration."""
        if attendee_id not in self.attendees:
            return False
        
        attendee = self.attendees[attendee_id]
        oh = self.open_houses.get(attendee.open_house_id)
        
        if oh and attendee_id in oh.attendees:
            oh.attendees.remove(attendee_id)
            oh.expected_attendance = len(oh.attendees)
        
        del self.attendees[attendee_id]
        self._save_data()
        return True
    
    def get_open_house(self, oh_id: str) -> Optional[OpenHouse]:
        """Get an open house by ID."""
        return self.open_houses.get(oh_id)
    
    def get_attendees(self, oh_id: str) -> List[OpenHouseAttendee]:
        """Get attendees for an open house."""
        if oh_id not in self.open_houses:
            return []
        
        return [
            self.attendees[att_id] 
            for att_id in self.open_houses[oh_id].attendees 
            if att_id in self.attendees
        ]
    
    def get_upcoming(self, days: int = 14, agent_id: str = None) -> List[OpenHouse]:
        """Get upcoming open houses."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)
        
        upcoming = [
            oh for oh in self.open_houses.values()
            if oh.status == OpenHouseStatus.SCHEDULED
            and now <= oh.date <= cutoff
        ]
        
        if agent_id:
            upcoming = [oh for oh in upcoming if oh.hosted_by == agent_id]
        
        upcoming.sort(key=lambda oh: oh.date)
        return upcoming
    
    def get_by_property(self, property_id: str) -> List[OpenHouse]:
        """Get open houses for a property."""
        return [
            oh for oh in self.open_houses.values()
            if oh.property_id == property_id
        ]
    
    def get_stats(self, agent_id: str = None, days: int = 90) -> Dict:
        """Get open house statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        open_houses = list(self.open_houses.values())
        if agent_id:
            open_houses = [oh for oh in open_houses if oh.hosted_by == agent_id]
        
        recent = [oh for oh in open_houses if oh.created_at > cutoff]
        completed = [oh for oh in recent if oh.status == OpenHouseStatus.COMPLETED]
        
        total_registrations = sum(oh.expected_attendance for oh in completed)
        total_attendance = sum(oh.actual_attendance for oh in completed)
        
        return {
            'total_open_houses': len(recent),
            'completed': len(completed),
            'cancelled': len([oh for oh in recent if oh.status == OpenHouseStatus.CANCELLED]),
            'upcoming': len([oh for oh in recent if oh.status == OpenHouseStatus.SCHEDULED]),
            'total_registrations': total_registrations,
            'total_attendance': total_attendance,
            'avg_attendance': total_attendance / len(completed) if completed else 0,
            'show_rate': (total_attendance / total_registrations * 100) if total_registrations > 0 else 0
        }
    
    def mark_completed(self, oh_id: str) -> Optional[OpenHouse]:
        """Mark an open house as completed."""
        if oh_id in self.open_houses:
            oh = self.open_houses[oh_id]
            oh.status = OpenHouseStatus.COMPLETED
            oh.updated_at = datetime.now()
            self._save_data()
            return oh
        return None
    
    def start_open_house(self, oh_id: str) -> Optional[OpenHouse]:
        """Mark an open house as in progress."""
        if oh_id in self.open_houses:
            oh = self.open_houses[oh_id]
            oh.status = OpenHouseStatus.IN_PROGRESS
            oh.updated_at = datetime.now()
            self._save_data()
            return oh
        return None
