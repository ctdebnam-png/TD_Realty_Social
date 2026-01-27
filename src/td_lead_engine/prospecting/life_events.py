"""Life event signal collector - probate, divorce, marriage, permits."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
from enum import Enum
import json
import os


class LifeEventType(Enum):
    """Types of life events that trigger moves."""
    PROBATE = "probate"
    DIVORCE = "divorce"
    MARRIAGE = "marriage"
    BIRTH = "birth"
    DEATH = "death"
    JOB_CHANGE = "job_change"
    RETIREMENT = "retirement"
    BANKRUPTCY = "bankruptcy"
    MAJOR_RENOVATION = "major_renovation"


@dataclass
class LifeEvent:
    """A life event record."""
    id: str
    event_type: LifeEventType
    person_name: str
    spouse_name: str = ""
    address: str = ""
    city: str = ""
    state: str = "OH"
    zip_code: str = ""
    case_number: str = ""
    filing_date: datetime = None
    property_address: str = ""
    estimated_value: float = 0
    source: str = ""
    details: Dict = field(default_factory=dict)
    collected_at: datetime = field(default_factory=datetime.now)


class LifeEventCollector:
    """Collect life event data from public records."""
    
    # Franklin County court URLs
    COURT_SOURCES = {
        'probate': 'https://probate.franklincountyohio.gov',
        'domestic': 'https://drj.fccourts.org',  # Divorce
        'common_pleas': 'https://fcdcfcjs.co.franklin.oh.us'
    }
    
    def __init__(self, storage_path: str = "data/prospecting/life_events"):
        self.storage_path = storage_path
        self.events: Dict[str, LifeEvent] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_events()
    
    def _load_events(self):
        """Load cached life events."""
        events_file = f"{self.storage_path}/life_events.json"
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                data = json.load(f)
                for e in data:
                    event = LifeEvent(
                        id=e['id'],
                        event_type=LifeEventType(e['event_type']),
                        person_name=e['person_name'],
                        spouse_name=e.get('spouse_name', ''),
                        address=e.get('address', ''),
                        city=e.get('city', ''),
                        state=e.get('state', 'OH'),
                        zip_code=e.get('zip_code', ''),
                        case_number=e.get('case_number', ''),
                        filing_date=datetime.fromisoformat(e['filing_date']) if e.get('filing_date') else None,
                        property_address=e.get('property_address', ''),
                        estimated_value=e.get('estimated_value', 0),
                        source=e.get('source', ''),
                        details=e.get('details', {}),
                        collected_at=datetime.fromisoformat(e['collected_at'])
                    )
                    self.events[event.id] = event
    
    def _save_events(self):
        """Save life events."""
        events_data = [
            {
                'id': e.id,
                'event_type': e.event_type.value,
                'person_name': e.person_name,
                'spouse_name': e.spouse_name,
                'address': e.address,
                'city': e.city,
                'state': e.state,
                'zip_code': e.zip_code,
                'case_number': e.case_number,
                'filing_date': e.filing_date.isoformat() if e.filing_date else None,
                'property_address': e.property_address,
                'estimated_value': e.estimated_value,
                'source': e.source,
                'details': e.details,
                'collected_at': e.collected_at.isoformat()
            }
            for e in self.events.values()
        ]
        
        with open(f"{self.storage_path}/life_events.json", 'w') as f:
            json.dump(events_data, f, indent=2)
    
    def add_event(self, event: LifeEvent) -> bool:
        """Add a life event."""
        # Check for duplicate by case number
        if event.case_number:
            for existing in self.events.values():
                if existing.case_number == event.case_number:
                    return False
        
        self.events[event.id] = event
        self._save_events()
        return True
    
    def import_probate_cases(self, records: List[Dict]) -> int:
        """Import probate court records."""
        import uuid
        added = 0
        
        for record in records:
            event = LifeEvent(
                id=str(uuid.uuid4())[:12],
                event_type=LifeEventType.PROBATE,
                person_name=record.get('decedent', record.get('name', '')),
                case_number=record.get('case_number', ''),
                filing_date=datetime.fromisoformat(record['filing_date']) if record.get('filing_date') else None,
                property_address=record.get('property_address', ''),
                address=record.get('address', ''),
                city=record.get('city', ''),
                estimated_value=record.get('estate_value', 0),
                source='probate_court',
                details={
                    'executor': record.get('executor', ''),
                    'attorney': record.get('attorney', ''),
                    'case_type': record.get('case_type', '')
                }
            )
            
            if self.add_event(event):
                added += 1
        
        return added
    
    def import_divorce_cases(self, records: List[Dict]) -> int:
        """Import divorce court records."""
        import uuid
        added = 0
        
        for record in records:
            parties = record.get('parties', [])
            person1 = parties[0] if len(parties) > 0 else ''
            person2 = parties[1] if len(parties) > 1 else ''
            
            event = LifeEvent(
                id=str(uuid.uuid4())[:12],
                event_type=LifeEventType.DIVORCE,
                person_name=person1,
                spouse_name=person2,
                case_number=record.get('case_number', ''),
                filing_date=datetime.fromisoformat(record['filing_date']) if record.get('filing_date') else None,
                property_address=record.get('property_address', record.get('marital_residence', '')),
                address=record.get('address', ''),
                city=record.get('city', ''),
                source='domestic_court',
                details={
                    'case_type': record.get('case_type', 'divorce'),
                    'status': record.get('status', '')
                }
            )
            
            if self.add_event(event):
                added += 1
        
        return added
    
    def import_building_permits(self, records: List[Dict]) -> int:
        """Import building permit records (major renovations)."""
        import uuid
        added = 0
        
        for record in records:
            permit_type = record.get('permit_type', '').lower()
            value = record.get('value', 0)
            
            # Only major renovations ($20k+)
            if value < 20000:
                continue
            
            event = LifeEvent(
                id=str(uuid.uuid4())[:12],
                event_type=LifeEventType.MAJOR_RENOVATION,
                person_name=record.get('owner', record.get('applicant', '')),
                property_address=record.get('address', ''),
                address=record.get('address', ''),
                city=record.get('city', ''),
                filing_date=datetime.fromisoformat(record['issue_date']) if record.get('issue_date') else None,
                estimated_value=value,
                source='building_permits',
                details={
                    'permit_type': permit_type,
                    'permit_number': record.get('permit_number', ''),
                    'description': record.get('description', '')
                }
            )
            
            if self.add_event(event):
                added += 1
        
        return added
    
    def get_events_by_type(self, event_type: LifeEventType) -> List[LifeEvent]:
        """Get events by type."""
        events = [e for e in self.events.values() if e.event_type == event_type]
        events.sort(key=lambda e: e.filing_date or datetime.min, reverse=True)
        return events
    
    def get_recent_events(self, days: int = 30) -> List[LifeEvent]:
        """Get recent life events."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        events = [e for e in self.events.values() if e.filing_date and e.filing_date >= cutoff]
        events.sort(key=lambda e: e.filing_date, reverse=True)
        return events
    
    def get_probate_leads(self) -> List[LifeEvent]:
        """Get probate cases (estate sales)."""
        return self.get_events_by_type(LifeEventType.PROBATE)
    
    def get_divorce_leads(self) -> List[LifeEvent]:
        """Get divorce cases (forced sales)."""
        return self.get_events_by_type(LifeEventType.DIVORCE)
    
    def convert_to_prospect_record(self, event: LifeEvent) -> Dict:
        """Convert to prospect record format."""
        return {
            'address': event.property_address or event.address,
            'city': event.city,
            'state': event.state,
            'owner_name': event.person_name,
            'spouse_name': event.spouse_name,
            'event_type': event.event_type.value,
            'case_number': event.case_number,
            'filing_date': event.filing_date.isoformat() if event.filing_date else None,
            'property_value': event.estimated_value,
            'details': event.details
        }
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        by_type = {}
        for etype in LifeEventType:
            by_type[etype.value] = len(self.get_events_by_type(etype))
        
        return {
            'total_events': len(self.events),
            'by_type': by_type,
            'recent_30_days': len(self.get_recent_events(30)),
            'probate_cases': len(self.get_probate_leads()),
            'divorce_cases': len(self.get_divorce_leads())
        }
