"""MLS client for property data."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta
import json
import os
import requests
from abc import ABC, abstractmethod


class MLSProvider(Enum):
    """Supported MLS providers."""
    RETS = "rets"
    SPARK = "spark"
    BRIDGE = "bridge"
    TRESTLE = "trestle"
    CRMLS = "crmls"
    REALCOMP = "realcomp"
    COLUMBUS_REALTORS = "columbus_realtors"


class PropertyStatus(Enum):
    """Property listing status."""
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    COMING_SOON = "coming_soon"


class PropertyType(Enum):
    """Property types."""
    SINGLE_FAMILY = "single_family"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"
    MULTI_FAMILY = "multi_family"
    LAND = "land"
    COMMERCIAL = "commercial"
    MOBILE = "mobile"


@dataclass
class Property:
    """Property listing data."""
    mls_id: str
    mls_provider: str
    status: PropertyStatus
    property_type: PropertyType
    address: str
    city: str
    state: str
    zip_code: str
    county: str = ""
    subdivision: str = ""
    latitude: float = None
    longitude: float = None
    
    # Pricing
    list_price: float = 0
    original_price: float = 0
    sold_price: float = None
    price_per_sqft: float = None
    
    # Details
    bedrooms: int = 0
    bathrooms_full: int = 0
    bathrooms_half: int = 0
    sqft_living: int = 0
    sqft_lot: int = 0
    year_built: int = None
    stories: int = 1
    garage_spaces: int = 0
    
    # Features
    features: List[str] = field(default_factory=list)
    appliances: List[str] = field(default_factory=list)
    flooring: List[str] = field(default_factory=list)
    heating: str = ""
    cooling: str = ""
    basement: str = ""
    pool: bool = False
    fireplace: bool = False
    waterfront: bool = False
    
    # School Info
    school_district: str = ""
    elementary_school: str = ""
    middle_school: str = ""
    high_school: str = ""
    
    # HOA
    hoa_fee: float = 0
    hoa_frequency: str = ""  # monthly, annual
    
    # Dates
    list_date: datetime = None
    pending_date: datetime = None
    sold_date: datetime = None
    days_on_market: int = 0
    
    # Agent Info
    listing_agent_name: str = ""
    listing_agent_phone: str = ""
    listing_agent_email: str = ""
    listing_office: str = ""
    
    # Media
    photos: List[str] = field(default_factory=list)
    virtual_tour_url: str = ""
    video_url: str = ""
    
    # Description
    public_remarks: str = ""
    private_remarks: str = ""
    directions: str = ""
    
    # Timestamps
    last_modified: datetime = field(default_factory=datetime.now)
    synced_at: datetime = field(default_factory=datetime.now)
    
    @property
    def full_address(self) -> str:
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"
    
    @property
    def total_bathrooms(self) -> float:
        return self.bathrooms_full + (self.bathrooms_half * 0.5)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'mls_id': self.mls_id,
            'mls_provider': self.mls_provider,
            'status': self.status.value if isinstance(self.status, PropertyStatus) else self.status,
            'property_type': self.property_type.value if isinstance(self.property_type, PropertyType) else self.property_type,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'county': self.county,
            'subdivision': self.subdivision,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'list_price': self.list_price,
            'original_price': self.original_price,
            'sold_price': self.sold_price,
            'price_per_sqft': self.price_per_sqft,
            'bedrooms': self.bedrooms,
            'bathrooms_full': self.bathrooms_full,
            'bathrooms_half': self.bathrooms_half,
            'sqft_living': self.sqft_living,
            'sqft_lot': self.sqft_lot,
            'year_built': self.year_built,
            'stories': self.stories,
            'garage_spaces': self.garage_spaces,
            'features': self.features,
            'appliances': self.appliances,
            'flooring': self.flooring,
            'heating': self.heating,
            'cooling': self.cooling,
            'basement': self.basement,
            'pool': self.pool,
            'fireplace': self.fireplace,
            'waterfront': self.waterfront,
            'school_district': self.school_district,
            'elementary_school': self.elementary_school,
            'middle_school': self.middle_school,
            'high_school': self.high_school,
            'hoa_fee': self.hoa_fee,
            'hoa_frequency': self.hoa_frequency,
            'list_date': self.list_date.isoformat() if self.list_date else None,
            'pending_date': self.pending_date.isoformat() if self.pending_date else None,
            'sold_date': self.sold_date.isoformat() if self.sold_date else None,
            'days_on_market': self.days_on_market,
            'listing_agent_name': self.listing_agent_name,
            'listing_agent_phone': self.listing_agent_phone,
            'listing_agent_email': self.listing_agent_email,
            'listing_office': self.listing_office,
            'photos': self.photos,
            'virtual_tour_url': self.virtual_tour_url,
            'video_url': self.video_url,
            'public_remarks': self.public_remarks,
            'private_remarks': self.private_remarks,
            'directions': self.directions,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
            'synced_at': self.synced_at.isoformat() if self.synced_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Property':
        """Create from dictionary."""
        status = data.get('status', 'active')
        if isinstance(status, str):
            try:
                status = PropertyStatus(status)
            except ValueError:
                status = PropertyStatus.ACTIVE
        
        prop_type = data.get('property_type', 'single_family')
        if isinstance(prop_type, str):
            try:
                prop_type = PropertyType(prop_type)
            except ValueError:
                prop_type = PropertyType.SINGLE_FAMILY
        
        return cls(
            mls_id=data.get('mls_id', ''),
            mls_provider=data.get('mls_provider', ''),
            status=status,
            property_type=prop_type,
            address=data.get('address', ''),
            city=data.get('city', ''),
            state=data.get('state', ''),
            zip_code=data.get('zip_code', ''),
            county=data.get('county', ''),
            subdivision=data.get('subdivision', ''),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            list_price=data.get('list_price', 0),
            original_price=data.get('original_price', 0),
            sold_price=data.get('sold_price'),
            price_per_sqft=data.get('price_per_sqft'),
            bedrooms=data.get('bedrooms', 0),
            bathrooms_full=data.get('bathrooms_full', 0),
            bathrooms_half=data.get('bathrooms_half', 0),
            sqft_living=data.get('sqft_living', 0),
            sqft_lot=data.get('sqft_lot', 0),
            year_built=data.get('year_built'),
            stories=data.get('stories', 1),
            garage_spaces=data.get('garage_spaces', 0),
            features=data.get('features', []),
            appliances=data.get('appliances', []),
            flooring=data.get('flooring', []),
            heating=data.get('heating', ''),
            cooling=data.get('cooling', ''),
            basement=data.get('basement', ''),
            pool=data.get('pool', False),
            fireplace=data.get('fireplace', False),
            waterfront=data.get('waterfront', False),
            school_district=data.get('school_district', ''),
            elementary_school=data.get('elementary_school', ''),
            middle_school=data.get('middle_school', ''),
            high_school=data.get('high_school', ''),
            hoa_fee=data.get('hoa_fee', 0),
            hoa_frequency=data.get('hoa_frequency', ''),
            list_date=datetime.fromisoformat(data['list_date']) if data.get('list_date') else None,
            pending_date=datetime.fromisoformat(data['pending_date']) if data.get('pending_date') else None,
            sold_date=datetime.fromisoformat(data['sold_date']) if data.get('sold_date') else None,
            days_on_market=data.get('days_on_market', 0),
            listing_agent_name=data.get('listing_agent_name', ''),
            listing_agent_phone=data.get('listing_agent_phone', ''),
            listing_agent_email=data.get('listing_agent_email', ''),
            listing_office=data.get('listing_office', ''),
            photos=data.get('photos', []),
            virtual_tour_url=data.get('virtual_tour_url', ''),
            video_url=data.get('video_url', ''),
            public_remarks=data.get('public_remarks', ''),
            private_remarks=data.get('private_remarks', ''),
            directions=data.get('directions', ''),
            last_modified=datetime.fromisoformat(data['last_modified']) if data.get('last_modified') else None,
            synced_at=datetime.fromisoformat(data['synced_at']) if data.get('synced_at') else None
        )


class MLSAdapter(ABC):
    """Abstract base class for MLS adapters."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to MLS."""
        pass
    
    @abstractmethod
    def search(self, criteria: Dict) -> List[Property]:
        """Search for properties."""
        pass
    
    @abstractmethod
    def get_property(self, mls_id: str) -> Optional[Property]:
        """Get a single property by MLS ID."""
        pass
    
    @abstractmethod
    def get_photos(self, mls_id: str) -> List[str]:
        """Get property photos."""
        pass


