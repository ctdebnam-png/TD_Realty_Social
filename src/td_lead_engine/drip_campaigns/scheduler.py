"""Campaign scheduler for timing message delivery."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid
import threading
import time


class MessageStatus(Enum):
    """Status of a scheduled message."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class ScheduledMessage:
    """A message scheduled for delivery."""
    id: str
    enrollment_id: str
    campaign_id: str
    lead_id: str
    step_id: str
    message_type: str  # email or sms
    scheduled_for: datetime
    status: MessageStatus = MessageStatus.PENDING
    content: Dict = field(default_factory=dict)
    sent_at: datetime = None
    error: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class CampaignScheduler:
    """Schedule and manage campaign message delivery."""
    
    def __init__(
        self,
        campaign_manager,
        template_library,
        storage_path: str = "data/drip_campaigns"
    ):
        self.campaign_manager = campaign_manager
        self.template_library = template_library
        self.storage_path = storage_path
        self.scheduled_messages: Dict[str, ScheduledMessage] = {}
        self._running = False
        self._thread = None
        
        self._load_data()
    
    def _load_data(self):
        """Load scheduled messages from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/scheduled_messages.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for m in data:
                    message = ScheduledMessage(
                        id=m['id'],
                        enrollment_id=m['enrollment_id'],
                        campaign_id=m['campaign_id'],
                        lead_id=m['lead_id'],
                        step_id=m['step_id'],
                        message_type=m['message_type'],
                        scheduled_for=datetime.fromisoformat(m['scheduled_for']),
                        status=MessageStatus(m.get('status', 'pending')),
                        content=m.get('content', {}),
                        sent_at=datetime.fromisoformat(m['sent_at']) if m.get('sent_at') else None,
                        error=m.get('error', ''),
                        created_at=datetime.fromisoformat(m['created_at'])
                    )
                    self.scheduled_messages[message.id] = message
    
    def _save_data(self):
        """Save scheduled messages to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        messages_data = [
            {
                'id': m.id,
                'enrollment_id': m.enrollment_id,
                'campaign_id': m.campaign_id,
                'lead_id': m.lead_id,
                'step_id': m.step_id,
                'message_type': m.message_type,
                'scheduled_for': m.scheduled_for.isoformat(),
                'status': m.status.value,
                'content': m.content,
                'sent_at': m.sent_at.isoformat() if m.sent_at else None,
                'error': m.error,
                'created_at': m.created_at.isoformat()
            }
            for m in self.scheduled_messages.values()
        ]
        
        with open(f"{self.storage_path}/scheduled_messages.json", 'w') as f:
            json.dump(messages_data, f, indent=2)
    
    def schedule_message(
        self,
        enrollment_id: str,
        campaign_id: str,
        lead_id: str,
        step_id: str,
        message_type: str,
        scheduled_for: datetime,
        content: Dict = None
    ) -> ScheduledMessage:
        """Schedule a message for delivery."""
        message = ScheduledMessage(
            id=str(uuid.uuid4())[:12],
            enrollment_id=enrollment_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            step_id=step_id,
            message_type=message_type,
            scheduled_for=scheduled_for,
            content=content or {}
        )
        self.scheduled_messages[message.id] = message
        self._save_data()
        return message
    
    def cancel_message(self, message_id: str) -> bool:
        """Cancel a scheduled message."""
        message = self.scheduled_messages.get(message_id)
        if not message or message.status != MessageStatus.PENDING:
            return False
        
        message.status = MessageStatus.CANCELLED
        self._save_data()
        return True
    
    def get_pending_messages(self, before: datetime = None) -> List[ScheduledMessage]:
        """Get pending messages ready for delivery."""
        check_time = before or datetime.now()
        
        pending = [
            m for m in self.scheduled_messages.values()
            if m.status == MessageStatus.PENDING and m.scheduled_for <= check_time
        ]
        
        pending.sort(key=lambda m: m.scheduled_for)
        return pending
    
    def mark_sent(self, message_id: str):
        """Mark a message as sent."""
        message = self.scheduled_messages.get(message_id)
        if message:
            message.status = MessageStatus.SENT
            message.sent_at = datetime.now()
            self._save_data()
    
    def mark_failed(self, message_id: str, error: str = ""):
        """Mark a message as failed."""
        message = self.scheduled_messages.get(message_id)
        if message:
            message.status = MessageStatus.FAILED
            message.error = error
            self._save_data()
    
    def process_pending(self) -> Dict:
        """Process all pending messages."""
        results = {
            'processed': 0,
            'sent': 0,
            'failed': 0
        }
        
        pending = self.get_pending_messages()
        
        for message in pending:
            results['processed'] += 1
            
            # Here you would integrate with actual email/SMS sending
            # For now, simulate sending
            success = self._send_message(message)
            
            if success:
                self.mark_sent(message.id)
                results['sent'] += 1
                
                # Advance the enrollment
                self.campaign_manager.advance_enrollment(message.enrollment_id)
            else:
                self.mark_failed(message.id, "Send failed")
                results['failed'] += 1
        
        return results
    
    def _send_message(self, message: ScheduledMessage) -> bool:
        """Send a message (placeholder for actual integration)."""
        # In production, this would integrate with email/SMS providers
        # For now, return True to simulate successful send
        return True
    
    def start_scheduler(self, interval_seconds: int = 60):
        """Start the background scheduler."""
        if self._running:
            return
        
        self._running = True
        
        def run():
            while self._running:
                try:
                    self.process_pending()
                except Exception:
                    pass
                time.sleep(interval_seconds)
        
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
    
    def stop_scheduler(self):
        """Stop the background scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def get_lead_schedule(self, lead_id: str) -> List[Dict]:
        """Get scheduled messages for a lead."""
        messages = [
            m for m in self.scheduled_messages.values()
            if m.lead_id == lead_id
        ]
        
        messages.sort(key=lambda m: m.scheduled_for)
        
        return [
            {
                'id': m.id,
                'campaign_id': m.campaign_id,
                'message_type': m.message_type,
                'scheduled_for': m.scheduled_for.isoformat(),
                'status': m.status.value
            }
            for m in messages
        ]
    
    def reschedule_message(
        self,
        message_id: str,
        new_time: datetime
    ) -> bool:
        """Reschedule a pending message."""
        message = self.scheduled_messages.get(message_id)
        if not message or message.status != MessageStatus.PENDING:
            return False
        
        message.scheduled_for = new_time
        self._save_data()
        return True
    
    def get_schedule_stats(self) -> Dict:
        """Get scheduler statistics."""
        now = datetime.now()
        
        pending = [m for m in self.scheduled_messages.values() if m.status == MessageStatus.PENDING]
        
        return {
            'total_messages': len(self.scheduled_messages),
            'pending': len(pending),
            'sent': len([m for m in self.scheduled_messages.values() if m.status == MessageStatus.SENT]),
            'failed': len([m for m in self.scheduled_messages.values() if m.status == MessageStatus.FAILED]),
            'cancelled': len([m for m in self.scheduled_messages.values() if m.status == MessageStatus.CANCELLED]),
            'next_24h': len([m for m in pending if m.scheduled_for <= now + timedelta(hours=24)]),
            'overdue': len([m for m in pending if m.scheduled_for < now])
        }
