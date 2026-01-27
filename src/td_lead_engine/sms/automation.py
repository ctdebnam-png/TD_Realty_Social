"""SMS automation system with triggers."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any

from .messaging import SMSMessenger, SMSMessage
from .templates import SMSTemplateManager


class SMSTriggerType(Enum):
    """Types of SMS automation triggers."""
    NEW_LEAD = "new_lead"
    SHOWING_SCHEDULED = "showing_scheduled"
    SHOWING_REMINDER = "showing_reminder"
    SHOWING_COMPLETED = "showing_completed"
    OFFER_SUBMITTED = "offer_submitted"
    OFFER_RECEIVED = "offer_received"
    OFFER_STATUS_CHANGE = "offer_status_change"
    TRANSACTION_MILESTONE = "transaction_milestone"
    NEW_LISTING_MATCH = "new_listing_match"
    PRICE_DROP = "price_drop"
    INACTIVITY = "inactivity"
    LEAD_RESPONSE = "lead_response"


@dataclass
class SMSTrigger:
    """An SMS automation trigger."""
    id: str
    name: str
    trigger_type: SMSTriggerType
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
            elif event_data[key] != value:
                return False
        return True


@dataclass
class ScheduledSMS:
    """A scheduled SMS message."""
    id: str
    trigger_id: str
    template_id: str
    recipient_phone: str
    recipient_name: str
    scheduled_for: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, sent, failed, cancelled
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None


class SMSAutomation:
    """Manages SMS automation and triggers."""

    def __init__(
        self,
        messenger: SMSMessenger = None,
        template_manager: SMSTemplateManager = None,
        data_dir: str = "data/sms_automation"
    ):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.messenger = messenger or SMSMessenger()
        self.template_manager = template_manager or SMSTemplateManager()
        self.triggers: Dict[str, SMSTrigger] = {}
        self.scheduled: Dict[str, ScheduledSMS] = {}
        self._load_data()
        self._ensure_default_triggers()

    def _load_data(self):
        """Load existing data from files."""
        triggers_file = os.path.join(self.data_dir, "triggers.json")
        if os.path.exists(triggers_file):
            with open(triggers_file) as f:
                data = json.load(f)
                for item in data:
                    item['trigger_type'] = SMSTriggerType(item['trigger_type'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    self.triggers[item['id']] = SMSTrigger(**item)

        scheduled_file = os.path.join(self.data_dir, "scheduled.json")
        if os.path.exists(scheduled_file):
            with open(scheduled_file) as f:
                data = json.load(f)
                for item in data:
                    item['scheduled_for'] = datetime.fromisoformat(item['scheduled_for'])
                    if item.get('sent_at'):
                        item['sent_at'] = datetime.fromisoformat(item['sent_at'])
                    self.scheduled[item['id']] = ScheduledSMS(**item)

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
            for sms in self.scheduled.values():
                item = asdict(sms)
                item['scheduled_for'] = sms.scheduled_for.isoformat()
                if sms.sent_at:
                    item['sent_at'] = sms.sent_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    def create_trigger(
        self,
        name: str,
        trigger_type: SMSTriggerType,
        template_id: str,
        conditions: Optional[Dict] = None,
        delay_minutes: int = 0
    ) -> SMSTrigger:
        """Create a new SMS trigger."""
        trigger = SMSTrigger(
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

    def update_trigger(self, trigger_id: str, **updates) -> Optional[SMSTrigger]:
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

    def get_trigger(self, trigger_id: str) -> Optional[SMSTrigger]:
        """Get a trigger by ID."""
        return self.triggers.get(trigger_id)

    def get_triggers_by_type(self, trigger_type: SMSTriggerType) -> List[SMSTrigger]:
        """Get all active triggers of a specific type."""
        return [t for t in self.triggers.values()
                if t.trigger_type == trigger_type and t.is_active]

    def fire_event(
        self,
        trigger_type: SMSTriggerType,
        recipient_phone: str,
        recipient_name: str,
        event_data: Dict[str, Any]
    ) -> List[ScheduledSMS]:
        """Fire an event and schedule matching SMS messages."""
        scheduled = []

        for trigger in self.get_triggers_by_type(trigger_type):
            if trigger.matches(event_data):
                sms = self.schedule_sms(
                    trigger_id=trigger.id,
                    template_id=trigger.template_id,
                    recipient_phone=recipient_phone,
                    recipient_name=recipient_name,
                    delay_minutes=trigger.delay_minutes,
                    context=event_data
                )
                scheduled.append(sms)

        return scheduled

    def schedule_sms(
        self,
        trigger_id: str,
        template_id: str,
        recipient_phone: str,
        recipient_name: str,
        delay_minutes: int = 0,
        context: Optional[Dict] = None
    ) -> ScheduledSMS:
        """Schedule an SMS for delivery."""
        scheduled_for = datetime.now() + timedelta(minutes=delay_minutes)

        sms = ScheduledSMS(
            id=str(uuid.uuid4()),
            trigger_id=trigger_id,
            template_id=template_id,
            recipient_phone=recipient_phone,
            recipient_name=recipient_name,
            scheduled_for=scheduled_for,
            context=context or {}
        )

        self.scheduled[sms.id] = sms
        self._save_data()
        return sms

    def get_pending_sms(self, before: Optional[datetime] = None) -> List[ScheduledSMS]:
        """Get SMS messages ready to be sent."""
        if before is None:
            before = datetime.now()

        return [
            s for s in self.scheduled.values()
            if s.status == "pending" and s.scheduled_for <= before
        ]

    def send_pending(self) -> List[SMSMessage]:
        """Send all pending SMS messages."""
        sent = []
        for scheduled in self.get_pending_sms():
            msg = self.send_scheduled(scheduled.id)
            if msg:
                sent.append(msg)
        return sent

    def send_scheduled(self, scheduled_id: str) -> Optional[SMSMessage]:
        """Send a scheduled SMS message."""
        if scheduled_id not in self.scheduled:
            return None

        scheduled = self.scheduled[scheduled_id]

        # Render template
        rendered = self.template_manager.render_template(
            scheduled.template_id,
            scheduled.context
        )

        if not rendered:
            scheduled.status = "failed"
            self._save_data()
            return None

        # Send message
        try:
            message = self.messenger.send(
                to=scheduled.recipient_phone,
                message=rendered,
                contact_name=scheduled.recipient_name,
                metadata={'trigger_id': scheduled.trigger_id, 'scheduled_id': scheduled_id}
            )

            scheduled.status = "sent"
            scheduled.sent_at = datetime.now()
            scheduled.message_id = message.id
            self._save_data()

            return message

        except Exception as e:
            scheduled.status = "failed"
            self._save_data()
            return None

    def cancel_scheduled(self, scheduled_id: str) -> bool:
        """Cancel a scheduled SMS."""
        if scheduled_id in self.scheduled:
            scheduled = self.scheduled[scheduled_id]
            if scheduled.status == "pending":
                scheduled.status = "cancelled"
                self._save_data()
                return True
        return False

    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get automation statistics."""
        cutoff = datetime.now() - timedelta(days=days)

        recent = [s for s in self.scheduled.values()
                  if s.scheduled_for >= cutoff]

        sent = [s for s in recent if s.status == "sent"]
        failed = [s for s in recent if s.status == "failed"]
        pending = [s for s in recent if s.status == "pending"]

        # Group by trigger
        by_trigger = {}
        for s in sent:
            by_trigger[s.trigger_id] = by_trigger.get(s.trigger_id, 0) + 1

        return {
            'total_scheduled': len(recent),
            'total_sent': len(sent),
            'total_failed': len(failed),
            'pending': len(pending),
            'active_triggers': len([t for t in self.triggers.values() if t.is_active]),
            'by_trigger': by_trigger
        }

    def _ensure_default_triggers(self):
        """Create default triggers if none exist."""
        if not self.triggers:
            self._create_default_triggers()

    def _create_default_triggers(self):
        """Create default SMS automation triggers."""

        # New lead welcome (immediate)
        self.create_trigger(
            name="Welcome SMS - Buyer",
            trigger_type=SMSTriggerType.NEW_LEAD,
            template_id="sms_welcome_buyer",
            conditions={'lead_type': 'buyer'},
            delay_minutes=5  # 5 minute delay
        )

        self.create_trigger(
            name="Welcome SMS - Seller",
            trigger_type=SMSTriggerType.NEW_LEAD,
            template_id="sms_welcome_seller",
            conditions={'lead_type': 'seller'},
            delay_minutes=5
        )

        # Showing confirmations
        self.create_trigger(
            name="Showing Confirmation",
            trigger_type=SMSTriggerType.SHOWING_SCHEDULED,
            template_id="sms_showing_scheduled",
            delay_minutes=0  # Immediate
        )

        # Showing reminders
        self.create_trigger(
            name="Showing Reminder - 24hr",
            trigger_type=SMSTriggerType.SHOWING_REMINDER,
            template_id="sms_showing_reminder_24h",
            conditions={'hours_until': 24},
            delay_minutes=0
        )

        self.create_trigger(
            name="Showing Reminder - 1hr",
            trigger_type=SMSTriggerType.SHOWING_REMINDER,
            template_id="sms_showing_reminder_1h",
            conditions={'hours_until': 1},
            delay_minutes=0
        )

        # Post-showing follow-up
        self.create_trigger(
            name="Showing Follow-up",
            trigger_type=SMSTriggerType.SHOWING_COMPLETED,
            template_id="sms_showing_followup",
            delay_minutes=60  # 1 hour after
        )

        # Offer notifications
        self.create_trigger(
            name="Offer Submitted Confirmation",
            trigger_type=SMSTriggerType.OFFER_SUBMITTED,
            template_id="sms_offer_submitted",
            delay_minutes=0
        )

        self.create_trigger(
            name="Offer Received (Seller)",
            trigger_type=SMSTriggerType.OFFER_RECEIVED,
            template_id="sms_offer_received",
            delay_minutes=0
        )

        # New listing alerts
        self.create_trigger(
            name="New Listing Match",
            trigger_type=SMSTriggerType.NEW_LISTING_MATCH,
            template_id="sms_new_listing",
            delay_minutes=0
        )

        # Price drops
        self.create_trigger(
            name="Price Drop Alert",
            trigger_type=SMSTriggerType.PRICE_DROP,
            template_id="sms_price_drop",
            delay_minutes=0
        )

        self._save_data()
