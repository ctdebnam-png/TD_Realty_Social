"""Event tracking for user interactions."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class EventCategory(Enum):
    """Event categories."""
    PAGE = "page"
    LEAD = "lead"
    PROPERTY = "property"
    SEARCH = "search"
    FORM = "form"
    CALCULATOR = "calculator"
    COMMUNICATION = "communication"
    TRANSACTION = "transaction"
    SYSTEM = "system"


@dataclass
class TrackingEvent:
    """A tracked event."""
    id: str
    category: EventCategory
    action: str
    label: str = ""
    value: float = None
    
    # Context
    visitor_id: str = ""
    session_id: str = ""
    lead_id: str = ""
    property_id: str = ""
    
    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    page_url: str = ""
    referrer: str = ""
    user_agent: str = ""
    ip_address: str = ""
    
    # Custom properties
    properties: Dict = field(default_factory=dict)


class EventTracker:
    """Track and analyze user events."""
    
    def __init__(self, storage_path: str = "data/events"):
        self.storage_path = storage_path
        self.events: List[TrackingEvent] = []
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        self._load_events()
    
    def _load_events(self):
        """Load recent events from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        events_file = f"{self.storage_path}/events.json"
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                data = json.load(f)
                for event_data in data[-5000:]:  # Keep last 5000
                    event = TrackingEvent(
                        id=event_data['id'],
                        category=EventCategory(event_data['category']),
                        action=event_data['action'],
                        label=event_data.get('label', ''),
                        value=event_data.get('value'),
                        visitor_id=event_data.get('visitor_id', ''),
                        session_id=event_data.get('session_id', ''),
                        lead_id=event_data.get('lead_id', ''),
                        property_id=event_data.get('property_id', ''),
                        timestamp=datetime.fromisoformat(event_data['timestamp']),
                        page_url=event_data.get('page_url', ''),
                        referrer=event_data.get('referrer', ''),
                        user_agent=event_data.get('user_agent', ''),
                        ip_address=event_data.get('ip_address', ''),
                        properties=event_data.get('properties', {})
                    )
                    self.events.append(event)
    
    def _save_events(self):
        """Save events to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Keep last 5000 events
        data = [
            {
                'id': e.id,
                'category': e.category.value,
                'action': e.action,
                'label': e.label,
                'value': e.value,
                'visitor_id': e.visitor_id,
                'session_id': e.session_id,
                'lead_id': e.lead_id,
                'property_id': e.property_id,
                'timestamp': e.timestamp.isoformat(),
                'page_url': e.page_url,
                'referrer': e.referrer,
                'user_agent': e.user_agent,
                'ip_address': e.ip_address,
                'properties': e.properties
            }
            for e in self.events[-5000:]
        ]
        
        with open(f"{self.storage_path}/events.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def on_event(self, event_key: str, handler: Callable):
        """Register an event handler."""
        if event_key not in self.event_handlers:
            self.event_handlers[event_key] = []
        self.event_handlers[event_key].append(handler)
    
    def _trigger_handlers(self, event: TrackingEvent):
        """Trigger event handlers."""
        event_key = f"{event.category.value}:{event.action}"
        
        # Specific handlers
        handlers = self.event_handlers.get(event_key, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        
        # Category handlers
        category_handlers = self.event_handlers.get(event.category.value, [])
        for handler in category_handlers:
            try:
                handler(event)
            except Exception:
                pass
        
        # Global handlers
        global_handlers = self.event_handlers.get('*', [])
        for handler in global_handlers:
            try:
                handler(event)
            except Exception:
                pass
    
    def track(
        self,
        category: EventCategory,
        action: str,
        label: str = "",
        value: float = None,
        visitor_id: str = "",
        session_id: str = "",
        lead_id: str = "",
        property_id: str = "",
        page_url: str = "",
        referrer: str = "",
        user_agent: str = "",
        ip_address: str = "",
        properties: Dict = None
    ) -> TrackingEvent:
        """Track an event."""
        event = TrackingEvent(
            id=str(uuid.uuid4())[:12],
            category=category,
            action=action,
            label=label,
            value=value,
            visitor_id=visitor_id,
            session_id=session_id,
            lead_id=lead_id,
            property_id=property_id,
            page_url=page_url,
            referrer=referrer,
            user_agent=user_agent,
            ip_address=ip_address,
            properties=properties or {}
        )
        
        self.events.append(event)
        self._save_events()
        self._trigger_handlers(event)
        
        return event
    
    # Convenience methods for common events
    def track_page_view(
        self,
        page_url: str,
        page_title: str = "",
        visitor_id: str = "",
        session_id: str = "",
        referrer: str = ""
    ):
        """Track a page view."""
        return self.track(
            category=EventCategory.PAGE,
            action='view',
            label=page_title,
            visitor_id=visitor_id,
            session_id=session_id,
            page_url=page_url,
            referrer=referrer
        )
    
    def track_property_view(
        self,
        property_id: str,
        property_address: str = "",
        visitor_id: str = "",
        lead_id: str = ""
    ):
        """Track a property view."""
        return self.track(
            category=EventCategory.PROPERTY,
            action='view',
            label=property_address,
            visitor_id=visitor_id,
            lead_id=lead_id,
            property_id=property_id
        )
    
    def track_property_favorite(
        self,
        property_id: str,
        visitor_id: str = "",
        lead_id: str = ""
    ):
        """Track property being favorited."""
        return self.track(
            category=EventCategory.PROPERTY,
            action='favorite',
            visitor_id=visitor_id,
            lead_id=lead_id,
            property_id=property_id
        )
    
    def track_search(
        self,
        search_criteria: Dict,
        results_count: int = 0,
        visitor_id: str = "",
        lead_id: str = ""
    ):
        """Track a property search."""
        return self.track(
            category=EventCategory.SEARCH,
            action='perform',
            value=results_count,
            visitor_id=visitor_id,
            lead_id=lead_id,
            properties=search_criteria
        )
    
    def track_form_submission(
        self,
        form_id: str,
        form_name: str = "",
        visitor_id: str = "",
        lead_id: str = ""
    ):
        """Track a form submission."""
        return self.track(
            category=EventCategory.FORM,
            action='submit',
            label=form_name,
            visitor_id=visitor_id,
            lead_id=lead_id,
            properties={'form_id': form_id}
        )
    
    def track_calculator_use(
        self,
        calculator_type: str,
        visitor_id: str = "",
        lead_id: str = ""
    ):
        """Track calculator usage."""
        return self.track(
            category=EventCategory.CALCULATOR,
            action='use',
            label=calculator_type,
            visitor_id=visitor_id,
            lead_id=lead_id
        )
    
    def track_lead_created(
        self,
        lead_id: str,
        source: str = "",
        visitor_id: str = ""
    ):
        """Track lead creation."""
        return self.track(
            category=EventCategory.LEAD,
            action='created',
            label=source,
            lead_id=lead_id,
            visitor_id=visitor_id
        )
    
    def track_showing_scheduled(
        self,
        property_id: str,
        lead_id: str = ""
    ):
        """Track showing scheduled."""
        return self.track(
            category=EventCategory.PROPERTY,
            action='showing_scheduled',
            lead_id=lead_id,
            property_id=property_id
        )
    
    def get_events(
        self,
        category: EventCategory = None,
        action: str = None,
        visitor_id: str = None,
        lead_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100
    ) -> List[TrackingEvent]:
        """Get events with filters."""
        events = self.events
        
        if category:
            events = [e for e in events if e.category == category]
        
        if action:
            events = [e for e in events if e.action == action]
        
        if visitor_id:
            events = [e for e in events if e.visitor_id == visitor_id]
        
        if lead_id:
            events = [e for e in events if e.lead_id == lead_id]
        
        if start_date:
            events = [e for e in events if e.timestamp >= start_date]
        
        if end_date:
            events = [e for e in events if e.timestamp <= end_date]
        
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
    
    def get_event_counts(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Get event counts by category and action."""
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()
        
        events = [e for e in self.events if start_date <= e.timestamp <= end_date]
        
        counts = {}
        for event in events:
            key = f"{event.category.value}:{event.action}"
            counts[key] = counts.get(key, 0) + 1
        
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    
    def get_funnel_analysis(
        self,
        steps: List[tuple],  # [(category, action), ...]
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Analyze conversion funnel."""
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()
        
        events = [e for e in self.events if start_date <= e.timestamp <= end_date]
        
        # Group events by visitor
        visitor_events = {}
        for event in events:
            if event.visitor_id:
                if event.visitor_id not in visitor_events:
                    visitor_events[event.visitor_id] = []
                visitor_events[event.visitor_id].append(event)
        
        # Analyze funnel
        funnel_results = []
        for i, (category, action) in enumerate(steps):
            visitors_at_step = set()
            
            for visitor_id, v_events in visitor_events.items():
                # Check if visitor completed this step
                for event in v_events:
                    if event.category.value == category and event.action == action:
                        visitors_at_step.add(visitor_id)
                        break
            
            count = len(visitors_at_step)
            prev_count = funnel_results[i-1]['count'] if i > 0 else count
            drop_rate = ((prev_count - count) / prev_count * 100) if prev_count > 0 else 0
            
            funnel_results.append({
                'step': f"{category}:{action}",
                'count': count,
                'drop_rate': round(drop_rate, 1)
            })
        
        return {
            'steps': funnel_results,
            'overall_conversion': (
                (funnel_results[-1]['count'] / funnel_results[0]['count'] * 100)
                if funnel_results and funnel_results[0]['count'] > 0 else 0
            )
        }
    
    def get_property_engagement(self, property_id: str) -> Dict:
        """Get engagement metrics for a property."""
        events = [e for e in self.events if e.property_id == property_id]
        
        views = len([e for e in events if e.action == 'view'])
        favorites = len([e for e in events if e.action == 'favorite'])
        inquiries = len([e for e in events if e.action == 'inquiry'])
        showings = len([e for e in events if e.action == 'showing_scheduled'])
        
        unique_visitors = len(set(e.visitor_id for e in events if e.visitor_id))
        
        return {
            'total_views': views,
            'favorites': favorites,
            'inquiries': inquiries,
            'showings_scheduled': showings,
            'unique_visitors': unique_visitors,
            'favorite_rate': (favorites / views * 100) if views > 0 else 0,
            'inquiry_rate': (inquiries / views * 100) if views > 0 else 0
        }
