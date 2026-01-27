"""Buyer-specific portal features."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class SavedSearch:
    """Saved property search criteria."""

    id: str
    client_id: str
    name: str

    # Search criteria
    locations: List[str] = field(default_factory=list)  # Cities, neighborhoods, zip codes
    min_price: int = 0
    max_price: int = 10000000
    min_beds: int = 0
    max_beds: int = 10
    min_baths: float = 0
    max_baths: float = 10
    min_sqft: int = 0
    max_sqft: int = 100000
    property_types: List[str] = field(default_factory=list)  # single_family, condo, etc.

    # Additional filters
    year_built_min: int = 0
    year_built_max: int = 2100
    lot_size_min: int = 0
    garage_spaces: int = 0
    must_have_features: List[str] = field(default_factory=list)  # pool, basement, etc.
    keywords: str = ""

    # Alert settings
    alert_frequency: str = "instant"  # instant, daily, weekly
    alert_enabled: bool = True
    last_alert_sent: Optional[datetime] = None

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SavedProperty:
    """Saved/favorited property."""

    id: str
    client_id: str
    property_id: str  # MLS number or internal ID

    # Property details (snapshot)
    address: str
    city: str
    price: int
    beds: int
    baths: float
    sqft: int
    photo_url: str = ""

    # Client interaction
    notes: str = ""
    rating: int = 0  # 1-5 stars
    tags: List[str] = field(default_factory=list)  # "favorite", "maybe", "toured", etc.

    # Status tracking
    status: str = "active"  # active, pending, sold, off_market
    price_at_save: int = 0
    current_price: int = 0
    price_changed: bool = False

    # Showing
    showing_requested: bool = False
    showing_scheduled: Optional[datetime] = None
    toured: bool = False
    tour_date: Optional[datetime] = None
    tour_feedback: str = ""

    saved_at: datetime = field(default_factory=datetime.now)


class BuyerPortal:
    """Buyer-specific portal functionality."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize buyer portal."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "buyer_portal.json"
        self.saved_searches: Dict[str, List[SavedSearch]] = {}  # By client_id
        self.saved_properties: Dict[str, List[SavedProperty]] = {}  # By client_id
        self._load_data()

    def _load_data(self):
        """Load buyer portal data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for client_id, searches in data.get("saved_searches", {}).items():
                        self.saved_searches[client_id] = [
                            SavedSearch(
                                id=s["id"],
                                client_id=s["client_id"],
                                name=s["name"],
                                locations=s.get("locations", []),
                                min_price=s.get("min_price", 0),
                                max_price=s.get("max_price", 10000000),
                                min_beds=s.get("min_beds", 0),
                                min_baths=s.get("min_baths", 0),
                                property_types=s.get("property_types", []),
                                alert_frequency=s.get("alert_frequency", "daily"),
                                alert_enabled=s.get("alert_enabled", True),
                                created_at=datetime.fromisoformat(s["created_at"])
                            )
                            for s in searches
                        ]

                    for client_id, properties in data.get("saved_properties", {}).items():
                        self.saved_properties[client_id] = [
                            SavedProperty(
                                id=p["id"],
                                client_id=p["client_id"],
                                property_id=p["property_id"],
                                address=p["address"],
                                city=p["city"],
                                price=p["price"],
                                beds=p["beds"],
                                baths=p["baths"],
                                sqft=p["sqft"],
                                notes=p.get("notes", ""),
                                rating=p.get("rating", 0),
                                tags=p.get("tags", []),
                                status=p.get("status", "active"),
                                showing_requested=p.get("showing_requested", False),
                                toured=p.get("toured", False),
                                saved_at=datetime.fromisoformat(p["saved_at"])
                            )
                            for p in properties
                        ]

            except Exception as e:
                logger.error(f"Error loading buyer portal data: {e}")

    def _save_data(self):
        """Save buyer portal data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "saved_searches": {
                client_id: [
                    {
                        "id": s.id,
                        "client_id": s.client_id,
                        "name": s.name,
                        "locations": s.locations,
                        "min_price": s.min_price,
                        "max_price": s.max_price,
                        "min_beds": s.min_beds,
                        "min_baths": s.min_baths,
                        "property_types": s.property_types,
                        "alert_frequency": s.alert_frequency,
                        "alert_enabled": s.alert_enabled,
                        "created_at": s.created_at.isoformat()
                    }
                    for s in searches
                ]
                for client_id, searches in self.saved_searches.items()
            },
            "saved_properties": {
                client_id: [
                    {
                        "id": p.id,
                        "client_id": p.client_id,
                        "property_id": p.property_id,
                        "address": p.address,
                        "city": p.city,
                        "price": p.price,
                        "beds": p.beds,
                        "baths": p.baths,
                        "sqft": p.sqft,
                        "notes": p.notes,
                        "rating": p.rating,
                        "tags": p.tags,
                        "status": p.status,
                        "showing_requested": p.showing_requested,
                        "toured": p.toured,
                        "saved_at": p.saved_at.isoformat()
                    }
                    for p in properties
                ]
                for client_id, properties in self.saved_properties.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_saved_search(
        self,
        client_id: str,
        name: str,
        locations: List[str],
        min_price: int = 0,
        max_price: int = 10000000,
        min_beds: int = 0,
        min_baths: float = 0,
        property_types: List[str] = None,
        alert_frequency: str = "daily"
    ) -> SavedSearch:
        """Create a saved search for a buyer."""
        search = SavedSearch(
            id=str(uuid.uuid4())[:8],
            client_id=client_id,
            name=name,
            locations=locations,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            min_baths=min_baths,
            property_types=property_types or [],
            alert_frequency=alert_frequency
        )

        if client_id not in self.saved_searches:
            self.saved_searches[client_id] = []
        self.saved_searches[client_id].append(search)
        self._save_data()

        return search

    def save_property(
        self,
        client_id: str,
        property_id: str,
        address: str,
        city: str,
        price: int,
        beds: int,
        baths: float,
        sqft: int,
        photo_url: str = ""
    ) -> SavedProperty:
        """Save a property for a buyer."""
        # Check if already saved
        existing = self.get_saved_properties(client_id)
        for prop in existing:
            if prop.property_id == property_id:
                return prop  # Already saved

        saved = SavedProperty(
            id=str(uuid.uuid4())[:8],
            client_id=client_id,
            property_id=property_id,
            address=address,
            city=city,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            photo_url=photo_url,
            price_at_save=price,
            current_price=price
        )

        if client_id not in self.saved_properties:
            self.saved_properties[client_id] = []
        self.saved_properties[client_id].append(saved)
        self._save_data()

        return saved

    def unsave_property(self, client_id: str, property_id: str) -> bool:
        """Remove a saved property."""
        if client_id not in self.saved_properties:
            return False

        original_count = len(self.saved_properties[client_id])
        self.saved_properties[client_id] = [
            p for p in self.saved_properties[client_id]
            if p.property_id != property_id
        ]

        if len(self.saved_properties[client_id]) < original_count:
            self._save_data()
            return True
        return False

    def update_property_notes(self, client_id: str, property_id: str, notes: str) -> bool:
        """Update notes for a saved property."""
        props = self.saved_properties.get(client_id, [])
        for prop in props:
            if prop.property_id == property_id:
                prop.notes = notes
                self._save_data()
                return True
        return False

    def rate_property(self, client_id: str, property_id: str, rating: int) -> bool:
        """Rate a saved property (1-5 stars)."""
        if rating < 1 or rating > 5:
            return False

        props = self.saved_properties.get(client_id, [])
        for prop in props:
            if prop.property_id == property_id:
                prop.rating = rating
                self._save_data()
                return True
        return False

    def tag_property(self, client_id: str, property_id: str, tag: str) -> bool:
        """Add a tag to a saved property."""
        props = self.saved_properties.get(client_id, [])
        for prop in props:
            if prop.property_id == property_id:
                if tag not in prop.tags:
                    prop.tags.append(tag)
                    self._save_data()
                return True
        return False

    def record_tour(
        self,
        client_id: str,
        property_id: str,
        tour_date: datetime,
        feedback: str = ""
    ) -> bool:
        """Record that a property was toured."""
        props = self.saved_properties.get(client_id, [])
        for prop in props:
            if prop.property_id == property_id:
                prop.toured = True
                prop.tour_date = tour_date
                prop.tour_feedback = feedback
                if "toured" not in prop.tags:
                    prop.tags.append("toured")
                self._save_data()
                return True
        return False

    def get_saved_searches(self, client_id: str) -> List[SavedSearch]:
        """Get all saved searches for a client."""
        return self.saved_searches.get(client_id, [])

    def get_saved_properties(self, client_id: str) -> List[SavedProperty]:
        """Get all saved properties for a client."""
        return self.saved_properties.get(client_id, [])

    def get_favorites(self, client_id: str) -> List[SavedProperty]:
        """Get favorited properties."""
        props = self.saved_properties.get(client_id, [])
        return [p for p in props if p.rating >= 4 or "favorite" in p.tags]

    def get_toured_properties(self, client_id: str) -> List[SavedProperty]:
        """Get properties that have been toured."""
        props = self.saved_properties.get(client_id, [])
        return [p for p in props if p.toured]

    def get_buyer_summary(self, client_id: str) -> Dict[str, Any]:
        """Get summary for buyer dashboard."""
        searches = self.get_saved_searches(client_id)
        properties = self.get_saved_properties(client_id)
        favorites = self.get_favorites(client_id)
        toured = self.get_toured_properties(client_id)

        # Calculate average criteria from searches
        if searches:
            avg_max_price = sum(s.max_price for s in searches) / len(searches)
            all_locations = set()
            for s in searches:
                all_locations.update(s.locations)
        else:
            avg_max_price = 0
            all_locations = set()

        return {
            "saved_searches": len(searches),
            "saved_properties": len(properties),
            "favorites": len(favorites),
            "toured": len(toured),
            "pending_showings": len([p for p in properties if p.showing_requested and not p.toured]),
            "search_locations": list(all_locations),
            "budget_range": f"${avg_max_price:,.0f}" if avg_max_price else "Not set",
            "recent_saves": [
                {
                    "address": p.address,
                    "city": p.city,
                    "price": p.price,
                    "saved_at": p.saved_at.isoformat()
                }
                for p in sorted(properties, key=lambda x: x.saved_at, reverse=True)[:5]
            ]
        }

    def check_price_changes(self, client_id: str) -> List[Dict[str, Any]]:
        """Check for price changes on saved properties."""
        # This would integrate with MLS/listing data
        changes = []
        props = self.saved_properties.get(client_id, [])

        for prop in props:
            if prop.current_price != prop.price_at_save:
                change = prop.current_price - prop.price_at_save
                changes.append({
                    "property_id": prop.property_id,
                    "address": prop.address,
                    "original_price": prop.price_at_save,
                    "current_price": prop.current_price,
                    "change": change,
                    "change_percent": (change / prop.price_at_save * 100) if prop.price_at_save else 0
                })

        return changes
