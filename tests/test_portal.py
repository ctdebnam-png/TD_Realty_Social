"""Tests for client portal functionality."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from td_lead_engine.portal import (
    ClientPortal,
    BuyerPortal,
    SellerPortal,
    SavedSearch,
    SavedProperty,
)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def client_portal(temp_data_dir):
    """Create client portal with temp storage."""
    return ClientPortal(data_path=temp_data_dir / "portal.json")


@pytest.fixture
def buyer_portal(temp_data_dir):
    """Create buyer portal with temp storage."""
    return BuyerPortal(data_path=temp_data_dir / "buyer_portal.json")


@pytest.fixture
def seller_portal(temp_data_dir):
    """Create seller portal with temp storage."""
    return SellerPortal(data_path=temp_data_dir / "seller_portal.json")


class TestClientPortal:
    """Tests for ClientPortal."""

    def test_create_account(self, client_portal):
        """Test account creation."""
        account = client_portal.create_account(
            client_id="test123",
            email="test@example.com",
            name="Test User",
            phone="555-1234",
            client_type="buyer"
        )

        assert account is not None
        assert account.client_id == "test123"
        assert account.email == "test@example.com"
        assert account.name == "Test User"

    def test_authenticate_valid(self, client_portal):
        """Test valid authentication."""
        # Create account
        client_portal.create_account(
            client_id="test123",
            email="test@example.com",
            name="Test User",
            password="secure123"
        )

        # Authenticate
        session = client_portal.authenticate("test@example.com", "secure123")
        assert session is not None
        assert session.client_id == "test123"

    def test_authenticate_invalid(self, client_portal):
        """Test invalid authentication."""
        client_portal.create_account(
            client_id="test123",
            email="test@example.com",
            name="Test User",
            password="secure123"
        )

        session = client_portal.authenticate("test@example.com", "wrongpassword")
        assert session is None

    def test_session_validation(self, client_portal):
        """Test session token validation."""
        client_portal.create_account(
            client_id="test123",
            email="test@example.com",
            name="Test User",
            password="secure123"
        )

        session = client_portal.authenticate("test@example.com", "secure123")
        assert client_portal.validate_session(session.token) is True
        assert client_portal.validate_session("invalid_token") is False


class TestBuyerPortal:
    """Tests for BuyerPortal."""

    def test_create_saved_search(self, buyer_portal):
        """Test creating a saved search."""
        search = buyer_portal.create_saved_search(
            client_id="buyer123",
            name="Dream Home Search",
            locations=["Columbus", "Dublin"],
            min_price=200000,
            max_price=400000,
            min_beds=3,
            min_baths=2,
            property_types=["single_family"]
        )

        assert search is not None
        assert search.name == "Dream Home Search"
        assert "Columbus" in search.locations
        assert search.min_price == 200000

    def test_save_property(self, buyer_portal):
        """Test saving a property."""
        saved = buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS123456",
            address="123 Main St",
            city="Columbus",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500
        )

        assert saved is not None
        assert saved.property_id == "MLS123456"
        assert saved.price == 350000

    def test_save_property_duplicate(self, buyer_portal):
        """Test that duplicate saves return existing."""
        saved1 = buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS123456",
            address="123 Main St",
            city="Columbus",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500
        )

        saved2 = buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS123456",
            address="123 Main St",
            city="Columbus",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500
        )

        assert saved1.id == saved2.id

    def test_rate_property(self, buyer_portal):
        """Test rating a saved property."""
        buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS123456",
            address="123 Main St",
            city="Columbus",
            price=350000,
            beds=4,
            baths=2.5,
            sqft=2500
        )

        result = buyer_portal.rate_property("buyer123", "MLS123456", 5)
        assert result is True

        # Invalid rating
        result = buyer_portal.rate_property("buyer123", "MLS123456", 6)
        assert result is False

    def test_get_favorites(self, buyer_portal):
        """Test getting favorite properties."""
        buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS1",
            address="1 Main St",
            city="Columbus",
            price=300000,
            beds=3,
            baths=2,
            sqft=2000
        )

        buyer_portal.save_property(
            client_id="buyer123",
            property_id="MLS2",
            address="2 Main St",
            city="Columbus",
            price=400000,
            beds=4,
            baths=3,
            sqft=2500
        )

        # Rate one highly
        buyer_portal.rate_property("buyer123", "MLS1", 5)

        favorites = buyer_portal.get_favorites("buyer123")
        assert len(favorites) == 1
        assert favorites[0].property_id == "MLS1"


class TestSellerPortal:
    """Tests for SellerPortal."""

    def test_add_listing(self, seller_portal):
        """Test adding a listing."""
        listing = seller_portal.add_listing(
            client_id="seller123",
            address="456 Oak Ave",
            city="Columbus",
            list_price=500000,
            beds=4,
            baths=3,
            sqft=3000,
            mls_number="MLS789"
        )

        assert listing is not None
        assert listing.address == "456 Oak Ave"
        assert listing.list_price == 500000

    def test_schedule_showing(self, seller_portal):
        """Test scheduling a showing."""
        listing = seller_portal.add_listing(
            client_id="seller123",
            address="456 Oak Ave",
            city="Columbus",
            list_price=500000
        )

        showing = seller_portal.schedule_showing(
            listing_id=listing.id,
            scheduled_time=datetime.now() + timedelta(days=1),
            buyer_agent_name="John Agent",
            buyer_agent_phone="555-9999"
        )

        assert showing is not None
        assert showing.buyer_agent_name == "John Agent"

    def test_submit_offer(self, seller_portal):
        """Test submitting an offer."""
        listing = seller_portal.add_listing(
            client_id="seller123",
            address="456 Oak Ave",
            city="Columbus",
            list_price=500000
        )

        offer = seller_portal.submit_offer(
            listing_id=listing.id,
            offer_price=490000,
            buyer_name="Jane Buyer",
            buyer_agent_name="John Agent",
            earnest_money=5000,
            financing_type="conventional"
        )

        assert offer is not None
        assert offer.offer_price == 490000
        assert offer.status == "pending"

    def test_respond_to_offer(self, seller_portal):
        """Test responding to an offer."""
        listing = seller_portal.add_listing(
            client_id="seller123",
            address="456 Oak Ave",
            city="Columbus",
            list_price=500000
        )

        offer = seller_portal.submit_offer(
            listing_id=listing.id,
            offer_price=490000,
            buyer_name="Jane Buyer"
        )

        result = seller_portal.respond_to_offer(
            listing_id=listing.id,
            offer_id=offer.id,
            response="counter",
            counter_amount=495000
        )

        assert result is True

        # Check offer was updated
        offers = seller_portal.get_listing_offers(listing.id)
        assert offers[0].status == "countered"
        assert offers[0].counter_amount == 495000
