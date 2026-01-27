"""Email automation system with triggers and scheduling."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable


class TriggerType(Enum):
    """Types of automation triggers."""
    NEW_LEAD = "new_lead"
    LEAD_SCORE_CHANGE = "lead_score_change"
    STAGE_CHANGE = "stage_change"
    PROPERTY_VIEWED = "property_viewed"
    PROPERTY_SAVED = "property_saved"
    SHOWING_SCHEDULED = "showing_scheduled"
    SHOWING_COMPLETED = "showing_completed"
    OFFER_SUBMITTED = "offer_submitted"
    OFFER_ACCEPTED = "offer_accepted"
    TRANSACTION_MILESTONE = "transaction_milestone"
    INACTIVITY = "inactivity"
    BIRTHDAY = "birthday"
    ANNIVERSARY = "anniversary"
    MARKET_UPDATE = "market_update"
    PRICE_DROP = "price_drop"
    NEW_LISTING_MATCH = "new_listing_match"


@dataclass
class EmailTrigger:
    """An automation trigger that sends emails."""
    id: str
    name: str
    trigger_type: TriggerType
    template_id: str
    is_active: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    delay_minutes: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def matches(self, event_data: Dict) -> bool:
        """Check if event data matches trigger conditions."""
        for key, value in self.conditions.items():
            if key not in event_data:
                return False
            if isinstance(value, dict):
                if 'min' in value and event_data[key] < value['min']:
                    return False
                if 'max' in value and event_data[key] > value['max']:
                    return False
                if 'equals' in value and event_data[key] != value['equals']:
                    return False
                if 'contains' in value and value['contains'] not in str(event_data[key]):
                    return False
            elif event_data[key] != value:
                return False
        return True


@dataclass
class ScheduledEmail:
    """An email scheduled for future delivery."""
    id: str
    trigger_id: str
    template_id: str
    recipient_email: str
    recipient_name: str
    scheduled_for: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, sent, failed, cancelled
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class EmailEvent:
    """Tracking for email events."""
    id: str
    email_id: str
    event_type: str  # sent, delivered, opened, clicked, bounced, unsubscribed
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmailAutomation:
    """Manages email automation triggers and scheduling."""

    def __init__(self, data_dir: str = "data/email"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.triggers: Dict[str, EmailTrigger] = {}
        self.scheduled_emails: Dict[str, ScheduledEmail] = {}
        self.email_events: List[EmailEvent] = []
        self.event_handlers: Dict[TriggerType, List[Callable]] = {}
        self._load_data()

    def _load_data(self):
        """Load existing data from files."""
        triggers_file = os.path.join(self.data_dir, "triggers.json")
        if os.path.exists(triggers_file):
            with open(triggers_file) as f:
                data = json.load(f)
                for item in data:
                    item['trigger_type'] = TriggerType(item['trigger_type'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    self.triggers[item['id']] = EmailTrigger(**item)

        scheduled_file = os.path.join(self.data_dir, "scheduled.json")
        if os.path.exists(scheduled_file):
            with open(scheduled_file) as f:
                data = json.load(f)
                for item in data:
                    item['scheduled_for'] = datetime.fromisoformat(item['scheduled_for'])
                    if item.get('sent_at'):
                        item['sent_at'] = datetime.fromisoformat(item['sent_at'])
                    self.scheduled_emails[item['id']] = ScheduledEmail(**item)

    def _save_data(self):
        """Save data to files."""
        triggers_file = os.path.join(self.data_dir, "triggers.json")
        with open(triggers_file, 'w') as f:
            data = []
            for trigger in self.triggers.values():
                item = asdict(trigger)
                item['trigger_type'] = trigger.trigger_type.value
                item['created_at'] = trigger.created_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

        scheduled_file = os.path.join(self.data_dir, "scheduled.json")
        with open(scheduled_file, 'w') as f:
            data = []
            for email in self.scheduled_emails.values():
                item = asdict(email)
                item['scheduled_for'] = email.scheduled_for.isoformat()
                if email.sent_at:
                    item['sent_at'] = email.sent_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    def create_trigger(
        self,
        name: str,
        trigger_type: TriggerType,
        template_id: str,
        conditions: Optional[Dict] = None,
        delay_minutes: int = 0
    ) -> EmailTrigger:
        """Create a new automation trigger."""
        trigger = EmailTrigger(
            id=str(uuid.uuid4()),
            name=name,
            trigger_type=trigger_type,
            template_id=template_id,
            conditions=conditions or {},
            delay_minutes=delay_minutes
        )
        self.triggers[trigger.id] = trigger
        self._save_data()
        return trigger

    def update_trigger(self, trigger_id: str, **updates) -> Optional[EmailTrigger]:
        """Update a trigger."""
        if trigger_id not in self.triggers:
            return None
        trigger = self.triggers[trigger_id]
        for key, value in updates.items():
            if hasattr(trigger, key):
                setattr(trigger, key, value)
        self._save_data()
        return trigger

    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger."""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            self._save_data()
            return True
        return False

    def get_trigger(self, trigger_id: str) -> Optional[EmailTrigger]:
        """Get a trigger by ID."""
        return self.triggers.get(trigger_id)

    def get_triggers_by_type(self, trigger_type: TriggerType) -> List[EmailTrigger]:
        """Get all triggers of a specific type."""
        return [t for t in self.triggers.values()
                if t.trigger_type == trigger_type and t.is_active]

    def fire_event(
        self,
        trigger_type: TriggerType,
        recipient_email: str,
        recipient_name: str,
        event_data: Dict[str, Any]
    ) -> List[ScheduledEmail]:
        """Fire an event and schedule matching emails."""
        scheduled = []

        for trigger in self.get_triggers_by_type(trigger_type):
            if trigger.matches(event_data):
                email = self.schedule_email(
                    trigger_id=trigger.id,
                    template_id=trigger.template_id,
                    recipient_email=recipient_email,
                    recipient_name=recipient_name,
                    delay_minutes=trigger.delay_minutes,
                    context=event_data
                )
                scheduled.append(email)

        return scheduled

    def schedule_email(
        self,
        trigger_id: str,
        template_id: str,
        recipient_email: str,
        recipient_name: str,
        delay_minutes: int = 0,
        context: Optional[Dict] = None
    ) -> ScheduledEmail:
        """Schedule an email for delivery."""
        scheduled_for = datetime.now() + timedelta(minutes=delay_minutes)

        email = ScheduledEmail(
            id=str(uuid.uuid4()),
            trigger_id=trigger_id,
            template_id=template_id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            scheduled_for=scheduled_for,
            context=context or {}
        )

        self.scheduled_emails[email.id] = email
        self._save_data()
        return email

    def get_pending_emails(self, before: Optional[datetime] = None) -> List[ScheduledEmail]:
        """Get emails that are ready to be sent."""
        if before is None:
            before = datetime.now()

        return [
            e for e in self.scheduled_emails.values()
            if e.status == "pending" and e.scheduled_for <= before
        ]

    def mark_sent(self, email_id: str, success: bool = True, error: str = None):
        """Mark an email as sent or failed."""
        if email_id in self.scheduled_emails:
            email = self.scheduled_emails[email_id]
            email.status = "sent" if success else "failed"
            email.sent_at = datetime.now()
            email.error_message = error
            self._save_data()

            # Track event
            self.track_event(email_id, "sent" if success else "failed")

    def cancel_email(self, email_id: str) -> bool:
        """Cancel a scheduled email."""
        if email_id in self.scheduled_emails:
            email = self.scheduled_emails[email_id]
            if email.status == "pending":
                email.status = "cancelled"
                self._save_data()
                return True
        return False

    def track_event(
        self,
        email_id: str,
        event_type: str,
        metadata: Optional[Dict] = None
    ) -> EmailEvent:
        """Track an email event (open, click, etc.)."""
        event = EmailEvent(
            id=str(uuid.uuid4()),
            email_id=email_id,
            event_type=event_type,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.email_events.append(event)
        return event

    def get_email_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get email statistics for the last N days."""
        cutoff = datetime.now() - timedelta(days=days)

        sent = [e for e in self.scheduled_emails.values()
                if e.status == "sent" and e.sent_at and e.sent_at >= cutoff]
        failed = [e for e in self.scheduled_emails.values()
                  if e.status == "failed" and e.sent_at and e.sent_at >= cutoff]

        events_in_period = [e for e in self.email_events if e.timestamp >= cutoff]
        opens = [e for e in events_in_period if e.event_type == "opened"]
        clicks = [e for e in events_in_period if e.event_type == "clicked"]

        total_sent = len(sent)
        return {
            'total_sent': total_sent,
            'total_failed': len(failed),
            'total_opens': len(opens),
            'total_clicks': len(clicks),
            'open_rate': len(opens) / total_sent * 100 if total_sent else 0,
            'click_rate': len(clicks) / total_sent * 100 if total_sent else 0,
            'delivery_rate': total_sent / (total_sent + len(failed)) * 100 if (total_sent + len(failed)) else 100
        }

    # Pre-built automation helpers

    def setup_welcome_sequence(self, template_ids: List[str]):
        """Set up a welcome email sequence for new leads."""
        # Immediate welcome
        self.create_trigger(
            name="Welcome Email",
            trigger_type=TriggerType.NEW_LEAD,
            template_id=template_ids[0] if template_ids else "welcome_1",
            delay_minutes=0
        )

        # Day 2: Introduction
        if len(template_ids) > 1:
            self.create_trigger(
                name="Welcome Day 2",
                trigger_type=TriggerType.NEW_LEAD,
                template_id=template_ids[1],
                delay_minutes=1440  # 24 hours
            )

        # Day 5: Resources
        if len(template_ids) > 2:
            self.create_trigger(
                name="Welcome Day 5",
                trigger_type=TriggerType.NEW_LEAD,
                template_id=template_ids[2],
                delay_minutes=7200  # 5 days
            )

    def setup_hot_lead_alert(self, template_id: str, score_threshold: int = 80):
        """Alert agent when a lead becomes hot."""
        self.create_trigger(
            name="Hot Lead Alert",
            trigger_type=TriggerType.LEAD_SCORE_CHANGE,
            template_id=template_id,
            conditions={'score': {'min': score_threshold}},
            delay_minutes=0
        )

    def setup_showing_reminders(self, template_id: str):
        """Set up showing reminder emails."""
        # 24 hour reminder
        self.create_trigger(
            name="Showing Reminder 24h",
            trigger_type=TriggerType.SHOWING_SCHEDULED,
            template_id=template_id,
            delay_minutes=-1440  # 24 hours before (negative = before event)
        )

    def setup_follow_up_sequence(self, template_ids: List[str]):
        """Set up post-showing follow-up sequence."""
        # Immediate thank you
        self.create_trigger(
            name="Showing Thank You",
            trigger_type=TriggerType.SHOWING_COMPLETED,
            template_id=template_ids[0] if template_ids else "showing_thanks",
            delay_minutes=60  # 1 hour after
        )

        # Day 2: Feedback request
        if len(template_ids) > 1:
            self.create_trigger(
                name="Showing Feedback Request",
                trigger_type=TriggerType.SHOWING_COMPLETED,
                template_id=template_ids[1],
                delay_minutes=2880  # 2 days
            )

    def setup_inactivity_reengagement(self, template_id: str, days_inactive: int = 14):
        """Set up re-engagement for inactive leads."""
        self.create_trigger(
            name="Re-engagement Email",
            trigger_type=TriggerType.INACTIVITY,
            template_id=template_id,
            conditions={'days_inactive': {'min': days_inactive}},
            delay_minutes=0
        )
