"""Listing alerts for saved searches."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import threading
import time

from .client import MLSClient, Property, PropertyStatus
from .search import PropertySearch, SearchCriteria, SavedSearch


class AlertType(Enum):
    """Types of listing alerts."""
    NEW_LISTING = "new_listing"
    PRICE_CHANGE = "price_change"
    PRICE_REDUCTION = "price_reduction"
    PRICE_INCREASE = "price_increase"
    BACK_ON_MARKET = "back_on_market"
    OPEN_HOUSE = "open_house"
    STATUS_CHANGE = "status_change"


@dataclass
class Alert:
    """A single listing alert."""
    id: str
    alert_type: AlertType
    search_id: str
    lead_id: str
    property: Property
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: datetime = None
    viewed_at: datetime = None
    details: Dict = field(default_factory=dict)


@dataclass
class AlertPreferences:
    """User alert preferences."""
    lead_id: str
    email_alerts: bool = True
    sms_alerts: bool = False
    push_alerts: bool = True
    frequency: str = "instant"  # instant, daily, weekly
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 8    # 8 AM
    alert_types: List[AlertType] = field(default_factory=lambda: list(AlertType))


class ListingAlerts:
    """Listing alert system."""
    
    def __init__(
        self,
        mls_client: MLSClient,
        property_search: PropertySearch,
        storage_path: str = "data/alerts"
    ):
        self.mls_client = mls_client
        self.property_search = property_search
        self.storage_path = storage_path
        
        self.alerts: Dict[str, Alert] = {}
        self.preferences: Dict[str, AlertPreferences] = {}
        self.property_snapshots: Dict[str, Dict] = {}  # For tracking changes
        self.alert_handlers: List[Callable] = []
        
        self._alert_thread: Optional[threading.Thread] = None
        self._running = False
        
        self._load_data()
    
    def _load_data(self):
        """Load alert data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load alerts
        alerts_file = f"{self.storage_path}/alerts.json"
        if os.path.exists(alerts_file):
            with open(alerts_file, 'r') as f:
                data = json.load(f)
                for alert_data in data[-1000:]:  # Keep last 1000
                    alert = Alert(
                        id=alert_data['id'],
                        alert_type=AlertType(alert_data['alert_type']),
                        search_id=alert_data['search_id'],
                        lead_id=alert_data['lead_id'],
                        property=Property.from_dict(alert_data['property']),
                        created_at=datetime.fromisoformat(alert_data['created_at']),
                        sent_at=datetime.fromisoformat(alert_data['sent_at']) if alert_data.get('sent_at') else None,
                        viewed_at=datetime.fromisoformat(alert_data['viewed_at']) if alert_data.get('viewed_at') else None,
                        details=alert_data.get('details', {})
                    )
                    self.alerts[alert.id] = alert
        
        # Load preferences
        prefs_file = f"{self.storage_path}/preferences.json"
        if os.path.exists(prefs_file):
            with open(prefs_file, 'r') as f:
                data = json.load(f)
                for pref_data in data:
                    alert_types = [AlertType(t) for t in pref_data.get('alert_types', [])]
                    prefs = AlertPreferences(
                        lead_id=pref_data['lead_id'],
                        email_alerts=pref_data.get('email_alerts', True),
                        sms_alerts=pref_data.get('sms_alerts', False),
                        push_alerts=pref_data.get('push_alerts', True),
                        frequency=pref_data.get('frequency', 'instant'),
                        quiet_hours_start=pref_data.get('quiet_hours_start', 22),
                        quiet_hours_end=pref_data.get('quiet_hours_end', 8),
                        alert_types=alert_types if alert_types else list(AlertType)
                    )
                    self.preferences[prefs.lead_id] = prefs
        
        # Load property snapshots
        snapshots_file = f"{self.storage_path}/snapshots.json"
        if os.path.exists(snapshots_file):
            with open(snapshots_file, 'r') as f:
                self.property_snapshots = json.load(f)
    
    def _save_data(self):
        """Save alert data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save alerts (last 1000)
        alerts_data = [
            {
                'id': a.id,
                'alert_type': a.alert_type.value,
                'search_id': a.search_id,
                'lead_id': a.lead_id,
                'property': a.property.to_dict(),
                'created_at': a.created_at.isoformat(),
                'sent_at': a.sent_at.isoformat() if a.sent_at else None,
                'viewed_at': a.viewed_at.isoformat() if a.viewed_at else None,
                'details': a.details
            }
            for a in list(self.alerts.values())[-1000:]
        ]
        with open(f"{self.storage_path}/alerts.json", 'w') as f:
            json.dump(alerts_data, f, indent=2)
        
        # Save preferences
        prefs_data = [
            {
                'lead_id': p.lead_id,
                'email_alerts': p.email_alerts,
                'sms_alerts': p.sms_alerts,
                'push_alerts': p.push_alerts,
                'frequency': p.frequency,
                'quiet_hours_start': p.quiet_hours_start,
                'quiet_hours_end': p.quiet_hours_end,
                'alert_types': [t.value for t in p.alert_types]
            }
            for p in self.preferences.values()
        ]
        with open(f"{self.storage_path}/preferences.json", 'w') as f:
            json.dump(prefs_data, f, indent=2)
        
        # Save snapshots
        with open(f"{self.storage_path}/snapshots.json", 'w') as f:
            json.dump(self.property_snapshots, f, indent=2)
    
    def add_alert_handler(self, handler: Callable):
        """Add a handler for alert events."""
        self.alert_handlers.append(handler)
    
    def _notify_handlers(self, alert: Alert):
        """Notify all handlers of a new alert."""
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception:
                pass
    
    def set_preferences(
        self,
        lead_id: str,
        email_alerts: bool = None,
        sms_alerts: bool = None,
        push_alerts: bool = None,
        frequency: str = None,
        quiet_hours_start: int = None,
        quiet_hours_end: int = None,
        alert_types: List[AlertType] = None
    ) -> AlertPreferences:
        """Set alert preferences for a lead."""
        if lead_id in self.preferences:
            prefs = self.preferences[lead_id]
        else:
            prefs = AlertPreferences(lead_id=lead_id)
        
        if email_alerts is not None:
            prefs.email_alerts = email_alerts
        if sms_alerts is not None:
            prefs.sms_alerts = sms_alerts
        if push_alerts is not None:
            prefs.push_alerts = push_alerts
        if frequency is not None:
            prefs.frequency = frequency
        if quiet_hours_start is not None:
            prefs.quiet_hours_start = quiet_hours_start
        if quiet_hours_end is not None:
            prefs.quiet_hours_end = quiet_hours_end
        if alert_types is not None:
            prefs.alert_types = alert_types
        
        self.preferences[lead_id] = prefs
        self._save_data()
        return prefs
    
    def get_preferences(self, lead_id: str) -> AlertPreferences:
        """Get alert preferences for a lead."""
        if lead_id not in self.preferences:
            self.preferences[lead_id] = AlertPreferences(lead_id=lead_id)
        return self.preferences[lead_id]
    
    def check_for_alerts(self) -> List[Alert]:
        """Check all saved searches for new alerts."""
        new_alerts = []
        
        for saved_search in self.property_search.saved_searches.values():
            # Run the search
            results = self.property_search.search(saved_search.criteria)
            
            for prop in results.properties:
                # Check for new listing
                if saved_search.notify_new_listings:
                    if self._is_new_for_search(prop, saved_search):
                        alert = self._create_alert(
                            AlertType.NEW_LISTING,
                            saved_search,
                            prop
                        )
                        new_alerts.append(alert)
                
                # Check for price changes
                if saved_search.notify_price_changes:
                    price_change = self._check_price_change(prop)
                    if price_change:
                        alert_type, details = price_change
                        alert = self._create_alert(
                            alert_type,
                            saved_search,
                            prop,
                            details
                        )
                        new_alerts.append(alert)
            
            # Update snapshot for this search
            self._update_search_snapshot(saved_search, results.properties)
        
        self._save_data()
        return new_alerts
    
    def _is_new_for_search(self, prop: Property, search: SavedSearch) -> bool:
        """Check if property is new for this search."""
        snapshot_key = f"search_{search.id}"
        
        if snapshot_key not in self.property_snapshots:
            return True
        
        seen_ids = self.property_snapshots[snapshot_key].get('property_ids', [])
        return prop.mls_id not in seen_ids
    
    def _check_price_change(self, prop: Property) -> Optional[tuple]:
        """Check if property has a price change."""
        snapshot_key = f"property_{prop.mls_id}"
        
        if snapshot_key not in self.property_snapshots:
            # First time seeing this property
            self.property_snapshots[snapshot_key] = {
                'list_price': prop.list_price,
                'status': prop.status.value,
                'last_checked': datetime.now().isoformat()
            }
            return None
        
        old_price = self.property_snapshots[snapshot_key].get('list_price')
        
        if old_price and old_price != prop.list_price:
            # Price changed
            change_amount = prop.list_price - old_price
            change_pct = (change_amount / old_price) * 100
            
            # Update snapshot
            self.property_snapshots[snapshot_key]['list_price'] = prop.list_price
            self.property_snapshots[snapshot_key]['last_checked'] = datetime.now().isoformat()
            
            details = {
                'old_price': old_price,
                'new_price': prop.list_price,
                'change_amount': change_amount,
                'change_percent': change_pct
            }
            
            if change_amount < 0:
                return (AlertType.PRICE_REDUCTION, details)
            else:
                return (AlertType.PRICE_INCREASE, details)
        
        return None
    
    def _update_search_snapshot(self, search: SavedSearch, properties: List[Property]):
        """Update snapshot for a saved search."""
        snapshot_key = f"search_{search.id}"
        self.property_snapshots[snapshot_key] = {
            'property_ids': [p.mls_id for p in properties],
            'last_checked': datetime.now().isoformat()
        }
    
    def _create_alert(
        self,
        alert_type: AlertType,
        search: SavedSearch,
        prop: Property,
        details: Dict = None
    ) -> Alert:
        """Create a new alert."""
        import uuid
        
        alert = Alert(
            id=str(uuid.uuid4())[:8],
            alert_type=alert_type,
            search_id=search.id,
            lead_id=search.lead_id,
            property=prop,
            details=details or {}
        )
        
        self.alerts[alert.id] = alert
        self._notify_handlers(alert)
        
        return alert
    
    def get_alerts(
        self,
        lead_id: str,
        unread_only: bool = False,
        alert_type: AlertType = None,
        limit: int = 50
    ) -> List[Alert]:
        """Get alerts for a lead."""
        alerts = [a for a in self.alerts.values() if a.lead_id == lead_id]
        
        if unread_only:
            alerts = [a for a in alerts if a.viewed_at is None]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]
    
    def mark_alert_viewed(self, alert_id: str) -> bool:
        """Mark an alert as viewed."""
        if alert_id in self.alerts:
            self.alerts[alert_id].viewed_at = datetime.now()
            self._save_data()
            return True
        return False
    
    def mark_all_viewed(self, lead_id: str) -> int:
        """Mark all alerts as viewed for a lead."""
        count = 0
        for alert in self.alerts.values():
            if alert.lead_id == lead_id and alert.viewed_at is None:
                alert.viewed_at = datetime.now()
                count += 1
        
        if count > 0:
            self._save_data()
        return count
    
    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save_data()
            return True
        return False
    
    def get_unread_count(self, lead_id: str) -> int:
        """Get count of unread alerts for a lead."""
        return len([a for a in self.alerts.values() 
                   if a.lead_id == lead_id and a.viewed_at is None])
    
    def should_send_now(self, lead_id: str) -> bool:
        """Check if alerts should be sent now based on preferences."""
        prefs = self.get_preferences(lead_id)
        
        # Check quiet hours
        current_hour = datetime.now().hour
        if prefs.quiet_hours_start < prefs.quiet_hours_end:
            # Normal range (e.g., 22-8 doesn't wrap)
            if prefs.quiet_hours_start <= current_hour < prefs.quiet_hours_end:
                return False
        else:
            # Wraps around midnight (e.g., 22-8)
            if current_hour >= prefs.quiet_hours_start or current_hour < prefs.quiet_hours_end:
                return False
        
        return True
    
    def get_pending_alerts_for_delivery(self) -> Dict[str, List[Alert]]:
        """Get alerts pending delivery, grouped by lead."""
        pending = {}
        
        for alert in self.alerts.values():
            if alert.sent_at is None:
                prefs = self.get_preferences(alert.lead_id)
                
                # Check if this alert type is enabled
                if alert.alert_type not in prefs.alert_types:
                    continue
                
                # Check frequency
                if prefs.frequency == 'instant':
                    if alert.lead_id not in pending:
                        pending[alert.lead_id] = []
                    pending[alert.lead_id].append(alert)
                elif prefs.frequency == 'daily':
                    # Check if we've sent today
                    pass  # Would need to track last daily send
                elif prefs.frequency == 'weekly':
                    pass  # Would need to track last weekly send
        
        return pending
    
    def mark_alerts_sent(self, alert_ids: List[str]):
        """Mark alerts as sent."""
        now = datetime.now()
        for alert_id in alert_ids:
            if alert_id in self.alerts:
                self.alerts[alert_id].sent_at = now
        self._save_data()
    
    def start_monitoring(self, check_interval_minutes: int = 15):
        """Start background alert monitoring."""
        if self._running:
            return
        
        self._running = True
        self._alert_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(check_interval_minutes,),
            daemon=True
        )
        self._alert_thread.start()
    
    def stop_monitoring(self):
        """Stop background alert monitoring."""
        self._running = False
        if self._alert_thread:
            self._alert_thread.join(timeout=5)
    
    def _monitoring_loop(self, interval_minutes: int):
        """Background monitoring loop."""
        while self._running:
            try:
                self.check_for_alerts()
            except Exception:
                pass
            
            # Sleep in small increments for responsive shutdown
            for _ in range(interval_minutes * 60):
                if not self._running:
                    break
                time.sleep(1)
    
    def get_alert_summary(self, lead_id: str, days: int = 7) -> Dict:
        """Get alert summary for a lead."""
        cutoff = datetime.now() - timedelta(days=days)
        
        alerts = [a for a in self.alerts.values() 
                 if a.lead_id == lead_id and a.created_at > cutoff]
        
        by_type = {}
        for alert in alerts:
            type_name = alert.alert_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1
        
        return {
            'total_alerts': len(alerts),
            'unread': len([a for a in alerts if a.viewed_at is None]),
            'by_type': by_type,
            'saved_searches': len(self.property_search.get_saved_searches(lead_id))
        }
