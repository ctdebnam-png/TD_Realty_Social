"""Notification management system."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any, Callable


class NotificationType(Enum):
    """Types of notifications."""
    # Lead-related
    NEW_LEAD = "new_lead"
    HOT_LEAD = "hot_lead"
    LEAD_RESPONSE = "lead_response"
    LEAD_ACTIVITY = "lead_activity"

    # Showing-related
    SHOWING_REQUEST = "showing_request"
    SHOWING_CONFIRMED = "showing_confirmed"
    SHOWING_REMINDER = "showing_reminder"
    SHOWING_FEEDBACK = "showing_feedback"

    # Offer-related
    OFFER_RECEIVED = "offer_received"
    OFFER_COUNTER = "offer_counter"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    OFFER_EXPIRED = "offer_expired"

    # Transaction-related
    TRANSACTION_UPDATE = "transaction_update"
    MILESTONE_COMPLETED = "milestone_completed"
    DOCUMENT_RECEIVED = "document_received"
    DOCUMENT_SIGNED = "document_signed"
    CLOSING_REMINDER = "closing_reminder"

    # Property-related
    NEW_LISTING = "new_listing"
    PRICE_CHANGE = "price_change"
    STATUS_CHANGE = "status_change"

    # Task-related
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE = "task_due"
    TASK_OVERDUE = "task_overdue"

    # System
    SYSTEM_ALERT = "system_alert"
    REVIEW_RECEIVED = "review_received"
    MESSAGE_RECEIVED = "message_received"


class NotificationPriority(Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class Notification:
    """A notification to be delivered."""
    id: str
    recipient_id: str
    recipient_type: str  # agent, client, admin
    notification_type: NotificationType
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    status: NotificationStatus = NotificationStatus.PENDING
    channels: List[str] = field(default_factory=list)  # email, sms, push, in_app
    data: Dict[str, Any] = field(default_factory=dict)
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @property
    def is_read(self) -> bool:
        return self.status == NotificationStatus.READ

    @property
    def is_expired(self) -> bool:
        return self.expires_at and datetime.now() > self.expires_at


@dataclass
class NotificationRule:
    """A rule for automatic notification routing."""
    id: str
    name: str
    notification_type: NotificationType
    conditions: Dict[str, Any] = field(default_factory=dict)
    channels: List[str] = field(default_factory=list)
    priority: NotificationPriority = NotificationPriority.NORMAL
    is_active: bool = True


class NotificationManager:
    """Manages notifications across all channels."""

    def __init__(self, data_dir: str = "data/notifications"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.notifications: Dict[str, Notification] = {}
        self.rules: Dict[str, NotificationRule] = {}
        self.channel_handlers: Dict[str, Callable] = {}
        self._load_data()
        self._ensure_default_rules()

    def _load_data(self):
        """Load existing data from files."""
        notifications_file = os.path.join(self.data_dir, "notifications.json")
        if os.path.exists(notifications_file):
            with open(notifications_file) as f:
                data = json.load(f)
                for item in data:
                    item['notification_type'] = NotificationType(item['notification_type'])
                    item['priority'] = NotificationPriority(item['priority'])
                    item['status'] = NotificationStatus(item['status'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    if item.get('sent_at'):
                        item['sent_at'] = datetime.fromisoformat(item['sent_at'])
                    if item.get('read_at'):
                        item['read_at'] = datetime.fromisoformat(item['read_at'])
                    if item.get('expires_at'):
                        item['expires_at'] = datetime.fromisoformat(item['expires_at'])
                    self.notifications[item['id']] = Notification(**item)

        rules_file = os.path.join(self.data_dir, "rules.json")
        if os.path.exists(rules_file):
            with open(rules_file) as f:
                data = json.load(f)
                for item in data:
                    item['notification_type'] = NotificationType(item['notification_type'])
                    item['priority'] = NotificationPriority(item['priority'])
                    self.rules[item['id']] = NotificationRule(**item)

    def _save_data(self):
        """Save data to files."""
        notifications_file = os.path.join(self.data_dir, "notifications.json")
        with open(notifications_file, 'w') as f:
            data = []
            for notif in self.notifications.values():
                item = asdict(notif)
                item['notification_type'] = notif.notification_type.value
                item['priority'] = notif.priority.value
                item['status'] = notif.status.value
                item['created_at'] = notif.created_at.isoformat()
                if notif.sent_at:
                    item['sent_at'] = notif.sent_at.isoformat()
                if notif.read_at:
                    item['read_at'] = notif.read_at.isoformat()
                if notif.expires_at:
                    item['expires_at'] = notif.expires_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

        rules_file = os.path.join(self.data_dir, "rules.json")
        with open(rules_file, 'w') as f:
            data = []
            for rule in self.rules.values():
                item = asdict(rule)
                item['notification_type'] = rule.notification_type.value
                item['priority'] = rule.priority.value
                data.append(item)
            json.dump(data, f, indent=2)

    def register_channel(self, channel_name: str, handler: Callable):
        """Register a channel handler."""
        self.channel_handlers[channel_name] = handler

    def create_notification(
        self,
        recipient_id: str,
        recipient_type: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = None,
        channels: List[str] = None,
        data: Dict = None,
        action_url: str = None,
        action_label: str = None,
        expires_in_hours: int = None
    ) -> Notification:
        """Create a new notification."""
        # Get channels and priority from rules if not specified
        if channels is None or priority is None:
            rule = self._find_matching_rule(notification_type, data or {})
            if rule:
                channels = channels or rule.channels
                priority = priority or rule.priority

        # Defaults
        channels = channels or ['in_app']
        priority = priority or NotificationPriority.NORMAL

        expires_at = None
        if expires_in_hours:
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)

        notification = Notification(
            id=str(uuid.uuid4()),
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            channels=channels,
            data=data or {},
            action_url=action_url,
            action_label=action_label,
            expires_at=expires_at
        )

        self.notifications[notification.id] = notification
        self._save_data()

        return notification

    def send_notification(self, notification_id: str) -> bool:
        """Send a notification through its channels."""
        notification = self.get_notification(notification_id)
        if not notification or notification.status != NotificationStatus.PENDING:
            return False

        success = False
        for channel in notification.channels:
            if channel in self.channel_handlers:
                try:
                    self.channel_handlers[channel](notification)
                    success = True
                except Exception as e:
                    print(f"Error sending via {channel}: {e}")

        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now()
        else:
            notification.status = NotificationStatus.FAILED

        self._save_data()
        return success

    def notify(
        self,
        recipient_id: str,
        recipient_type: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create and immediately send a notification."""
        notification = self.create_notification(
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            notification_type=notification_type,
            title=title,
            message=message,
            **kwargs
        )
        self.send_notification(notification.id)
        return notification

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self.notifications.get(notification_id)

    def get_notifications(
        self,
        recipient_id: str,
        unread_only: bool = False,
        notification_type: NotificationType = None,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a recipient."""
        results = []
        for notif in self.notifications.values():
            if notif.recipient_id != recipient_id:
                continue
            if notif.is_expired:
                continue
            if unread_only and notif.is_read:
                continue
            if notification_type and notif.notification_type != notification_type:
                continue
            results.append(notif)

        results.sort(key=lambda n: n.created_at, reverse=True)
        return results[:limit]

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notification = self.get_notification(notification_id)
        if notification and not notification.is_read:
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now()
            self._save_data()
            return True
        return False

    def mark_all_read(self, recipient_id: str):
        """Mark all notifications as read for a recipient."""
        for notif in self.notifications.values():
            if notif.recipient_id == recipient_id and not notif.is_read:
                notif.status = NotificationStatus.READ
                notif.read_at = datetime.now()
        self._save_data()

    def get_unread_count(self, recipient_id: str) -> int:
        """Get unread notification count for a recipient."""
        count = 0
        for notif in self.notifications.values():
            if (notif.recipient_id == recipient_id and
                not notif.is_read and
                not notif.is_expired):
                count += 1
        return count

    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification."""
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            self._save_data()
            return True
        return False

    def cleanup_expired(self):
        """Remove expired notifications."""
        expired = [n.id for n in self.notifications.values() if n.is_expired]
        for nid in expired:
            del self.notifications[nid]
        if expired:
            self._save_data()

    def _find_matching_rule(
        self,
        notification_type: NotificationType,
        data: Dict
    ) -> Optional[NotificationRule]:
        """Find a matching notification rule."""
        for rule in self.rules.values():
            if rule.notification_type == notification_type and rule.is_active:
                # Check conditions
                matches = True
                for key, value in rule.conditions.items():
                    if key in data and data[key] != value:
                        matches = False
                        break
                if matches:
                    return rule
        return None

    def create_rule(
        self,
        name: str,
        notification_type: NotificationType,
        channels: List[str],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        conditions: Dict = None
    ) -> NotificationRule:
        """Create a notification rule."""
        rule = NotificationRule(
            id=str(uuid.uuid4()),
            name=name,
            notification_type=notification_type,
            channels=channels,
            priority=priority,
            conditions=conditions or {}
        )
        self.rules[rule.id] = rule
        self._save_data()
        return rule

    def _ensure_default_rules(self):
        """Create default notification rules if none exist."""
        if not self.rules:
            self._create_default_rules()

    def _create_default_rules(self):
        """Create default notification routing rules."""

        # High priority - multi-channel
        self.create_rule(
            name="Hot Lead Alert",
            notification_type=NotificationType.HOT_LEAD,
            channels=['in_app', 'email', 'sms', 'push'],
            priority=NotificationPriority.URGENT
        )

        self.create_rule(
            name="Offer Received",
            notification_type=NotificationType.OFFER_RECEIVED,
            channels=['in_app', 'email', 'sms', 'push'],
            priority=NotificationPriority.URGENT
        )

        self.create_rule(
            name="Offer Accepted",
            notification_type=NotificationType.OFFER_ACCEPTED,
            channels=['in_app', 'email', 'sms'],
            priority=NotificationPriority.HIGH
        )

        # Normal priority
        self.create_rule(
            name="New Lead",
            notification_type=NotificationType.NEW_LEAD,
            channels=['in_app', 'email'],
            priority=NotificationPriority.NORMAL
        )

        self.create_rule(
            name="Showing Request",
            notification_type=NotificationType.SHOWING_REQUEST,
            channels=['in_app', 'email', 'push'],
            priority=NotificationPriority.HIGH
        )

        self.create_rule(
            name="Showing Reminder",
            notification_type=NotificationType.SHOWING_REMINDER,
            channels=['in_app', 'sms', 'push'],
            priority=NotificationPriority.NORMAL
        )

        self.create_rule(
            name="Document Received",
            notification_type=NotificationType.DOCUMENT_RECEIVED,
            channels=['in_app', 'email'],
            priority=NotificationPriority.NORMAL
        )

        self.create_rule(
            name="Transaction Update",
            notification_type=NotificationType.TRANSACTION_UPDATE,
            channels=['in_app', 'email'],
            priority=NotificationPriority.NORMAL
        )

        self.create_rule(
            name="Message Received",
            notification_type=NotificationType.MESSAGE_RECEIVED,
            channels=['in_app', 'push'],
            priority=NotificationPriority.NORMAL
        )

        # Low priority
        self.create_rule(
            name="New Listing",
            notification_type=NotificationType.NEW_LISTING,
            channels=['in_app', 'email'],
            priority=NotificationPriority.LOW
        )

        self.create_rule(
            name="Review Received",
            notification_type=NotificationType.REVIEW_RECEIVED,
            channels=['in_app', 'email'],
            priority=NotificationPriority.LOW
        )

        self._save_data()

    # Convenience methods for common notifications

    def notify_new_lead(
        self,
        agent_id: str,
        lead_name: str,
        lead_source: str,
        lead_score: int
    ) -> Notification:
        """Send new lead notification."""
        priority = NotificationPriority.URGENT if lead_score >= 80 else NotificationPriority.NORMAL
        notification_type = NotificationType.HOT_LEAD if lead_score >= 80 else NotificationType.NEW_LEAD

        return self.notify(
            recipient_id=agent_id,
            recipient_type='agent',
            notification_type=notification_type,
            title=f"New {'Hot ' if lead_score >= 80 else ''}Lead: {lead_name}",
            message=f"New lead from {lead_source} with score {lead_score}. Follow up quickly!",
            priority=priority,
            data={'lead_name': lead_name, 'source': lead_source, 'score': lead_score},
            action_url=f"/leads",
            action_label="View Lead"
        )

    def notify_showing_request(
        self,
        agent_id: str,
        property_address: str,
        requested_date: str,
        client_name: str
    ) -> Notification:
        """Send showing request notification."""
        return self.notify(
            recipient_id=agent_id,
            recipient_type='agent',
            notification_type=NotificationType.SHOWING_REQUEST,
            title="Showing Request",
            message=f"{client_name} requested a showing at {property_address} on {requested_date}",
            data={'property': property_address, 'date': requested_date, 'client': client_name},
            action_url="/showings",
            action_label="Review Request"
        )

    def notify_offer_received(
        self,
        seller_id: str,
        property_address: str,
        offer_amount: float,
        buyer_name: str
    ) -> Notification:
        """Send offer received notification."""
        return self.notify(
            recipient_id=seller_id,
            recipient_type='client',
            notification_type=NotificationType.OFFER_RECEIVED,
            title="New Offer Received!",
            message=f"You've received a ${offer_amount:,.0f} offer on {property_address} from {buyer_name}",
            data={'property': property_address, 'amount': offer_amount, 'buyer': buyer_name},
            action_url="/portal/my-listings",
            action_label="Review Offer"
        )

    def notify_transaction_update(
        self,
        client_id: str,
        property_address: str,
        update_message: str
    ) -> Notification:
        """Send transaction update notification."""
        return self.notify(
            recipient_id=client_id,
            recipient_type='client',
            notification_type=NotificationType.TRANSACTION_UPDATE,
            title="Transaction Update",
            message=f"{property_address}: {update_message}",
            data={'property': property_address},
            action_url="/portal/dashboard",
            action_label="View Details"
        )