class SparkAdapter(MLSAdapter):
    """Spark API adapter."""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://sparkapi.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.access_token = None
        self.token_expires = None
    
    def connect(self) -> bool:
        """Authenticate with Spark API."""
        # OAuth implementation would go here
        return True
    
    def _get_headers(self) -> Dict:
        """Get request headers."""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'X-SparkApi-User-Agent': 'TDRealty/1.0',
            'Content-Type': 'application/json'
        }
    
    def search(self, criteria: Dict) -> List[Property]:
        """Search properties via Spark API."""
        # Build query
        query_parts = []
        
        if criteria.get('city'):
            query_parts.append(f"City Eq '{criteria['city']}'")
        if criteria.get('min_price'):
            query_parts.append(f"ListPrice Ge {criteria['min_price']}")
        if criteria.get('max_price'):
            query_parts.append(f"ListPrice Le {criteria['max_price']}")
        if criteria.get('min_beds'):
            query_parts.append(f"BedsTotal Ge {criteria['min_beds']}")
        if criteria.get('status'):
            query_parts.append(f"StandardStatus Eq '{criteria['status']}'")
        
        query = " And ".join(query_parts) if query_parts else ""
        
        # In production, make actual API call
        # response = requests.get(
        #     f"{self.base_url}/v1/listings",
        #     headers=self._get_headers(),
        #     params={'_filter': query, '_limit': criteria.get('limit', 50)}
        # )
        
        return []  # Placeholder
    
    def get_property(self, mls_id: str) -> Optional[Property]:
        """Get property by MLS ID."""
        # In production, make actual API call
        return None
    
    def get_photos(self, mls_id: str) -> List[str]:
        """Get property photos."""
        return []


