"""Mobile API endpoints for agent and client apps."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid
import hashlib
import secrets


class DeviceType(Enum):
    """Mobile device types."""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"


@dataclass
class MobileDevice:
    """A registered mobile device."""
    id: str
    user_id: str
    device_type: DeviceType
    device_token: str  # Push notification token
    device_name: str = ""
    os_version: str = ""
    app_version: str = ""
    last_active: datetime = field(default_factory=datetime.now)
    registered_at: datetime = field(default_factory=datetime.now)
    push_enabled: bool = True


@dataclass
class APISession:
    """Mobile API session."""
    id: str
    user_id: str
    device_id: str
    access_token: str
    refresh_token: str
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None
    last_used: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class MobileAPI:
    """Mobile API service."""
    
    def __init__(self, storage_path: str = "data/mobile"):
        self.storage_path = storage_path
        self.devices: Dict[str, MobileDevice] = {}
        self.sessions: Dict[str, APISession] = {}
        self.token_expiry_hours = 24
        self.refresh_token_days = 30
        
        self._load_data()
    
    def _load_data(self):
        """Load mobile data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load devices
        devices_file = f"{self.storage_path}/devices.json"
        if os.path.exists(devices_file):
            with open(devices_file, 'r') as f:
                data = json.load(f)
                for device_data in data:
                    device = MobileDevice(
                        id=device_data['id'],
                        user_id=device_data['user_id'],
                        device_type=DeviceType(device_data['device_type']),
                        device_token=device_data['device_token'],
                        device_name=device_data.get('device_name', ''),
                        os_version=device_data.get('os_version', ''),
                        app_version=device_data.get('app_version', ''),
                        last_active=datetime.fromisoformat(device_data['last_active']) if device_data.get('last_active') else datetime.now(),
                        registered_at=datetime.fromisoformat(device_data['registered_at']) if device_data.get('registered_at') else datetime.now(),
                        push_enabled=device_data.get('push_enabled', True)
                    )
                    self.devices[device.id] = device
        
        # Load sessions
        sessions_file = f"{self.storage_path}/sessions.json"
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                data = json.load(f)
                for session_data in data:
                    session = APISession(
                        id=session_data['id'],
                        user_id=session_data['user_id'],
                        device_id=session_data['device_id'],
                        access_token=session_data['access_token'],
                        refresh_token=session_data['refresh_token'],
                        created_at=datetime.fromisoformat(session_data['created_at']) if session_data.get('created_at') else datetime.now(),
                        expires_at=datetime.fromisoformat(session_data['expires_at']) if session_data.get('expires_at') else None,
                        last_used=datetime.fromisoformat(session_data['last_used']) if session_data.get('last_used') else datetime.now(),
                        is_active=session_data.get('is_active', True)
                    )
                    self.sessions[session.id] = session
    
    def _save_data(self):
        """Save mobile data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save devices
        devices_data = [
            {
                'id': d.id,
                'user_id': d.user_id,
                'device_type': d.device_type.value,
                'device_token': d.device_token,
                'device_name': d.device_name,
                'os_version': d.os_version,
                'app_version': d.app_version,
                'last_active': d.last_active.isoformat(),
                'registered_at': d.registered_at.isoformat(),
                'push_enabled': d.push_enabled
            }
            for d in self.devices.values()
        ]
        
        with open(f"{self.storage_path}/devices.json", 'w') as f:
            json.dump(devices_data, f, indent=2)
        
        # Save sessions
        sessions_data = [
            {
                'id': s.id,
                'user_id': s.user_id,
                'device_id': s.device_id,
                'access_token': s.access_token,
                'refresh_token': s.refresh_token,
                'created_at': s.created_at.isoformat(),
                'expires_at': s.expires_at.isoformat() if s.expires_at else None,
                'last_used': s.last_used.isoformat(),
                'is_active': s.is_active
            }
            for s in self.sessions.values()
        ]
        
        with open(f"{self.storage_path}/sessions.json", 'w') as f:
            json.dump(sessions_data, f, indent=2)
    
    def register_device(
        self,
        user_id: str,
        device_type: DeviceType,
        device_token: str,
        device_name: str = "",
        os_version: str = "",
        app_version: str = ""
    ) -> MobileDevice:
        """Register a mobile device."""
        # Check for existing device with same token
        for device in self.devices.values():
            if device.device_token == device_token:
                # Update existing device
                device.user_id = user_id
                device.device_name = device_name
                device.os_version = os_version
                device.app_version = app_version
                device.last_active = datetime.now()
                self._save_data()
                return device
        
        # Create new device
        device = MobileDevice(
            id=str(uuid.uuid4())[:12],
            user_id=user_id,
            device_type=device_type,
            device_token=device_token,
            device_name=device_name,
            os_version=os_version,
            app_version=app_version
        )
        self.devices[device.id] = device
        self._save_data()
        return device
    
    def unregister_device(self, device_id: str) -> bool:
        """Unregister a device."""
        if device_id in self.devices:
            del self.devices[device_id]
            # Invalidate sessions for this device
            for session in self.sessions.values():
                if session.device_id == device_id:
                    session.is_active = False
            self._save_data()
            return True
        return False
    
    def create_session(
        self,
        user_id: str,
        device_id: str
    ) -> APISession:
        """Create a new API session."""
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(48)
        
        session = APISession(
            id=str(uuid.uuid4())[:12],
            user_id=user_id,
            device_id=device_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now() + timedelta(hours=self.token_expiry_hours)
        )
        self.sessions[session.id] = session
        self._save_data()
        return session
    
    def validate_token(self, access_token: str) -> Optional[APISession]:
        """Validate an access token."""
        for session in self.sessions.values():
            if session.access_token == access_token and session.is_active:
                if session.expires_at and session.expires_at > datetime.now():
                    session.last_used = datetime.now()
                    return session
        return None
    
    def refresh_session(self, refresh_token: str) -> Optional[APISession]:
        """Refresh a session using refresh token."""
        for session in self.sessions.values():
            if session.refresh_token == refresh_token and session.is_active:
                # Check if refresh token is still valid
                refresh_expiry = session.created_at + timedelta(days=self.refresh_token_days)
                if refresh_expiry > datetime.now():
                    # Create new session
                    return self.create_session(session.user_id, session.device_id)
        return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            self._save_data()
            return True
        return False
    
    def get_user_devices(self, user_id: str) -> List[MobileDevice]:
        """Get all devices for a user."""
        return [d for d in self.devices.values() if d.user_id == user_id]
    
    def update_device_token(self, device_id: str, new_token: str) -> Optional[MobileDevice]:
        """Update device push token."""
        if device_id in self.devices:
            self.devices[device_id].device_token = new_token
            self._save_data()
            return self.devices[device_id]
        return None
    
    def set_push_enabled(self, device_id: str, enabled: bool) -> Optional[MobileDevice]:
        """Enable or disable push notifications for a device."""
        if device_id in self.devices:
            self.devices[device_id].push_enabled = enabled
            self._save_data()
            return self.devices[device_id]
        return None
    
    # API Response helpers
    def success_response(self, data: Any = None, message: str = "Success") -> Dict:
        """Create a success response."""
        response = {
            'success': True,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if data is not None:
            response['data'] = data
        return response
    
    def error_response(self, message: str, code: str = "ERROR", status: int = 400) -> Dict:
        """Create an error response."""
        return {
            'success': False,
            'error': {
                'code': code,
                'message': message
            },
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
    
    def paginated_response(
        self,
        items: List,
        page: int,
        page_size: int,
        total_count: int
    ) -> Dict:
        """Create a paginated response."""
        total_pages = (total_count + page_size - 1) // page_size
        return {
            'success': True,
            'data': items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'timestamp': datetime.now().isoformat()
        }
    
    # Mobile-optimized data formatters
    def format_lead_for_mobile(self, lead: Dict) -> Dict:
        """Format lead data for mobile display."""
        return {
            'id': lead.get('id'),
            'name': f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            'email': lead.get('email'),
            'phone': lead.get('phone'),
            'status': lead.get('status'),
            'score': lead.get('score', 0),
            'type': lead.get('lead_type'),
            'source': lead.get('source'),
            'last_activity': lead.get('last_activity'),
            'created_at': lead.get('created_at'),
            'avatar_url': self._get_avatar_url(lead.get('email')),
            'quick_actions': ['call', 'text', 'email']
        }
    
    def format_property_for_mobile(self, property_data: Dict) -> Dict:
        """Format property data for mobile display."""
        return {
            'id': property_data.get('mls_id'),
            'address': property_data.get('address'),
            'city': property_data.get('city'),
            'price': property_data.get('list_price'),
            'price_formatted': f"${property_data.get('list_price', 0):,.0f}",
            'beds': property_data.get('bedrooms'),
            'baths': property_data.get('bathrooms_full', 0) + (property_data.get('bathrooms_half', 0) * 0.5),
            'sqft': property_data.get('sqft_living'),
            'sqft_formatted': f"{property_data.get('sqft_living', 0):,}",
            'status': property_data.get('status'),
            'days_on_market': property_data.get('days_on_market'),
            'primary_photo': property_data.get('photos', ['/static/images/no-photo.jpg'])[0],
            'photo_count': len(property_data.get('photos', [])),
            'latitude': property_data.get('latitude'),
            'longitude': property_data.get('longitude')
        }
    
    def format_task_for_mobile(self, task: Dict) -> Dict:
        """Format task data for mobile display."""
        return {
            'id': task.get('id'),
            'title': task.get('title'),
            'type': task.get('task_type'),
            'priority': task.get('priority'),
            'status': task.get('status'),
            'due_date': task.get('due_date'),
            'is_overdue': self._is_overdue(task.get('due_date')),
            'lead_id': task.get('lead_id'),
            'lead_name': task.get('lead_name'),
            'property_id': task.get('property_id'),
            'property_address': task.get('property_address')
        }
    
    def _get_avatar_url(self, email: str) -> str:
        """Generate Gravatar URL for email."""
        if not email:
            return '/static/images/default-avatar.png'
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{email_hash}?d=mp&s=100"
    
    def _is_overdue(self, due_date: str) -> bool:
        """Check if a date is overdue."""
        if not due_date:
            return False
        try:
            due = datetime.fromisoformat(due_date)
            return due < datetime.now()
        except ValueError:
            return False
    
    def get_dashboard_data(self, user_id: str) -> Dict:
        """Get dashboard summary data for mobile."""
        # This would integrate with other modules
        return {
            'summary': {
                'new_leads_today': 0,
                'tasks_due_today': 0,
                'showings_today': 0,
                'unread_messages': 0
            },
            'quick_stats': {
                'active_leads': 0,
                'pending_transactions': 0,
                'listings_active': 0
            },
            'recent_activity': [],
            'upcoming': []
        }
