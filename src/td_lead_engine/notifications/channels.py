"""Notification delivery channels."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime


class NotificationChannel(ABC):
    """Base class for notification channels."""

    @abstractmethod
    def send(self, notification) -> bool:
        """Send a notification through this channel."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the channel name."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    def __init__(self, email_service=None):
        self.email_service = email_service

    def get_name(self) -> str:
        return "email"

    def send(self, notification) -> bool:
        """Send notification via email."""
        if not self.email_service:
            # Log or simulate
            print(f"[EMAIL] To: {notification.recipient_id}")
            print(f"  Subject: {notification.title}")
            print(f"  Body: {notification.message}")
            return True

        try:
            # In production, use actual email service
            # self.email_service.send(
            #     to=notification.data.get('email'),
            #     subject=notification.title,
            #     body=notification.message
            # )
            return True
        except Exception as e:
            print(f"Email send error: {e}")
            return False


class SMSChannel(NotificationChannel):
    """SMS notification channel."""

    def __init__(self, sms_service=None):
        self.sms_service = sms_service

    def get_name(self) -> str:
        return "sms"

    def send(self, notification) -> bool:
        """Send notification via SMS."""
        if not self.sms_service:
            # Log or simulate
            print(f"[SMS] To: {notification.recipient_id}")
            print(f"  Message: {notification.message[:160]}")
            return True

        try:
            phone = notification.data.get('phone')
            if phone:
                # self.sms_service.send(phone, notification.message)
                return True
            return False
        except Exception as e:
            print(f"SMS send error: {e}")
            return False


class PushChannel(NotificationChannel):
    """Push notification channel."""

    def __init__(self, push_service=None):
        self.push_service = push_service

    def get_name(self) -> str:
        return "push"

    def send(self, notification) -> bool:
        """Send push notification."""
        if not self.push_service:
            # Log or simulate
            print(f"[PUSH] To: {notification.recipient_id}")
            print(f"  Title: {notification.title}")
            print(f"  Body: {notification.message[:100]}")
            return True

        try:
            # In production, use Firebase, APNS, etc.
            # self.push_service.send(
            #     user_id=notification.recipient_id,
            #     title=notification.title,
            #     body=notification.message,
            #     data=notification.data
            # )
            return True
        except Exception as e:
            print(f"Push send error: {e}")
            return False


@dataclass
class InAppNotification:
    """In-app notification for display in the web/mobile UI."""
    id: str
    title: str
    message: str
    type: str
    priority: str
    timestamp: datetime
    is_read: bool = False
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    data: Dict[str, Any] = None


class InAppChannel(NotificationChannel):
    """In-app notification channel (stores for later display)."""

    def __init__(self, storage=None):
        self.storage = storage or {}  # In production, use database

    def get_name(self) -> str:
        return "in_app"

    def send(self, notification) -> bool:
        """Store notification for in-app display."""
        try:
            in_app = InAppNotification(
                id=notification.id,
                title=notification.title,
                message=notification.message,
                type=notification.notification_type.value,
                priority=notification.priority.value,
                timestamp=datetime.now(),
                action_url=notification.action_url,
                action_label=notification.action_label,
                data=notification.data
            )

            # Store by recipient
            recipient = notification.recipient_id
            if recipient not in self.storage:
                self.storage[recipient] = []
            self.storage[recipient].append(in_app)

            print(f"[IN-APP] Stored for: {recipient}")
            print(f"  Title: {notification.title}")
            return True
        except Exception as e:
            print(f"In-app notification error: {e}")
            return False

    def get_notifications(self, recipient_id: str, limit: int = 50) -> list:
        """Get in-app notifications for a user."""
        if recipient_id not in self.storage:
            return []
        return sorted(
            self.storage[recipient_id],
            key=lambda n: n.timestamp,
            reverse=True
        )[:limit]

    def mark_read(self, recipient_id: str, notification_id: str):
        """Mark a notification as read."""
        if recipient_id in self.storage:
            for notif in self.storage[recipient_id]:
                if notif.id == notification_id:
                    notif.is_read = True
                    break

    def get_unread_count(self, recipient_id: str) -> int:
        """Get unread count for a user."""
        if recipient_id not in self.storage:
            return 0
        return len([n for n in self.storage[recipient_id] if not n.is_read])


class WebhookChannel(NotificationChannel):
    """Webhook notification channel for external integrations."""

    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url

    def get_name(self) -> str:
        return "webhook"

    def send(self, notification) -> bool:
        """Send notification via webhook."""
        if not self.webhook_url:
            print(f"[WEBHOOK] No URL configured")
            return False

        try:
            # In production, use requests library
            # import requests
            # response = requests.post(
            #     self.webhook_url,
            #     json={
            #         'id': notification.id,
            #         'type': notification.notification_type.value,
            #         'title': notification.title,
            #         'message': notification.message,
            #         'data': notification.data,
            #         'timestamp': notification.created_at.isoformat()
            #     },
            #     timeout=10
            # )
            # return response.status_code == 200

            print(f"[WEBHOOK] Would POST to: {self.webhook_url}")
            print(f"  Type: {notification.notification_type.value}")
            print(f"  Title: {notification.title}")
            return True
        except Exception as e:
            print(f"Webhook send error: {e}")
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel."""

    def __init__(self, webhook_url: str = None, channel: str = None):
        self.webhook_url = webhook_url
        self.channel = channel or "#notifications"

    def get_name(self) -> str:
        return "slack"

    def send(self, notification) -> bool:
        """Send notification to Slack."""
        if not self.webhook_url:
            print(f"[SLACK] No webhook URL configured")
            return False

        try:
            # Build Slack message
            priority_emoji = {
                'urgent': ':rotating_light:',
                'high': ':warning:',
                'normal': ':bell:',
                'low': ':information_source:'
            }.get(notification.priority.value, ':bell:')

            # In production, use requests
            # import requests
            # response = requests.post(
            #     self.webhook_url,
            #     json={
            #         'channel': self.channel,
            #         'text': f"{priority_emoji} *{notification.title}*\n{notification.message}",
            #         'attachments': [{
            #             'fields': [
            #                 {'title': k, 'value': str(v), 'short': True}
            #                 for k, v in notification.data.items()
            #             ]
            #         }] if notification.data else []
            #     }
            # )
            # return response.status_code == 200

            print(f"[SLACK] {self.channel}")
            print(f"  {priority_emoji} {notification.title}")
            print(f"  {notification.message}")
            return True
        except Exception as e:
            print(f"Slack send error: {e}")
            return False


def create_channel_registry(
    email_service=None,
    sms_service=None,
    push_service=None,
    slack_webhook=None
) -> Dict[str, NotificationChannel]:
    """Create a registry of notification channels."""
    channels = {
        'email': EmailChannel(email_service),
        'sms': SMSChannel(sms_service),
        'push': PushChannel(push_service),
        'in_app': InAppChannel()
    }

    if slack_webhook:
        channels['slack'] = SlackChannel(slack_webhook)

    return channels
