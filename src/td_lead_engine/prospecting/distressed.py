"""Distressed property collector - foreclosures, tax liens, code violations."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
from enum import Enum
import json
import os


class DistressType(Enum):
    """Types of distressed properties."""
    PRE_FORECLOSURE = "pre_foreclosure"  # NOD filed
    FORECLOSURE = "foreclosure"           # Foreclosure auction scheduled
    REO = "reo"                           # Bank owned
    TAX_LIEN = "tax_lien"                 # Tax lien filed
    TAX_DEED = "tax_deed"                 # Tax deed sale
    CODE_VIOLATION = "code_violation"     # City code issues
    VACANT = "vacant"                     # Appears abandoned


@dataclass
class DistressedProperty:
    """A distressed property record."""
    id: str
    address: str
    city: str
    state: str = "OH"
    zip_code: str = ""
    distress_type: DistressType = DistressType.PRE_FORECLOSURE
    owner_name: str = ""
    owner_phone: str = ""
    mailing_address: str = ""
    estimated_value: float = 0
    amount_owed: float = 0
    equity_estimate: float = 0
    case_number: str = ""
    filing_date: datetime = None
    auction_date: datetime = None
    lender: str = ""
    attorney: str = ""
    status: str = "active"
    source: str = ""
    collected_at: datetime = field(default_factory=datetime.now)


class DistressedPropertyCollector:
    """Collect distressed property data from public records."""
    
    # Ohio foreclosure data sources
    OHIO_SOURCES = {
        'franklin_sheriff': 'https://sheriff.franklincountyohio.gov/sales',
        'ohio_foreclosures': 'https://ohioforeclosures.com',
        'auction_com': 'https://www.auction.com/residential/oh',
        'hubzu': 'https://www.hubzu.com/search/oh'
    }
    
    def __init__(self, storage_path: str = "data/prospecting/distressed"):
        self.storage_path = storage_path
        self.properties: Dict[str, DistressedProperty] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_properties()
    
    def _load_properties(self):
        """Load cached distressed properties."""
        props_file = f"{self.storage_path}/distressed_properties.json"
        if os.path.exists(props_file):
            with open(props_file, 'r') as f:
                data = json.load(f)
                for p in data:
                    prop = DistressedProperty(
                        id=p['id'],
                        address=p['address'],
                        city=p['city'],
                        state=p.get('state', 'OH'),
                        zip_code=p.get('zip_code', ''),
                        distress_type=DistressType(p.get('distress_type', 'pre_foreclosure')),
                        owner_name=p.get('owner_name', ''),
                        owner_phone=p.get('owner_phone', ''),
                        mailing_address=p.get('mailing_address', ''),
                        estimated_value=p.get('estimated_value', 0),
                        amount_owed=p.get('amount_owed', 0),
                        equity_estimate=p.get('equity_estimate', 0),
                        case_number=p.get('case_number', ''),
                        filing_date=datetime.fromisoformat(p['filing_date']) if p.get('filing_date') else None,
                        auction_date=datetime.fromisoformat(p['auction_date']) if p.get('auction_date') else None,
                        lender=p.get('lender', ''),
                        attorney=p.get('attorney', ''),
                        status=p.get('status', 'active'),
                        source=p.get('source', ''),
                        collected_at=datetime.fromisoformat(p['collected_at'])
                    )
                    self.properties[prop.id] = prop
    
    def _save_properties(self):
        """Save distressed properties."""
        props_data = [
            {
                'id': p.id,
                'address': p.address,
                'city': p.city,
                'state': p.state,
                'zip_code': p.zip_code,
                'distress_type': p.distress_type.value,
                'owner_name': p.owner_name,
                'owner_phone': p.owner_phone,
                'mailing_address': p.mailing_address,
                'estimated_value': p.estimated_value,
                'amount_owed': p.amount_owed,
                'equity_estimate': p.equity_estimate,
                'case_number': p.case_number,
                'filing_date': p.filing_date.isoformat() if p.filing_date else None,
                'auction_date': p.auction_date.isoformat() if p.auction_date else None,
                'lender': p.lender,
                'attorney': p.attorney,
                'status': p.status,
                'source': p.source,
                'collected_at': p.collected_at.isoformat()
            }
            for p in self.properties.values()
        ]
        
        with open(f"{self.storage_path}/distressed_properties.json", 'w') as f:
            json.dump(props_data, f, indent=2)
    
    def add_property(self, prop: DistressedProperty) -> bool:
        """Add a distressed property."""
        # Check for duplicate by case number or address
        for existing in self.properties.values():
            if prop.case_number and existing.case_number == prop.case_number:
                return False
            if prop.address.lower() == existing.address.lower():
                return False
        
        self.properties[prop.id] = prop
        self._save_properties()
        return True
    
    def get_pre_foreclosures(self) -> List[DistressedProperty]:
        """Get pre-foreclosure properties (best time to contact)."""
        props = [p for p in self.properties.values() if p.distress_type == DistressType.PRE_FORECLOSURE]
        props.sort(key=lambda p: p.filing_date or datetime.min, reverse=True)
        return props
    
    def get_upcoming_auctions(self, days: int = 30) -> List[DistressedProperty]:
        """Get properties with upcoming auctions."""
        from datetime import timedelta
        cutoff = datetime.now() + timedelta(days=days)
        
        props = [
            p for p in self.properties.values()
            if p.auction_date and datetime.now() <= p.auction_date <= cutoff
        ]
        props.sort(key=lambda p: p.auction_date)
        return props
    
    def get_high_equity_distressed(self, min_equity: float = 50000) -> List[DistressedProperty]:
        """Get distressed properties with significant equity."""
        props = [p for p in self.properties.values() if p.equity_estimate >= min_equity]
        props.sort(key=lambda p: p.equity_estimate, reverse=True)
        return props
    
    def get_by_distress_type(self, distress_type: DistressType) -> List[DistressedProperty]:
        """Get properties by distress type."""
        return [p for p in self.properties.values() if p.distress_type == distress_type]
    
    def convert_to_prospect_record(self, prop: DistressedProperty) -> Dict:
        """Convert to prospect record format."""
        return {
            'address': prop.address,
            'city': prop.city,
            'state': prop.state,
            'zip_code': prop.zip_code,
            'owner_name': prop.owner_name,
            'phone': prop.owner_phone,
            'mailing_address': prop.mailing_address,
            'property_value': prop.estimated_value,
            'amount_owed': prop.amount_owed,
            'equity': prop.equity_estimate,
            'distress_type': prop.distress_type.value,
            'case_number': prop.case_number,
            'filing_date': prop.filing_date.isoformat() if prop.filing_date else None,
            'auction_date': prop.auction_date.isoformat() if prop.auction_date else None,
            'lender': prop.lender
        }
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        by_type = {}
        for dtype in DistressType:
            by_type[dtype.value] = len(self.get_by_distress_type(dtype))
        
        return {
            'total_properties': len(self.properties),
            'by_type': by_type,
            'pre_foreclosures': len(self.get_pre_foreclosures()),
            'upcoming_auctions': len(self.get_upcoming_auctions()),
            'high_equity': len(self.get_high_equity_distressed()),
            'total_value': sum(p.estimated_value for p in self.properties.values()),
            'total_equity': sum(p.equity_estimate for p in self.properties.values())
        }
