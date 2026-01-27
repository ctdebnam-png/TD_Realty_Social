"""FSBO (For Sale By Owner) listing collector."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
import re
import urllib.request
import urllib.parse


@dataclass
class FSBOListing:
    """A For Sale By Owner listing."""
    id: str
    address: str
    city: str
    state: str = "OH"
    zip_code: str = ""
    price: float = 0
    bedrooms: int = 0
    bathrooms: float = 0
    sqft: int = 0
    description: str = ""
    seller_name: str = ""
    seller_phone: str = ""
    seller_email: str = ""
    source: str = ""
    source_url: str = ""
    listed_date: datetime = None
    days_on_market: int = 0
    photos: List[str] = field(default_factory=list)
    collected_at: datetime = field(default_factory=datetime.now)


class FSBOCollector:
    """Collect FSBO listings from multiple sources."""
    
    # Central Ohio cities to search
    OHIO_CITIES = [
        "Columbus", "Dublin", "Westerville", "Powell", "Delaware",
        "Hilliard", "Grove City", "Gahanna", "Reynoldsburg", "Pickerington",
        "New Albany", "Upper Arlington", "Worthington", "Bexley", 
        "Grandview Heights", "Canal Winchester", "Pataskala", "Sunbury"
    ]
    
    # Central Ohio ZIP codes
    OHIO_ZIPS = [
        "43015", "43016", "43017", "43026", "43035", "43054", "43065",
        "43068", "43081", "43082", "43085", "43110", "43119", "43123",
        "43147", "43201", "43202", "43204", "43206", "43209", "43212",
        "43214", "43215", "43220", "43221", "43230", "43235"
    ]
    
    def __init__(self, storage_path: str = "data/prospecting/fsbo"):
        self.storage_path = storage_path
        self.listings: Dict[str, FSBOListing] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_listings()
    
    def _load_listings(self):
        """Load cached FSBO listings."""
        listings_file = f"{self.storage_path}/listings.json"
        if os.path.exists(listings_file):
            with open(listings_file, 'r') as f:
                data = json.load(f)
                for l in data:
                    listing = FSBOListing(
                        id=l['id'],
                        address=l['address'],
                        city=l['city'],
                        state=l.get('state', 'OH'),
                        zip_code=l.get('zip_code', ''),
                        price=l.get('price', 0),
                        bedrooms=l.get('bedrooms', 0),
                        bathrooms=l.get('bathrooms', 0),
                        sqft=l.get('sqft', 0),
                        description=l.get('description', ''),
                        seller_name=l.get('seller_name', ''),
                        seller_phone=l.get('seller_phone', ''),
                        seller_email=l.get('seller_email', ''),
                        source=l.get('source', ''),
                        source_url=l.get('source_url', ''),
                        listed_date=datetime.fromisoformat(l['listed_date']) if l.get('listed_date') else None,
                        days_on_market=l.get('days_on_market', 0),
                        photos=l.get('photos', []),
                        collected_at=datetime.fromisoformat(l['collected_at'])
                    )
                    self.listings[listing.id] = listing
    
    def _save_listings(self):
        """Save FSBO listings."""
        listings_data = [
            {
                'id': l.id,
                'address': l.address,
                'city': l.city,
                'state': l.state,
                'zip_code': l.zip_code,
                'price': l.price,
                'bedrooms': l.bedrooms,
                'bathrooms': l.bathrooms,
                'sqft': l.sqft,
                'description': l.description,
                'seller_name': l.seller_name,
                'seller_phone': l.seller_phone,
                'seller_email': l.seller_email,
                'source': l.source,
                'source_url': l.source_url,
                'listed_date': l.listed_date.isoformat() if l.listed_date else None,
                'days_on_market': l.days_on_market,
                'photos': l.photos,
                'collected_at': l.collected_at.isoformat()
            }
            for l in self.listings.values()
        ]
        
        with open(f"{self.storage_path}/listings.json", 'w') as f:
            json.dump(listings_data, f, indent=2)
    
    def add_listing(self, listing: FSBOListing) -> bool:
        """Add a new FSBO listing."""
        # Check for duplicate by address
        addr_key = listing.address.lower().strip()
        for existing in self.listings.values():
            if existing.address.lower().strip() == addr_key:
                return False
        
        self.listings[listing.id] = listing
        self._save_listings()
        return True
    
    def collect_from_zillow_fsbo(self) -> List[FSBOListing]:
        """Collect FSBO listings from Zillow.
        
        Note: In production, this would use Zillow's API or scraping.
        For now, returns placeholder data.
        """
        # This would make actual API calls to Zillow
        # Zillow has FSBO listings at: https://www.zillow.com/homes/fsbo/
        return []
    
    def collect_from_craigslist(self) -> List[FSBOListing]:
        """Collect FSBO listings from Craigslist Columbus.
        
        Note: Would scrape https://columbus.craigslist.org/search/rea
        """
        return []
    
    def collect_from_facebook_marketplace(self) -> List[FSBOListing]:
        """Collect FSBO listings from Facebook Marketplace.
        
        Note: Would use Facebook API or scraping.
        """
        return []
    
    def collect_from_forsalebyowner_com(self) -> List[FSBOListing]:
        """Collect from ForSaleByOwner.com."""
        return []
    
    def collect_all(self) -> Dict[str, int]:
        """Collect from all sources."""
        results = {}
        
        zillow = self.collect_from_zillow_fsbo()
        for l in zillow:
            self.add_listing(l)
        results['zillow'] = len(zillow)
        
        craigslist = self.collect_from_craigslist()
        for l in craigslist:
            self.add_listing(l)
        results['craigslist'] = len(craigslist)
        
        facebook = self.collect_from_facebook_marketplace()
        for l in facebook:
            self.add_listing(l)
        results['facebook'] = len(facebook)
        
        fsbo_com = self.collect_from_forsalebyowner_com()
        for l in fsbo_com:
            self.add_listing(l)
        results['forsalebyowner'] = len(fsbo_com)
        
        return results
    
    def get_active_listings(self, max_days: int = 60) -> List[FSBOListing]:
        """Get active FSBO listings."""
        cutoff = datetime.now() - timedelta(days=max_days)
        listings = [l for l in self.listings.values() if l.collected_at >= cutoff]
        listings.sort(key=lambda l: l.collected_at, reverse=True)
        return listings
    
    def get_listings_by_city(self, city: str) -> List[FSBOListing]:
        """Get listings in a specific city."""
        city_lower = city.lower()
        return [l for l in self.listings.values() if l.city.lower() == city_lower]
    
    def get_listings_by_price(self, min_price: float = 0, max_price: float = float('inf')) -> List[FSBOListing]:
        """Get listings in a price range."""
        return [l for l in self.listings.values() if min_price <= l.price <= max_price]
    
    def get_stale_listings(self, min_days: int = 30) -> List[FSBOListing]:
        """Get FSBO listings that have been on market too long (motivated sellers)."""
        listings = [l for l in self.listings.values() if l.days_on_market >= min_days]
        listings.sort(key=lambda l: l.days_on_market, reverse=True)
        return listings
    
    def convert_to_prospect_record(self, listing: FSBOListing) -> Dict:
        """Convert FSBO listing to prospect record format."""
        return {
            'address': listing.address,
            'city': listing.city,
            'state': listing.state,
            'zip_code': listing.zip_code,
            'seller_name': listing.seller_name,
            'phone': listing.seller_phone,
            'email': listing.seller_email,
            'price': listing.price,
            'source': f'fsbo_{listing.source}',
            'url': listing.source_url,
            'days_listed': listing.days_on_market,
            'bedrooms': listing.bedrooms,
            'bathrooms': listing.bathrooms,
            'sqft': listing.sqft
        }
    
    def get_stats(self) -> Dict:
        """Get FSBO collection statistics."""
        by_city = {}
        by_source = {}
        
        for listing in self.listings.values():
            if listing.city not in by_city:
                by_city[listing.city] = 0
            by_city[listing.city] += 1
            
            if listing.source not in by_source:
                by_source[listing.source] = 0
            by_source[listing.source] += 1
        
        prices = [l.price for l in self.listings.values() if l.price > 0]
        
        return {
            'total_listings': len(self.listings),
            'active_listings': len(self.get_active_listings()),
            'stale_listings': len(self.get_stale_listings()),
            'by_city': by_city,
            'by_source': by_source,
            'avg_price': sum(prices) / len(prices) if prices else 0,
            'avg_days_on_market': sum(l.days_on_market for l in self.listings.values()) / len(self.listings) if self.listings else 0
        }
