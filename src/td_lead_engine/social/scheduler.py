"""Social media post scheduling and automation."""

import json
import logging
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

from .poster import SocialPoster, SocialPost, Platform, PostType, PostStatus
from .content_generator import ContentGenerator

logger = logging.getLogger(__name__)


class PostingFrequency(Enum):
    """Posting frequency options."""
    DAILY = "daily"
    WEEKDAYS = "weekdays"
    TWICE_WEEKLY = "twice_weekly"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class SocialScheduler:
    """Schedule and automate social media posts."""

    def __init__(self, poster: Optional[SocialPoster] = None):
        """Initialize scheduler."""
        self.poster = poster or SocialPoster()
        self.content_generator = ContentGenerator()

        # Optimal posting times by platform (local time)
        self.optimal_times = {
            Platform.FACEBOOK: [time(9, 0), time(13, 0), time(16, 0)],
            Platform.INSTAGRAM: [time(11, 0), time(14, 0), time(19, 0)],
            Platform.TWITTER: [time(8, 0), time(12, 0), time(17, 0)],
            Platform.LINKEDIN: [time(7, 30), time(12, 0), time(17, 30)],
        }

        # Best days by platform (0=Monday, 6=Sunday)
        self.best_days = {
            Platform.FACEBOOK: [1, 2, 3, 4],  # Tue-Fri
            Platform.INSTAGRAM: [0, 1, 2, 3, 4],  # Mon-Fri
            Platform.TWITTER: [1, 2, 3],  # Tue-Thu
            Platform.LINKEDIN: [1, 2, 3],  # Tue-Thu
        }

    def get_optimal_time(
        self,
        platform: Platform,
        target_date: datetime = None
    ) -> datetime:
        """Get optimal posting time for a platform."""
        if target_date is None:
            target_date = datetime.now()

        # Get available times for this platform
        times = self.optimal_times.get(platform, [time(12, 0)])

        # Pick a time that hasn't passed yet today, or the first time tomorrow
        now_time = datetime.now().time()

        for post_time in times:
            if target_date.date() > datetime.now().date() or post_time > now_time:
                return datetime.combine(target_date.date(), post_time)

        # All times passed today, use first time tomorrow
        return datetime.combine(target_date.date() + timedelta(days=1), times[0])

    def schedule_listing_announcement(
        self,
        property_address: str,
        price: int,
        beds: int,
        baths: float,
        sqft: int,
        photo_urls: List[str],
        listing_url: str = "",
        property_id: str = "",
        features: List[str] = None,
        platforms: List[Platform] = None
    ) -> List[SocialPost]:
        """Schedule listing announcement across platforms."""
        if platforms is None:
            platforms = [Platform.FACEBOOK, Platform.INSTAGRAM]

        # Generate content variations
        content = self.content_generator.generate_new_listing_content(
            address=property_address,
            price=price,
            beds=beds,
            baths=baths,
            sqft=sqft,
            features=features
        )

        posts = []
        base_time = datetime.now()

        for i, platform in enumerate(platforms):
            # Stagger posts across platforms
            post_time = self.get_optimal_time(platform, base_time + timedelta(hours=i * 2))

            # Choose content style based on platform
            if platform == Platform.LINKEDIN:
                post_content = content["professional"]
            elif platform == Platform.INSTAGRAM:
                post_content = content["excited"]
            else:
                post_content = content["casual"]

            post = self.poster.create_post(
                content=post_content,
                post_type=PostType.NEW_LISTING,
                platforms=[platform],
                hashtags=content["hashtags"],
                media_urls=photo_urls,
                link_url=listing_url,
                property_id=property_id,
                property_address=property_address,
                scheduled_time=post_time
            )
            posts.append(post)

        return posts

    def schedule_sold_announcement(
        self,
        property_address: str,
        sale_price: int,
        client_type: str = "buyer",
        days_on_market: int = 0,
        over_asking: bool = False,
        photo_url: str = "",
        property_id: str = "",
        platforms: List[Platform] = None
    ) -> List[SocialPost]:
        """Schedule sold announcement."""
        if platforms is None:
            platforms = [Platform.FACEBOOK, Platform.INSTAGRAM]

        content = self.content_generator.generate_sold_content(
            address=property_address,
            sale_price=sale_price,
            client_type=client_type,
            days_on_market=days_on_market,
            over_asking=over_asking
        )

        posts = []
        base_time = datetime.now()

        for i, platform in enumerate(platforms):
            post_time = self.get_optimal_time(platform, base_time + timedelta(hours=i * 2))

            post = self.poster.create_post(
                content=content["celebration"],
                post_type=PostType.JUST_SOLD,
                platforms=[platform],
                hashtags=content["hashtags"],
                media_urls=[photo_url] if photo_url else [],
                property_id=property_id,
                property_address=property_address,
                scheduled_time=post_time
            )
            posts.append(post)

        return posts

    def schedule_open_house_series(
        self,
        property_address: str,
        open_house_date: datetime,
        start_time: str,
        end_time: str,
        price: int,
        photo_url: str = "",
        property_id: str = ""
    ) -> List[SocialPost]:
        """Schedule a series of open house posts."""
        posts = []

        content = self.content_generator.generate_open_house_content(
            address=property_address,
            date=open_house_date,
            start_time=start_time,
            end_time=end_time,
            price=price
        )

        # Announcement post (3-4 days before)
        announcement_time = open_house_date - timedelta(days=3)
        announcement_time = datetime.combine(
            announcement_time.date(),
            time(10, 0)
        )

        post1 = self.poster.create_post(
            content=content["invitation"],
            post_type=PostType.OPEN_HOUSE,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=content["hashtags"],
            media_urls=[photo_url] if photo_url else [],
            property_id=property_id,
            property_address=property_address,
            scheduled_time=announcement_time
        )
        posts.append(post1)

        # Reminder post (day before)
        reminder_time = open_house_date - timedelta(days=1)
        reminder_time = datetime.combine(
            reminder_time.date(),
            time(17, 0)
        )

        post2 = self.poster.create_post(
            content=content["countdown"],
            post_type=PostType.OPEN_HOUSE,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=content["hashtags"],
            media_urls=[photo_url] if photo_url else [],
            property_id=property_id,
            property_address=property_address,
            scheduled_time=reminder_time
        )
        posts.append(post2)

        # Day-of reminder (morning of)
        dayof_time = datetime.combine(
            open_house_date.date(),
            time(9, 0)
        )

        post3 = self.poster.create_post(
            content=content["reminder"],
            post_type=PostType.OPEN_HOUSE,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=content["hashtags"],
            media_urls=[photo_url] if photo_url else [],
            property_id=property_id,
            property_address=property_address,
            scheduled_time=dayof_time
        )
        posts.append(post3)

        return posts

    def create_content_calendar(
        self,
        start_date: datetime,
        days: int = 30,
        posts_per_week: int = 5
    ) -> List[Dict[str, Any]]:
        """Create a content calendar with post suggestions."""
        calendar = []
        current_date = start_date

        # Content mix
        content_types = [
            ("tip", 2),  # 2 tips per week
            ("market_update", 1),  # 1 market update
            ("community", 1),  # 1 community post
            ("behind_scenes", 1),  # 1 behind the scenes
        ]

        week_posts = []
        for content_type, count in content_types:
            week_posts.extend([content_type] * count)

        post_index = 0

        for day in range(days):
            current_date = start_date + timedelta(days=day)

            # Skip weekends for some platforms
            if current_date.weekday() in [5, 6]:  # Saturday, Sunday
                continue

            if post_index < len(week_posts):
                content_type = week_posts[post_index]

                # Generate suggested content
                if content_type == "tip":
                    tip_category = "buying" if day % 2 == 0 else "selling"
                    suggestion = self.content_generator.generate_tip_content(tip_category)
                    calendar.append({
                        "date": current_date.isoformat(),
                        "day": current_date.strftime("%A"),
                        "type": "tip",
                        "suggested_content": suggestion["educational"],
                        "hashtags": suggestion["hashtags"],
                        "platforms": ["facebook", "instagram"]
                    })
                elif content_type == "market_update":
                    calendar.append({
                        "date": current_date.isoformat(),
                        "day": current_date.strftime("%A"),
                        "type": "market_update",
                        "suggested_content": "[Market data to be filled in]",
                        "hashtags": self.content_generator.get_hashtag_suggestions("market"),
                        "platforms": ["facebook", "linkedin"]
                    })
                elif content_type == "community":
                    calendar.append({
                        "date": current_date.isoformat(),
                        "day": current_date.strftime("%A"),
                        "type": "community",
                        "suggested_content": "Share local event, business spotlight, or neighborhood highlight",
                        "hashtags": ["ColumbusOH", "LocalBusiness", "Community"],
                        "platforms": ["facebook", "instagram"]
                    })
                elif content_type == "behind_scenes":
                    calendar.append({
                        "date": current_date.isoformat(),
                        "day": current_date.strftime("%A"),
                        "type": "behind_scenes",
                        "suggested_content": "Share day in the life, showing prep, or office moments",
                        "hashtags": ["RealtorLife", "BehindTheScenes", "RealEstateAgent"],
                        "platforms": ["instagram"]
                    })

                post_index += 1

            # Reset for next week
            if current_date.weekday() == 4:  # Friday
                post_index = 0

        return calendar

    def auto_schedule_week(
        self,
        start_date: datetime = None
    ) -> Dict[str, Any]:
        """Auto-schedule posts for the upcoming week."""
        if start_date is None:
            start_date = datetime.now()

        calendar = self.create_content_calendar(start_date, days=7, posts_per_week=5)

        scheduled = []
        for entry in calendar:
            if entry["type"] == "tip":
                # Auto-generate tip posts
                tip_content = self.content_generator.generate_tip_content()

                post = self.poster.create_post(
                    content=tip_content["educational"],
                    post_type=PostType.TIP,
                    platforms=[Platform(p) for p in entry["platforms"]],
                    hashtags=entry["hashtags"],
                    scheduled_time=datetime.fromisoformat(entry["date"]).replace(hour=10, minute=0)
                )
                scheduled.append({
                    "post_id": post.id,
                    "date": entry["date"],
                    "type": entry["type"]
                })

        return {
            "week_starting": start_date.isoformat(),
            "posts_scheduled": len(scheduled),
            "scheduled": scheduled
        }

    def get_posting_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for posting strategy."""
        analytics = self.poster.get_analytics(days=30)

        recommendations = []

        # Check posting frequency
        posts_per_week = analytics["total_posts"] / 4  # Approximate
        if posts_per_week < 3:
            recommendations.append({
                "category": "frequency",
                "priority": "high",
                "message": "Increase posting frequency to at least 3-5 times per week for better engagement."
            })
        elif posts_per_week > 10:
            recommendations.append({
                "category": "frequency",
                "priority": "medium",
                "message": "Consider reducing posting frequency to avoid audience fatigue."
            })

        # Check content mix
        by_type = analytics.get("by_type", {})
        if not by_type.get("tip") or by_type.get("tip", 0) < 2:
            recommendations.append({
                "category": "content",
                "priority": "medium",
                "message": "Add more educational tip content to provide value to your audience."
            })

        if not by_type.get("market_update"):
            recommendations.append({
                "category": "content",
                "priority": "medium",
                "message": "Share market updates to position yourself as a local expert."
            })

        # Check platform coverage
        by_platform = analytics.get("by_platform", {})
        if "instagram" not in by_platform:
            recommendations.append({
                "category": "platform",
                "priority": "high",
                "message": "Add Instagram to your social strategy - it's highly visual and popular for real estate."
            })

        if "linkedin" not in by_platform:
            recommendations.append({
                "category": "platform",
                "priority": "low",
                "message": "Consider LinkedIn for professional networking and referral opportunities."
            })

        # Engagement recommendations
        avg_engagement = analytics.get("avg_engagement_per_post", 0)
        if avg_engagement < 10:
            recommendations.append({
                "category": "engagement",
                "priority": "high",
                "message": "Try asking questions in posts, using calls-to-action, and engaging with comments to boost interaction."
            })

        return {
            "current_stats": {
                "posts_last_30_days": analytics["total_posts"],
                "avg_posts_per_week": round(posts_per_week, 1),
                "avg_engagement": round(avg_engagement, 1),
                "platforms_used": list(by_platform.keys())
            },
            "recommendations": recommendations,
            "suggested_weekly_mix": {
                "new_listings": "As available",
                "just_sold": "As available",
                "tips": 2,
                "market_updates": 1,
                "community": 1,
                "behind_scenes": 1
            }
        }
