"""SMS messaging service with provider abstraction."""

import json
import os
import uuid
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Protocol
from abc import ABC, abstractmethod


class MessageStatus(Enum):
    """Status of an SMS message."""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    UNDELIVERED = "undelivered"


class MessageDirection(Enum):
    """Direction of message."""
    OUTBOUND = "outbound"
    INBOUND = "inbound"


@dataclass
class SMSMessage:
    """An SMS message."""
    id: str
    to_number: str
    from_number: str
    body: str
    direction: MessageDirection = MessageDirection.OUTBOUND
    status: MessageStatus = MessageStatus.QUEUED
    provider_id: Optional[str] = None
    contact_id: Optional[str] = None
    contact_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    """A conversation thread with a contact."""
    id: str
    contact_id: str
    contact_name: str
    contact_number: str
    messages: List[str] = field(default_factory=list)  # Message IDs
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    is_archived: bool = False


class SMSProvider(ABC):
    """Abstract base class for SMS providers."""

    @abstractmethod
    def send(self, to: str, message: str, from_number: str = None) -> Dict[str, Any]:
        """Send an SMS message."""
        pass

    @abstractmethod
    def get_status(self, message_id: str) -> MessageStatus:
        """Get the status of a sent message."""
        pass


class TwilioProvider(SMSProvider):
    """Twilio SMS provider (simulated)."""

    def __init__(self, account_sid: str = None, auth_token: str = None, from_number: str = None):
        self.account_sid = account_sid or os.environ.get('TWILIO_ACCOUNT_SID', 'test_sid')
        self.auth_token = auth_token or os.environ.get('TWILIO_AUTH_TOKEN', 'test_token')
        self.from_number = from_number or os.environ.get('TWILIO_FROM_NUMBER', '+16145550123')

    def send(self, to: str, message: str, from_number: str = None) -> Dict[str, Any]:
        """Send SMS via Twilio (simulated in dev)."""
        # In production, this would use twilio-python client
        # from twilio.rest import Client
        # client = Client(self.account_sid, self.auth_token)
        # message = client.messages.create(body=message, from_=from_number or self.from_number, to=to)

        # Simulated response
        return {
            'sid': f'SM{uuid.uuid4().hex[:32]}',
            'status': 'queued',
            'to': to,
            'from': from_number or self.from_number,
            'body': message,
            'date_created': datetime.now().isoformat()
        }

    def get_status(self, message_id: str) -> MessageStatus:
        """Get message status from Twilio (simulated)."""
        # In production, would query Twilio API
        return MessageStatus.DELIVERED


class MockSMSProvider(SMSProvider):
    """Mock SMS provider for testing."""

    def __init__(self):
        self.sent_messages = []

    def send(self, to: str, message: str, from_number: str = None) -> Dict[str, Any]:
        """Simulate sending an SMS."""
        msg_data = {
            'sid': f'MOCK{uuid.uuid4().hex[:28]}',
            'status': 'sent',
            'to': to,
            'from': from_number or '+16145550000',
            'body': message,
            'date_created': datetime.now().isoformat()
        }
        self.sent_messages.append(msg_data)
        return msg_data

    def get_status(self, message_id: str) -> MessageStatus:
        return MessageStatus.DELIVERED


