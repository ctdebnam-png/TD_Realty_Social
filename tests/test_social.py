"""Tests for social media functionality."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from td_lead_engine.social import (
    SocialPoster,
    SocialPost,
    Platform,
    ContentGenerator,
    SocialScheduler,
)
from td_lead_engine.social.poster import PostType, PostStatus


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def social_poster(temp_data_dir):
    """Create social poster with temp storage."""
    return SocialPoster(data_path=temp_data_dir / "social_posts.json")


@pytest.fixture
def content_generator():
    """Create content generator."""
    return ContentGenerator()


@pytest.fixture
def social_scheduler(temp_data_dir):
    """Create social scheduler with temp storage."""
    poster = SocialPoster(data_path=temp_data_dir / "social_posts.json")
    return SocialScheduler(poster=poster)


class TestSocialPoster:
    """Tests for SocialPoster."""

    def test_create_post(self, social_poster):
        """Test creating a post."""
        post = social_poster.create_post(
            content="Check out this new listing!",
            post_type=PostType.NEW_LISTING,
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM],
            hashtags=["NewListing", "RealEstate"],
            property_address="123 Main St"
        )

        assert post is not None
        assert post.post_type == PostType.NEW_LISTING
        assert Platform.FACEBOOK in post.platforms

    def test_create_listing_post(self, social_poster):
        """Test creating listing announcement."""
        post = social_poster.create_listing_post(
            property_address="123 Main St, Columbus OH",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500,
            photo_urls=["https://example.com/photo1.jpg"],
            listing_url="https://example.com/listing"
        )

        assert post is not None
        assert "350,000" in post.content
        assert "4 Beds" in post.content

    def test_create_sold_post(self, social_poster):
        """Test creating sold announcement."""
        post = social_poster.create_sold_post(
            property_address="456 Oak Ave, Dublin OH",
            sale_price=425000,
            days_on_market=14
        )

        assert post is not None
        assert "SOLD" in post.content
        assert "425,000" in post.content

    def test_schedule_post(self, social_poster):
        """Test scheduling a post."""
        post = social_poster.create_post(
            content="Scheduled post",
            post_type=PostType.TIP,
            platforms=[Platform.FACEBOOK]
        )

        scheduled_time = datetime.now() + timedelta(days=1)
        result = social_poster.schedule_post(post.id, scheduled_time)

        assert result is True

        # Check post is scheduled
        scheduled = social_poster.get_scheduled_posts()
        assert len(scheduled) == 1
        assert scheduled[0].status == PostStatus.SCHEDULED

    def test_get_due_posts(self, social_poster):
        """Test getting due posts."""
        # Create past scheduled post
        post = social_poster.create_post(
            content="Due post",
            post_type=PostType.TIP,
            platforms=[Platform.FACEBOOK],
            scheduled_time=datetime.now() - timedelta(hours=1)
        )

        due = social_poster.get_due_posts()
        assert len(due) == 1

    def test_get_analytics(self, social_poster):
        """Test getting analytics."""
        # Create some posts
        for i in range(3):
            social_poster.create_post(
                content=f"Post {i}",
                post_type=PostType.TIP if i % 2 == 0 else PostType.NEW_LISTING,
                platforms=[Platform.FACEBOOK]
            )

        analytics = social_poster.get_analytics(days=30)

        assert analytics["total_posts"] == 3
        assert "by_type" in analytics
        assert "by_platform" in analytics


class TestContentGenerator:
    """Tests for ContentGenerator."""

    def test_generate_new_listing_content(self, content_generator):
        """Test generating listing content."""
        content = content_generator.generate_new_listing_content(
            address="123 Main St, Columbus OH",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500,
            features=["Updated kitchen", "Hardwood floors", "Large backyard"]
        )

        assert "excited" in content
        assert "elegant" in content
        assert "casual" in content
        assert "professional" in content
        assert "hashtags" in content

        # Check content includes property details
        assert "350,000" in content["excited"]
        assert "4" in content["excited"]

    def test_generate_sold_content(self, content_generator):
        """Test generating sold content."""
        content = content_generator.generate_sold_content(
            address="456 Oak Ave",
            sale_price=425000,
            client_type="buyer",
            days_on_market=10,
            over_asking=True
        )

        assert "celebration" in content
        assert "grateful" in content
        assert "SOLD" in content["celebration"]

    def test_generate_open_house_content(self, content_generator):
        """Test generating open house content."""
        content = content_generator.generate_open_house_content(
            address="789 Elm St",
            date=datetime.now() + timedelta(days=3),
            start_time="1:00 PM",
            end_time="4:00 PM",
            price=300000
        )

        assert "invitation" in content
        assert "OPEN HOUSE" in content["invitation"]
        assert "1:00 PM" in content["invitation"]

    def test_generate_market_update_content(self, content_generator):
        """Test generating market update content."""
        content = content_generator.generate_market_update_content(
            area="Dublin",
            median_price=450000,
            price_change=5.2,
            days_on_market=14,
            inventory="Low"
        )

        assert "informative" in content
        assert "Dublin" in content["informative"]
        assert "450,000" in content["informative"]

    def test_generate_tip_content(self, content_generator):
        """Test generating tip content."""
        content = content_generator.generate_tip_content(category="buying")

        assert "educational" in content
        assert "title" in content
        assert "hashtags" in content

    def test_get_hashtag_suggestions(self, content_generator):
        """Test hashtag suggestions."""
        hashtags = content_generator.get_hashtag_suggestions(
            post_type="listing",
            location="columbus"
        )

        assert len(hashtags) > 0
        assert "NewListing" in hashtags or "JustListed" in hashtags


class TestSocialScheduler:
    """Tests for SocialScheduler."""

    def test_schedule_listing_announcement(self, social_scheduler):
        """Test scheduling listing announcement."""
        posts = social_scheduler.schedule_listing_announcement(
            property_address="123 Main St",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500,
            photo_urls=["https://example.com/photo.jpg"],
            platforms=[Platform.FACEBOOK, Platform.INSTAGRAM]
        )

        assert len(posts) == 2
        assert all(p.status == PostStatus.SCHEDULED for p in posts)

    def test_schedule_open_house_series(self, social_scheduler):
        """Test scheduling open house post series."""
        open_house_date = datetime.now() + timedelta(days=5)

        posts = social_scheduler.schedule_open_house_series(
            property_address="456 Oak Ave",
            open_house_date=open_house_date,
            start_time="1:00 PM",
            end_time="4:00 PM",
            price=400000
        )

        # Should create announcement, reminder, and day-of posts
        assert len(posts) == 3

    def test_create_content_calendar(self, social_scheduler):
        """Test creating content calendar."""
        calendar = social_scheduler.create_content_calendar(
            start_date=datetime.now(),
            days=14,
            posts_per_week=5
        )

        assert len(calendar) > 0
        assert all("date" in entry for entry in calendar)
        assert all("type" in entry for entry in calendar)

    def test_get_optimal_time(self, social_scheduler):
        """Test getting optimal posting time."""
        tomorrow = datetime.now() + timedelta(days=1)

        optimal = social_scheduler.get_optimal_time(Platform.INSTAGRAM, tomorrow)

        assert optimal is not None
        assert optimal.date() >= tomorrow.date()

    def test_get_posting_recommendations(self, social_scheduler):
        """Test getting posting recommendations."""
        recommendations = social_scheduler.get_posting_recommendations()

        assert "current_stats" in recommendations
        assert "recommendations" in recommendations
        assert "suggested_weekly_mix" in recommendations
