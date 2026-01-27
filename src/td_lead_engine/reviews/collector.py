"""Review and testimonial collection."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid
import hashlib

logger = logging.getLogger(__name__)


class ReviewStatus(Enum):
    """Review status."""
    REQUESTED = "requested"
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PUBLISHED = "published"
    DECLINED = "declined"


class ReviewSource(Enum):
    """Review source platform."""
    GOOGLE = "google"
    ZILLOW = "zillow"
    REALTOR_COM = "realtor_com"
    FACEBOOK = "facebook"
    YELP = "yelp"
    INTERNAL = "internal"


@dataclass
class ReviewRequest:
    """Request for a review."""

    id: str
    client_id: str
    client_name: str
    client_email: str
    client_phone: str = ""

    # Transaction context
    transaction_id: str = ""
    property_address: str = ""
    transaction_type: str = ""  # "buyer", "seller"
    close_date: Optional[datetime] = None

    # Request tracking
    status: ReviewStatus = ReviewStatus.REQUESTED
    requested_at: datetime = field(default_factory=datetime.now)
    reminder_count: int = 0
    last_reminder: Optional[datetime] = None

    # Access
    access_token: str = ""
    expires_at: Optional[datetime] = None


@dataclass
class Review:
    """Client review/testimonial."""

    id: str
    client_id: str
    client_name: str

    # Review content
    rating: int  # 1-5 stars
    title: str = ""
    content: str = ""
    highlights: List[str] = field(default_factory=list)  # Selected positive aspects

    # Source
    source: ReviewSource = ReviewSource.INTERNAL
    external_url: str = ""
    external_id: str = ""

    # Context
    transaction_id: str = ""
    property_address: str = ""
    transaction_type: str = ""

    # Status
    status: ReviewStatus = ReviewStatus.SUBMITTED
    approved_at: Optional[datetime] = None
    published_at: Optional[datetime] = None

    # Display preferences
    display_name: str = ""  # How client wants to be shown
    show_photo: bool = False
    photo_url: str = ""
    video_url: str = ""

    # Permissions
    can_use_marketing: bool = True
    can_use_website: bool = True
    can_use_social: bool = True

    submitted_at: datetime = field(default_factory=datetime.now)


class ReviewCollector:
    """Collect and manage reviews."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize review collector."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "reviews.json"
        self.reviews: List[Review] = []
        self.requests: List[ReviewRequest] = []
        self._load_data()

        # Review request templates
        self.highlight_options = [
            "Excellent communication",
            "Very knowledgeable about the area",
            "Made the process easy",
            "Responsive and available",
            "Great negotiator",
            "Professional and courteous",
            "Went above and beyond",
            "Found the perfect home",
            "Sold quickly for top dollar",
            "Would recommend to friends",
            "Helpful with first-time buying",
            "Expert market advice"
        ]

    def _load_data(self):
        """Load review data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for r in data.get("reviews", []):
                        review = Review(
                            id=r["id"],
                            client_id=r["client_id"],
                            client_name=r["client_name"],
                            rating=r["rating"],
                            title=r.get("title", ""),
                            content=r.get("content", ""),
                            highlights=r.get("highlights", []),
                            source=ReviewSource(r.get("source", "internal")),
                            status=ReviewStatus(r.get("status", "submitted")),
                            transaction_id=r.get("transaction_id", ""),
                            property_address=r.get("property_address", ""),
                            transaction_type=r.get("transaction_type", ""),
                            display_name=r.get("display_name", ""),
                            can_use_marketing=r.get("can_use_marketing", True),
                            submitted_at=datetime.fromisoformat(r["submitted_at"])
                        )
                        self.reviews.append(review)

                    for req in data.get("requests", []):
                        request = ReviewRequest(
                            id=req["id"],
                            client_id=req["client_id"],
                            client_name=req["client_name"],
                            client_email=req["client_email"],
                            transaction_id=req.get("transaction_id", ""),
                            status=ReviewStatus(req.get("status", "requested")),
                            access_token=req.get("access_token", ""),
                            requested_at=datetime.fromisoformat(req["requested_at"])
                        )
                        self.requests.append(request)

            except Exception as e:
                logger.error(f"Error loading reviews: {e}")

    def _save_data(self):
        """Save review data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "reviews": [
                {
                    "id": r.id,
                    "client_id": r.client_id,
                    "client_name": r.client_name,
                    "rating": r.rating,
                    "title": r.title,
                    "content": r.content,
                    "highlights": r.highlights,
                    "source": r.source.value,
                    "status": r.status.value,
                    "transaction_id": r.transaction_id,
                    "property_address": r.property_address,
                    "transaction_type": r.transaction_type,
                    "display_name": r.display_name,
                    "can_use_marketing": r.can_use_marketing,
                    "submitted_at": r.submitted_at.isoformat()
                }
                for r in self.reviews
            ],
            "requests": [
                {
                    "id": req.id,
                    "client_id": req.client_id,
                    "client_name": req.client_name,
                    "client_email": req.client_email,
                    "transaction_id": req.transaction_id,
                    "status": req.status.value,
                    "access_token": req.access_token,
                    "requested_at": req.requested_at.isoformat()
                }
                for req in self.requests
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_token(self, request_id: str) -> str:
        """Generate secure access token."""
        data = f"{request_id}:{datetime.now().isoformat()}:{uuid.uuid4()}"
        return hashlib.sha256(data.encode()).hexdigest()[:24]

    def request_review(
        self,
        client_id: str,
        client_name: str,
        client_email: str,
        transaction_id: str = "",
        property_address: str = "",
        transaction_type: str = "",
        close_date: Optional[datetime] = None
    ) -> ReviewRequest:
        """Request a review from a client."""
        request_id = str(uuid.uuid4())[:8]
        access_token = self._generate_token(request_id)

        request = ReviewRequest(
            id=request_id,
            client_id=client_id,
            client_name=client_name,
            client_email=client_email,
            transaction_id=transaction_id,
            property_address=property_address,
            transaction_type=transaction_type,
            close_date=close_date,
            access_token=access_token,
            expires_at=datetime.now() + timedelta(days=30)
        )

        self.requests.append(request)
        self._save_data()

        # Would send email here
        logger.info(f"Review requested from {client_name} ({client_email})")

        return request

    def submit_review(
        self,
        access_token: str,
        rating: int,
        content: str,
        title: str = "",
        highlights: List[str] = None,
        display_name: str = "",
        can_use_marketing: bool = True,
        can_use_website: bool = True,
        can_use_social: bool = True
    ) -> Optional[Review]:
        """Submit a review using access token."""
        # Find request
        request = None
        for req in self.requests:
            if req.access_token == access_token and req.status == ReviewStatus.REQUESTED:
                request = req
                break

        if not request:
            logger.warning("Invalid or expired review token")
            return None

        # Validate rating
        if rating < 1 or rating > 5:
            return None

        # Create review
        review_id = str(uuid.uuid4())[:8]

        review = Review(
            id=review_id,
            client_id=request.client_id,
            client_name=request.client_name,
            rating=rating,
            title=title,
            content=content,
            highlights=highlights or [],
            transaction_id=request.transaction_id,
            property_address=request.property_address,
            transaction_type=request.transaction_type,
            display_name=display_name or request.client_name,
            can_use_marketing=can_use_marketing,
            can_use_website=can_use_website,
            can_use_social=can_use_social
        )

        self.reviews.append(review)

        # Update request status
        request.status = ReviewStatus.SUBMITTED
        self._save_data()

        logger.info(f"Review submitted: {rating} stars from {request.client_name}")

        return review

    def add_external_review(
        self,
        client_name: str,
        rating: int,
        content: str,
        source: ReviewSource,
        external_url: str = "",
        external_id: str = "",
        transaction_id: str = "",
        property_address: str = ""
    ) -> Review:
        """Add a review from an external platform."""
        review_id = str(uuid.uuid4())[:8]

        review = Review(
            id=review_id,
            client_id="",
            client_name=client_name,
            rating=rating,
            content=content,
            source=source,
            external_url=external_url,
            external_id=external_id,
            transaction_id=transaction_id,
            property_address=property_address,
            display_name=client_name,
            status=ReviewStatus.APPROVED  # External reviews are pre-approved
        )

        self.reviews.append(review)
        self._save_data()

        return review

    def approve_review(self, review_id: str) -> bool:
        """Approve a review for publication."""
        for review in self.reviews:
            if review.id == review_id:
                review.status = ReviewStatus.APPROVED
                review.approved_at = datetime.now()
                self._save_data()
                return True
        return False

    def publish_review(self, review_id: str) -> bool:
        """Mark review as published."""
        for review in self.reviews:
            if review.id == review_id:
                if review.status == ReviewStatus.APPROVED:
                    review.status = ReviewStatus.PUBLISHED
                    review.published_at = datetime.now()
                    self._save_data()
                    return True
        return False

    def send_reminder(self, request_id: str) -> bool:
        """Send a reminder for pending review request."""
        for request in self.requests:
            if request.id == request_id and request.status == ReviewStatus.REQUESTED:
                request.reminder_count += 1
                request.last_reminder = datetime.now()
                self._save_data()

                # Would send reminder email here
                logger.info(f"Reminder sent to {request.client_email}")
                return True
        return False

    def get_review(self, review_id: str) -> Optional[Review]:
        """Get a specific review."""
        for review in self.reviews:
            if review.id == review_id:
                return review
        return None

    def get_pending_requests(self) -> List[ReviewRequest]:
        """Get pending review requests."""
        return [r for r in self.requests if r.status == ReviewStatus.REQUESTED]

    def get_reviews_for_approval(self) -> List[Review]:
        """Get reviews pending approval."""
        return [r for r in self.reviews if r.status == ReviewStatus.SUBMITTED]

    def get_published_reviews(self) -> List[Review]:
        """Get published reviews."""
        return [r for r in self.reviews if r.status == ReviewStatus.PUBLISHED]

    def get_reviews_by_rating(self, min_rating: int = 4) -> List[Review]:
        """Get reviews with minimum rating."""
        return [
            r for r in self.reviews
            if r.rating >= min_rating and r.status in [ReviewStatus.APPROVED, ReviewStatus.PUBLISHED]
        ]

    def get_review_statistics(self) -> Dict[str, Any]:
        """Get review statistics."""
        if not self.reviews:
            return {
                "total_reviews": 0,
                "average_rating": 0,
                "rating_distribution": {}
            }

        total = len(self.reviews)
        avg = sum(r.rating for r in self.reviews) / total

        distribution = {i: 0 for i in range(1, 6)}
        for review in self.reviews:
            distribution[review.rating] += 1

        by_source = {}
        for review in self.reviews:
            source = review.source.value
            by_source[source] = by_source.get(source, 0) + 1

        by_type = {"buyer": 0, "seller": 0, "other": 0}
        for review in self.reviews:
            tx_type = review.transaction_type or "other"
            by_type[tx_type] = by_type.get(tx_type, 0) + 1

        return {
            "total_reviews": total,
            "average_rating": round(avg, 1),
            "rating_distribution": distribution,
            "by_source": by_source,
            "by_transaction_type": by_type,
            "five_star_count": distribution[5],
            "five_star_percent": f"{(distribution[5]/total*100):.0f}%" if total > 0 else "0%",
            "pending_requests": len(self.get_pending_requests()),
            "pending_approval": len(self.get_reviews_for_approval())
        }

    def get_featured_testimonials(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get featured testimonials for display."""
        # Get highest rated, most recent reviews with good content
        eligible = [
            r for r in self.reviews
            if r.status in [ReviewStatus.APPROVED, ReviewStatus.PUBLISHED]
            and r.rating >= 4
            and len(r.content) > 50
            and r.can_use_website
        ]

        # Sort by rating then date
        eligible.sort(key=lambda x: (x.rating, x.submitted_at), reverse=True)

        return [
            {
                "id": r.id,
                "name": r.display_name or r.client_name.split()[0] + " " + r.client_name.split()[-1][0] + ".",
                "rating": r.rating,
                "title": r.title,
                "content": r.content,
                "highlights": r.highlights[:3],
                "transaction_type": r.transaction_type,
                "location": r.property_address.split(",")[0] if r.property_address else "",
                "photo_url": r.photo_url,
                "date": r.submitted_at.strftime("%B %Y")
            }
            for r in eligible[:count]
        ]

    def generate_review_request_email(self, request: ReviewRequest) -> Dict[str, str]:
        """Generate review request email content."""
        review_url = f"https://portal.tdrealty.com/review/{request.access_token}"

        subject = f"How was your experience with TD Realty?"

        body = f"""Hi {request.client_name.split()[0]},

Congratulations on your {"new home" if request.transaction_type == "buyer" else "successful sale"}!

We hope you had a great experience working with us. Your feedback means the world to us and helps other families find the right agent for their real estate needs.

Would you mind taking a moment to share your experience?

Click here to leave a review: {review_url}

It only takes about 2 minutes, and we'd really appreciate it!

Thank you for trusting us with your {"home purchase" if request.transaction_type == "buyer" else "home sale"}.

Best regards,
TD Realty

P.S. If you know anyone looking to buy or sell, we'd love to help them too!
"""

        return {
            "subject": subject,
            "body": body,
            "review_url": review_url
        }

    def generate_review_widget_html(self, max_reviews: int = 3) -> str:
        """Generate HTML widget for displaying reviews."""
        testimonials = self.get_featured_testimonials(max_reviews)
        stats = self.get_review_statistics()

        html = f"""
<div class="review-widget">
    <div class="review-summary">
        <span class="rating-badge">{stats['average_rating']}</span>
        <span class="star-display">{'★' * int(stats['average_rating'])}{'☆' * (5 - int(stats['average_rating']))}</span>
        <span class="review-count">Based on {stats['total_reviews']} reviews</span>
    </div>
    <div class="testimonials">
"""

        for t in testimonials:
            stars = '★' * t['rating'] + '☆' * (5 - t['rating'])
            html += f"""
        <div class="testimonial">
            <div class="testimonial-header">
                <span class="client-name">{t['name']}</span>
                <span class="stars">{stars}</span>
            </div>
            <p class="testimonial-content">"{t['content'][:200]}{'...' if len(t['content']) > 200 else ''}"</p>
            <div class="testimonial-meta">
                <span class="transaction-type">{t['transaction_type'].title()} Client</span>
                <span class="date">{t['date']}</span>
            </div>
        </div>
"""

        html += """
    </div>
</div>
"""

        return html
