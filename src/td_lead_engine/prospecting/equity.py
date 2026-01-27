"""High equity owner identification from auditor records."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import json
import os


@dataclass
class HighEquityOwner:
    """An owner with significant home equity."""
    id: str
    address: str
    city: str
    state: str = "OH"
    zip_code: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    mailing_address: str = ""
    current_value: float = 0
    purchase_price: float = 0
    purchase_date: datetime = None
    years_owned: float = 0
    equity_amount: float = 0
    equity_percent: float = 0
    appreciation: float = 0
    appreciation_percent: float = 0
    bedrooms: int = 0
    bathrooms: float = 0
    sqft: int = 0
    year_built: int = 0
    collected_at: datetime = field(default_factory=datetime.now)


class HighEquityCollector:
    """Identify homeowners with high equity from auditor data."""
    
    def __init__(self, storage_path: str = "data/prospecting/equity"):
        self.storage_path = storage_path
        self.owners: Dict[str, HighEquityOwner] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_owners()
    
    def _load_owners(self):
        """Load cached high equity owners."""
        owners_file = f"{self.storage_path}/high_equity_owners.json"
        if os.path.exists(owners_file):
            with open(owners_file, 'r') as f:
                data = json.load(f)
                for o in data:
                    owner = HighEquityOwner(
                        id=o['id'],
                        address=o['address'],
                        city=o['city'],
                        state=o.get('state', 'OH'),
                        zip_code=o.get('zip_code', ''),
                        owner_name=o.get('owner_name', ''),
                        owner_phone=o.get('owner_phone', ''),
                        mailing_address=o.get('mailing_address', ''),
                        current_value=o.get('current_value', 0),
                        purchase_price=o.get('purchase_price', 0),
                        purchase_date=datetime.fromisoformat(o['purchase_date']) if o.get('purchase_date') else None,
                        years_owned=o.get('years_owned', 0),
                        equity_amount=o.get('equity_amount', 0),
                        equity_percent=o.get('equity_percent', 0),
                        appreciation=o.get('appreciation', 0),
                        appreciation_percent=o.get('appreciation_percent', 0),
                        bedrooms=o.get('bedrooms', 0),
                        bathrooms=o.get('bathrooms', 0),
                        sqft=o.get('sqft', 0),
                        year_built=o.get('year_built', 0),
                        collected_at=datetime.fromisoformat(o['collected_at'])
                    )
                    self.owners[owner.id] = owner
    
    def _save_owners(self):
        """Save high equity owners."""
        owners_data = [
            {
                'id': o.id,
                'address': o.address,
                'city': o.city,
                'state': o.state,
                'zip_code': o.zip_code,
                'owner_name': o.owner_name,
                'owner_phone': o.owner_phone,
                'mailing_address': o.mailing_address,
                'current_value': o.current_value,
                'purchase_price': o.purchase_price,
                'purchase_date': o.purchase_date.isoformat() if o.purchase_date else None,
                'years_owned': o.years_owned,
                'equity_amount': o.equity_amount,
                'equity_percent': o.equity_percent,
                'appreciation': o.appreciation,
                'appreciation_percent': o.appreciation_percent,
                'bedrooms': o.bedrooms,
                'bathrooms': o.bathrooms,
                'sqft': o.sqft,
                'year_built': o.year_built,
                'collected_at': o.collected_at.isoformat()
            }
            for o in self.owners.values()
        ]
        
        with open(f"{self.storage_path}/high_equity_owners.json", 'w') as f:
            json.dump(owners_data, f, indent=2)
    
    def identify_from_auditor_data(
        self,
        records: List[Dict],
        min_equity_percent: float = 40,
        min_equity_amount: float = 50000
    ) -> int:
        """Identify high equity owners from auditor records."""
        import uuid
        added = 0
        
        for record in records:
            current_value = record.get('market_value', record.get('appraised_value', 0))
            purchase_price = record.get('last_sale_price', record.get('sale_price', 0))
            
            if not current_value or not purchase_price:
                continue
            
            # Calculate equity
            equity_amount = current_value - purchase_price
            equity_percent = (equity_amount / current_value * 100) if current_value else 0
            
            # Filter by thresholds
            if equity_percent < min_equity_percent or equity_amount < min_equity_amount:
                continue
            
            # Calculate years owned
            years_owned = 0
            purchase_date = record.get('last_sale_date', record.get('sale_date'))
            if purchase_date:
                try:
                    pd = datetime.fromisoformat(purchase_date) if isinstance(purchase_date, str) else purchase_date
                    years_owned = (datetime.now() - pd).days / 365
                except:
                    pass
            
            # Calculate appreciation
            appreciation = current_value - purchase_price
            appreciation_percent = (appreciation / purchase_price * 100) if purchase_price else 0
            
            owner = HighEquityOwner(
                id=str(uuid.uuid4())[:12],
                address=record.get('address', record.get('property_address', '')),
                city=record.get('city', ''),
                zip_code=record.get('zip', record.get('zip_code', '')),
                owner_name=record.get('owner_name', record.get('owner', '')),
                mailing_address=record.get('mailing_address', ''),
                current_value=current_value,
                purchase_price=purchase_price,
                purchase_date=datetime.fromisoformat(purchase_date) if purchase_date and isinstance(purchase_date, str) else purchase_date,
                years_owned=round(years_owned, 1),
                equity_amount=equity_amount,
                equity_percent=round(equity_percent, 1),
                appreciation=appreciation,
                appreciation_percent=round(appreciation_percent, 1),
                bedrooms=record.get('bedrooms', 0),
                bathrooms=record.get('bathrooms', 0),
                sqft=record.get('sqft', record.get('living_area', 0)),
                year_built=record.get('year_built', 0)
            )
            
            # Check for duplicate
            exists = False
            for existing in self.owners.values():
                if existing.address.lower() == owner.address.lower():
                    exists = True
                    break
            
            if not exists:
                self.owners[owner.id] = owner
                added += 1
        
        self._save_owners()
        return added
    
    def get_highest_equity(self, limit: int = 100) -> List[HighEquityOwner]:
        """Get owners with highest equity amounts."""
        owners = list(self.owners.values())
        owners.sort(key=lambda o: o.equity_amount, reverse=True)
        return owners[:limit]
    
    def get_long_term_owners(self, min_years: int = 10) -> List[HighEquityOwner]:
        """Get long-term owners with high equity."""
        owners = [o for o in self.owners.values() if o.years_owned >= min_years]
        owners.sort(key=lambda o: o.years_owned, reverse=True)
        return owners
    
    def get_by_equity_range(self, min_equity: float, max_equity: float) -> List[HighEquityOwner]:
        """Get owners in an equity range."""
        owners = [o for o in self.owners.values() if min_equity <= o.equity_amount <= max_equity]
        owners.sort(key=lambda o: o.equity_amount, reverse=True)
        return owners
    
    def get_by_value_range(self, min_value: float, max_value: float) -> List[HighEquityOwner]:
        """Get owners in a property value range."""
        owners = [o for o in self.owners.values() if min_value <= o.current_value <= max_value]
        owners.sort(key=lambda o: o.current_value, reverse=True)
        return owners
    
    def get_best_prospects(self, limit: int = 50) -> List[HighEquityOwner]:
        """Get best prospects based on equity and tenure."""
        # Score based on equity amount, percentage, and years owned
        scored = []
        for owner in self.owners.values():
            score = 0
            score += owner.equity_percent * 0.5  # Weight equity %
            score += min(owner.years_owned, 15) * 2  # Weight years (cap at 15)
            score += (owner.equity_amount / 10000)  # Weight absolute equity
            scored.append((owner, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [o for o, s in scored[:limit]]
    
    def convert_to_prospect_record(self, owner: HighEquityOwner) -> Dict:
        """Convert to prospect record format."""
        return {
            'address': owner.address,
            'city': owner.city,
            'state': owner.state,
            'zip_code': owner.zip_code,
            'owner_name': owner.owner_name,
            'phone': owner.owner_phone,
            'mailing_address': owner.mailing_address,
            'property_value': owner.current_value,
            'purchase_price': owner.purchase_price,
            'equity': owner.equity_amount,
            'equity_percent': owner.equity_percent,
            'years_owned': owner.years_owned,
            'appreciation': owner.appreciation
        }
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        if not self.owners:
            return {'total_owners': 0}
        
        equities = [o.equity_amount for o in self.owners.values()]
        years = [o.years_owned for o in self.owners.values()]
        
        return {
            'total_owners': len(self.owners),
            'total_equity': sum(equities),
            'avg_equity': sum(equities) / len(equities),
            'median_equity': sorted(equities)[len(equities) // 2],
            'max_equity': max(equities),
            'avg_years_owned': sum(years) / len(years),
            'long_term_owners': len(self.get_long_term_owners()),
            'total_value': sum(o.current_value for o in self.owners.values())
        }
