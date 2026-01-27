"""Social media posting functionality."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class PostStatus(Enum):
    """Post status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class PostType(Enum):
    """Type of post."""
    NEW_LISTING = "new_listing"
    JUST_SOLD = "just_sold"
    OPEN_HOUSE = "open_house"
    PRICE_REDUCTION = "price_reduction"
    MARKET_UPDATE = "market_update"
    TESTIMONIAL = "testimonial"
    TIP = "tip"
    BEHIND_SCENES = "behind_scenes"
    MILESTONE = "milestone"
    HOLIDAY = "holiday"
    COMMUNITY = "community"
    CUSTOM = "custom"


@dataclass
class SocialPost:
    """Social media post."""

    id: str
    post_type: PostType

    # Content
    content: str
    hashtags: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)
    link_url: str = ""

    # Platform-specific content
    platform_content: Dict[str, str] = field(default_factory=dict)
    # e.g., {"instagram": "shorter version", "linkedin": "professional version"}

    # Scheduling
    platforms: List[Platform] = field(default_factory=list)
    scheduled_time: Optional[datetime] = None
    published_times: Dict[str, datetime] = field(default_factory=dict)

    # Status
    status: PostStatus = PostStatus.DRAFT

    # Metadata
    property_id: str = ""
    property_address: str = ""
    campaign_id: str = ""

    # Analytics
    engagement: Dict[str, Dict[str, int]] = field(default_factory=dict)
    # {"facebook": {"likes": 10, "comments": 2, "shares": 1}}

    created_at: datetime = field(default_factory=datetime.now)


class SocialPoster:
    """Post to social media platforms."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize social poster."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "social_posts.json"
        self.posts: Dict[str, SocialPost] = {}
        self.credentials: Dict[str, Dict] = {}
        self._load_data()

    def _load_data(self):
        """Load social post data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for post_data in data.get("posts", []):
                        post = SocialPost(
                            id=post_data["id"],
                            post_type=PostType(post_data.get("post_type", "custom")),
                            content=post_data["content"],
                            hashtags=post_data.get("hashtags", []),
                            media_urls=post_data.get("media_urls", []),
                            link_url=post_data.get("link_url", ""),
                            platforms=[Platform(p) for p in post_data.get("platforms", [])],
                            status=PostStatus(post_data.get("status", "draft")),
                            property_id=post_data.get("property_id", ""),
                            property_address=post_data.get("property_address", ""),
                            created_at=datetime.fromisoformat(post_data["created_at"])
                        )

                        if post_data.get("scheduled_time"):
                            post.scheduled_time = datetime.fromisoformat(post_data["scheduled_time"])

                        self.posts[post.id] = post

                    self.credentials = data.get("credentials", {})

            except Exception as e:
                logger.error(f"Error loading social posts: {e}")

    def _save_data(self):
        """Save social post data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "posts": [
                {
                    "id": post.id,
                    "post_type": post.post_type.value,
                    "content": post.content,
                    "hashtags": post.hashtags,
                    "media_urls": post.media_urls,
                    "link_url": post.link_url,
                    "platforms": [p.value for p in post.platforms],
                    "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
                    "status": post.status.value,
                    "property_id": post.property_id,
                    "property_address": post.property_address,
                    "engagement": post.engagement,
                    "created_at": post.created_at.isoformat()
                }
                for post in self.posts.values()
            ],
            "credentials": self.credentials,
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_post(
        self,
        content: str,
        post_type: PostType = PostType.CUSTOM,
        platforms: List[Platform] = None,
        hashtags: List[str] = None,
        media_urls: List[str] = None,
        link_url: str = "",
        property_id: str = "",
        property_address: str = "",
        scheduled_time: Optional[datetime] = None
    ) -> SocialPost:
        """Create a new social post."""
        post_id = str(uuid.uuid4())[:8]

        post = SocialPost(
            id=post_id,
            post_type=post_type,
            content=content,
            hashtags=hashtags or [],
            media_urls=media_urls or [],
            link_url=link_url,
            platforms=platforms or [Platform.FACEBOOK, Platform.INSTAGRAM],
            property_id=property_id,
            property_address=property_address,
            scheduled_time=scheduled_time,
            status=PostStatus.SCHEDULED if scheduled_time else PostStatus.DRAFT
        )

        self.posts[post_id] = post
        self._save_data()

        return post

    def create_listing_post(
        self,
        property_address: str,
        price: int,
        beds: int,
        baths: float,
        sqft: int,
        photo_urls: List[str],
        listing_url: str = "",
        property_id: str = ""
    ) -> SocialPost:
        """Create a new listing announcement post."""
        content = f"""🏠 NEW LISTING ALERT! 🏠

📍 {property_address}

✨ {beds} Beds | {baths} Baths | {sqft:,} Sq Ft
💰 ${price:,}

Don't miss this opportunity! Contact us today for a private showing.

