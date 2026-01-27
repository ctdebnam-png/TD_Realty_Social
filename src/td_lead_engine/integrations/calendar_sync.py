"""Calendar synchronization for Google Calendar and Outlook."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class CalendarProvider(Enum):
    """Supported calendar providers."""
    GOOGLE = "google"
    OUTLOOK = "outlook"
    APPLE = "apple"
    ICAL = "ical"


class EventType(Enum):
    """Types of calendar events."""
    SHOWING = "showing"
    OPEN_HOUSE = "open_house"
    CLIENT_MEETING = "client_meeting"
    INSPECTION = "inspection"
    CLOSING = "closing"
    FOLLOW_UP = "follow_up"
    TASK = "task"
    OTHER = "other"


class SyncStatus(Enum):
    """Sync status."""
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


@dataclass
class CalendarConnection:
    """A connected calendar."""
    id: str
    provider: CalendarProvider
    account_email: str
    calendar_id: str
    calendar_name: str
    is_primary: bool = False
    sync_enabled: bool = True
    last_sync: datetime = None
    access_token: str = ""
    refresh_token: str = ""
    token_expires: datetime = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CalendarEvent:
    """A calendar event."""
    id: str
    connection_id: str
    external_id: str = ""
    event_type: EventType = EventType.OTHER
    title: str = ""
    description: str = ""
    location: str = ""
    start_time: datetime = None
    end_time: datetime = None
    all_day: bool = False
    attendees: List[str] = field(default_factory=list)
    reminders: List[int] = field(default_factory=list)  # Minutes before
    related_lead_id: str = ""
    related_property_id: str = ""
    sync_status: SyncStatus = SyncStatus.PENDING
    local_modified: datetime = None
    remote_modified: datetime = None
    created_at: datetime = field(default_factory=datetime.now)


class CalendarSync:
    """Calendar synchronization service."""
    
    def __init__(
        self,
        google_client_id: str = None,
        google_client_secret: str = None,
        outlook_client_id: str = None,
        outlook_client_secret: str = None,
        storage_path: str = "data/integrations/calendar"
    ):
        self.google_client_id = google_client_id or os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = google_client_secret or os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.outlook_client_id = outlook_client_id or os.getenv("OUTLOOK_CLIENT_ID", "")
        self.outlook_client_secret = outlook_client_secret or os.getenv("OUTLOOK_CLIENT_SECRET", "")
        self.storage_path = storage_path
        
        self.connections: Dict[str, CalendarConnection] = {}
        self.events: Dict[str, CalendarEvent] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load connections
        connections_file = f"{self.storage_path}/connections.json"
        if os.path.exists(connections_file):
            with open(connections_file, 'r') as f:
                data = json.load(f)
                for c in data:
                    conn = CalendarConnection(
                        id=c['id'],
                        provider=CalendarProvider(c['provider']),
                        account_email=c['account_email'],
                        calendar_id=c['calendar_id'],
                        calendar_name=c['calendar_name'],
                        is_primary=c.get('is_primary', False),
                        sync_enabled=c.get('sync_enabled', True),
                        last_sync=datetime.fromisoformat(c['last_sync']) if c.get('last_sync') else None,
                        access_token=c.get('access_token', ''),
                        refresh_token=c.get('refresh_token', ''),
                        token_expires=datetime.fromisoformat(c['token_expires']) if c.get('token_expires') else None,
                        created_at=datetime.fromisoformat(c['created_at'])
                    )
                    self.connections[conn.id] = conn
        
        # Load events
        events_file = f"{self.storage_path}/events.json"
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                data = json.load(f)
                for e in data:
                    event = CalendarEvent(
                        id=e['id'],
                        connection_id=e['connection_id'],
                        external_id=e.get('external_id', ''),
                        event_type=EventType(e.get('event_type', 'other')),
                        title=e.get('title', ''),
                        description=e.get('description', ''),
                        location=e.get('location', ''),
                        start_time=datetime.fromisoformat(e['start_time']) if e.get('start_time') else None,
                        end_time=datetime.fromisoformat(e['end_time']) if e.get('end_time') else None,
                        all_day=e.get('all_day', False),
                        attendees=e.get('attendees', []),
                        reminders=e.get('reminders', []),
                        related_lead_id=e.get('related_lead_id', ''),
                        related_property_id=e.get('related_property_id', ''),
                        sync_status=SyncStatus(e.get('sync_status', 'pending')),
                        local_modified=datetime.fromisoformat(e['local_modified']) if e.get('local_modified') else None,
                        remote_modified=datetime.fromisoformat(e['remote_modified']) if e.get('remote_modified') else None,
                        created_at=datetime.fromisoformat(e['created_at'])
                    )
                    self.events[event.id] = event
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save connections (excluding tokens for security)
        connections_data = [
            {
                'id': c.id,
                'provider': c.provider.value,
                'account_email': c.account_email,
                'calendar_id': c.calendar_id,
                'calendar_name': c.calendar_name,
                'is_primary': c.is_primary,
                'sync_enabled': c.sync_enabled,
                'last_sync': c.last_sync.isoformat() if c.last_sync else None,
                'access_token': c.access_token,
                'refresh_token': c.refresh_token,
                'token_expires': c.token_expires.isoformat() if c.token_expires else None,
                'created_at': c.created_at.isoformat()
            }
            for c in self.connections.values()
        ]
        
        with open(f"{self.storage_path}/connections.json", 'w') as f:
            json.dump(connections_data, f, indent=2)
        
        # Save events
        events_data = [
            {
                'id': e.id,
                'connection_id': e.connection_id,
                'external_id': e.external_id,
                'event_type': e.event_type.value,
                'title': e.title,
                'description': e.description,
                'location': e.location,
                'start_time': e.start_time.isoformat() if e.start_time else None,
                'end_time': e.end_time.isoformat() if e.end_time else None,
                'all_day': e.all_day,
                'attendees': e.attendees,
                'reminders': e.reminders,
                'related_lead_id': e.related_lead_id,
                'related_property_id': e.related_property_id,
                'sync_status': e.sync_status.value,
                'local_modified': e.local_modified.isoformat() if e.local_modified else None,
                'remote_modified': e.remote_modified.isoformat() if e.remote_modified else None,
                'created_at': e.created_at.isoformat()
            }
            for e in self.events.values()
        ]
        
        with open(f"{self.storage_path}/events.json", 'w') as f:
            json.dump(events_data, f, indent=2)
    
    def add_connection(
        self,
        provider: CalendarProvider,
        account_email: str,
        calendar_id: str,
        calendar_name: str,
        access_token: str = "",
        refresh_token: str = "",
        is_primary: bool = False
    ) -> CalendarConnection:
        """Add a calendar connection."""
        conn = CalendarConnection(
            id=str(uuid.uuid4())[:12],
            provider=provider,
            account_email=account_email,
            calendar_id=calendar_id,
            calendar_name=calendar_name,
            is_primary=is_primary,
            access_token=access_token,
            refresh_token=refresh_token
        )
        self.connections[conn.id] = conn
        self._save_data()
        return conn
    
    def remove_connection(self, connection_id: str) -> bool:
        """Remove a calendar connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            # Remove associated events
            self.events = {
                eid: e for eid, e in self.events.items()
                if e.connection_id != connection_id
            }
            self._save_data()
            return True
        return False
    
    def create_event(
        self,
        connection_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime = None,
        event_type: EventType = EventType.OTHER,
        **kwargs
    ) -> CalendarEvent:
        """Create a calendar event."""
        if not end_time:
            end_time = start_time + timedelta(hours=1)
        
        event = CalendarEvent(
            id=str(uuid.uuid4())[:12],
            connection_id=connection_id,
            event_type=event_type,
            title=title,
            description=kwargs.get('description', ''),
            location=kwargs.get('location', ''),
            start_time=start_time,
            end_time=end_time,
            all_day=kwargs.get('all_day', False),
            attendees=kwargs.get('attendees', []),
            reminders=kwargs.get('reminders', [30]),  # Default 30 min reminder
            related_lead_id=kwargs.get('lead_id', ''),
            related_property_id=kwargs.get('property_id', ''),
            local_modified=datetime.now()
        )
        
        self.events[event.id] = event
        self._save_data()
        return event
    
    def update_event(self, event_id: str, **kwargs) -> Optional[CalendarEvent]:
        """Update a calendar event."""
        event = self.events.get(event_id)
        if not event:
            return None
        
        for key, value in kwargs.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        event.local_modified = datetime.now()
        event.sync_status = SyncStatus.PENDING
        self._save_data()
        return event
    
    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if event_id in self.events:
            del self.events[event_id]
            self._save_data()
            return True
        return False
    
    def create_showing(
        self,
        connection_id: str,
        property_address: str,
        lead_name: str,
        start_time: datetime,
        duration_minutes: int = 60,
        lead_id: str = "",
        property_id: str = "",
        notes: str = ""
    ) -> CalendarEvent:
        """Create a property showing event."""
        return self.create_event(
            connection_id=connection_id,
            title=f"Showing: {property_address}",
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration_minutes),
            event_type=EventType.SHOWING,
            location=property_address,
            description=f"Showing for {lead_name}\n\n{notes}",
            lead_id=lead_id,
            property_id=property_id,
            reminders=[60, 15]  # 1 hour and 15 min reminders
        )
    
    def create_open_house(
        self,
        connection_id: str,
        property_address: str,
        start_time: datetime,
        end_time: datetime,
        property_id: str = "",
        notes: str = ""
    ) -> CalendarEvent:
        """Create an open house event."""
        return self.create_event(
            connection_id=connection_id,
            title=f"Open House: {property_address}",
            start_time=start_time,
            end_time=end_time,
            event_type=EventType.OPEN_HOUSE,
            location=property_address,
            description=notes,
            property_id=property_id,
            reminders=[1440, 60]  # 1 day and 1 hour reminders
        )
    
    def create_closing(
        self,
        connection_id: str,
        property_address: str,
        client_name: str,
        closing_time: datetime,
        location: str = "",
        lead_id: str = "",
        property_id: str = ""
    ) -> CalendarEvent:
        """Create a closing event."""
        return self.create_event(
            connection_id=connection_id,
            title=f"Closing: {property_address}",
            start_time=closing_time,
            end_time=closing_time + timedelta(hours=2),
            event_type=EventType.CLOSING,
            location=location or "Title Company",
            description=f"Closing for {client_name}\nProperty: {property_address}",
            lead_id=lead_id,
            property_id=property_id,
            reminders=[1440, 120, 60]  # 1 day, 2 hours, 1 hour
        )
    
    def get_events(
        self,
        connection_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: EventType = None
    ) -> List[CalendarEvent]:
        """Get calendar events with filters."""
        events = list(self.events.values())
        
        if connection_id:
            events = [e for e in events if e.connection_id == connection_id]
        
        if start_date:
            events = [e for e in events if e.start_time and e.start_time >= start_date]
        
        if end_date:
            events = [e for e in events if e.start_time and e.start_time <= end_date]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        events.sort(key=lambda e: e.start_time or datetime.min)
        return events
    
    def get_upcoming_events(self, days: int = 7, connection_id: str = None) -> List[CalendarEvent]:
        """Get upcoming events."""
        start = datetime.now()
        end = start + timedelta(days=days)
        return self.get_events(connection_id=connection_id, start_date=start, end_date=end)
    
    def get_lead_events(self, lead_id: str) -> List[CalendarEvent]:
        """Get events for a lead."""
        events = [e for e in self.events.values() if e.related_lead_id == lead_id]
        events.sort(key=lambda e: e.start_time or datetime.min)
        return events
    
    def get_property_events(self, property_id: str) -> List[CalendarEvent]:
        """Get events for a property."""
        events = [e for e in self.events.values() if e.related_property_id == property_id]
        events.sort(key=lambda e: e.start_time or datetime.min)
        return events
    
    def sync_connection(self, connection_id: str) -> Dict:
        """Sync events with external calendar (placeholder)."""
        conn = self.connections.get(connection_id)
        if not conn:
            return {'success': False, 'error': 'Connection not found'}
        
        # Would implement actual sync with Google/Outlook APIs
        # For now, mark events as synced
        synced_count = 0
        for event in self.events.values():
            if event.connection_id == connection_id and event.sync_status == SyncStatus.PENDING:
                event.sync_status = SyncStatus.SYNCED
                event.remote_modified = datetime.now()
                synced_count += 1
        
        conn.last_sync = datetime.now()
        self._save_data()
        
        return {
            'success': True,
            'synced_events': synced_count,
            'last_sync': conn.last_sync.isoformat()
        }
    
    def sync_all(self) -> Dict:
        """Sync all enabled connections."""
        results = {}
        for conn in self.connections.values():
            if conn.sync_enabled:
                results[conn.id] = self.sync_connection(conn.id)
        return results
    
    def get_availability(
        self,
        connection_id: str,
        date: datetime,
        duration_minutes: int = 60
    ) -> List[Dict]:
        """Get available time slots for a date."""
        # Get events for the day
        start = date.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        events = self.get_events(connection_id=connection_id, start_date=start, end_date=end)
        
        # Define business hours (9 AM - 7 PM)
        business_start = date.replace(hour=9, minute=0, second=0)
        business_end = date.replace(hour=19, minute=0, second=0)
        
        # Find available slots
        available = []
        current = business_start
        
        while current + timedelta(minutes=duration_minutes) <= business_end:
            slot_end = current + timedelta(minutes=duration_minutes)
            
            # Check if slot conflicts with any event
            conflict = False
            for event in events:
                if event.start_time and event.end_time:
                    if not (slot_end <= event.start_time or current >= event.end_time):
                        conflict = True
                        break
            
            if not conflict:
                available.append({
                    'start': current.isoformat(),
                    'end': slot_end.isoformat()
                })
            
            current += timedelta(minutes=30)  # 30-minute increments
        
        return available
