"""Tests for scheduling functionality."""

import pytest
import tempfile
from datetime import datetime, timedelta, time, date
from pathlib import Path

from td_lead_engine.scheduling import (
    ShowingScheduler,
    ShowingRequest,
    TimeSlot,
    AvailabilityManager,
    AgentAvailability,
)
from td_lead_engine.scheduling.showing_scheduler import ShowingStatus, ShowingType


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def showing_scheduler(temp_data_dir):
    """Create showing scheduler with temp storage."""
    return ShowingScheduler(data_path=temp_data_dir / "showings.json")


@pytest.fixture
def availability_manager(temp_data_dir):
    """Create availability manager with temp storage."""
    return AvailabilityManager(data_path=temp_data_dir / "availability.json")


class TestShowingScheduler:
    """Tests for ShowingScheduler."""

    def test_request_showing(self, showing_scheduler):
        """Test requesting a showing."""
        requested_time = datetime.now() + timedelta(days=1)

        showing = showing_scheduler.request_showing(
            property_id="prop123",
            property_address="123 Main St",
            buyer_name="John Buyer",
            buyer_phone="555-1234",
            buyer_email="john@example.com",
            requested_datetime=requested_time,
            buyer_agent_name="Jane Agent"
        )

        assert showing is not None
        assert showing.buyer_name == "John Buyer"
        assert showing.status == ShowingStatus.PENDING_APPROVAL

    def test_confirm_showing(self, showing_scheduler):
        """Test confirming a showing."""
        requested_time = datetime.now() + timedelta(days=1)

        showing = showing_scheduler.request_showing(
            property_id="prop123",
            property_address="123 Main St",
            buyer_name="John Buyer",
            buyer_phone="555-1234",
            buyer_email="john@example.com",
            requested_datetime=requested_time
        )

        confirmed_time = datetime.now() + timedelta(days=1, hours=2)

        result = showing_scheduler.confirm_showing(
            showing.id,
            confirmed_datetime=confirmed_time,
            lockbox_code="1234",
            access_instructions="Ring doorbell"
        )

        assert result is True

        # Check updated
        showings = showing_scheduler.get_property_showings("prop123")
        assert showings[0].status == ShowingStatus.CONFIRMED
        assert showings[0].lockbox_code == "1234"

    def test_complete_showing_with_feedback(self, showing_scheduler):
        """Test completing a showing with feedback."""
        requested_time = datetime.now() + timedelta(days=1)

        showing = showing_scheduler.request_showing(
            property_id="prop123",
            property_address="123 Main St",
            buyer_name="John Buyer",
            buyer_phone="555-1234",
            buyer_email="john@example.com",
            requested_datetime=requested_time
        )

        showing_scheduler.confirm_showing(showing.id, requested_time)

        result = showing_scheduler.complete_showing(
            showing.id,
            interest_level="very_interested",
            feedback="Buyers loved the backyard"
        )

        assert result is True

        # Check feedback recorded
        showings = showing_scheduler.get_property_showings("prop123")
        assert showings[0].feedback_received is True
        assert showings[0].interest_level == "very_interested"

    def test_check_availability(self, showing_scheduler):
        """Test checking availability."""
        # Schedule a showing
        tomorrow = datetime.now() + timedelta(days=1)
        showing = showing_scheduler.request_showing(
            property_id="prop123",
            property_address="123 Main St",
            buyer_name="John Buyer",
            buyer_phone="555-1234",
            buyer_email="john@example.com",
            requested_datetime=tomorrow.replace(hour=10, minute=0)
        )
        showing_scheduler.confirm_showing(showing.id, tomorrow.replace(hour=10, minute=0))

        # Check conflicting time
        result = showing_scheduler.check_availability(
            property_id="prop123",
            date=tomorrow,
            requested_time=time(10, 0),
            duration=30
        )

        assert result["available"] is False
        assert len(result["conflicts"]) > 0

        # Check non-conflicting time
        result = showing_scheduler.check_availability(
            property_id="prop123",
            date=tomorrow,
            requested_time=time(14, 0),
            duration=30
        )

        assert result["available"] is True

    def test_get_upcoming_showings(self, showing_scheduler):
        """Test getting upcoming showings."""
        for i in range(3):
            future_time = datetime.now() + timedelta(days=i + 1)
            showing = showing_scheduler.request_showing(
                property_id=f"prop{i}",
                property_address=f"{i} Main St",
                buyer_name=f"Buyer {i}",
                buyer_phone="555-0000",
                buyer_email=f"buyer{i}@example.com",
                requested_datetime=future_time
            )
            showing_scheduler.confirm_showing(showing.id, future_time)

        upcoming = showing_scheduler.get_upcoming_showings(days=7)
        assert len(upcoming) == 3

    def test_showing_statistics(self, showing_scheduler):
        """Test showing statistics."""
        # Create some showings with different statuses
        base_time = datetime.now() + timedelta(days=1)

        for i in range(5):
            showing = showing_scheduler.request_showing(
                property_id="prop123",
                property_address="123 Main St",
                buyer_name=f"Buyer {i}",
                buyer_phone="555-0000",
                buyer_email=f"buyer{i}@example.com",
                requested_datetime=base_time + timedelta(hours=i * 2)
            )
            showing_scheduler.confirm_showing(showing.id, base_time + timedelta(hours=i * 2))

        # Complete some
        showings = showing_scheduler.get_property_showings("prop123")
        showing_scheduler.complete_showing(showings[0].id, interest_level="interested")
        showing_scheduler.complete_showing(showings[1].id, interest_level="very_interested")
        showing_scheduler.cancel_showing(showings[2].id)

        stats = showing_scheduler.get_showing_statistics("prop123")

        assert stats["total_showings"] == 5
        assert stats["completed"] == 2
        assert stats["cancelled"] == 1