🔗 Link in bio for more details!
"""

        hashtags = [
            "NewListing", "JustListed", "ForSale", "RealEstate",
            "ColumbusOH", "OhioRealEstate", "DreamHome",
            "HouseHunting", "HomeForSale", "TDRealty"
        ]

        return self.create_post(
            content=content,
            post_type=PostType.NEW_LISTING,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=hashtags,
            media_urls=photo_urls,
            link_url=listing_url,
            property_id=property_id,
            property_address=property_address
        )

    def create_sold_post(
        self,
        property_address: str,
        sale_price: int,
        photo_url: str = "",
        client_name: str = "",
        days_on_market: int = 0,
        property_id: str = ""
    ) -> SocialPost:
        """Create a just sold announcement post."""
        content = f"""🎉 JUST SOLD! 🎉

📍 {property_address}
💰 ${sale_price:,}
"""

        if days_on_market > 0:
            content += f"⏱️ {days_on_market} Days on Market\n"

        if client_name:
            content += f"\nCongratulations to our amazing clients! 🏡🔑\n"
        else:
            content += "\nAnother happy homeowner! 🏡🔑\n"

        content += """
Thinking of selling? Let's talk about what your home is worth!
📱 Call/text us today!
"""

        hashtags = [
            "JustSold", "Sold", "RealEstate", "ClosingDay",
            "NewHomeowner", "ColumbusRealtor", "OhioRealEstate",
            "TDRealty", "RealEstateAgent", "HomeSweetHome"
        ]

        return self.create_post(
            content=content,
            post_type=PostType.JUST_SOLD,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=hashtags,
            media_urls=[photo_url] if photo_url else [],
            property_id=property_id,
            property_address=property_address
        )

    def create_open_house_post(
        self,
        property_address: str,
        date: datetime,
        start_time: str,
        end_time: str,
        price: int,
        photo_url: str = "",
        property_id: str = ""
    ) -> SocialPost:
        """Create an open house announcement post."""
        date_str = date.strftime("%A, %B %d")

        content = f"""🏠 OPEN HOUSE 🏠

📍 {property_address}
📅 {date_str}
⏰ {start_time} - {end_time}
💰 ${price:,}

Stop by and tour this beautiful home!
No appointment necessary. See you there! 👋

