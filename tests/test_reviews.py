"""Tests for review collection functionality."""

import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from td_lead_engine.reviews import (
    ReviewCollector,
    Review,
    ReviewRequest,
    ReviewPublisher,
)
from td_lead_engine.reviews.collector import ReviewStatus, ReviewSource


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def review_collector(temp_data_dir):
    """Create review collector with temp storage."""
    return ReviewCollector(data_path=temp_data_dir / "reviews.json")


@pytest.fixture
def review_publisher(temp_data_dir):
    """Create review publisher with temp storage."""
    return ReviewPublisher(config_path=temp_data_dir / "publisher.json")


class TestReviewCollector:
    """Tests for ReviewCollector."""

    def test_request_review(self, review_collector):
        """Test requesting a review."""
        request = review_collector.request_review(
            client_id="client123",
            client_name="John Buyer",
            client_email="john@example.com",
            transaction_id="txn123",
            property_address="123 Main St",
            transaction_type="buyer"
        )

        assert request is not None
        assert request.client_name == "John Buyer"
        assert request.access_token != ""

    def test_submit_review(self, review_collector):
        """Test submitting a review."""
        request = review_collector.request_review(
            client_id="client123",
            client_name="John Buyer",
            client_email="john@example.com"
        )

        review = review_collector.submit_review(
            access_token=request.access_token,
            rating=5,
            content="Amazing experience! The agent was very helpful.",
            title="Best Realtor Ever",
            highlights=["Excellent communication", "Very knowledgeable"],
            display_name="John B."
        )

        assert review is not None
        assert review.rating == 5
        assert review.display_name == "John B."

    def test_submit_review_invalid_token(self, review_collector):
        """Test submitting with invalid token."""
        review = review_collector.submit_review(
            access_token="invalid_token",
            rating=5,
            content="Great service!"
        )

        assert review is None

    def test_submit_review_invalid_rating(self, review_collector):
        """Test submitting with invalid rating."""
        request = review_collector.request_review(
            client_id="client123",
            client_name="John Buyer",
            client_email="john@example.com"
        )

        review = review_collector.submit_review(
            access_token=request.access_token,
            rating=6,  # Invalid
            content="Great service!"
        )

        assert review is None

    def test_add_external_review(self, review_collector):
        """Test adding external review."""
        review = review_collector.add_external_review(
            client_name="Jane Customer",
            rating=5,
            content="Found this review on Google",
            source=ReviewSource.GOOGLE,
            external_url="https://google.com/review/123"
        )

        assert review is not None
        assert review.source == ReviewSource.GOOGLE
        assert review.status == ReviewStatus.APPROVED

    def test_approve_review(self, review_collector):
        """Test approving a review."""
        request = review_collector.request_review(
            client_id="client123",
            client_name="John",
            client_email="john@example.com"
        )

        review = review_collector.submit_review(
            access_token=request.access_token,
            rating=5,
            content="Great service!"
        )

        result = review_collector.approve_review(review.id)
        assert result is True

        # Check status
        updated = review_collector.get_review(review.id)
        assert updated.status == ReviewStatus.APPROVED

    def test_get_review_statistics(self, review_collector):
        """Test review statistics."""
        # Add some reviews
        for i in range(5):
            review_collector.add_external_review(
                client_name=f"Customer {i}",
                rating=5 if i < 3 else 4,
                content="Great!",
                source=ReviewSource.GOOGLE
            )

        stats = review_collector.get_review_statistics()

        assert stats["total_reviews"] == 5
        assert stats["average_rating"] == 4.6
        assert stats["five_star_count"] == 3

    def test_get_featured_testimonials(self, review_collector):
        """Test getting featured testimonials."""
        # Add reviews with varying quality
        review_collector.add_external_review(
            client_name="Good Customer",
            rating=5,
            content="This is a long enough review to be featured. " * 3,
            source=ReviewSource.GOOGLE
        )

        review_collector.add_external_review(
            client_name="Short Review",
            rating=5,
            content="Good",  # Too short
            source=ReviewSource.GOOGLE
        )

        featured = review_collector.get_featured_testimonials(count=5)

        # Only long enough reviews should be featured
        assert len(featured) == 1
        assert featured[0]["name"] == "Good Customer"


class TestReviewPublisher:
    """Tests for ReviewPublisher."""

    def test_create_social_post(self, review_publisher):
        """Test creating social media posts from review."""
        review = Review(
            id="rev123",
            client_id="client123",
            client_name="John Smith",
            rating=5,
            content="Amazing experience working with TD Realty!",
            display_name="John S.",
            transaction_type="buyer"
        )

        posts = review_publisher.create_social_post(review)

        assert "instagram" in posts
        assert "facebook" in posts
        assert "twitter" in posts
        assert "linkedin" in posts

        # Should contain rating stars
        assert "⭐" in posts["instagram"]

    def test_request_google_review(self, review_publisher):
        """Test generating Google review request."""
        review = Review(
            id="rev123",
            client_id="client123",
            client_name="John Smith",
            rating=5,
            content="Great experience!",
            display_name="John"
        )

        result = review_publisher.request_google_review(review)

        assert "email_content" in result
        assert "review_url" in result
        assert "John" in result["email_content"]

    def test_publish_to_website(self, review_publisher):
        """Test publishing to website."""
        review = Review(
            id="rev123",
            client_id="client123",
            client_name="John Smith",
            rating=5,
            content="Great experience!",
            display_name="John S.",
            can_use_website=True
        )

        result = review_publisher.publish_to_website(review)

        assert result["success"] is True
        assert result["platform"] == "website"
        assert "data" in result

    def test_generate_review_graphics(self, review_publisher):
        """Test generating graphics data."""
        review = Review(
            id="rev123",
            client_id="client123",
            client_name="John Smith",
            rating=5,
            content="Amazing experience!",
            display_name="John S."
        )

        graphics = review_publisher.generate_review_graphics(review)

        assert "instagram_square" in graphics
        assert "facebook_landscape" in graphics
        assert "story" in graphics