class SMSMessenger:
    """Manages SMS messaging operations."""

    def __init__(
        self,
        provider: SMSProvider = None,
        data_dir: str = "data/sms",
        from_number: str = None
    ):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.provider = provider or MockSMSProvider()
        self.from_number = from_number or '+16145550123'
        self.messages: Dict[str, SMSMessage] = {}
        self.conversations: Dict[str, Conversation] = {}
        self._load_data()

    def _load_data(self):
        """Load existing data from files."""
        messages_file = os.path.join(self.data_dir, "messages.json")
        if os.path.exists(messages_file):
            with open(messages_file) as f:
                data = json.load(f)
                for item in data:
                    item['direction'] = MessageDirection(item['direction'])
                    item['status'] = MessageStatus(item['status'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    if item.get('sent_at'):
                        item['sent_at'] = datetime.fromisoformat(item['sent_at'])
                    if item.get('delivered_at'):
                        item['delivered_at'] = datetime.fromisoformat(item['delivered_at'])
                    self.messages[item['id']] = SMSMessage(**item)

        convos_file = os.path.join(self.data_dir, "conversations.json")
        if os.path.exists(convos_file):
            with open(convos_file) as f:
                data = json.load(f)
                for item in data:
                    if item.get('last_message_at'):
                        item['last_message_at'] = datetime.fromisoformat(item['last_message_at'])
                    self.conversations[item['id']] = Conversation(**item)

    def _save_data(self):
        """Save data to files."""
        messages_file = os.path.join(self.data_dir, "messages.json")
        with open(messages_file, 'w') as f:
            data = []
            for msg in self.messages.values():
                item = asdict(msg)
                item['direction'] = msg.direction.value
                item['status'] = msg.status.value
                item['created_at'] = msg.created_at.isoformat()
                if msg.sent_at:
                    item['sent_at'] = msg.sent_at.isoformat()
                if msg.delivered_at:
                    item['delivered_at'] = msg.delivered_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

        convos_file = os.path.join(self.data_dir, "conversations.json")
        with open(convos_file, 'w') as f:
            data = []
            for convo in self.conversations.values():
                item = asdict(convo)
                if convo.last_message_at:
                    item['last_message_at'] = convo.last_message_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize a phone number to E.164 format."""
        # Remove all non-digits
        digits = re.sub(r'\D', '', phone)

        # Add country code if missing
        if len(digits) == 10:
            digits = '1' + digits

        return f'+{digits}'

    def send(
        self,
        to: str,
        message: str,
        contact_id: str = None,
        contact_name: str = None,
        metadata: Dict = None
    ) -> SMSMessage:
        """Send an SMS message."""
        to_normalized = self.normalize_phone(to)

        # Create message record
        sms = SMSMessage(
            id=str(uuid.uuid4()),
            to_number=to_normalized,
            from_number=self.from_number,
            body=message,
            direction=MessageDirection.OUTBOUND,
            contact_id=contact_id,
            contact_name=contact_name,
            metadata=metadata or {}
        )

        # Send via provider
        try:
            result = self.provider.send(to_normalized, message, self.from_number)
            sms.provider_id = result.get('sid')
            sms.status = MessageStatus.SENT
            sms.sent_at = datetime.now()
        except Exception as e:
            sms.status = MessageStatus.FAILED
            sms.error_message = str(e)

        self.messages[sms.id] = sms

        # Update conversation
        self._update_conversation(sms)

        self._save_data()
        return sms

    def _update_conversation(self, message: SMSMessage):
        """Update or create conversation for a message."""
        # Find existing conversation
        convo = None
        for c in self.conversations.values():
            if c.contact_number == message.to_number:
                convo = c
                break

        if not convo:
            convo = Conversation(
                id=str(uuid.uuid4()),
                contact_id=message.contact_id or '',
                contact_name=message.contact_name or message.to_number,
                contact_number=message.to_number
            )
            self.conversations[convo.id] = convo

        convo.messages.append(message.id)
        convo.last_message_at = datetime.now()

        if message.direction == MessageDirection.INBOUND:
            convo.unread_count += 1

    def receive(
        self,
        from_number: str,
        message: str,
        provider_id: str = None,
        contact_id: str = None,
        contact_name: str = None
    ) -> SMSMessage:
        """Record a received SMS message."""
        from_normalized = self.normalize_phone(from_number)

        sms = SMSMessage(
            id=str(uuid.uuid4()),
            to_number=self.from_number,
            from_number=from_normalized,
            body=message,
            direction=MessageDirection.INBOUND,
            status=MessageStatus.DELIVERED,
            provider_id=provider_id,
            contact_id=contact_id,
            contact_name=contact_name,
            delivered_at=datetime.now()
        )

        self.messages[sms.id] = sms
        self._update_conversation(sms)
        self._save_data()
        return sms

    def get_message(self, message_id: str) -> Optional[SMSMessage]:
        """Get a message by ID."""
        return self.messages.get(message_id)

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID."""
        return self.conversations.get(conversation_id)

    def get_conversation_messages(self, conversation_id: str) -> List[SMSMessage]:
        """Get all messages in a conversation."""
        convo = self.get_conversation(conversation_id)
        if not convo:
            return []
        return [self.messages[mid] for mid in convo.messages if mid in self.messages]

    def get_conversations(self, include_archived: bool = False) -> List[Conversation]:
        """Get all conversations, sorted by last message."""
        convos = list(self.conversations.values())
        if not include_archived:
            convos = [c for c in convos if not c.is_archived]
        return sorted(convos, key=lambda c: c.last_message_at or datetime.min, reverse=True)

    def mark_read(self, conversation_id: str):
        """Mark a conversation as read."""
        convo = self.get_conversation(conversation_id)
        if convo:
            convo.unread_count = 0
            self._save_data()

    def archive_conversation(self, conversation_id: str):
        """Archive a conversation."""
        convo = self.get_conversation(conversation_id)
        if convo:
            convo.is_archived = True
            self._save_data()

    def get_unread_count(self) -> int:
        """Get total unread message count."""
        return sum(c.unread_count for c in self.conversations.values())

    def search_messages(self, query: str, limit: int = 50) -> List[SMSMessage]:
        """Search messages by content."""
        query_lower = query.lower()
        results = []
        for msg in self.messages.values():
            if query_lower in msg.body.lower():
                results.append(msg)
            if len(results) >= limit:
                break
        return sorted(results, key=lambda m: m.created_at, reverse=True)

    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get messaging statistics."""
        cutoff = datetime.now() - timedelta(days=days)

        recent_messages = [m for m in self.messages.values() if m.created_at >= cutoff]

        outbound = [m for m in recent_messages if m.direction == MessageDirection.OUTBOUND]
        inbound = [m for m in recent_messages if m.direction == MessageDirection.INBOUND]
        sent = [m for m in outbound if m.status == MessageStatus.SENT]
        delivered = [m for m in outbound if m.status == MessageStatus.DELIVERED]
        failed = [m for m in outbound if m.status == MessageStatus.FAILED]

        return {
            'total_sent': len(outbound),
            'total_received': len(inbound),
            'delivered': len(delivered),
            'failed': len(failed),
            'delivery_rate': len(delivered) / len(sent) * 100 if sent else 100,
            'active_conversations': len([c for c in self.conversations.values()
                                        if c.last_message_at and c.last_message_at >= cutoff]),
            'unread_count': self.get_unread_count()
        }

    # Quick message helpers

    def send_showing_reminder(
        self,
        to: str,
        contact_name: str,
        property_address: str,
        showing_time: str,
        showing_date: str
    ) -> SMSMessage:
        """Send a showing reminder."""
        message = (
            f"Hi {contact_name}! Reminder: Your showing at {property_address} is "
            f"scheduled for {showing_date} at {showing_time}. "
            f"Reply YES to confirm or call us to reschedule. -TD Realty"
        )
        return self.send(to, message, contact_name=contact_name, metadata={'type': 'showing_reminder'})

    def send_new_listing_alert(
        self,
        to: str,
        contact_name: str,
        property_address: str,
        price: str,
        link: str
    ) -> SMSMessage:
        """Send a new listing alert."""
        message = (
            f"Hi {contact_name}! New listing alert: {property_address} - ${price}. "
            f"View details: {link} -TD Realty"
        )
        return self.send(to, message, contact_name=contact_name, metadata={'type': 'listing_alert'})

    def send_offer_update(
        self,
        to: str,
        contact_name: str,
        property_address: str,
        status: str
    ) -> SMSMessage:
        """Send an offer status update."""
        message = (
            f"Hi {contact_name}! Update on your offer for {property_address}: {status}. "
            f"I'll call you shortly to discuss next steps. -TD Realty"
        )
        return self.send(to, message, contact_name=contact_name, metadata={'type': 'offer_update'})
