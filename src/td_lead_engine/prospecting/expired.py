"""Expired and withdrawn listing collector."""

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime, timedelta
import json
import os


@dataclass
class ExpiredListing:
    """An expired or withdrawn MLS listing."""
    id: str
    mls_number: str
    address: str
    city: str
    state: str = "OH"
    zip_code: str = ""
    list_price: float = 0
    original_price: float = 0
    status: str = "expired"  # expired, withdrawn, cancelled
    days_on_market: int = 0
    bedrooms: int = 0
    bathrooms: float = 0
    sqft: int = 0
    year_built: int = 0
    listing_agent: str = ""
    listing_office: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    expired_date: datetime = None
    listed_date: datetime = None
    price_history: List[Dict] = field(default_factory=list)
    collected_at: datetime = field(default_factory=datetime.now)


class ExpiredListingCollector:
    """Collect expired and withdrawn listings from MLS data."""
    
    def __init__(self, storage_path: str = "data/prospecting/expired"):
        self.storage_path = storage_path
        self.listings: Dict[str, ExpiredListing] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_listings()
    
    def _load_listings(self):
        """Load cached expired listings."""
        listings_file = f"{self.storage_path}/expired_listings.json"
        if os.path.exists(listings_file):
            with open(listings_file, 'r') as f:
                data = json.load(f)
                for l in data:
                    listing = ExpiredListing(
                        id=l['id'],
                        mls_number=l['mls_number'],
                        address=l['address'],
                        city=l['city'],
                        state=l.get('state', 'OH'),
                        zip_code=l.get('zip_code', ''),
                        list_price=l.get('list_price', 0),
                        original_price=l.get('original_price', 0),
                        status=l.get('status', 'expired'),
                        days_on_market=l.get('days_on_market', 0),
                        bedrooms=l.get('bedrooms', 0),
                        bathrooms=l.get('bathrooms', 0),
                        sqft=l.get('sqft', 0),
                        year_built=l.get('year_built', 0),
                        listing_agent=l.get('listing_agent', ''),
                        listing_office=l.get('listing_office', ''),
                        owner_name=l.get('owner_name', ''),
                        owner_phone=l.get('owner_phone', ''),
                        expired_date=datetime.fromisoformat(l['expired_date']) if l.get('expired_date') else None,
                        listed_date=datetime.fromisoformat(l['listed_date']) if l.get('listed_date') else None,
                        price_history=l.get('price_history', []),
                        collected_at=datetime.fromisoformat(l['collected_at'])
                    )
                    self.listings[listing.id] = listing
    
    def _save_listings(self):
        """Save expired listings."""
        listings_data = [
            {
                'id': l.id,
                'mls_number': l.mls_number,
                'address': l.address,
                'city': l.city,
                'state': l.state,
                'zip_code': l.zip_code,
                'list_price': l.list_price,
                'original_price': l.original_price,
                'status': l.status,
                'days_on_market': l.days_on_market,
                'bedrooms': l.bedrooms,
                'bathrooms': l.bathrooms,
                'sqft': l.sqft,
                'year_built': l.year_built,
                'listing_agent': l.listing_agent,
                'listing_office': l.listing_office,
                'owner_name': l.owner_name,
                'owner_phone': l.owner_phone,
                'expired_date': l.expired_date.isoformat() if l.expired_date else None,
                'listed_date': l.listed_date.isoformat() if l.listed_date else None,
                'price_history': l.price_history,
                'collected_at': l.collected_at.isoformat()
            }
            for l in self.listings.values()
        ]
        
        with open(f"{self.storage_path}/expired_listings.json", 'w') as f:
            json.dump(listings_data, f, indent=2)
    
    def add_listing(self, listing: ExpiredListing) -> bool:
        """Add an expired listing."""
        # Check for duplicate
        if listing.mls_number:
            for existing in self.listings.values():
                if existing.mls_number == listing.mls_number:
                    return False
        
        self.listings[listing.id] = listing
        self._save_listings()
        return True
    
    def import_from_mls_export(self, csv_data: str) -> int:
        """Import expired listings from MLS CSV export."""
        import csv
        import io
        import uuid
        
        reader = csv.DictReader(io.StringIO(csv_data))
        added = 0
        
        for row in reader:
            status = row.get('Status', '').lower()
            if status not in ['expired', 'withdrawn', 'cancelled', 'canceled']:
                continue
            
            listing = ExpiredListing(
                id=str(uuid.uuid4())[:12],
                mls_number=row.get('MLS#', row.get('MLSNumber', '')),
                address=row.get('Address', row.get('StreetAddress', '')),
                city=row.get('City', ''),
                zip_code=row.get('Zip', row.get('PostalCode', '')),
                list_price=float(row.get('ListPrice', row.get('Price', 0)) or 0),
                original_price=float(row.get('OriginalPrice', row.get('ListPrice', 0)) or 0),
                status=status,
                days_on_market=int(row.get('DOM', row.get('DaysOnMarket', 0)) or 0),
                bedrooms=int(row.get('Beds', row.get('Bedrooms', 0)) or 0),
                bathrooms=float(row.get('Baths', row.get('Bathrooms', 0)) or 0),
                sqft=int(row.get('SqFt', row.get('LivingArea', 0)) or 0),
                listing_agent=row.get('ListingAgent', row.get('AgentName', '')),
                listing_office=row.get('ListingOffice', row.get('OfficeName', '')),
                owner_name=row.get('OwnerName', ''),
                owner_phone=row.get('OwnerPhone', '')
            )
            
            if self.add_listing(listing):
                added += 1
        
        return added
    
    def get_recent_expireds(self, days: int = 7) -> List[ExpiredListing]:
        """Get recently expired listings (best prospects)."""
        cutoff = datetime.now() - timedelta(days=days)
        listings = [
            l for l in self.listings.values() 
            if l.expired_date and l.expired_date >= cutoff
        ]
        listings.sort(key=lambda l: l.expired_date, reverse=True)
        return listings
    
    def get_long_dom_listings(self, min_days: int = 90) -> List[ExpiredListing]:
        """Get listings that sat on market too long (pricing issues)."""
        listings = [l for l in self.listings.values() if l.days_on_market >= min_days]
        listings.sort(key=lambda l: l.days_on_market, reverse=True)
        return listings
    
    def get_overpriced_listings(self) -> List[ExpiredListing]:
        """Get listings that had significant price reductions (overpriced)."""
        overpriced = []
        for l in self.listings.values():
            if l.original_price > 0 and l.list_price > 0:
                reduction = (l.original_price - l.list_price) / l.original_price * 100
                if reduction >= 10:  # 10%+ price reduction
                    overpriced.append(l)
        
        overpriced.sort(key=lambda l: l.original_price - l.list_price, reverse=True)
        return overpriced
    
    def get_by_previous_agent(self, agent_name: str) -> List[ExpiredListing]:
        """Get expired listings from a specific agent (avoid)."""
        agent_lower = agent_name.lower()
        return [l for l in self.listings.values() if agent_lower in l.listing_agent.lower()]
    
    def convert_to_prospect_record(self, listing: ExpiredListing) -> Dict:
        """Convert to prospect record format."""
        return {
            'address': listing.address,
            'city': listing.city,
            'state': listing.state,
            'zip_code': listing.zip_code,
            'owner_name': listing.owner_name,
            'phone': listing.owner_phone,
            'list_price': listing.list_price,
            'original_price': listing.original_price,
            'days_on_market': listing.days_on_market,
            'status': listing.status,
            'expired_date': listing.expired_date.isoformat() if listing.expired_date else None,
            'listing_agent': listing.listing_agent,
            'mls_number': listing.mls_number
        }
    
    def get_stats(self) -> Dict:
        """Get collection statistics."""
        by_status = {'expired': 0, 'withdrawn': 0, 'cancelled': 0}
        for l in self.listings.values():
            if l.status in by_status:
                by_status[l.status] += 1
        
        prices = [l.list_price for l in self.listings.values() if l.list_price > 0]
        doms = [l.days_on_market for l in self.listings.values()]
        
        return {
            'total_listings': len(self.listings),
            'by_status': by_status,
            'recent_7_days': len(self.get_recent_expireds(7)),
            'recent_30_days': len(self.get_recent_expireds(30)),
            'long_dom': len(self.get_long_dom_listings()),
            'overpriced': len(self.get_overpriced_listings()),
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'avg_dom': sum(doms) / len(doms) if doms else 0
        }
