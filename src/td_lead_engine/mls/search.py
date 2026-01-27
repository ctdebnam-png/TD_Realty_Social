"""Property search functionality."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import json
import os
import math

from .client import MLSClient, Property, PropertyStatus, PropertyType


class SortOption(Enum):
    """Property sort options."""
    PRICE_LOW_HIGH = "price_asc"
    PRICE_HIGH_LOW = "price_desc"
    NEWEST = "date_desc"
    OLDEST = "date_asc"
    SQFT = "sqft_desc"
    BEDS = "beds_desc"
    PRICE_REDUCED = "price_reduced"
    OPEN_HOUSE = "open_house"


@dataclass
class SearchCriteria:
    """Search criteria for property search."""
    # Location
    cities: List[str] = field(default_factory=list)
    zip_codes: List[str] = field(default_factory=list)
    counties: List[str] = field(default_factory=list)
    school_districts: List[str] = field(default_factory=list)
    subdivisions: List[str] = field(default_factory=list)
    
    # Radius search
    latitude: float = None
    longitude: float = None
    radius_miles: float = None
    
    # Price
    min_price: float = None
    max_price: float = None
    
    # Size
    min_beds: int = None
    max_beds: int = None
    min_baths: float = None
    max_baths: float = None
    min_sqft: int = None
    max_sqft: int = None
    min_lot_sqft: int = None
    max_lot_sqft: int = None
    
    # Details
    property_types: List[PropertyType] = field(default_factory=list)
    statuses: List[PropertyStatus] = field(default_factory=list)
    min_year_built: int = None
    max_year_built: int = None
    min_stories: int = None
    max_stories: int = None
    min_garage: int = None
    
    # Features
    features: List[str] = field(default_factory=list)  # pool, fireplace, etc.
    keywords: str = ""
    
    # HOA
    max_hoa: float = None
    
    # Market
    max_days_on_market: int = None
    price_reduced: bool = False
    new_listings_days: int = None
    
    # Sort and pagination
    sort_by: SortOption = SortOption.NEWEST
    page: int = 1
    page_size: int = 25
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'cities': self.cities,
            'zip_codes': self.zip_codes,
            'counties': self.counties,
            'school_districts': self.school_districts,
            'subdivisions': self.subdivisions,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_miles': self.radius_miles,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'min_beds': self.min_beds,
            'max_beds': self.max_beds,
            'min_baths': self.min_baths,
            'max_baths': self.max_baths,
            'min_sqft': self.min_sqft,
            'max_sqft': self.max_sqft,
            'min_lot_sqft': self.min_lot_sqft,
            'max_lot_sqft': self.max_lot_sqft,
            'property_types': [pt.value for pt in self.property_types] if self.property_types else [],
            'statuses': [s.value for s in self.statuses] if self.statuses else [],
            'min_year_built': self.min_year_built,
            'max_year_built': self.max_year_built,
            'min_stories': self.min_stories,
            'max_stories': self.max_stories,
            'min_garage': self.min_garage,
            'features': self.features,
            'keywords': self.keywords,
            'max_hoa': self.max_hoa,
            'max_days_on_market': self.max_days_on_market,
            'price_reduced': self.price_reduced,
            'new_listings_days': self.new_listings_days,
            'sort_by': self.sort_by.value if self.sort_by else None,
            'page': self.page,
            'page_size': self.page_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SearchCriteria':
        """Create from dictionary."""
        property_types = []
        for pt in data.get('property_types', []):
            try:
                property_types.append(PropertyType(pt))
            except ValueError:
                pass
        
        statuses = []
        for s in data.get('statuses', []):
            try:
                statuses.append(PropertyStatus(s))
            except ValueError:
                pass
        
        sort_by = SortOption.NEWEST
        if data.get('sort_by'):
            try:
                sort_by = SortOption(data['sort_by'])
            except ValueError:
                pass
        
        return cls(
            cities=data.get('cities', []),
            zip_codes=data.get('zip_codes', []),
            counties=data.get('counties', []),
            school_districts=data.get('school_districts', []),
            subdivisions=data.get('subdivisions', []),
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            radius_miles=data.get('radius_miles'),
            min_price=data.get('min_price'),
            max_price=data.get('max_price'),
            min_beds=data.get('min_beds'),
            max_beds=data.get('max_beds'),
            min_baths=data.get('min_baths'),
            max_baths=data.get('max_baths'),
            min_sqft=data.get('min_sqft'),
            max_sqft=data.get('max_sqft'),
            min_lot_sqft=data.get('min_lot_sqft'),
            max_lot_sqft=data.get('max_lot_sqft'),
            property_types=property_types,
            statuses=statuses,
            min_year_built=data.get('min_year_built'),
            max_year_built=data.get('max_year_built'),
            min_stories=data.get('min_stories'),
            max_stories=data.get('max_stories'),
            min_garage=data.get('min_garage'),
            features=data.get('features', []),
            keywords=data.get('keywords', ''),
            max_hoa=data.get('max_hoa'),
            max_days_on_market=data.get('max_days_on_market'),
            price_reduced=data.get('price_reduced', False),
            new_listings_days=data.get('new_listings_days'),
            sort_by=sort_by,
            page=data.get('page', 1),
            page_size=data.get('page_size', 25)
        )


@dataclass
class SearchResult:
    """Search result container."""
    properties: List[Property]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    criteria: SearchCriteria
    facets: Dict = field(default_factory=dict)


@dataclass
class SavedSearch:
    """A saved search for a user."""
    id: str
    lead_id: str
    name: str
    criteria: SearchCriteria
    notify_new_listings: bool = True
    notify_price_changes: bool = True
    notify_frequency: str = "daily"  # instant, daily, weekly
    last_notified: datetime = None
    created_at: datetime = field(default_factory=datetime.now)


class PropertySearch:
    """Property search engine."""
    
    def __init__(
        self,
        mls_client: MLSClient,
        storage_path: str = "data/searches"
    ):
        self.mls_client = mls_client
        self.storage_path = storage_path
        self.saved_searches: Dict[str, SavedSearch] = {}
        self._load_saved_searches()
    
    def _load_saved_searches(self):
        """Load saved searches from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        file_path = f"{self.storage_path}/saved_searches.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                for search_data in data:
                    search = SavedSearch(
                        id=search_data['id'],
                        lead_id=search_data['lead_id'],
                        name=search_data['name'],
                        criteria=SearchCriteria.from_dict(search_data['criteria']),
                        notify_new_listings=search_data.get('notify_new_listings', True),
                        notify_price_changes=search_data.get('notify_price_changes', True),
                        notify_frequency=search_data.get('notify_frequency', 'daily'),
                        last_notified=datetime.fromisoformat(search_data['last_notified']) if search_data.get('last_notified') else None,
                        created_at=datetime.fromisoformat(search_data['created_at']) if search_data.get('created_at') else datetime.now()
                    )
                    self.saved_searches[search.id] = search
    
    def _save_saved_searches(self):
        """Save searches to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'id': s.id,
                'lead_id': s.lead_id,
                'name': s.name,
                'criteria': s.criteria.to_dict(),
                'notify_new_listings': s.notify_new_listings,
                'notify_price_changes': s.notify_price_changes,
                'notify_frequency': s.notify_frequency,
                'last_notified': s.last_notified.isoformat() if s.last_notified else None,
                'created_at': s.created_at.isoformat()
            }
            for s in self.saved_searches.values()
        ]
        
        with open(f"{self.storage_path}/saved_searches.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def search(self, criteria: SearchCriteria) -> SearchResult:
        """Search for properties matching criteria."""
        # Get all properties from MLS client
        all_properties = list(self.mls_client.properties.values())
        
        # Apply filters
        filtered = self._apply_filters(all_properties, criteria)
        
        # Calculate facets before pagination
        facets = self._calculate_facets(filtered, criteria)
        
        # Sort
        sorted_props = self._sort_properties(filtered, criteria.sort_by)
        
        # Paginate
        total_count = len(sorted_props)
        total_pages = math.ceil(total_count / criteria.page_size)
        start = (criteria.page - 1) * criteria.page_size
        end = start + criteria.page_size
        page_results = sorted_props[start:end]
        
        return SearchResult(
            properties=page_results,
            total_count=total_count,
            page=criteria.page,
            page_size=criteria.page_size,
            total_pages=total_pages,
            criteria=criteria,
            facets=facets
        )
    
    def _apply_filters(self, properties: List[Property], criteria: SearchCriteria) -> List[Property]:
        """Apply search filters to properties."""
        results = []
        
        for prop in properties:
            # Status filter
            if criteria.statuses:
                if prop.status not in criteria.statuses:
                    continue
            elif prop.status != PropertyStatus.ACTIVE:
                # Default to active only
                continue
            
            # Location filters
            if criteria.cities:
                if prop.city.lower() not in [c.lower() for c in criteria.cities]:
                    continue
            
            if criteria.zip_codes:
                if prop.zip_code not in criteria.zip_codes:
                    continue
            
            if criteria.counties:
                if prop.county.lower() not in [c.lower() for c in criteria.counties]:
                    continue
            
            if criteria.school_districts:
                if prop.school_district.lower() not in [s.lower() for s in criteria.school_districts]:
                    continue
            
            if criteria.subdivisions:
                if prop.subdivision.lower() not in [s.lower() for s in criteria.subdivisions]:
                    continue
            
            # Radius search
            if criteria.latitude and criteria.longitude and criteria.radius_miles:
                if prop.latitude and prop.longitude:
                    distance = self._calculate_distance(
                        criteria.latitude, criteria.longitude,
                        prop.latitude, prop.longitude
                    )
                    if distance > criteria.radius_miles:
                        continue
                else:
                    continue  # Skip properties without coordinates
            
            # Price filters
            if criteria.min_price and prop.list_price < criteria.min_price:
                continue
            if criteria.max_price and prop.list_price > criteria.max_price:
                continue
            
            # Size filters
            if criteria.min_beds and prop.bedrooms < criteria.min_beds:
                continue
            if criteria.max_beds and prop.bedrooms > criteria.max_beds:
                continue
            if criteria.min_baths and prop.total_bathrooms < criteria.min_baths:
                continue
            if criteria.max_baths and prop.total_bathrooms > criteria.max_baths:
                continue
            if criteria.min_sqft and prop.sqft_living < criteria.min_sqft:
                continue
            if criteria.max_sqft and prop.sqft_living > criteria.max_sqft:
                continue
            if criteria.min_lot_sqft and prop.sqft_lot < criteria.min_lot_sqft:
                continue
            if criteria.max_lot_sqft and prop.sqft_lot > criteria.max_lot_sqft:
                continue
            
            # Property type
            if criteria.property_types:
                if prop.property_type not in criteria.property_types:
                    continue
            
            # Details
            if criteria.min_year_built and prop.year_built:
                if prop.year_built < criteria.min_year_built:
                    continue
            if criteria.max_year_built and prop.year_built:
                if prop.year_built > criteria.max_year_built:
                    continue
            if criteria.min_stories and prop.stories < criteria.min_stories:
                continue
            if criteria.max_stories and prop.stories > criteria.max_stories:
                continue
            if criteria.min_garage and prop.garage_spaces < criteria.min_garage:
                continue
            
            # Features
            if criteria.features:
                prop_features = [f.lower() for f in prop.features]
                for required_feature in criteria.features:
                    if required_feature.lower() not in prop_features:
                        # Check specific attributes
                        if required_feature.lower() == 'pool' and not prop.pool:
                            continue
                        elif required_feature.lower() == 'fireplace' and not prop.fireplace:
                            continue
                        elif required_feature.lower() == 'waterfront' and not prop.waterfront:
                            continue
            
            # HOA
            if criteria.max_hoa is not None:
                if prop.hoa_fee > criteria.max_hoa:
                    continue
            
            # Market conditions
            if criteria.max_days_on_market:
                if prop.days_on_market > criteria.max_days_on_market:
                    continue
            
            if criteria.price_reduced:
                if not prop.original_price or prop.list_price >= prop.original_price:
                    continue
            
            if criteria.new_listings_days:
                if not prop.list_date:
                    continue
                days_since_listed = (datetime.now() - prop.list_date).days
                if days_since_listed > criteria.new_listings_days:
                    continue
            
            # Keyword search
            if criteria.keywords:
                keywords = criteria.keywords.lower()
                searchable = f"{prop.address} {prop.public_remarks} {' '.join(prop.features)}".lower()
                if keywords not in searchable:
                    continue
            
            results.append(prop)
        
        return results
    
    def _sort_properties(self, properties: List[Property], sort_by: SortOption) -> List[Property]:
        """Sort properties."""
        if sort_by == SortOption.PRICE_LOW_HIGH:
            return sorted(properties, key=lambda p: p.list_price)
        elif sort_by == SortOption.PRICE_HIGH_LOW:
            return sorted(properties, key=lambda p: p.list_price, reverse=True)
        elif sort_by == SortOption.NEWEST:
            return sorted(properties, key=lambda p: p.list_date or datetime.min, reverse=True)
        elif sort_by == SortOption.OLDEST:
            return sorted(properties, key=lambda p: p.list_date or datetime.min)
        elif sort_by == SortOption.SQFT:
            return sorted(properties, key=lambda p: p.sqft_living, reverse=True)
        elif sort_by == SortOption.BEDS:
            return sorted(properties, key=lambda p: p.bedrooms, reverse=True)
        elif sort_by == SortOption.PRICE_REDUCED:
            def reduction_amount(p):
                if p.original_price and p.list_price < p.original_price:
                    return p.original_price - p.list_price
                return 0
            return sorted(properties, key=reduction_amount, reverse=True)
        
        return properties
    
    def _calculate_facets(self, properties: List[Property], criteria: SearchCriteria) -> Dict:
        """Calculate facets for search results."""
        facets = {
            'cities': {},
            'property_types': {},
            'price_ranges': {},
            'bedroom_counts': {},
            'year_built_ranges': {}
        }
        
        for prop in properties:
            # Cities
            facets['cities'][prop.city] = facets['cities'].get(prop.city, 0) + 1
            
            # Property types
            pt = prop.property_type.value
            facets['property_types'][pt] = facets['property_types'].get(pt, 0) + 1
            
            # Price ranges
            if prop.list_price < 200000:
                facets['price_ranges']['Under $200K'] = facets['price_ranges'].get('Under $200K', 0) + 1
            elif prop.list_price < 300000:
                facets['price_ranges']['$200K - $300K'] = facets['price_ranges'].get('$200K - $300K', 0) + 1
            elif prop.list_price < 400000:
                facets['price_ranges']['$300K - $400K'] = facets['price_ranges'].get('$300K - $400K', 0) + 1
            elif prop.list_price < 500000:
                facets['price_ranges']['$400K - $500K'] = facets['price_ranges'].get('$400K - $500K', 0) + 1
            else:
                facets['price_ranges']['$500K+'] = facets['price_ranges'].get('$500K+', 0) + 1
            
            # Bedrooms
            beds = str(prop.bedrooms) + ' bed'
            if prop.bedrooms != 1:
                beds += 's'
            facets['bedroom_counts'][beds] = facets['bedroom_counts'].get(beds, 0) + 1
            
            # Year built
            if prop.year_built:
                if prop.year_built < 1970:
                    facets['year_built_ranges']['Before 1970'] = facets['year_built_ranges'].get('Before 1970', 0) + 1
                elif prop.year_built < 1990:
                    facets['year_built_ranges']['1970-1990'] = facets['year_built_ranges'].get('1970-1990', 0) + 1
                elif prop.year_built < 2010:
                    facets['year_built_ranges']['1990-2010'] = facets['year_built_ranges'].get('1990-2010', 0) + 1
                else:
                    facets['year_built_ranges']['2010+'] = facets['year_built_ranges'].get('2010+', 0) + 1
        
        return facets
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles."""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def save_search(
        self,
        lead_id: str,
        name: str,
        criteria: SearchCriteria,
        notify_new_listings: bool = True,
        notify_price_changes: bool = True,
        notify_frequency: str = "daily"
    ) -> SavedSearch:
        """Save a search for a lead."""
        import uuid
        
        search = SavedSearch(
            id=str(uuid.uuid4())[:8],
            lead_id=lead_id,
            name=name,
            criteria=criteria,
            notify_new_listings=notify_new_listings,
            notify_price_changes=notify_price_changes,
            notify_frequency=notify_frequency
        )
        
        self.saved_searches[search.id] = search
        self._save_saved_searches()
        return search
    
    def update_saved_search(self, search_id: str, updates: Dict) -> Optional[SavedSearch]:
        """Update a saved search."""
        if search_id not in self.saved_searches:
            return None
        
        search = self.saved_searches[search_id]
        for key, value in updates.items():
            if hasattr(search, key):
                if key == 'criteria' and isinstance(value, dict):
                    search.criteria = SearchCriteria.from_dict(value)
                else:
                    setattr(search, key, value)
        
        self._save_saved_searches()
        return search
    
    def delete_saved_search(self, search_id: str) -> bool:
        """Delete a saved search."""
        if search_id in self.saved_searches:
            del self.saved_searches[search_id]
            self._save_saved_searches()
            return True
        return False
    
    def get_saved_searches(self, lead_id: str) -> List[SavedSearch]:
        """Get saved searches for a lead."""
        return [s for s in self.saved_searches.values() if s.lead_id == lead_id]
    
    def run_saved_search(self, search_id: str) -> Optional[SearchResult]:
        """Run a saved search."""
        if search_id not in self.saved_searches:
            return None
        
        search = self.saved_searches[search_id]
        return self.search(search.criteria)
    
    def get_matching_properties_count(self, criteria: SearchCriteria) -> int:
        """Get count of matching properties without full search."""
        all_properties = list(self.mls_client.properties.values())
        filtered = self._apply_filters(all_properties, criteria)
        return len(filtered)
