"""Campaign analytics and performance tracking."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class EventType(Enum):
    """Campaign event types."""
    ENROLLED = "enrolled"
    EMAIL_SENT = "email_sent"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    SMS_SENT = "sms_sent"
    SMS_CLICKED = "sms_clicked"
    UNSUBSCRIBED = "unsubscribed"
    COMPLETED = "completed"
    CONVERTED = "converted"


@dataclass
class CampaignEvent:
    """An event in a campaign."""
    id: str
    campaign_id: str
    enrollment_id: str
    lead_id: str
    event_type: EventType
    step_id: str = ""
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class CampaignAnalytics:
    """Track and analyze campaign performance."""
    
    def __init__(self, storage_path: str = "data/drip_campaigns"):
        self.storage_path = storage_path
        self.events: List[CampaignEvent] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load events from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/campaign_events.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for e in data[-50000:]:  # Keep last 50k events
                    event = CampaignEvent(
                        id=e['id'],
                        campaign_id=e['campaign_id'],
                        enrollment_id=e['enrollment_id'],
                        lead_id=e['lead_id'],
                        event_type=EventType(e['event_type']),
                        step_id=e.get('step_id', ''),
                        metadata=e.get('metadata', {}),
                        timestamp=datetime.fromisoformat(e['timestamp'])
                    )
                    self.events.append(event)
    
    def _save_data(self):
        """Save events to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        events_data = [
            {
                'id': e.id,
                'campaign_id': e.campaign_id,
                'enrollment_id': e.enrollment_id,
                'lead_id': e.lead_id,
                'event_type': e.event_type.value,
                'step_id': e.step_id,
                'metadata': e.metadata,
                'timestamp': e.timestamp.isoformat()
            }
            for e in self.events[-50000:]
        ]
        
        with open(f"{self.storage_path}/campaign_events.json", 'w') as f:
            json.dump(events_data, f, indent=2)
    
    def record_event(
        self,
        campaign_id: str,
        enrollment_id: str,
        lead_id: str,
        event_type: EventType,
        step_id: str = "",
        metadata: Dict = None
    ):
        """Record a campaign event."""
        import uuid
        event = CampaignEvent(
            id=str(uuid.uuid4())[:12],
            campaign_id=campaign_id,
            enrollment_id=enrollment_id,
            lead_id=lead_id,
            event_type=event_type,
            step_id=step_id,
            metadata=metadata or {}
        )
        self.events.append(event)
        self._save_data()
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Get comprehensive metrics for a campaign."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        # Filter events
        events = [
            e for e in self.events
            if e.campaign_id == campaign_id and start <= e.timestamp <= end
        ]
        
        # Count by type
        enrolled = len([e for e in events if e.event_type == EventType.ENROLLED])
        emails_sent = len([e for e in events if e.event_type == EventType.EMAIL_SENT])
        emails_opened = len([e for e in events if e.event_type == EventType.EMAIL_OPENED])
        emails_clicked = len([e for e in events if e.event_type == EventType.EMAIL_CLICKED])
        sms_sent = len([e for e in events if e.event_type == EventType.SMS_SENT])
        unsubscribed = len([e for e in events if e.event_type == EventType.UNSUBSCRIBED])
        completed = len([e for e in events if e.event_type == EventType.COMPLETED])
        converted = len([e for e in events if e.event_type == EventType.CONVERTED])
        
        return {
            'campaign_id': campaign_id,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'enrollments': {
                'total': enrolled,
                'completed': completed,
                'unsubscribed': unsubscribed,
                'completion_rate': round(completed / enrolled * 100, 1) if enrolled else 0,
                'unsubscribe_rate': round(unsubscribed / enrolled * 100, 1) if enrolled else 0
            },
            'email': {
                'sent': emails_sent,
                'opened': emails_opened,
                'clicked': emails_clicked,
                'open_rate': round(emails_opened / emails_sent * 100, 1) if emails_sent else 0,
                'click_rate': round(emails_clicked / emails_sent * 100, 1) if emails_sent else 0,
                'click_to_open_rate': round(emails_clicked / emails_opened * 100, 1) if emails_opened else 0
            },
            'sms': {
                'sent': sms_sent
            },
            'conversions': {
                'total': converted,
                'conversion_rate': round(converted / enrolled * 100, 1) if enrolled else 0
            }
        }
    
    def get_step_metrics(self, campaign_id: str, step_id: str) -> Dict:
        """Get metrics for a specific campaign step."""
        step_events = [
            e for e in self.events
            if e.campaign_id == campaign_id and e.step_id == step_id
        ]
        
        sent = len([e for e in step_events if e.event_type in [EventType.EMAIL_SENT, EventType.SMS_SENT]])
        opened = len([e for e in step_events if e.event_type == EventType.EMAIL_OPENED])
        clicked = len([e for e in step_events if e.event_type in [EventType.EMAIL_CLICKED, EventType.SMS_CLICKED]])
        
        return {
            'step_id': step_id,
            'sent': sent,
            'opened': opened,
            'clicked': clicked,
            'open_rate': round(opened / sent * 100, 1) if sent else 0,
            'click_rate': round(clicked / sent * 100, 1) if sent else 0
        }
    
    def get_engagement_timeline(
        self,
        campaign_id: str,
        days: int = 30
    ) -> List[Dict]:
        """Get daily engagement timeline."""
        start = datetime.now() - timedelta(days=days)
        
        events = [
            e for e in self.events
            if e.campaign_id == campaign_id and e.timestamp >= start
        ]
        
        # Group by day
        daily = {}
        for i in range(days):
            day = (start + timedelta(days=i)).strftime('%Y-%m-%d')
            daily[day] = {
                'date': day,
                'enrolled': 0,
                'emails_sent': 0,
                'emails_opened': 0,
                'clicks': 0
            }
        
        for event in events:
            day = event.timestamp.strftime('%Y-%m-%d')
            if day in daily:
                if event.event_type == EventType.ENROLLED:
                    daily[day]['enrolled'] += 1
                elif event.event_type == EventType.EMAIL_SENT:
                    daily[day]['emails_sent'] += 1
                elif event.event_type == EventType.EMAIL_OPENED:
                    daily[day]['emails_opened'] += 1
                elif event.event_type in [EventType.EMAIL_CLICKED, EventType.SMS_CLICKED]:
                    daily[day]['clicks'] += 1
        
        return list(daily.values())
    
    def get_best_performing_campaigns(self, limit: int = 10) -> List[Dict]:
        """Get best performing campaigns by conversion rate."""
        campaign_ids = set(e.campaign_id for e in self.events)
        
        campaign_stats = []
        for campaign_id in campaign_ids:
            metrics = self.get_campaign_metrics(campaign_id)
            campaign_stats.append({
                'campaign_id': campaign_id,
                'enrollments': metrics['enrollments']['total'],
                'conversions': metrics['conversions']['total'],
                'conversion_rate': metrics['conversions']['conversion_rate'],
                'open_rate': metrics['email']['open_rate'],
                'click_rate': metrics['email']['click_rate']
            })
        
        campaign_stats.sort(key=lambda x: x['conversion_rate'], reverse=True)
        return campaign_stats[:limit]
    
    def get_lead_engagement(self, lead_id: str) -> Dict:
        """Get engagement history for a lead."""
        lead_events = [e for e in self.events if e.lead_id == lead_id]
        lead_events.sort(key=lambda e: e.timestamp)
        
        campaigns = set(e.campaign_id for e in lead_events)
        
        return {
            'lead_id': lead_id,
            'total_events': len(lead_events),
            'campaigns_enrolled': len(campaigns),
            'emails_received': len([e for e in lead_events if e.event_type == EventType.EMAIL_SENT]),
            'emails_opened': len([e for e in lead_events if e.event_type == EventType.EMAIL_OPENED]),
            'clicks': len([e for e in lead_events if e.event_type in [EventType.EMAIL_CLICKED, EventType.SMS_CLICKED]]),
            'converted': any(e.event_type == EventType.CONVERTED for e in lead_events),
            'last_engagement': lead_events[-1].timestamp.isoformat() if lead_events else None
        }