Save the date and share with friends! 🏡
"""

        hashtags = [
            "OpenHouse", "OpenHouseWeekend", "HomeTour", "RealEstate",
            "ColumbusOH", "HouseHunting", "DreamHome", "ForSale",
            "TDRealty", "ComeOnIn"
        ]

        return self.create_post(
            content=content,
            post_type=PostType.OPEN_HOUSE,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=hashtags,
            media_urls=[photo_url] if photo_url else [],
            property_id=property_id,
            property_address=property_address,
            scheduled_time=date - timedelta(days=2)  # Post 2 days before
        )

    def publish_post(self, post_id: str) -> Dict[str, Any]:
        """Publish a post to all platforms."""
        post = self.posts.get(post_id)
        if not post:
            return {"error": "Post not found"}

        post.status = PostStatus.PUBLISHING
        results = {}

        for platform in post.platforms:
            try:
                result = self._publish_to_platform(post, platform)
                results[platform.value] = result

                if result.get("success"):
                    post.published_times[platform.value] = datetime.now()

            except Exception as e:
                logger.error(f"Error publishing to {platform.value}: {e}")
                results[platform.value] = {"success": False, "error": str(e)}

        # Update status
        if all(r.get("success") for r in results.values()):
            post.status = PostStatus.PUBLISHED
        elif any(r.get("success") for r in results.values()):
            post.status = PostStatus.PUBLISHED  # Partial success
        else:
            post.status = PostStatus.FAILED

        self._save_data()

        return {
            "post_id": post_id,
            "status": post.status.value,
            "results": results
        }

    def _publish_to_platform(self, post: SocialPost, platform: Platform) -> Dict[str, Any]:
        """Publish to a specific platform."""
        # Get platform-specific content or use default
        content = post.platform_content.get(platform.value, post.content)

        # Add hashtags
        if post.hashtags:
            hashtag_str = " ".join(f"#{tag}" for tag in post.hashtags)
            if platform in [Platform.INSTAGRAM, Platform.TWITTER]:
                content = f"{content}\n\n{hashtag_str}"

        # Platform-specific publishing
        if platform == Platform.FACEBOOK:
            return self._publish_to_facebook(content, post.media_urls, post.link_url)
        elif platform == Platform.INSTAGRAM:
            return self._publish_to_instagram(content, post.media_urls)
        elif platform == Platform.TWITTER:
            return self._publish_to_twitter(content, post.media_urls)
        elif platform == Platform.LINKEDIN:
            return self._publish_to_linkedin(content, post.media_urls, post.link_url)
        else:
            return {"success": False, "error": f"Platform {platform.value} not implemented"}

    def _publish_to_facebook(self, content: str, media_urls: List[str], link_url: str) -> Dict[str, Any]:
        """Publish to Facebook."""
        # Would integrate with Facebook Graph API
        logger.info(f"Publishing to Facebook: {content[:50]}...")

        # Simulated success
        return {
            "success": True,
            "platform": "facebook",
            "post_id": f"fb_{uuid.uuid4().hex[:8]}",
            "url": f"https://facebook.com/post/{uuid.uuid4().hex[:8]}"
        }

    def _publish_to_instagram(self, content: str, media_urls: List[str]) -> Dict[str, Any]:
        """Publish to Instagram."""
        if not media_urls:
            return {"success": False, "error": "Instagram requires at least one image"}

        # Would integrate with Instagram API
        logger.info(f"Publishing to Instagram: {content[:50]}...")

        return {
            "success": True,
            "platform": "instagram",
            "post_id": f"ig_{uuid.uuid4().hex[:8]}",
            "url": f"https://instagram.com/p/{uuid.uuid4().hex[:8]}"
        }

    def _publish_to_twitter(self, content: str, media_urls: List[str]) -> Dict[str, Any]:
        """Publish to Twitter/X."""
        # Check character limit
        if len(content) > 280:
            content = content[:277] + "..."

        # Would integrate with Twitter API
        logger.info(f"Publishing to Twitter: {content[:50]}...")

        return {
            "success": True,
            "platform": "twitter",
            "tweet_id": f"tw_{uuid.uuid4().hex[:8]}",
            "url": f"https://twitter.com/user/status/{uuid.uuid4().hex[:8]}"
        }

    def _publish_to_linkedin(self, content: str, media_urls: List[str], link_url: str) -> Dict[str, Any]:
        """Publish to LinkedIn."""
        # Would integrate with LinkedIn API
        logger.info(f"Publishing to LinkedIn: {content[:50]}...")

        return {
            "success": True,
            "platform": "linkedin",
            "post_id": f"li_{uuid.uuid4().hex[:8]}",
            "url": f"https://linkedin.com/posts/{uuid.uuid4().hex[:8]}"
        }

    def schedule_post(self, post_id: str, scheduled_time: datetime) -> bool:
        """Schedule a post for later publishing."""
        post = self.posts.get(post_id)
        if not post:
            return False

        post.scheduled_time = scheduled_time
        post.status = PostStatus.SCHEDULED
        self._save_data()

        return True

    def get_scheduled_posts(self) -> List[SocialPost]:
        """Get all scheduled posts."""
        return [
            p for p in self.posts.values()
            if p.status == PostStatus.SCHEDULED and p.scheduled_time
        ]

    def get_due_posts(self) -> List[SocialPost]:
        """Get posts due for publishing."""
        now = datetime.now()
        return [
            p for p in self.posts.values()
            if p.status == PostStatus.SCHEDULED
            and p.scheduled_time
            and p.scheduled_time <= now
        ]

    def process_scheduled_posts(self) -> Dict[str, Any]:
        """Process all due scheduled posts."""
        due_posts = self.get_due_posts()
        results = {
            "processed": 0,
            "published": 0,
            "failed": 0,
            "details": []
        }

        for post in due_posts:
            result = self.publish_post(post.id)
            results["processed"] += 1

            if post.status == PostStatus.PUBLISHED:
                results["published"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "post_id": post.id,
                "status": post.status.value
            })

        return results

    def update_engagement(self, post_id: str, platform: str, engagement: Dict[str, int]) -> bool:
        """Update engagement metrics for a post."""
        post = self.posts.get(post_id)
        if not post:
            return False

        post.engagement[platform] = engagement
        self._save_data()
        return True

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get social media analytics."""
        cutoff = datetime.now() - timedelta(days=days)

        recent_posts = [
            p for p in self.posts.values()
            if p.created_at >= cutoff
        ]

        total_engagement = {
            "likes": 0,
            "comments": 0,
            "shares": 0
        }

        by_platform = {}
        by_type = {}

        for post in recent_posts:
            # Aggregate engagement
            for platform, metrics in post.engagement.items():
                total_engagement["likes"] += metrics.get("likes", 0)
                total_engagement["comments"] += metrics.get("comments", 0)
                total_engagement["shares"] += metrics.get("shares", 0)

                if platform not in by_platform:
                    by_platform[platform] = {"posts": 0, "engagement": 0}
                by_platform[platform]["posts"] += 1
                by_platform[platform]["engagement"] += sum(metrics.values())

            # By post type
            post_type = post.post_type.value
            if post_type not in by_type:
                by_type[post_type] = 0
            by_type[post_type] += 1

        return {
            "period_days": days,
            "total_posts": len(recent_posts),
            "published": len([p for p in recent_posts if p.status == PostStatus.PUBLISHED]),
            "scheduled": len([p for p in recent_posts if p.status == PostStatus.SCHEDULED]),
            "total_engagement": total_engagement,
            "by_platform": by_platform,
            "by_type": by_type,
            "avg_engagement_per_post": sum(total_engagement.values()) / len(recent_posts) if recent_posts else 0
        }
