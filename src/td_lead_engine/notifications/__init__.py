"""Notification system module."""

from .manager import NotificationManager, Notification, NotificationType, NotificationPriority
from .channels import NotificationChannel, EmailChannel, SMSChannel, PushChannel, InAppChannel
from .preferences import NotificationPreferences, PreferenceManager

__all__ = [
    'NotificationManager',
    'Notification',
    'NotificationType',
    'NotificationPriority',
    'NotificationChannel',
    'EmailChannel',
    'SMSChannel',
    'PushChannel',
    'InAppChannel',
    'NotificationPreferences',
    'PreferenceManager',
]
