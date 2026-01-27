"""Franklin County and Central Ohio public records collector."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import os


@dataclass
class PropertyRecord:
    """A property record from county records."""
    parcel_id: str
    address: str
    city: str
    zip_code: str
    owner_name: str
    sale_date: datetime = None
    sale_price: float = 0
    assessed_value: float = 0
    market_value: float = 0
    year_built: int = 0
    bedrooms: int = 0
    bathrooms: float = 0
    sqft: int = 0
    lot_size: float = 0
    property_type: str = "single_family"


@dataclass
class TransferRecord:
    """A property transfer record."""
    parcel_id: str
    address: str
    grantor: str  # Seller
    grantee: str  # Buyer
    sale_date: datetime
    sale_price: float
    transfer_type: str = "warranty_deed"


class FranklinCountyRecords:
    """Access Franklin County public records."""
    
    # Franklin County Auditor API (public data)
    AUDITOR_URL = "https://apps.franklincountyauditor.com"
    
    # Other Central Ohio county auditor sites
    COUNTY_URLS = {
        'franklin': 'https://apps.franklincountyauditor.com',
        'delaware': 'https://www.co.delaware.oh.us/auditor/',
        'licking': 'https://www.lcounty.com/auditor/',
        'fairfield': 'https://www.fairfieldcountyauditor.org/',
        'pickaway': 'https://www.pickawayauditor.com/',
        'union': 'https://auditor.co.union.oh.us/',
        'madison': 'https://www.co.madison.oh.us/auditor/'
    }
    
    def __init__(self, storage_path: str = "data/county_records"):
        self.storage_path = storage_path
        self.records: Dict[str, PropertyRecord] = {}
        self.transfers: List[TransferRecord] = []
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_data()
    
    def _load_data(self):
        """Load cached records."""
        records_file = f"{self.storage_path}/property_records.json"
        if os.path.exists(records_file):
            with open(records_file, 'r') as f:
                data = json.load(f)
                for r in data:
                    record = PropertyRecord(
                        parcel_id=r['parcel_id'],
                        address=r['address'],
                        city=r['city'],
                        zip_code=r['zip_code'],
                        owner_name=r['owner_name'],
                        sale_date=datetime.fromisoformat(r['sale_date']) if r.get('sale_date') else None,
                        sale_price=r.get('sale_price', 0),
                        assessed_value=r.get('assessed_value', 0),
                        market_value=r.get('market_value', 0),
                        year_built=r.get('year_built', 0),
                        bedrooms=r.get('bedrooms', 0),
                        bathrooms=r.get('bathrooms', 0),
                        sqft=r.get('sqft', 0),
                        lot_size=r.get('lot_size', 0),
                        property_type=r.get('property_type', 'single_family')
                    )
                    self.records[record.parcel_id] = record
        
        transfers_file = f"{self.storage_path}/transfers.json"
        if os.path.exists(transfers_file):
            with open(transfers_file, 'r') as f:
                data = json.load(f)
                for t in data:
                    transfer = TransferRecord(
                        parcel_id=t['parcel_id'],
                        address=t['address'],
                        grantor=t['grantor'],
                        grantee=t['grantee'],
                        sale_date=datetime.fromisoformat(t['sale_date']),
                        sale_price=t['sale_price'],
                        transfer_type=t.get('transfer_type', 'warranty_deed')
                    )
                    self.transfers.append(transfer)
    
    def _save_data(self):
        """Save records to cache."""
        records_data = [
            {
                'parcel_id': r.parcel_id,
                'address': r.address,
                'city': r.city,
                'zip_code': r.zip_code,
                'owner_name': r.owner_name,
                'sale_date': r.sale_date.isoformat() if r.sale_date else None,
                'sale_price': r.sale_price,
                'assessed_value': r.assessed_value,
                'market_value': r.market_value,
                'year_built': r.year_built,
                'bedrooms': r.bedrooms,
                'bathrooms': r.bathrooms,
                'sqft': r.sqft,
                'lot_size': r.lot_size,
                'property_type': r.property_type
            }
            for r in self.records.values()
        ]
        
        with open(f"{self.storage_path}/property_records.json", 'w') as f:
            json.dump(records_data, f, indent=2)
        
        transfers_data = [
            {
                'parcel_id': t.parcel_id,
                'address': t.address,
                'grantor': t.grantor,
                'grantee': t.grantee,
                'sale_date': t.sale_date.isoformat(),
                'sale_price': t.sale_price,
                'transfer_type': t.transfer_type
            }
            for t in self.transfers[-10000:]  # Keep last 10k
        ]
        
        with open(f"{self.storage_path}/transfers.json", 'w') as f:
            json.dump(transfers_data, f, indent=2)
    
    def lookup_property(self, address: str = None, parcel_id: str = None) -> Optional[PropertyRecord]:
        """Look up a property by address or parcel ID."""
        if parcel_id and parcel_id in self.records:
            return self.records[parcel_id]
        
        if address:
            address_lower = address.lower()
            for record in self.records.values():
                if address_lower in record.address.lower():
                    return record
        
        return None
    
    def get_recent_sales(
        self,
        city: str = None,
        zip_code: str = None,
        days: int = 90,
        min_price: float = 0,
        max_price: float = float('inf')
    ) -> List[TransferRecord]:
        """Get recent property sales."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days)
        
        results = []
        for transfer in self.transfers:
            if transfer.sale_date < cutoff:
                continue
            if min_price > transfer.sale_price or transfer.sale_price > max_price:
                continue
            
            # Get property record for filtering
            record = self.records.get(transfer.parcel_id)
            if record:
                if city and record.city.lower() != city.lower():
                    continue
                if zip_code and record.zip_code != zip_code:
                    continue
            
            results.append(transfer)
        
        results.sort(key=lambda t: t.sale_date, reverse=True)
        return results
    
    def get_comparable_sales(
        self,
        address: str,
        radius_miles: float = 1.0,
        months: int = 6,
        price_range_pct: float = 0.2
    ) -> List[Dict]:
        """Find comparable sales for a property."""
        # Look up the subject property
        subject = self.lookup_property(address=address)
        if not subject:
            return []
        
        # Get recent sales in the area
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        min_price = subject.market_value * (1 - price_range_pct)
        max_price = subject.market_value * (1 + price_range_pct)
        
        comps = []
        for transfer in self.transfers:
            if transfer.sale_date < cutoff:
                continue
            if transfer.parcel_id == subject.parcel_id:
                continue
            
            record = self.records.get(transfer.parcel_id)
            if not record:
                continue
            
            # Same ZIP code (approximates radius)
            if record.zip_code != subject.zip_code:
                continue
            
            # Price range
            if not (min_price <= transfer.sale_price <= max_price):
                continue
            
            # Similar property type
            if record.property_type != subject.property_type:
                continue
            
            comps.append({
                'address': record.address,
                'city': record.city,
                'sale_date': transfer.sale_date.isoformat(),
                'sale_price': transfer.sale_price,
                'sqft': record.sqft,
                'price_per_sqft': round(transfer.sale_price / record.sqft, 2) if record.sqft else 0,
                'bedrooms': record.bedrooms,
                'bathrooms': record.bathrooms,
                'year_built': record.year_built
            })
        
        # Sort by date (most recent first)
        comps.sort(key=lambda c: c['sale_date'], reverse=True)
        return comps[:10]  # Return top 10 comps
    
    def analyze_neighborhood(self, zip_code: str) -> Dict:
        """Analyze a neighborhood by ZIP code."""
        properties = [r for r in self.records.values() if r.zip_code == zip_code]
        
        if not properties:
            return {'error': 'No properties found'}
        
        import statistics
        
        values = [p.market_value for p in properties if p.market_value > 0]
        years = [p.year_built for p in properties if p.year_built > 0]
        sqfts = [p.sqft for p in properties if p.sqft > 0]
        
        # Recent sales
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=180)
        recent_sales = [
            t for t in self.transfers 
            if self.records.get(t.parcel_id, PropertyRecord('', '', '', '', '')).zip_code == zip_code
            and t.sale_date >= cutoff
        ]
        
        sale_prices = [t.sale_price for t in recent_sales if t.sale_price > 0]
        
        return {
            'zip_code': zip_code,
            'total_properties': len(properties),
            'property_values': {
                'median': statistics.median(values) if values else 0,
                'average': round(statistics.mean(values), 0) if values else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0
            },
            'building_age': {
                'median_year': int(statistics.median(years)) if years else 0,
                'oldest': min(years) if years else 0,
                'newest': max(years) if years else 0
            },
            'size': {
                'median_sqft': int(statistics.median(sqfts)) if sqfts else 0,
                'avg_sqft': int(statistics.mean(sqfts)) if sqfts else 0
            },
            'recent_sales': {
                'count': len(recent_sales),
                'median_price': statistics.median(sale_prices) if sale_prices else 0,
                'avg_price': round(statistics.mean(sale_prices), 0) if sale_prices else 0
            }
        }
    
    def find_potential_sellers(self, criteria: Dict = None) -> List[PropertyRecord]:
        """Find potential sellers based on criteria (for farming)."""
        criteria = criteria or {}
        
        results = []
        for record in self.records.values():
            # Long-term owners (potential sellers)
            if criteria.get('min_ownership_years'):
                if record.sale_date:
                    years_owned = (datetime.now() - record.sale_date).days / 365
                    if years_owned < criteria['min_ownership_years']:
                        continue
            
            # High equity (market value >> sale price)
            if criteria.get('min_equity_ratio'):
                if record.sale_price > 0 and record.market_value > 0:
                    equity_ratio = record.market_value / record.sale_price
                    if equity_ratio < criteria['min_equity_ratio']:
                        continue
            
            # Specific area
            if criteria.get('zip_codes'):
                if record.zip_code not in criteria['zip_codes']:
                    continue
            
            # Property type
            if criteria.get('property_types'):
                if record.property_type not in criteria['property_types']:
                    continue
            
            results.append(record)
        
        return results
