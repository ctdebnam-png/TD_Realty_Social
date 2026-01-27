"""Website visitor tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid
import hashlib


class VisitorStatus(Enum):
    """Visitor status."""
    ANONYMOUS = "anonymous"
    IDENTIFIED = "identified"
    LEAD = "lead"
    CUSTOMER = "customer"


@dataclass
class PageView:
    """A single page view."""
    url: str
    title: str
    timestamp: datetime
    duration_seconds: int = 0
    scroll_depth: int = 0
    referrer: str = ""


@dataclass
class VisitorSession:
    """A visitor session."""
    id: str
    visitor_id: str
    started_at: datetime
    ended_at: datetime = None
    page_views: List[PageView] = field(default_factory=list)
    events: List[Dict] = field(default_factory=list)
    
    # Session context
    landing_page: str = ""
    exit_page: str = ""
    referrer: str = ""
    utm_source: str = ""
    utm_medium: str = ""
    utm_campaign: str = ""
    utm_content: str = ""
    utm_term: str = ""
    
    # Device info
    device_type: str = ""
    browser: str = ""
    os: str = ""
    screen_resolution: str = ""
    
    # Location
    ip_address: str = ""
    city: str = ""
    region: str = ""
    country: str = ""
    
    @property
    def total_page_views(self) -> int:
        return len(self.page_views)
    
    @property
    def session_duration(self) -> int:
        """Session duration in seconds."""
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return int((datetime.now() - self.started_at).total_seconds())
    
    @property
    def is_bounce(self) -> bool:
        return len(self.page_views) <= 1


@dataclass
class Visitor:
    """A website visitor."""
    id: str
    status: VisitorStatus = VisitorStatus.ANONYMOUS
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    # Identity
    email: str = ""
    lead_id: str = ""
    
    # Engagement
    total_sessions: int = 0
    total_page_views: int = 0
    total_time_on_site: int = 0  # seconds
    
    # Interest signals
    properties_viewed: List[str] = field(default_factory=list)
    searches_performed: List[Dict] = field(default_factory=list)
    favorites: List[str] = field(default_factory=list)
    calculators_used: List[str] = field(default_factory=list)
    
    # Attribution
    first_touch_source: str = ""
    first_touch_medium: str = ""
    first_touch_campaign: str = ""
    last_touch_source: str = ""
    last_touch_medium: str = ""
    last_touch_campaign: str = ""
    
    # Scoring
    engagement_score: int = 0
    intent_signals: List[str] = field(default_factory=list)
    
    # Device fingerprint
    fingerprint: str = ""
    
    sessions: List[str] = field(default_factory=list)  # Session IDs


class VisitorTracker:
    """Track website visitors."""
    
    def __init__(self, storage_path: str = "data/tracking"):
        self.storage_path = storage_path
        self.visitors: Dict[str, Visitor] = {}
        self.sessions: Dict[str, VisitorSession] = {}
        self.active_sessions: Dict[str, str] = {}  # fingerprint -> session_id
        
        self._load_data()
    
    def _load_data(self):
        """Load tracking data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load visitors
        visitors_file = f"{self.storage_path}/visitors.json"
        if os.path.exists(visitors_file):
            with open(visitors_file, 'r') as f:
                data = json.load(f)
                for visitor_data in data:
                    visitor = Visitor(
                        id=visitor_data['id'],
                        status=VisitorStatus(visitor_data.get('status', 'anonymous')),
                        first_seen=datetime.fromisoformat(visitor_data['first_seen']) if visitor_data.get('first_seen') else datetime.now(),
                        last_seen=datetime.fromisoformat(visitor_data['last_seen']) if visitor_data.get('last_seen') else datetime.now(),
                        email=visitor_data.get('email', ''),
                        lead_id=visitor_data.get('lead_id', ''),
                        total_sessions=visitor_data.get('total_sessions', 0),
                        total_page_views=visitor_data.get('total_page_views', 0),
                        total_time_on_site=visitor_data.get('total_time_on_site', 0),
                        properties_viewed=visitor_data.get('properties_viewed', []),
                        searches_performed=visitor_data.get('searches_performed', []),
                        favorites=visitor_data.get('favorites', []),
                        calculators_used=visitor_data.get('calculators_used', []),
                        first_touch_source=visitor_data.get('first_touch_source', ''),
                        first_touch_medium=visitor_data.get('first_touch_medium', ''),
                        first_touch_campaign=visitor_data.get('first_touch_campaign', ''),
                        last_touch_source=visitor_data.get('last_touch_source', ''),
                        last_touch_medium=visitor_data.get('last_touch_medium', ''),
                        last_touch_campaign=visitor_data.get('last_touch_campaign', ''),
                        engagement_score=visitor_data.get('engagement_score', 0),
                        intent_signals=visitor_data.get('intent_signals', []),
                        fingerprint=visitor_data.get('fingerprint', ''),
                        sessions=visitor_data.get('sessions', [])
                    )
                    self.visitors[visitor.id] = visitor
        
        # Load recent sessions
        sessions_file = f"{self.storage_path}/sessions.json"
        if os.path.exists(sessions_file):
            with open(sessions_file, 'r') as f:
                data = json.load(f)
                for session_data in data[-1000:]:  # Keep last 1000 sessions
                    page_views = [
                        PageView(
                            url=pv['url'],
                            title=pv.get('title', ''),
                            timestamp=datetime.fromisoformat(pv['timestamp']),
                            duration_seconds=pv.get('duration_seconds', 0),
                            scroll_depth=pv.get('scroll_depth', 0),
                            referrer=pv.get('referrer', '')
                        )
                        for pv in session_data.get('page_views', [])
                    ]
                    
                    session = VisitorSession(
                        id=session_data['id'],
                        visitor_id=session_data['visitor_id'],
                        started_at=datetime.fromisoformat(session_data['started_at']),
                        ended_at=datetime.fromisoformat(session_data['ended_at']) if session_data.get('ended_at') else None,
                        page_views=page_views,
                        events=session_data.get('events', []),
                        landing_page=session_data.get('landing_page', ''),
                        exit_page=session_data.get('exit_page', ''),
                        referrer=session_data.get('referrer', ''),
                        utm_source=session_data.get('utm_source', ''),
                        utm_medium=session_data.get('utm_medium', ''),
                        utm_campaign=session_data.get('utm_campaign', ''),
                        utm_content=session_data.get('utm_content', ''),
                        utm_term=session_data.get('utm_term', ''),
                        device_type=session_data.get('device_type', ''),
                        browser=session_data.get('browser', ''),
                        os=session_data.get('os', ''),
                        screen_resolution=session_data.get('screen_resolution', ''),
                        ip_address=session_data.get('ip_address', ''),
                        city=session_data.get('city', ''),
                        region=session_data.get('region', ''),
                        country=session_data.get('country', '')
                    )
                    self.sessions[session.id] = session
    
    def _save_data(self):
        """Save tracking data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save visitors
        visitors_data = [
            {
                'id': v.id,
                'status': v.status.value,
                'first_seen': v.first_seen.isoformat(),
                'last_seen': v.last_seen.isoformat(),
                'email': v.email,
                'lead_id': v.lead_id,
                'total_sessions': v.total_sessions,
                'total_page_views': v.total_page_views,
                'total_time_on_site': v.total_time_on_site,
                'properties_viewed': v.properties_viewed[-50:],
                'searches_performed': v.searches_performed[-20:],
                'favorites': v.favorites,
                'calculators_used': v.calculators_used,
                'first_touch_source': v.first_touch_source,
                'first_touch_medium': v.first_touch_medium,
                'first_touch_campaign': v.first_touch_campaign,
                'last_touch_source': v.last_touch_source,
                'last_touch_medium': v.last_touch_medium,
                'last_touch_campaign': v.last_touch_campaign,
                'engagement_score': v.engagement_score,
                'intent_signals': v.intent_signals[-20:],
                'fingerprint': v.fingerprint,
                'sessions': v.sessions[-50:]
            }
            for v in self.visitors.values()
        ]
        
        with open(f"{self.storage_path}/visitors.json", 'w') as f:
            json.dump(visitors_data, f, indent=2)
        
        # Save sessions (last 1000)
        sessions_data = [
            {
                'id': s.id,
                'visitor_id': s.visitor_id,
                'started_at': s.started_at.isoformat(),
                'ended_at': s.ended_at.isoformat() if s.ended_at else None,
                'page_views': [
                    {
                        'url': pv.url,
                        'title': pv.title,
                        'timestamp': pv.timestamp.isoformat(),
                        'duration_seconds': pv.duration_seconds,
                        'scroll_depth': pv.scroll_depth,
                        'referrer': pv.referrer
                    }
                    for pv in s.page_views
                ],
                'events': s.events,
                'landing_page': s.landing_page,
                'exit_page': s.exit_page,
                'referrer': s.referrer,
                'utm_source': s.utm_source,
                'utm_medium': s.utm_medium,
                'utm_campaign': s.utm_campaign,
                'utm_content': s.utm_content,
                'utm_term': s.utm_term,
                'device_type': s.device_type,
                'browser': s.browser,
                'os': s.os,
                'screen_resolution': s.screen_resolution,
                'ip_address': s.ip_address,
                'city': s.city,
                'region': s.region,
                'country': s.country
            }
            for s in list(self.sessions.values())[-1000:]
        ]
        
        with open(f"{self.storage_path}/sessions.json", 'w') as f:
            json.dump(sessions_data, f, indent=2)
    
    def get_or_create_visitor(
        self,
        fingerprint: str,
        ip_address: str = "",
        user_agent: str = ""
    ) -> Visitor:
        """Get or create a visitor by fingerprint."""
        # Look for existing visitor
        for visitor in self.visitors.values():
            if visitor.fingerprint == fingerprint:
                return visitor
        
        # Create new visitor
        visitor = Visitor(
            id=str(uuid.uuid4())[:12],
            fingerprint=fingerprint
        )
        self.visitors[visitor.id] = visitor
        self._save_data()
        return visitor
    
    def start_session(
        self,
        visitor_id: str,
        landing_page: str,
        referrer: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        device_type: str = "",
        browser: str = "",
        os: str = "",
        screen_resolution: str = "",
        ip_address: str = ""
    ) -> VisitorSession:
        """Start a new session."""
        session = VisitorSession(
            id=str(uuid.uuid4())[:12],
            visitor_id=visitor_id,
            started_at=datetime.now(),
            landing_page=landing_page,
            referrer=referrer,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
            device_type=device_type,
            browser=browser,
            os=os,
            screen_resolution=screen_resolution,
            ip_address=ip_address
        )
        
        self.sessions[session.id] = session
        
        # Update visitor
        if visitor_id in self.visitors:
            visitor = self.visitors[visitor_id]
            visitor.total_sessions += 1
            visitor.last_seen = datetime.now()
            visitor.sessions.append(session.id)
            
            # Update attribution
            if not visitor.first_touch_source:
                visitor.first_touch_source = utm_source or self._parse_source(referrer)
                visitor.first_touch_medium = utm_medium or self._parse_medium(referrer)
                visitor.first_touch_campaign = utm_campaign
            
            visitor.last_touch_source = utm_source or self._parse_source(referrer)
            visitor.last_touch_medium = utm_medium or self._parse_medium(referrer)
            visitor.last_touch_campaign = utm_campaign
        
        self._save_data()
        return session
    
    def track_page_view(
        self,
        session_id: str,
        url: str,
        title: str = "",
        referrer: str = "",
        duration_seconds: int = 0,
        scroll_depth: int = 0
    ):
        """Track a page view."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        page_view = PageView(
            url=url,
            title=title,
            timestamp=datetime.now(),
            duration_seconds=duration_seconds,
            scroll_depth=scroll_depth,
            referrer=referrer
        )
        session.page_views.append(page_view)
        session.exit_page = url
        
        # Update visitor
        if session.visitor_id in self.visitors:
            visitor = self.visitors[session.visitor_id]
            visitor.total_page_views += 1
            visitor.last_seen = datetime.now()
            
            # Check for property views
            if '/property/' in url or '/listing/' in url:
                property_id = self._extract_property_id(url)
                if property_id and property_id not in visitor.properties_viewed:
                    visitor.properties_viewed.append(property_id)
                    self._add_intent_signal(visitor, 'property_viewed')
            
            # Check for calculator use
            if '/calculator/' in url or 'mortgage' in url.lower():
                calc_type = self._extract_calculator_type(url)
                if calc_type and calc_type not in visitor.calculators_used:
                    visitor.calculators_used.append(calc_type)
                    self._add_intent_signal(visitor, 'calculator_used')
            
            # Update engagement score
            self._update_engagement_score(visitor)
        
        self._save_data()
    
    def track_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict = None
    ):
        """Track a custom event."""
        if session_id not in self.sessions:
            return
        
        session = self.sessions[session_id]
        event = {
            'type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': event_data or {}
        }
        session.events.append(event)
        
        # Update visitor based on event type
        if session.visitor_id in self.visitors:
            visitor = self.visitors[session.visitor_id]
            
            if event_type == 'search':
                visitor.searches_performed.append(event_data or {})
                self._add_intent_signal(visitor, 'search_performed')
            
            elif event_type == 'favorite':
                property_id = (event_data or {}).get('property_id')
                if property_id and property_id not in visitor.favorites:
                    visitor.favorites.append(property_id)
                    self._add_intent_signal(visitor, 'property_favorited')
            
            elif event_type == 'form_started':
                self._add_intent_signal(visitor, 'form_started')
            
            elif event_type == 'schedule_showing':
                self._add_intent_signal(visitor, 'showing_scheduled')
            
            self._update_engagement_score(visitor)
        
        self._save_data()
    
    def end_session(self, session_id: str):
        """End a session."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session.ended_at = datetime.now()
            
            # Update visitor time on site
            if session.visitor_id in self.visitors:
                visitor = self.visitors[session.visitor_id]
                visitor.total_time_on_site += session.session_duration
            
            self._save_data()
    
    def identify_visitor(
        self,
        visitor_id: str,
        email: str,
        lead_id: str = ""
    ):
        """Identify a visitor with their email."""
        if visitor_id not in self.visitors:
            return
        
        visitor = self.visitors[visitor_id]
        visitor.email = email
        visitor.lead_id = lead_id
        visitor.status = VisitorStatus.IDENTIFIED if not lead_id else VisitorStatus.LEAD
        
        self._save_data()
    
    def _parse_source(self, referrer: str) -> str:
        """Parse traffic source from referrer."""
        if not referrer:
            return 'direct'
        
        referrer = referrer.lower()
        if 'google' in referrer:
            return 'google'
        elif 'facebook' in referrer or 'fb.com' in referrer:
            return 'facebook'
        elif 'instagram' in referrer:
            return 'instagram'
        elif 'zillow' in referrer:
            return 'zillow'
        elif 'realtor.com' in referrer:
            return 'realtor.com'
        elif 'bing' in referrer:
            return 'bing'
        
        return 'referral'
    
    def _parse_medium(self, referrer: str) -> str:
        """Parse traffic medium from referrer."""
        if not referrer:
            return 'direct'
        
        source = self._parse_source(referrer)
        if source in ['google', 'bing']:
            return 'organic'
        elif source in ['facebook', 'instagram']:
            return 'social'
        
        return 'referral'
    
    def _extract_property_id(self, url: str) -> Optional[str]:
        """Extract property ID from URL."""
        import re
        patterns = [
            r'/property/([a-zA-Z0-9]+)',
            r'/listing/([a-zA-Z0-9]+)',
            r'/mls/([a-zA-Z0-9]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_calculator_type(self, url: str) -> Optional[str]:
        """Extract calculator type from URL."""
        url = url.lower()
        if 'mortgage' in url:
            return 'mortgage'
        elif 'affordability' in url:
            return 'affordability'
        elif 'closing' in url:
            return 'closing_costs'
        elif 'investment' in url:
            return 'investment'
        return 'other'
    
    def _add_intent_signal(self, visitor: Visitor, signal: str):
        """Add an intent signal to visitor."""
        if signal not in visitor.intent_signals:
            visitor.intent_signals.append(signal)
    
    def _update_engagement_score(self, visitor: Visitor):
        """Update visitor engagement score."""
        score = 0
        
        # Page views (1 point each, max 20)
        score += min(visitor.total_page_views, 20)
        
        # Sessions (5 points each, max 25)
        score += min(visitor.total_sessions * 5, 25)
        
        # Properties viewed (3 points each, max 15)
        score += min(len(visitor.properties_viewed) * 3, 15)
        
        # Searches (2 points each, max 10)
        score += min(len(visitor.searches_performed) * 2, 10)
        
        # Favorites (5 points each, max 15)
        score += min(len(visitor.favorites) * 5, 15)
        
        # Calculators used (5 points each, max 15)
        score += min(len(visitor.calculators_used) * 5, 15)
        
        visitor.engagement_score = score
    
    def get_visitor(self, visitor_id: str) -> Optional[Visitor]:
        """Get visitor by ID."""
        return self.visitors.get(visitor_id)
    
    def get_visitor_sessions(self, visitor_id: str) -> List[VisitorSession]:
        """Get all sessions for a visitor."""
        return [s for s in self.sessions.values() if s.visitor_id == visitor_id]
    
    def get_hot_visitors(self, min_score: int = 50, limit: int = 20) -> List[Visitor]:
        """Get highly engaged visitors."""
        hot = [v for v in self.visitors.values() if v.engagement_score >= min_score]
        hot.sort(key=lambda v: v.engagement_score, reverse=True)
        return hot[:limit]
    
    def get_visitor_stats(self, days: int = 30) -> Dict:
        """Get visitor statistics."""
        cutoff = datetime.now() - timedelta(days=days)
        
        recent_visitors = [v for v in self.visitors.values() if v.last_seen > cutoff]
        recent_sessions = [s for s in self.sessions.values() if s.started_at > cutoff]
        
        total_page_views = sum(len(s.page_views) for s in recent_sessions)
        bounces = sum(1 for s in recent_sessions if s.is_bounce)
        
        return {
            'unique_visitors': len(recent_visitors),
            'total_sessions': len(recent_sessions),
            'total_page_views': total_page_views,
            'pages_per_session': total_page_views / len(recent_sessions) if recent_sessions else 0,
            'bounce_rate': (bounces / len(recent_sessions) * 100) if recent_sessions else 0,
            'avg_session_duration': sum(s.session_duration for s in recent_sessions) / len(recent_sessions) if recent_sessions else 0,
            'new_visitors': len([v for v in recent_visitors if v.first_seen > cutoff]),
            'returning_visitors': len([v for v in recent_visitors if v.first_seen <= cutoff]),
            'identified_visitors': len([v for v in recent_visitors if v.status != VisitorStatus.ANONYMOUS]),
            'high_intent_visitors': len([v for v in recent_visitors if v.engagement_score >= 50])
        }
