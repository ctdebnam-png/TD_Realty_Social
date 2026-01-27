"""Notification preferences management."""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, time
from typing import Optional, Dict, List, Any
from enum import Enum


class QuietHoursMode(Enum):
    """Quiet hours mode."""
    OFF = "off"
    ALWAYS = "always"
    SCHEDULED = "scheduled"


@dataclass
class ChannelPreference:
    """Preferences for a specific notification channel."""
    enabled: bool = True
    quiet_hours: QuietHoursMode = QuietHoursMode.OFF
    quiet_start: str = "22:00"  # 10 PM
    quiet_end: str = "08:00"    # 8 AM


@dataclass
class NotificationTypePreference:
    """Preferences for a specific notification type."""
    enabled: bool = True
    channels: Dict[str, bool] = field(default_factory=lambda: {
        'email': True,
        'sms': True,
        'push': True,
        'in_app': True
    })
    frequency: str = "immediate"  # immediate, daily_digest, weekly_digest


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    user_id: str
    email: Optional[str] = None
    phone: Optional[str] = None

    # Global settings
    notifications_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True

    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_start: str = "22:00"
    quiet_end: str = "08:00"
    urgent_override_quiet: bool = True  # Urgent notifications ignore quiet hours

    # Channel-specific preferences
    channel_preferences: Dict[str, ChannelPreference] = field(default_factory=dict)

    # Type-specific preferences
    type_preferences: Dict[str, NotificationTypePreference] = field(default_factory=dict)

    # Digest settings
    daily_digest_enabled: bool = False
    daily_digest_time: str = "09:00"
    weekly_digest_enabled: bool = False
    weekly_digest_day: str = "monday"

    updated_at: datetime = field(default_factory=datetime.now)

    def is_channel_enabled(self, channel: str) -> bool:
        """Check if a channel is enabled."""
        if not self.notifications_enabled:
            return False

        if channel == 'email' and not self.email_enabled:
            return False
        if channel == 'sms' and not self.sms_enabled:
            return False
        if channel == 'push' and not self.push_enabled:
            return False

        if channel in self.channel_preferences:
            return self.channel_preferences[channel].enabled

        return True

    def should_send(
        self,
        notification_type: str,
        channel: str,
        is_urgent: bool = False
    ) -> bool:
        """Check if a notification should be sent."""
        if not self.notifications_enabled:
            return False

        if not self.is_channel_enabled(channel):
            return False

        # Check type-specific preferences
        if notification_type in self.type_preferences:
            type_pref = self.type_preferences[notification_type]
            if not type_pref.enabled:
                return False
            if channel in type_pref.channels and not type_pref.channels[channel]:
                return False

        # Check quiet hours
        if self.quiet_hours_enabled and not (is_urgent and self.urgent_override_quiet):
            if self._is_quiet_hours():
                return False

        return True

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        now = datetime.now().time()
        start = time.fromisoformat(self.quiet_start)
        end = time.fromisoformat(self.quiet_end)

        if start <= end:
            return start <= now <= end
        else:
            # Quiet hours span midnight
            return now >= start or now <= end


