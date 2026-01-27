"""Review publishing to external platforms."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

from .collector import Review, ReviewSource

logger = logging.getLogger(__name__)


class PublishPlatform(Enum):
    """Platforms to publish reviews."""
    WEBSITE = "website"
    GOOGLE_BUSINESS = "google_business"
    FACEBOOK = "facebook"
    ZILLOW = "zillow"
    REALTOR_COM = "realtor_com"
    SOCIAL_MEDIA = "social_media"


class ReviewPublisher:
    """Publish reviews to various platforms."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize publisher."""
        self.config_path = config_path or Path.home() / ".td-lead-engine" / "review_publisher.json"
        self.config = self._load_config()
        self.publish_history: List[Dict] = []

    def _load_config(self) -> Dict[str, Any]:
        """Load publisher configuration."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading publisher config: {e}")

        return {
            "auto_publish": False,
            "min_rating_for_publish": 4,
            "platforms": {
                "website": {"enabled": True},
                "google_business": {"enabled": False, "api_key": ""},
                "facebook": {"enabled": False, "page_id": "", "access_token": ""},
                "zillow": {"enabled": False},
                "social_media": {"enabled": True}
            }
        }

    def _save_config(self):
        """Save configuration."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def publish_to_website(self, review: Review) -> Dict[str, Any]:
        """Publish review to website."""
        # Generate website-ready format
        display_data = {
            "id": review.id,
            "name": review.display_name,
            "rating": review.rating,
            "title": review.title,
            "content": review.content,
            "highlights": review.highlights,
            "photo_url": review.photo_url if review.show_photo else "",
            "transaction_type": review.transaction_type,
            "location": review.property_address.split(",")[0] if review.property_address else "",
            "date": review.submitted_at.strftime("%B %d, %Y"),
            "published_at": datetime.now().isoformat()
        }

        self._log_publish(review.id, "website", "success")

        return {
            "success": True,
            "platform": "website",
            "data": display_data
        }

    def create_social_post(self, review: Review) -> Dict[str, str]:
        """Create social media post from review."""
        # Create engaging post from review
        stars = "⭐" * review.rating

        if len(review.content) > 200:
            excerpt = review.content[:197] + "..."
        else:
            excerpt = review.content

        # Different formats for different platforms
        instagram_post = f"""
{stars}

"{excerpt}"

- {review.display_name}, {review.transaction_type.title()} Client

Thank you for your kind words! We're so glad we could help you {"find your dream home" if review.transaction_type == "buyer" else "sell your home"}! 🏡

#TDRealty #ColumbusRealEstate #OhioRealtor #ClientReview #5StarService #RealEstateAgent
"""

        facebook_post = f"""
We love hearing from our clients! {stars}

"{review.content}"

- {review.display_name}

Thinking about buying or selling? We'd love to help you too! Send us a message or visit our website to get started.

#RealEstate #Columbus #OhioHomes #Testimonial
"""

        twitter_post = f"""
{stars} "{excerpt}" - {review.display_name}

Thank you for trusting us with your real estate journey!

#ColumbusOH #RealEstate
"""

        linkedin_post = f"""
Client Spotlight {stars}

We're honored to share this review from {review.display_name}:

"{review.content}"

At TD Realty, we're committed to providing exceptional service to every client. Thank you for the opportunity to serve you!

#RealEstate #ClientTestimonial #ColumbusOhio #RealtorLife
"""

        return {
            "instagram": instagram_post.strip(),
            "facebook": facebook_post.strip(),
            "twitter": twitter_post.strip(),
            "linkedin": linkedin_post.strip()
        }

    def request_google_review(self, review: Review) -> Dict[str, Any]:
        """Generate request for Google review."""
        # Google doesn't allow importing reviews, but we can request them
        google_review_url = self.config.get("google_review_url", "https://g.page/r/YOUR_PLACE_ID/review")

        email_content = f"""
Hi {review.display_name.split()[0]},

Thank you so much for your kind words about working with us!

Would you mind copying your review to Google? It helps other families find us when searching for a real estate agent.

Just click here: {google_review_url}

And paste your review:
"{review.content}"

Thank you again!

Best regards,
TD Realty
"""

        return {
            "type": "google_review_request",
            "review_url": google_review_url,
            "email_content": email_content,
            "original_review": review.content
        }

    def request_zillow_review(self, review: Review) -> Dict[str, Any]:
        """Generate request for Zillow review."""
        zillow_profile_url = self.config.get("zillow_profile_url", "https://www.zillow.com/profile/YOUR_PROFILE")

        email_content = f"""
Hi {review.display_name.split()[0]},

Thank you for the wonderful review! We really appreciate it.

If you have a moment, would you mind leaving a similar review on Zillow? Many home buyers and sellers start their search there.

Here's the link: {zillow_profile_url}

Thank you so much for your support!

Best regards,
TD Realty
"""

        return {
            "type": "zillow_review_request",
            "profile_url": zillow_profile_url,
            "email_content": email_content
        }

    def publish_review(
        self,
        review: Review,
        platforms: List[PublishPlatform] = None
    ) -> Dict[str, Any]:
        """Publish review to specified platforms."""
        if not review.can_use_marketing:
            return {"error": "Client has not authorized marketing use"}

        if platforms is None:
            platforms = [PublishPlatform.WEBSITE, PublishPlatform.SOCIAL_MEDIA]

        results = {}

        for platform in platforms:
            if platform == PublishPlatform.WEBSITE and review.can_use_website:
                results["website"] = self.publish_to_website(review)

            elif platform == PublishPlatform.SOCIAL_MEDIA and review.can_use_social:
                results["social_posts"] = self.create_social_post(review)
                self._log_publish(review.id, "social_media", "generated")

            elif platform == PublishPlatform.GOOGLE_BUSINESS:
                results["google"] = self.request_google_review(review)
                self._log_publish(review.id, "google", "requested")

            elif platform == PublishPlatform.ZILLOW:
                results["zillow"] = self.request_zillow_review(review)
                self._log_publish(review.id, "zillow", "requested")

        return results

    def _log_publish(self, review_id: str, platform: str, status: str):
        """Log publishing action."""
        self.publish_history.append({
            "review_id": review_id,
            "platform": platform,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })

    def generate_review_graphics(self, review: Review) -> Dict[str, str]:
        """Generate data for review graphics/images."""
        # Would integrate with image generation service
        return {
            "instagram_square": {
                "type": "1080x1080",
                "background": "brand_gradient",
                "quote": f'"{review.content[:150]}..."' if len(review.content) > 150 else f'"{review.content}"',
                "stars": review.rating,
                "author": review.display_name,
                "logo": "bottom_right"
            },
            "facebook_landscape": {
                "type": "1200x630",
                "background": "brand_photo",
                "quote": review.content[:200],
                "stars": review.rating,
                "author": review.display_name
            },
            "story": {
                "type": "1080x1920",
                "background": "brand_video",
                "quote": review.content[:100],
                "stars": review.rating,
                "author": review.display_name,
                "swipe_up": "View More Reviews"
            }
        }

    def create_video_testimonial_script(self, review: Review) -> str:
        """Create script for video testimonial."""
        script = f"""
VIDEO TESTIMONIAL SCRIPT
========================

INTRO (On-screen text):
"What Our Clients Say"

TITLE CARD:
{review.display_name}
{review.transaction_type.title()} Client
{"⭐" * review.rating}

TESTIMONIAL AUDIO/TEXT:
"{review.content}"

CLOSING:
Ready to start your real estate journey?
Contact TD Realty Today
[Phone Number] | [Website]

---

SUGGESTED B-ROLL:
- Client's new home exterior (if buyer)
- Sold sign being placed (if seller)
- Agent and client handshake
- Key exchange
- Family moving in

MUSIC:
Upbeat, inspiring background track

LENGTH:
30-60 seconds recommended
"""
        return script

    def batch_publish(self, reviews: List[Review]) -> Dict[str, Any]:
        """Batch publish multiple reviews."""
        results = {
            "total": len(reviews),
            "published": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }

        for review in reviews:
            if review.rating < self.config.get("min_rating_for_publish", 4):
                results["skipped"] += 1
                results["details"].append({
                    "review_id": review.id,
                    "status": "skipped",
                    "reason": "Below minimum rating"
                })
                continue

            try:
                result = self.publish_review(review)
                results["published"] += 1
                results["details"].append({
                    "review_id": review.id,
                    "status": "published",
                    "platforms": list(result.keys())
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({
                    "review_id": review.id,
                    "status": "failed",
                    "error": str(e)
                })

        return results

    def get_review_report(self, reviews: List[Review]) -> str:
        """Generate a formatted review report."""
        stats = {
            "total": len(reviews),
            "avg_rating": sum(r.rating for r in reviews) / len(reviews) if reviews else 0,
            "five_star": len([r for r in reviews if r.rating == 5]),
            "buyers": len([r for r in reviews if r.transaction_type == "buyer"]),
            "sellers": len([r for r in reviews if r.transaction_type == "seller"])
        }

        report = f"""
================================================================================
                           CLIENT REVIEW REPORT
                           Generated: {datetime.now().strftime("%B %d, %Y")}
================================================================================

SUMMARY
-------
Total Reviews: {stats['total']}
Average Rating: {stats['avg_rating']:.1f} / 5.0
Five-Star Reviews: {stats['five_star']} ({(stats['five_star']/stats['total']*100):.0f}%)

By Client Type:
  Buyers: {stats['buyers']}
  Sellers: {stats['sellers']}

RECENT TESTIMONIALS
-------------------
"""

        for review in sorted(reviews, key=lambda x: x.submitted_at, reverse=True)[:5]:
            report += f"""
{"⭐" * review.rating} - {review.display_name}
{review.transaction_type.title()} | {review.submitted_at.strftime("%B %Y")}
"{review.content[:200]}{'...' if len(review.content) > 200 else ''}"

"""

        report += """
================================================================================
                              END OF REPORT
================================================================================
"""

        return report