class TestAvailabilityManager:
    """Tests for AvailabilityManager."""

    def test_setup_agent(self, availability_manager):
        """Test setting up an agent."""
        agent = availability_manager.setup_agent(
            agent_id="agent001",
            agent_name="Jane Agent",
            default_schedule=True
        )

        assert agent is not None
        assert agent.agent_name == "Jane Agent"
        # Default schedule should have weekday entries
        assert 0 in agent.weekly_schedule  # Monday

    def test_book_appointment(self, availability_manager):
        """Test booking an appointment."""
        availability_manager.setup_agent("agent001", "Jane Agent")

        tomorrow = (datetime.now() + timedelta(days=1)).date()
        # Adjust to a weekday
        while tomorrow.weekday() > 4:  # Skip weekend
            tomorrow += timedelta(days=1)

        apt_id = availability_manager.book_appointment(
            agent_id="agent001",
            appointment_date=tomorrow,
            start_time=time(10, 0),
            duration=60,
            appointment_type="showing",
            client_name="John Client"
        )

        assert apt_id is not None

    def test_is_available(self, availability_manager):
        """Test availability checking."""
        availability_manager.setup_agent("agent001", "Jane Agent")

        tomorrow = (datetime.now() + timedelta(days=1)).date()
        while tomorrow.weekday() > 4:
            tomorrow += timedelta(days=1)

        # Should be available during working hours
        assert availability_manager.is_available(
            "agent001", tomorrow, time(10, 0)
        ) is True

        # Book an appointment
        availability_manager.book_appointment(
            agent_id="agent001",
            appointment_date=tomorrow,
            start_time=time(10, 0),
            duration=60,
            appointment_type="showing",
            client_name="John"
        )

        # Should not be available during booked time
        assert availability_manager.is_available(
            "agent001", tomorrow, time(10, 0)
        ) is False

        # Should be available at different time
        assert availability_manager.is_available(
            "agent001", tomorrow, time(14, 0)
        ) is True

    def test_block_date(self, availability_manager):
        """Test blocking a date."""
        availability_manager.setup_agent("agent001", "Jane Agent")

        tomorrow = (datetime.now() + timedelta(days=1)).date()

        result = availability_manager.block_date("agent001", tomorrow)
        assert result is True

        # Should not be available on blocked date
        assert availability_manager.is_available(
            "agent001", tomorrow, time(10, 0)
        ) is False

    def test_get_available_slots(self, availability_manager):
        """Test getting available slots."""
        availability_manager.setup_agent("agent001", "Jane Agent")

        tomorrow = (datetime.now() + timedelta(days=1)).date()
        while tomorrow.weekday() > 4:
            tomorrow += timedelta(days=1)

        slots = availability_manager.get_available_slots(
            "agent001",
            tomorrow,
            slot_duration=30
        )

        assert len(slots) > 0
        # All should be available initially
        assert all(slot["available"] for slot in slots)

    def test_agent_schedule(self, availability_manager):
        """Test getting agent schedule."""
        availability_manager.setup_agent("agent001", "Jane Agent")

        start = datetime.now().date()
        end = start + timedelta(days=7)

        schedule = availability_manager.get_agent_schedule("agent001", start, end)

        assert len(schedule) == 8  # 8 days
        for day in schedule:
            assert "date" in day
            assert "available" in day
            assert "appointments" in day
