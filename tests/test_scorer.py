"""Tests for the scoring engine."""

import pytest
from td_lead_engine.core.scorer import LeadScorer, ScoringResult
from td_lead_engine.core.signals import SignalCategory


class TestLeadScorer:
    """Tests for LeadScorer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = LeadScorer()

    def test_score_empty_text(self):
        """Empty text should return zero score."""
        result = self.scorer.score_text("")
        assert result.total_score == 0
        assert result.tier == "cold"
        assert len(result.matches) == 0

    def test_score_first_time_homebuyer(self):
        """First time homebuyer should score high."""
        result = self.scorer.score_text("I'm a first time homebuyer")
        assert result.total_score >= 80
        assert len(result.matches) > 0
        assert any(m.signal.phrase == "first time homebuyer" for m in result.matches)

    def test_score_preapproved(self):
        """Preapproved buyer should score high."""
        result = self.scorer.score_text("I'm preapproved for a mortgage")
        assert result.total_score >= 90
        assert any(m.signal.phrase == "preapproved" for m in result.matches)

    def test_score_seller_intent(self):
        """Seller intent should be detected."""
        result = self.scorer.score_text("What is my home worth?")
        assert result.total_score > 0
        assert SignalCategory.SELLER_ACTIVE in result.category_scores

    def test_score_negative_realtor(self):
        """Competitor/realtor should get negative score."""
        result = self.scorer.score_text("As a realtor, I specialize in luxury homes")
        assert result.total_score < 0
        assert result.tier == "negative"
        assert result.is_negative

    def test_score_location_bonus(self):
        """Central Ohio locations should add to score."""
        result = self.scorer.score_text("Looking for homes in Powell")
        assert result.total_score > 0
        assert SignalCategory.LOCATION in result.category_scores

    def test_score_multiple_signals(self):
        """Multiple signals should stack."""
        text = "First time homebuyer, preapproved, looking in Powell"
        result = self.scorer.score_text(text)
        assert result.total_score >= 150  # Should be hot
        assert result.tier == "hot"
        assert len(result.matches) >= 3

    def test_score_life_events(self):
        """Life events should be detected."""
        result = self.scorer.score_text("Getting married next year and need to buy a home")
        assert result.total_score > 0
        assert SignalCategory.LIFE_EVENT in result.category_scores

    def test_score_timeline_urgency(self):
        """Timeline signals should be detected."""
        result = self.scorer.score_text("My lease is up in March")
        assert result.total_score >= 75
        assert SignalCategory.TIMELINE in result.category_scores

    def test_tier_calculation(self):
        """Tiers should be calculated correctly."""
        # Cold
        result = self.scorer.score_text("ohio")
        assert result.tier in ["cold", "lukewarm"]

        # Hot
        result = self.scorer.score_text(
            "First time homebuyer, preapproved, ready to buy in Powell"
        )
        assert result.tier == "hot"

    def test_case_insensitive(self):
        """Scoring should be case insensitive."""
        lower = self.scorer.score_text("first time homebuyer")
        upper = self.scorer.score_text("FIRST TIME HOMEBUYER")
        mixed = self.scorer.score_text("First Time Homebuyer")
        assert lower.total_score == upper.total_score == mixed.total_score

    def test_score_lead_multiple_sources(self):
        """Scoring should combine multiple text sources."""
        result = self.scorer.score_lead(
            notes="Looking for a house",
            bio="First time buyer",
            messages=["I'm preapproved"]
        )
        assert result.total_score > 0
        assert len(result.matches) >= 2


class TestScoringResult:
    """Tests for ScoringResult class."""

    def test_tier_assignment(self):
        """Tiers should be assigned based on score."""
        assert ScoringResult(total_score=200).tier == "hot"
        assert ScoringResult(total_score=150).tier == "hot"
        assert ScoringResult(total_score=100).tier == "warm"
        assert ScoringResult(total_score=75).tier == "warm"
        assert ScoringResult(total_score=50).tier == "lukewarm"
        assert ScoringResult(total_score=25).tier == "lukewarm"
        assert ScoringResult(total_score=10).tier == "cold"
        assert ScoringResult(total_score=-50).tier == "negative"

    def test_is_negative(self):
        """Negative flag should be set for negative scores."""
        assert ScoringResult(total_score=-1).is_negative
        assert not ScoringResult(total_score=0).is_negative
        assert not ScoringResult(total_score=100).is_negative
