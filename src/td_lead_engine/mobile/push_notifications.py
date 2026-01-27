"""Push notification service for mobile apps."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class NotificationType(Enum):
    """Push notification types."""
    NEW_LEAD = "new_lead"
    LEAD_ACTIVITY = "lead_activity"
    NEW_MESSAGE = "new_message"
    TASK_REMINDER = "task_reminder"
    TASK_ASSIGNED = "task_assigned"
    SHOWING_REMINDER = "showing_reminder"
    PRICE_CHANGE = "price_change"
    NEW_LISTING = "new_listing"
    OFFER_RECEIVED = "offer_received"
    DOCUMENT_SIGNED = "document_signed"
    TRANSACTION_UPDATE = "transaction_update"
    SYSTEM = "system"


@dataclass
class PushNotification:
    """A push notification."""
    id: str
    user_id: str
    notification_type: NotificationType
    title: str
    body: str
    data: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: datetime = None
    read_at: datetime = None
    
    # Delivery info
    device_ids: List[str] = field(default_factory=list)
    delivery_status: Dict[str, str] = field(default_factory=dict)  # device_id -> status


class PushNotificationService:
    """Send push notifications to mobile devices."""
    
    def __init__(
        self,
        storage_path: str = "data/push",
        fcm_server_key: str = "",
        apns_key_file: str = ""
    ):
        self.storage_path = storage_path
        self.fcm_server_key = fcm_server_key
        self.apns_key_file = apns_key_file
        self.notifications: List[PushNotification] = []
        
        self._load_notifications()
    
    def _load_notifications(self):
        """Load notification history."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        file_path = f"{self.storage_path}/notifications.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                for notif_data in data[-1000:]:
                    notif = PushNotification(
                        id=notif_data['id'],
                        user_id=notif_data['user_id'],
                        notification_type=NotificationType(notif_data['notification_type']),
                        title=notif_data['title'],
                        body=notif_data['body'],
                        data=notif_data.get('data', {}),
                        created_at=datetime.fromisoformat(notif_data['created_at']) if notif_data.get('created_at') else datetime.now(),
                        sent_at=datetime.fromisoformat(notif_data['sent_at']) if notif_data.get('sent_at') else None,
                        read_at=datetime.fromisoformat(notif_data['read_at']) if notif_data.get('read_at') else None,
                        device_ids=notif_data.get('device_ids', []),
                        delivery_status=notif_data.get('delivery_status', {})
                    )
                    self.notifications.append(notif)
    
    def _save_notifications(self):
        """Save notification history."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'id': n.id,
                'user_id': n.user_id,
                'notification_type': n.notification_type.value,
                'title': n.title,
                'body': n.body,
                'data': n.data,
                'created_at': n.created_at.isoformat(),
                'sent_at': n.sent_at.isoformat() if n.sent_at else None,
                'read_at': n.read_at.isoformat() if n.read_at else None,
                'device_ids': n.device_ids,
                'delivery_status': n.delivery_status
            }
            for n in self.notifications[-1000:]
        ]
        
        with open(f"{self.storage_path}/notifications.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def send(
        self,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: Dict = None,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send a push notification."""
        notification = PushNotification(
            id=str(uuid.uuid4())[:12],
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data or {}
        )
        
        # Send to devices
        if device_tokens:
            for token in device_tokens:
                success = self._send_to_device(token, notification)
                notification.delivery_status[token] = 'sent' if success else 'failed'
                notification.device_ids.append(token)
        
        notification.sent_at = datetime.now()
        self.notifications.append(notification)
        self._save_notifications()
        
        return notification
    
    def _send_to_device(self, device_token: str, notification: PushNotification) -> bool:
        """Send notification to a specific device."""
        # In production, this would use FCM for Android and APNs for iOS
        # For now, just simulate success
        return True
    
    def send_to_topic(
        self,
        topic: str,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: Dict = None
    ) -> bool:
        """Send notification to a topic (all subscribed devices)."""
        # FCM topic messaging
        return True
    
    # Convenience methods for common notifications
    def notify_new_lead(
        self,
        user_id: str,
        lead_name: str,
        lead_id: str,
        source: str,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send new lead notification."""
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.NEW_LEAD,
            title="New Lead!",
            body=f"{lead_name} from {source}",
            data={
                'type': 'new_lead',
                'lead_id': lead_id,
                'action': 'view_lead'
            },
            device_tokens=device_tokens
        )
    
    def notify_task_reminder(
        self,
        user_id: str,
        task_title: str,
        task_id: str,
        due_in_minutes: int,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send task reminder notification."""
        if due_in_minutes <= 0:
            body = f"Task overdue: {task_title}"
        elif due_in_minutes < 60:
            body = f"Task due in {due_in_minutes} minutes: {task_title}"
        else:
            hours = due_in_minutes // 60
            body = f"Task due in {hours} hour(s): {task_title}"
        
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.TASK_REMINDER,
            title="Task Reminder",
            body=body,
            data={
                'type': 'task_reminder',
                'task_id': task_id,
                'action': 'view_task'
            },
            device_tokens=device_tokens
        )
    
    def notify_showing_reminder(
        self,
        user_id: str,
        property_address: str,
        showing_time: str,
        lead_name: str,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send showing reminder notification."""
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.SHOWING_REMINDER,
            title="Upcoming Showing",
            body=f"{showing_time} - {property_address} with {lead_name}",
            data={
                'type': 'showing_reminder',
                'action': 'view_showing'
            },
            device_tokens=device_tokens
        )
    
    def notify_new_message(
        self,
        user_id: str,
        sender_name: str,
        message_preview: str,
        conversation_id: str,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send new message notification."""
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.NEW_MESSAGE,
            title=sender_name,
            body=message_preview[:100],
            data={
                'type': 'new_message',
                'conversation_id': conversation_id,
                'action': 'view_conversation'
            },
            device_tokens=device_tokens
        )
    
    def notify_price_change(
        self,
        user_id: str,
        property_address: str,
        old_price: float,
        new_price: float,
        property_id: str,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send price change notification."""
        change = new_price - old_price
        direction = "reduced" if change < 0 else "increased"
        
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.PRICE_CHANGE,
            title=f"Price {direction.title()}!",
            body=f"{property_address} now ${new_price:,.0f}",
            data={
                'type': 'price_change',
                'property_id': property_id,
                'old_price': old_price,
                'new_price': new_price,
                'action': 'view_property'
            },
            device_tokens=device_tokens
        )
    
    def notify_offer_received(
        self,
        user_id: str,
        property_address: str,
        offer_amount: float,
        buyer_name: str,
        device_tokens: List[str] = None
    ) -> PushNotification:
        """Send offer received notification."""
        return self.send(
            user_id=user_id,
            notification_type=NotificationType.OFFER_RECEIVED,
            title="New Offer Received!",
            body=f"${offer_amount:,.0f} on {property_address} from {buyer_name}",
            data={
                'type': 'offer_received',
                'action': 'view_offer'
            },
            device_tokens=device_tokens
        )
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for notif in self.notifications:
            if notif.id == notification_id:
                notif.read_at = datetime.now()
                self._save_notifications()
                return True
        return False
    
    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[PushNotification]:
        """Get notifications for a user."""
        notifications = [n for n in self.notifications if n.user_id == user_id]
        
        if unread_only:
            notifications = [n for n in notifications if n.read_at is None]
        
        notifications.sort(key=lambda n: n.created_at, reverse=True)
        return notifications[:limit]
    
    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for a user."""
        return len([n for n in self.notifications 
                   if n.user_id == user_id and n.read_at is None])