class PreferenceManager:
    """Manages notification preferences for all users."""

    def __init__(self, data_dir: str = "data/preferences"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.preferences: Dict[str, NotificationPreferences] = {}
        self._load_data()

    def _load_data(self):
        """Load preferences from file."""
        prefs_file = os.path.join(self.data_dir, "notification_preferences.json")
        if os.path.exists(prefs_file):
            with open(prefs_file) as f:
                data = json.load(f)
                for user_id, item in data.items():
                    # Convert nested dataclasses
                    channel_prefs = {}
                    for ch, cp in item.get('channel_preferences', {}).items():
                        cp['quiet_hours'] = QuietHoursMode(cp.get('quiet_hours', 'off'))
                        channel_prefs[ch] = ChannelPreference(**cp)
                    item['channel_preferences'] = channel_prefs

                    type_prefs = {}
                    for tp, val in item.get('type_preferences', {}).items():
                        type_prefs[tp] = NotificationTypePreference(**val)
                    item['type_preferences'] = type_prefs

                    if 'updated_at' in item:
                        item['updated_at'] = datetime.fromisoformat(item['updated_at'])

                    self.preferences[user_id] = NotificationPreferences(**item)

    def _save_data(self):
        """Save preferences to file."""
        prefs_file = os.path.join(self.data_dir, "notification_preferences.json")
        with open(prefs_file, 'w') as f:
            data = {}
            for user_id, prefs in self.preferences.items():
                item = asdict(prefs)
                # Convert enums
                for ch, cp in item.get('channel_preferences', {}).items():
                    if isinstance(cp.get('quiet_hours'), QuietHoursMode):
                        cp['quiet_hours'] = cp['quiet_hours'].value
                item['updated_at'] = prefs.updated_at.isoformat()
                data[user_id] = item
            json.dump(data, f, indent=2)

    def get_preferences(self, user_id: str) -> NotificationPreferences:
        """Get preferences for a user, creating defaults if needed."""
        if user_id not in self.preferences:
            self.preferences[user_id] = NotificationPreferences(user_id=user_id)
            self._create_default_type_preferences(self.preferences[user_id])
            self._save_data()
        return self.preferences[user_id]

    def update_preferences(self, user_id: str, **updates) -> NotificationPreferences:
        """Update preferences for a user."""
        prefs = self.get_preferences(user_id)
        for key, value in updates.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        prefs.updated_at = datetime.now()
        self._save_data()
        return prefs

    def set_channel_enabled(self, user_id: str, channel: str, enabled: bool):
        """Enable or disable a notification channel."""
        prefs = self.get_preferences(user_id)
        if channel == 'email':
            prefs.email_enabled = enabled
        elif channel == 'sms':
            prefs.sms_enabled = enabled
        elif channel == 'push':
            prefs.push_enabled = enabled
        prefs.updated_at = datetime.now()
        self._save_data()

    def set_type_preference(
        self,
        user_id: str,
        notification_type: str,
        enabled: bool = None,
        channels: Dict[str, bool] = None,
        frequency: str = None
    ):
        """Set preferences for a specific notification type."""
        prefs = self.get_preferences(user_id)

        if notification_type not in prefs.type_preferences:
            prefs.type_preferences[notification_type] = NotificationTypePreference()

        type_pref = prefs.type_preferences[notification_type]

        if enabled is not None:
            type_pref.enabled = enabled
        if channels is not None:
            type_pref.channels.update(channels)
        if frequency is not None:
            type_pref.frequency = frequency

        prefs.updated_at = datetime.now()
        self._save_data()

    def set_quiet_hours(
        self,
        user_id: str,
        enabled: bool,
        start: str = None,
        end: str = None,
        urgent_override: bool = True
    ):
        """Set quiet hours preferences."""
        prefs = self.get_preferences(user_id)
        prefs.quiet_hours_enabled = enabled
        if start:
            prefs.quiet_start = start
        if end:
            prefs.quiet_end = end
        prefs.urgent_override_quiet = urgent_override
        prefs.updated_at = datetime.now()
        self._save_data()

    def set_contact_info(self, user_id: str, email: str = None, phone: str = None):
        """Set contact information."""
        prefs = self.get_preferences(user_id)
        if email:
            prefs.email = email
        if phone:
            prefs.phone = phone
        prefs.updated_at = datetime.now()
        self._save_data()

    def should_notify(
        self,
        user_id: str,
        notification_type: str,
        channel: str,
        is_urgent: bool = False
    ) -> bool:
        """Check if a notification should be sent to a user."""
        prefs = self.get_preferences(user_id)
        return prefs.should_send(notification_type, channel, is_urgent)

    def get_enabled_channels(
        self,
        user_id: str,
        notification_type: str,
        is_urgent: bool = False
    ) -> List[str]:
        """Get list of enabled channels for a notification type."""
        prefs = self.get_preferences(user_id)
        enabled = []

        for channel in ['email', 'sms', 'push', 'in_app']:
            if prefs.should_send(notification_type, channel, is_urgent):
                enabled.append(channel)

        return enabled

    def _create_default_type_preferences(self, prefs: NotificationPreferences):
        """Create default preferences for each notification type."""
        # Lead notifications
        prefs.type_preferences['new_lead'] = NotificationTypePreference(
            channels={'email': True, 'sms': False, 'push': True, 'in_app': True}
        )
        prefs.type_preferences['hot_lead'] = NotificationTypePreference(
            channels={'email': True, 'sms': True, 'push': True, 'in_app': True}
        )

        # Showing notifications
        prefs.type_preferences['showing_request'] = NotificationTypePreference(
            channels={'email': True, 'sms': True, 'push': True, 'in_app': True}
        )
        prefs.type_preferences['showing_reminder'] = NotificationTypePreference(
            channels={'email': True, 'sms': True, 'push': True, 'in_app': True}
        )

        # Offer notifications
        prefs.type_preferences['offer_received'] = NotificationTypePreference(
            channels={'email': True, 'sms': True, 'push': True, 'in_app': True}
        )
        prefs.type_preferences['offer_accepted'] = NotificationTypePreference(
            channels={'email': True, 'sms': True, 'push': True, 'in_app': True}
        )

        # Property notifications
        prefs.type_preferences['new_listing'] = NotificationTypePreference(
            channels={'email': True, 'sms': False, 'push': False, 'in_app': True},
            frequency='daily_digest'
        )
        prefs.type_preferences['price_change'] = NotificationTypePreference(
            channels={'email': True, 'sms': False, 'push': True, 'in_app': True}
        )

        # Transaction notifications
        prefs.type_preferences['transaction_update'] = NotificationTypePreference(
            channels={'email': True, 'sms': False, 'push': True, 'in_app': True}
        )
        prefs.type_preferences['document_received'] = NotificationTypePreference(
            channels={'email': True, 'sms': False, 'push': False, 'in_app': True}
        )

        # Message notifications
        prefs.type_preferences['message_received'] = NotificationTypePreference(
            channels={'email': False, 'sms': False, 'push': True, 'in_app': True}
        )
