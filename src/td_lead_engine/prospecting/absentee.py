"""Absentee owner identification from public records."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import json
import os


@dataclass
class AbsenteeOwner:
    """An absentee owner (owner address differs from property)."""
    id: str
    property_address: str
    property_city: str
    property_state: str = "OH"
    property_zip: str = ""
    owner_name: str = ""
    mailing_address: str = ""
    mailing_city: str = ""
    mailing_state: str = ""
    mailing_zip: str = ""
    owner_phone: str = ""
    owner_email: str = ""
    property_value: float = 0
    last_sale_date: datetime = None
    last_sale_price: float = 0
    equity_estimate: float = 0
    property_type: str = "single_family"
    is_rental: bool = False
    out_of_state: bool = False
    years_owned: float = 0
    collected_at: datetime = field(default_factory=datetime.now)


class AbsenteeOwnerCollector:
    """Identify absentee owners from county auditor data."""
    
    def __init__(self, storage_path: str = "data/prospecting/absentee"):
        self.storage_path = storage_path
        self.owners: Dict[str, AbsenteeOwner] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_owners()
    
    def _load_owners(self):
        """Load cached absentee owners."""
        owners_file = f"{self.storage_path}/absentee_owners.json"
        if os.path.exists(owners_file):
            with open(owners_file, 'r') as f:
                data = json.load(f)
                for o in data:
                    owner = AbsenteeOwner(
                        id=o['id'],
                        property_address=o['property_address'],
                        property_city=o['property_city'],
                        property_state=o.get('property_state', 'OH'),
                        property_zip=o.get('property_zip', ''),
                        owner_name=o.get('owner_name', ''),
                        mailing_address=o.get('mailing_address', ''),
                        mailing_city=o.get('mailing_city', ''),
                        mailing_state=o.get('mailing_state', ''),
                        mailing_zip=o.get('mailing_zip', ''),
                        owner_phone=o.get('owner_phone', ''),
                        owner_email=o.get('owner_email', ''),
                        property_value=o.get('property_value', 0),
                        last_sale_date=datetime.fromisoformat(o['last_sale_date']) if o.get('last_sale_date') else None,
                        last_sale_price=o.get('last_sale_price', 0),
                        equity_estimate=o.get('equity_estimate', 0),
                        property_type=o.get('property_type', 'single_family'),
                        is_rental=o.get('is_rental', False),
                        out_of_state=o.get('out_of_state', False),
                        years_owned=o.get('years_owned', 0),
                        collected_at=datetime.fromisoformat(o['collected_at'])
                    )
                    self.owners[owner.id] = owner
    
    def _save_owners(self):
        """Save absentee owners."""
        owners_data = [
            {
                'id': o.id,
                'property_address': o.property_address,
                'property_city': o.property_city,
                'property_state': o.property_state,
                'property_zip': o.property_zip,
                'owner_name': o.owner_name,
                'mailing_address': o.mailing_address,
                'mailing_city': o.mailing_city,
                'mailing_state': o.mailing_state,
                'mailing_zip': o.mailing_zip,
                'owner_phone': o.owner_phone,
                'owner_email': o.owner_email,
                'property_value': o.property_value,
                'last_sale_date': o.last_sale_date.isoformat() if o.last_sale_date else None,
                'last_sale_price': o.last_sale_price,
                'equity_estimate': o.equity_estimate,
                'property_type': o.property_type,
                'is_rental': o.is_rental,
                'out_of_state': o.out_of_state,
                'years_owned': o.years_owned,
                'collected_at': o.collected_at.isoformat()
            }
            for o in self.owners.values()
        ]
        
        with open(f"{self.storage_path}/absentee_owners.json", 'w') as f:
            json.dump(owners_data, f, indent=2)
    
    def identify_from_auditor_data(self, records: List[Dict]) -> int:
        """Identify absentee owners from auditor records."""
        import uuid
        added = 0
        
        for record in records:
            property_addr = record.get('property_address', record.get('address', '')).lower()
            mailing_addr = record.get('mailing_address', '').lower()
            
            if not property_addr or not mailing_addr:
                continue
            
            # Check if addresses differ significantly
            if self._addresses_differ(property_addr, mailing_addr):
                # Determine if out of state
                mailing_state = record.get('mailing_state', 'OH')
                out_of_state = mailing_state != 'OH'
                
                # Calculate years owned
                years_owned = 0
                sale_date = record.get('last_sale_date')
                if sale_date:
                    try:
                        sale_dt = datetime.fromisoformat(sale_date) if isinstance(sale_date, str) else sale_date
                        years_owned = (datetime.now() - sale_dt).days / 365
                    except:
                        pass
                
                # Calculate equity
                value = record.get('market_value', 0)
                sale_price = record.get('last_sale_price', 0)
                equity = value - sale_price if value and sale_price else 0
                
                owner = AbsenteeOwner(
                    id=str(uuid.uuid4())[:12],
                    property_address=record.get('property_address', record.get('address', '')),
                    property_city=record.get('property_city', record.get('city', '')),
                    property_zip=record.get('property_zip', record.get('zip', '')),
                    owner_name=record.get('owner_name', ''),
                    mailing_address=record.get('mailing_address', ''),
                    mailing_city=record.get('mailing_city', ''),
                    mailing_state=mailing_state,
                    mailing_zip=record.get('mailing_zip', ''),
                    property_value=value,
                    last_sale_date=datetime.fromisoformat(sale_date) if sale_date and isinstance(sale_date, str) else sale_date,
                    last_sale_price=sale_price,
                    equity_estimate=equity,
                    out_of_state=out_of_state,
                    years_owned=round(years_owned, 1)
                )
                
                # Check for duplicate
                exists = False
                for existing in self.owners.values():
                    if existing.property_address.lower() == owner.property_address.lower():
                        exists = True
                        break
                
                if not exists:
                    self.owners[owner.id] = owner
                    added += 1
        
        self._save_owners()
        return added
    
    def _addresses_differ(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are different properties."""
        # Normalize
        addr1 = addr1.replace('.', '').replace(',', '').strip()
        addr2 = addr2.replace('.', '').replace(',', '').strip()
        
        # Extract street number and name
        parts1 = addr1.split()[:3]
        parts2 = addr2.split()[:3]
        
        return parts1 != parts2
    
    def get_out_of_state_owners(self) -> List[AbsenteeOwner]:
        """Get out-of-state absentee owners (most likely to sell)."""
        owners = [o for o in self.owners.values() if o.out_of_state]
        owners.sort(key=lambda o: o.property_value, reverse=True)
        return owners
    
    def get_long_distance_owners(self, min_years: float = 5) -> List[AbsenteeOwner]:
        """Get long-term absentee owners."""
        owners = [o for o in self.owners.values() if o.years_owned >= min_years]
        owners.sort(key=lambda o: o.years_owned, reverse=True)
        return owners
    
    def get_high_equity_absentee(self, min_equity: float = 100000) -> List[AbsenteeOwner]:
        """Get absentee owners with high equity."""
        owners = [o for o in self.owners.values() if o.equity_estimate >= min_equity]
        owners.sort(key=lambda o: o.equity_estimate, reverse=True)
        return owners
    
    def get_likely_rentals(self) -> List[AbsenteeOwner]:
        """Get properties likely being used as rentals."""
        # Absentee + local mailing = likely rental
        owners = [
            o for o in self.owners.values() 
            if not o.out_of_state and o.years_owned >= 2
        ]
        return owners
    
    def convert_to_prospect_record(self, owner: AbsenteeOwner) -> Dict:
        """Convert to prospect record format."""
        return {
            'address': owner.property_address,
            'city': owner.property_city,
            'state': owner.property_state,
            'zip_code': owner.property_zip,
            'owner_name': owner.owner_name,
            'phone': owner.owner_phone,
            'mailing_address': f"{owner.mailing_address}, {owner.mailing_city}, {owner.mailing_state} {owner.mailing_zip}",
            'property_value': owner.property_value,
            'equity': owner.equity_estimate,
            'years_owned': owner.years_owned,
            'out_of_state': owner.out_of_state,
            'is_rental': owner.is_rental
        }
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        out_of_state = len(self.get_out_of_state_owners())
        local = len(self.owners) - out_of_state
        
        return {
            'total_absentee': len(self.owners),
            'out_of_state': out_of_state,
            'local_absentee': local,
            'high_equity': len(self.get_high_equity_absentee()),
            'long_term': len(self.get_long_distance_owners()),
            'total_value': sum(o.property_value for o in self.owners.values()),
            'total_equity': sum(o.equity_estimate for o in self.owners.values())
        }
