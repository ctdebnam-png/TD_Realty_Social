"""Seller-specific portal features."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ShowingFeedback:
    """Feedback from a showing."""

    id: str
    showing_id: str
    buyer_agent: str
    buyer_interest_level: str  # "very_interested", "interested", "neutral", "not_interested"
    price_feedback: str  # "fair", "too_high", "too_low", "no_comment"
    condition_feedback: str
    general_comments: str
    follow_up_expected: bool = False
    received_at: datetime = field(default_factory=datetime.now)


@dataclass
class Showing:
    """Property showing record."""

    id: str
    listing_id: str
    scheduled_time: datetime
    duration_minutes: int = 30

    # Agent info
    buyer_agent_name: str = ""
    buyer_agent_phone: str = ""
    buyer_agent_email: str = ""
    buyer_agent_company: str = ""

    # Status
    status: str = "scheduled"  # scheduled, confirmed, completed, cancelled, no_show
    confirmed_at: Optional[datetime] = None

    # Feedback
    feedback: Optional[ShowingFeedback] = None

    # Access
    access_instructions: str = ""
    lockbox_code: str = ""

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Offer:
    """Offer on a listing."""

    id: str
    listing_id: str

    # Offer details
    offer_price: int
    earnest_money: int = 0
    down_payment_percent: float = 20.0
    financing_type: str = "conventional"  # conventional, FHA, VA, cash, other

    # Contingencies
    inspection_contingency: bool = True
    inspection_days: int = 10
    financing_contingency: bool = True
    financing_days: int = 21
    appraisal_contingency: bool = True
    sale_contingency: bool = False

    # Timeline
    closing_date: Optional[datetime] = None
    possession_date: Optional[datetime] = None

    # Buyer info
    buyer_name: str = ""
    buyer_agent_name: str = ""
    buyer_agent_phone: str = ""
    buyer_pre_approved: bool = False
    pre_approval_amount: int = 0

    # Terms
    inclusions: List[str] = field(default_factory=list)
    exclusions: List[str] = field(default_factory=list)
    special_terms: str = ""

    # Status
    status: str = "pending"  # pending, countered, accepted, rejected, expired, withdrawn
    counter_amount: int = 0
    counter_terms: str = ""

    submitted_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None


@dataclass
class ListingActivity:
    """Activity on a listing."""

    id: str
    listing_id: str
    activity_type: str  # "view", "save", "inquiry", "showing_request", "offer"
    source: str = ""  # "zillow", "realtor", "redfin", "website", "sign"
    details: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SellerListing:
    """Seller's listing in the portal."""

    id: str
    client_id: str
    mls_number: str = ""

    # Property details
    address: str = ""
    city: str = ""
    state: str = "OH"
    zip_code: str = ""
    beds: int = 0
    baths: float = 0
    sqft: int = 0
    lot_size: int = 0
    year_built: int = 0

    # Listing details
    list_price: int = 0
    original_price: int = 0
    list_date: Optional[datetime] = None
    status: str = "coming_soon"  # coming_soon, active, pending, sold, withdrawn, expired

    # Marketing
    photos_count: int = 0
    video_tour_url: str = ""
    virtual_tour_url: str = ""
    description: str = ""

    # Statistics
    days_on_market: int = 0
    total_views: int = 0
    total_saves: int = 0
    total_showings: int = 0
    total_inquiries: int = 0

    # Agent notes
    agent_notes: str = ""
    next_steps: str = ""

    created_at: datetime = field(default_factory=datetime.now)