class BridgeAdapter(MLSAdapter):
    """Bridge Interactive adapter."""
    
    def __init__(self, access_token: str, dataset_id: str):
        self.access_token = access_token
        self.dataset_id = dataset_id
        self.base_url = "https://api.bridgedataoutput.com/api/v2"
    
    def connect(self) -> bool:
        """Test connection."""
        return True
    
    def search(self, criteria: Dict) -> List[Property]:
        """Search via Bridge API."""
        # Build query parameters
        params = {
            'access_token': self.access_token,
            'limit': criteria.get('limit', 50)
        }
        
        if criteria.get('city'):
            params['City'] = criteria['city']
        if criteria.get('min_price'):
            params['ListPrice.gte'] = criteria['min_price']
        if criteria.get('max_price'):
            params['ListPrice.lte'] = criteria['max_price']
        
        # In production:
        # response = requests.get(
        #     f"{self.base_url}/{self.dataset_id}/listings",
        #     params=params
        # )
        
        return []
    
    def get_property(self, mls_id: str) -> Optional[Property]:
        """Get property."""
        return None
    
    def get_photos(self, mls_id: str) -> List[str]:
        """Get photos."""
        return []


class MLSClient:
    """Main MLS client for property data."""
    
    def __init__(
        self,
        provider: MLSProvider = MLSProvider.SPARK,
        config: Dict = None,
        storage_path: str = "data/mls"
    ):
        self.provider = provider
        self.config = config or {}
        self.storage_path = storage_path
        self.adapter: Optional[MLSAdapter] = None
        self.properties: Dict[str, Property] = {}
        
        self._init_adapter()
        self._load_properties()
    
    def _init_adapter(self):
        """Initialize the MLS adapter."""
        if self.provider == MLSProvider.SPARK:
            self.adapter = SparkAdapter(
                api_key=self.config.get('api_key', ''),
                api_secret=self.config.get('api_secret', ''),
                base_url=self.config.get('base_url', '')
            )
        elif self.provider == MLSProvider.BRIDGE:
            self.adapter = BridgeAdapter(
                access_token=self.config.get('access_token', ''),
                dataset_id=self.config.get('dataset_id', '')
            )
    
    def _load_properties(self):
        """Load cached properties from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        props_file = f"{self.storage_path}/properties.json"
        if os.path.exists(props_file):
            with open(props_file, 'r') as f:
                data = json.load(f)
                for prop_data in data:
                    prop = Property.from_dict(prop_data)
                    self.properties[prop.mls_id] = prop
    
    def _save_properties(self):
        """Save properties to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [prop.to_dict() for prop in self.properties.values()]
        with open(f"{self.storage_path}/properties.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def connect(self) -> bool:
        """Connect to MLS."""
        if self.adapter:
            return self.adapter.connect()
        return False
    
    def search(
        self,
        city: str = None,
        zip_code: str = None,
        min_price: float = None,
        max_price: float = None,
        min_beds: int = None,
        max_beds: int = None,
        min_baths: float = None,
        property_type: PropertyType = None,
        status: PropertyStatus = PropertyStatus.ACTIVE,
        features: List[str] = None,
        school_district: str = None,
        days_on_market_max: int = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Property]:
        """Search for properties."""
        criteria = {
            'city': city,
            'zip_code': zip_code,
            'min_price': min_price,
            'max_price': max_price,
            'min_beds': min_beds,
            'max_beds': max_beds,
            'min_baths': min_baths,
            'property_type': property_type.value if property_type else None,
            'status': status.value if status else 'active',
            'features': features,
            'school_district': school_district,
            'days_on_market_max': days_on_market_max,
            'limit': limit,
            'offset': offset
        }
        
        # Remove None values
        criteria = {k: v for k, v in criteria.items() if v is not None}
        
        # Try adapter first
        if self.adapter:
            results = self.adapter.search(criteria)
            if results:
                # Cache results
                for prop in results:
                    self.properties[prop.mls_id] = prop
                self._save_properties()
                return results
        
        # Fall back to cached data
        return self._search_cached(criteria)
    
    def _search_cached(self, criteria: Dict) -> List[Property]:
        """Search cached properties."""
        results = []
        
        for prop in self.properties.values():
            # Status filter
            if criteria.get('status'):
                if prop.status.value != criteria['status']:
                    continue
            
            # City filter
            if criteria.get('city'):
                if prop.city.lower() != criteria['city'].lower():
                    continue
            
            # Price filters
            if criteria.get('min_price') and prop.list_price < criteria['min_price']:
                continue
            if criteria.get('max_price') and prop.list_price > criteria['max_price']:
                continue
            
            # Bedroom filters
            if criteria.get('min_beds') and prop.bedrooms < criteria['min_beds']:
                continue
            if criteria.get('max_beds') and prop.bedrooms > criteria['max_beds']:
                continue
            
            # Bathroom filter
            if criteria.get('min_baths') and prop.total_bathrooms < criteria['min_baths']:
                continue
            
            # Property type
            if criteria.get('property_type'):
                if prop.property_type.value != criteria['property_type']:
                    continue
            
            results.append(prop)
        
        # Apply limit and offset
        offset = criteria.get('offset', 0)
        limit = criteria.get('limit', 50)
        return results[offset:offset + limit]
    
    def get_property(self, mls_id: str) -> Optional[Property]:
        """Get a property by MLS ID."""
        # Check cache first
        if mls_id in self.properties:
            return self.properties[mls_id]
        
        # Try adapter
        if self.adapter:
            prop = self.adapter.get_property(mls_id)
            if prop:
                self.properties[mls_id] = prop
                self._save_properties()
                return prop
        
        return None
    
    def add_property(self, property_data: Dict) -> Property:
        """Add or update a property."""
        prop = Property.from_dict(property_data)
        prop.synced_at = datetime.now()
        self.properties[prop.mls_id] = prop
        self._save_properties()
        return prop
    
    def update_property(self, mls_id: str, updates: Dict) -> Optional[Property]:
        """Update a property."""
        if mls_id not in self.properties:
            return None
        
        prop = self.properties[mls_id]
        for key, value in updates.items():
            if hasattr(prop, key):
                setattr(prop, key, value)
        
        prop.last_modified = datetime.now()
        self._save_properties()
        return prop
    
    def remove_property(self, mls_id: str) -> bool:
        """Remove a property from cache."""
        if mls_id in self.properties:
            del self.properties[mls_id]
            self._save_properties()
            return True
        return False
    
    def get_recent_listings(self, days: int = 7, limit: int = 20) -> List[Property]:
        """Get recently listed properties."""
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            p for p in self.properties.values()
            if p.list_date and p.list_date > cutoff and p.status == PropertyStatus.ACTIVE
        ]
        recent.sort(key=lambda p: p.list_date, reverse=True)
        return recent[:limit]
    
    def get_price_reductions(self, days: int = 7, limit: int = 20) -> List[Property]:
        """Get properties with recent price reductions."""
        results = []
        for prop in self.properties.values():
            if prop.original_price and prop.list_price < prop.original_price:
                reduction_pct = ((prop.original_price - prop.list_price) / prop.original_price) * 100
                if reduction_pct >= 1:  # At least 1% reduction
                    results.append((prop, reduction_pct))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:limit]]
    
    def get_market_stats(self, city: str = None) -> Dict:
        """Get market statistics."""
        props = list(self.properties.values())
        
        if city:
            props = [p for p in props if p.city.lower() == city.lower()]
        
        active = [p for p in props if p.status == PropertyStatus.ACTIVE]
        pending = [p for p in props if p.status == PropertyStatus.PENDING]
        sold_90_days = [
            p for p in props
            if p.status == PropertyStatus.SOLD and p.sold_date and
            (datetime.now() - p.sold_date).days <= 90
        ]
        
        if not active:
            return {}
        
        prices = [p.list_price for p in active if p.list_price > 0]
        sold_prices = [p.sold_price for p in sold_90_days if p.sold_price]
        
        return {
            'active_listings': len(active),
            'pending_listings': len(pending),
            'sold_last_90_days': len(sold_90_days),
            'median_list_price': sorted(prices)[len(prices)//2] if prices else 0,
            'average_list_price': sum(prices) / len(prices) if prices else 0,
            'median_sold_price': sorted(sold_prices)[len(sold_prices)//2] if sold_prices else 0,
            'average_days_on_market': sum(p.days_on_market for p in active) / len(active) if active else 0,
            'price_per_sqft_avg': sum(p.price_per_sqft or 0 for p in active if p.price_per_sqft) / len([p for p in active if p.price_per_sqft]) if any(p.price_per_sqft for p in active) else 0
        }