class SellerPortal:
    """Seller-specific portal functionality."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize seller portal."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "seller_portal.json"
        self.listings: Dict[str, List[SellerListing]] = {}  # By client_id
        self.showings: Dict[str, List[Showing]] = {}  # By listing_id
        self.offers: Dict[str, List[Offer]] = {}  # By listing_id
        self.activities: Dict[str, List[ListingActivity]] = {}  # By listing_id
        self._load_data()

    def _load_data(self):
        """Load seller portal data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for client_id, listings in data.get("listings", {}).items():
                        self.listings[client_id] = [
                            SellerListing(
                                id=l["id"],
                                client_id=l["client_id"],
                                mls_number=l.get("mls_number", ""),
                                address=l.get("address", ""),
                                city=l.get("city", ""),
                                list_price=l.get("list_price", 0),
                                original_price=l.get("original_price", 0),
                                status=l.get("status", "active"),
                                days_on_market=l.get("days_on_market", 0),
                                total_views=l.get("total_views", 0),
                                total_saves=l.get("total_saves", 0),
                                total_showings=l.get("total_showings", 0),
                                created_at=datetime.fromisoformat(l["created_at"])
                            )
                            for l in listings
                        ]

                    for listing_id, showings in data.get("showings", {}).items():
                        self.showings[listing_id] = [
                            Showing(
                                id=s["id"],
                                listing_id=s["listing_id"],
                                scheduled_time=datetime.fromisoformat(s["scheduled_time"]),
                                buyer_agent_name=s.get("buyer_agent_name", ""),
                                status=s.get("status", "scheduled")
                            )
                            for s in showings
                        ]

                    for listing_id, offers in data.get("offers", {}).items():
                        self.offers[listing_id] = [
                            Offer(
                                id=o["id"],
                                listing_id=o["listing_id"],
                                offer_price=o["offer_price"],
                                buyer_name=o.get("buyer_name", ""),
                                buyer_agent_name=o.get("buyer_agent_name", ""),
                                status=o.get("status", "pending"),
                                submitted_at=datetime.fromisoformat(o["submitted_at"])
                            )
                            for o in offers
                        ]

            except Exception as e:
                logger.error(f"Error loading seller portal data: {e}")

    def _save_data(self):
        """Save seller portal data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "listings": {
                client_id: [
                    {
                        "id": l.id,
                        "client_id": l.client_id,
                        "mls_number": l.mls_number,
                        "address": l.address,
                        "city": l.city,
                        "list_price": l.list_price,
                        "original_price": l.original_price,
                        "status": l.status,
                        "days_on_market": l.days_on_market,
                        "total_views": l.total_views,
                        "total_saves": l.total_saves,
                        "total_showings": l.total_showings,
                        "created_at": l.created_at.isoformat()
                    }
                    for l in listings
                ]
                for client_id, listings in self.listings.items()
            },
            "showings": {
                listing_id: [
                    {
                        "id": s.id,
                        "listing_id": s.listing_id,
                        "scheduled_time": s.scheduled_time.isoformat(),
                        "buyer_agent_name": s.buyer_agent_name,
                        "status": s.status
                    }
                    for s in showings
                ]
                for listing_id, showings in self.showings.items()
            },
            "offers": {
                listing_id: [
                    {
                        "id": o.id,
                        "listing_id": o.listing_id,
                        "offer_price": o.offer_price,
                        "buyer_name": o.buyer_name,
                        "buyer_agent_name": o.buyer_agent_name,
                        "status": o.status,
                        "submitted_at": o.submitted_at.isoformat()
                    }
                    for o in offers
                ]
                for listing_id, offers in self.offers.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_listing(
        self,
        client_id: str,
        address: str,
        city: str,
        list_price: int,
        beds: int = 0,
        baths: float = 0,
        sqft: int = 0,
        mls_number: str = ""
    ) -> SellerListing:
        """Add a listing for a seller."""
        listing = SellerListing(
            id=str(uuid.uuid4())[:8],
            client_id=client_id,
            mls_number=mls_number,
            address=address,
            city=city,
            list_price=list_price,
            original_price=list_price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            list_date=datetime.now(),
            status="active"
        )

        if client_id not in self.listings:
            self.listings[client_id] = []
        self.listings[client_id].append(listing)
        self._save_data()

        return listing

    def schedule_showing(
        self,
        listing_id: str,
        scheduled_time: datetime,
        buyer_agent_name: str,
        buyer_agent_phone: str = "",
        buyer_agent_email: str = "",
        duration_minutes: int = 30
    ) -> Showing:
        """Schedule a showing."""
        showing = Showing(
            id=str(uuid.uuid4())[:8],
            listing_id=listing_id,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            buyer_agent_name=buyer_agent_name,
            buyer_agent_phone=buyer_agent_phone,
            buyer_agent_email=buyer_agent_email,
            status="scheduled"
        )

        if listing_id not in self.showings:
            self.showings[listing_id] = []
        self.showings[listing_id].append(showing)

        # Update listing stats
        self._update_listing_stat(listing_id, "total_showings", 1)
        self._save_data()

        return showing

    def confirm_showing(self, listing_id: str, showing_id: str) -> bool:
        """Confirm a scheduled showing."""
        showings = self.showings.get(listing_id, [])
        for showing in showings:
            if showing.id == showing_id:
                showing.status = "confirmed"
                showing.confirmed_at = datetime.now()
                self._save_data()
                return True
        return False

    def complete_showing(
        self,
        listing_id: str,
        showing_id: str,
        interest_level: str = "neutral",
        price_feedback: str = "no_comment",
        comments: str = ""
    ) -> bool:
        """Mark showing as complete with feedback."""
        showings = self.showings.get(listing_id, [])
        for showing in showings:
            if showing.id == showing_id:
                showing.status = "completed"
                showing.feedback = ShowingFeedback(
                    id=str(uuid.uuid4())[:8],
                    showing_id=showing_id,
                    buyer_agent=showing.buyer_agent_name,
                    buyer_interest_level=interest_level,
                    price_feedback=price_feedback,
                    condition_feedback="",
                    general_comments=comments
                )
                self._save_data()
                return True
        return False

    def cancel_showing(self, listing_id: str, showing_id: str, reason: str = "") -> bool:
        """Cancel a showing."""
        showings = self.showings.get(listing_id, [])
        for showing in showings:
            if showing.id == showing_id:
                showing.status = "cancelled"
                self._save_data()
                return True
        return False

    def submit_offer(
        self,
        listing_id: str,
        offer_price: int,
        buyer_name: str,
        buyer_agent_name: str = "",
        buyer_agent_phone: str = "",
        earnest_money: int = 0,
        financing_type: str = "conventional",
        closing_date: Optional[datetime] = None,
        special_terms: str = ""
    ) -> Offer:
        """Submit an offer on a listing."""
        offer = Offer(
            id=str(uuid.uuid4())[:8],
            listing_id=listing_id,
            offer_price=offer_price,
            earnest_money=earnest_money,
            financing_type=financing_type,
            buyer_name=buyer_name,
            buyer_agent_name=buyer_agent_name,
            buyer_agent_phone=buyer_agent_phone,
            closing_date=closing_date,
            special_terms=special_terms,
            expires_at=datetime.now() + timedelta(days=3)  # Default 3 day expiration
        )

        if listing_id not in self.offers:
            self.offers[listing_id] = []
        self.offers[listing_id].append(offer)
        self._save_data()

        return offer

    def respond_to_offer(
        self,
        listing_id: str,
        offer_id: str,
        response: str,  # "accept", "reject", "counter"
        counter_amount: int = 0,
        counter_terms: str = ""
    ) -> bool:
        """Respond to an offer."""
        offers = self.offers.get(listing_id, [])
        for offer in offers:
            if offer.id == offer_id:
                if response == "accept":
                    offer.status = "accepted"
                    # Update listing status
                    self._update_listing_status(listing_id, "pending")
                elif response == "reject":
                    offer.status = "rejected"
                elif response == "counter":
                    offer.status = "countered"
                    offer.counter_amount = counter_amount
                    offer.counter_terms = counter_terms

                offer.responded_at = datetime.now()
                self._save_data()
                return True
        return False

    def record_activity(
        self,
        listing_id: str,
        activity_type: str,
        source: str = "",
        details: str = ""
    ):
        """Record activity on a listing."""
        activity = ListingActivity(
            id=str(uuid.uuid4())[:8],
            listing_id=listing_id,
            activity_type=activity_type,
            source=source,
            details=details
        )

        if listing_id not in self.activities:
            self.activities[listing_id] = []
        self.activities[listing_id].append(activity)

        # Update stats
        if activity_type == "view":
            self._update_listing_stat(listing_id, "total_views", 1)
        elif activity_type == "save":
            self._update_listing_stat(listing_id, "total_saves", 1)
        elif activity_type == "inquiry":
            self._update_listing_stat(listing_id, "total_inquiries", 1)

    def _update_listing_stat(self, listing_id: str, stat: str, increment: int):
        """Update a listing statistic."""
        for listings in self.listings.values():
            for listing in listings:
                if listing.id == listing_id:
                    current = getattr(listing, stat, 0)
                    setattr(listing, stat, current + increment)
                    return

    def _update_listing_status(self, listing_id: str, status: str):
        """Update listing status."""
        for listings in self.listings.values():
            for listing in listings:
                if listing.id == listing_id:
                    listing.status = status
                    return

    def get_seller_listings(self, client_id: str) -> List[SellerListing]:
        """Get all listings for a seller."""
        return self.listings.get(client_id, [])

    def get_listing_showings(self, listing_id: str) -> List[Showing]:
        """Get all showings for a listing."""
        return self.showings.get(listing_id, [])

    def get_upcoming_showings(self, listing_id: str) -> List[Showing]:
        """Get upcoming showings for a listing."""
        now = datetime.now()
        showings = self.showings.get(listing_id, [])
        return [
            s for s in showings
            if s.scheduled_time > now and s.status in ["scheduled", "confirmed"]
        ]

    def get_listing_offers(self, listing_id: str) -> List[Offer]:
        """Get all offers for a listing."""
        return self.offers.get(listing_id, [])

    def get_pending_offers(self, listing_id: str) -> List[Offer]:
        """Get pending offers for a listing."""
        offers = self.offers.get(listing_id, [])
        return [o for o in offers if o.status == "pending"]

    def get_seller_summary(self, client_id: str) -> Dict[str, Any]:
        """Get summary for seller dashboard."""
        listings = self.get_seller_listings(client_id)

        total_views = 0
        total_showings = 0
        total_offers = 0
        pending_offers = 0
        upcoming_showings = []

        for listing in listings:
            total_views += listing.total_views
            total_showings += listing.total_showings

            listing_offers = self.get_listing_offers(listing.id)
            total_offers += len(listing_offers)
            pending_offers += len([o for o in listing_offers if o.status == "pending"])

            upcoming = self.get_upcoming_showings(listing.id)
            for showing in upcoming[:3]:  # Max 3 per listing
                upcoming_showings.append({
                    "listing_address": listing.address,
                    "time": showing.scheduled_time.isoformat(),
                    "agent": showing.buyer_agent_name,
                    "status": showing.status
                })

        # Sort upcoming showings by time
        upcoming_showings.sort(key=lambda x: x["time"])

        return {
            "active_listings": len([l for l in listings if l.status == "active"]),
            "pending_listings": len([l for l in listings if l.status == "pending"]),
            "total_views": total_views,
            "total_showings": total_showings,
            "total_offers": total_offers,
            "pending_offers": pending_offers,
            "upcoming_showings": upcoming_showings[:5],
            "listings": [
                {
                    "id": l.id,
                    "address": l.address,
                    "city": l.city,
                    "price": l.list_price,
                    "status": l.status,
                    "days_on_market": l.days_on_market,
                    "views": l.total_views,
                    "showings": l.total_showings
                }
                for l in listings
            ]
        }

    def get_showing_feedback_summary(self, listing_id: str) -> Dict[str, Any]:
        """Get summary of showing feedback for a listing."""
        showings = self.showings.get(listing_id, [])
        completed = [s for s in showings if s.status == "completed" and s.feedback]

        if not completed:
            return {"message": "No feedback yet"}

        interest_levels = {}
        price_feedback = {}

        for showing in completed:
            fb = showing.feedback
            interest_levels[fb.buyer_interest_level] = interest_levels.get(fb.buyer_interest_level, 0) + 1
            price_feedback[fb.price_feedback] = price_feedback.get(fb.price_feedback, 0) + 1

        return {
            "total_showings": len(showings),
            "with_feedback": len(completed),
            "interest_breakdown": interest_levels,
            "price_perception": price_feedback,
            "recent_comments": [
                {
                    "agent": s.feedback.buyer_agent,
                    "interest": s.feedback.buyer_interest_level,
                    "comment": s.feedback.general_comments,
                    "date": s.scheduled_time.isoformat()
                }
                for s in completed[-5:]  # Last 5
                if s.feedback.general_comments
            ]
        }

    def get_offer_comparison(self, listing_id: str) -> Dict[str, Any]:
        """Compare offers on a listing."""
        offers = self.get_listing_offers(listing_id)

        if not offers:
            return {"message": "No offers received"}

        # Find listing for context
        listing = None
        for listings in self.listings.values():
            for l in listings:
                if l.id == listing_id:
                    listing = l
                    break

        list_price = listing.list_price if listing else 0

        comparison = []
        for offer in offers:
            comparison.append({
                "id": offer.id,
                "buyer": offer.buyer_name,
                "agent": offer.buyer_agent_name,
                "price": offer.offer_price,
                "vs_list": f"{(offer.offer_price / list_price * 100):.1f}%" if list_price else "N/A",
                "financing": offer.financing_type,
                "earnest_money": offer.earnest_money,
                "closing_date": offer.closing_date.isoformat() if offer.closing_date else "TBD",
                "contingencies": {
                    "inspection": offer.inspection_contingency,
                    "financing": offer.financing_contingency,
                    "appraisal": offer.appraisal_contingency,
                    "sale": offer.sale_contingency
                },
                "status": offer.status,
                "submitted": offer.submitted_at.isoformat()
            })

        # Sort by price descending
        comparison.sort(key=lambda x: x["price"], reverse=True)

        return {
            "list_price": list_price,
            "total_offers": len(offers),
            "highest_offer": max(o.offer_price for o in offers),
            "lowest_offer": min(o.offer_price for o in offers),
            "avg_offer": sum(o.offer_price for o in offers) / len(offers),
            "offers": comparison
        }
