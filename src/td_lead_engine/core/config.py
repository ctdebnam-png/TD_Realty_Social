"""Configurable scoring weights and ML-ready scoring configuration."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ScoringConfig:
    """Configurable scoring weights and thresholds."""

    # Tier thresholds (can be adjusted based on conversion data)
    hot_threshold: int = 150
    warm_threshold: int = 75
    lukewarm_threshold: int = 25

    # Category multipliers (for emphasizing certain signal types)
    category_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "buyer_active": 1.0,
        "buyer_passive": 1.0,
        "seller_active": 1.0,
        "seller_passive": 1.0,
        "investor": 1.0,
        "timeline": 1.2,  # Boost urgency signals
        "location": 1.0,
        "life_event": 1.1,  # Slight boost for life events
        "financial": 1.0,
        "negative": 1.0,
    })

    # Source quality multipliers (some sources produce better leads)
    source_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "instagram": 1.0,
        "facebook": 1.0,
        "linkedin": 1.1,  # Professional network
        "zillow": 1.2,  # High intent platform
        "google_ads": 1.2,  # Paid traffic = intent
        "google_forms": 1.1,  # Direct inquiry
        "google_business": 1.1,
        "nextdoor": 1.0,
        "manual": 1.0,
        "csv": 1.0,
    })

    # Signal weight adjustments (override default weights)
    signal_weight_overrides: Dict[str, int] = field(default_factory=dict)

    # Decay settings (reduce score over time without activity)
    enable_score_decay: bool = False
    decay_days: int = 30  # Days before decay starts
    decay_rate: float = 0.1  # 10% per period

    # ML model settings (for future ML integration)
    use_ml_scoring: bool = False
    ml_model_path: Optional[str] = None
    ml_weight: float = 0.5  # Blend ML score with rule-based

    # Updated timestamp
    updated_at: datetime = field(default_factory=datetime.now)


class ScoringConfigManager:
    """Manage and persist scoring configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager."""
        self.config_path = config_path or Path.home() / ".td-lead-engine" / "scoring_config.json"
        self.config = self._load_config()

    def _load_config(self) -> ScoringConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return ScoringConfig(
                        hot_threshold=data.get("hot_threshold", 150),
                        warm_threshold=data.get("warm_threshold", 75),
                        lukewarm_threshold=data.get("lukewarm_threshold", 25),
                        category_multipliers=data.get("category_multipliers", {}),
                        source_multipliers=data.get("source_multipliers", {}),
                        signal_weight_overrides=data.get("signal_weight_overrides", {}),
                        enable_score_decay=data.get("enable_score_decay", False),
                        decay_days=data.get("decay_days", 30),
                        decay_rate=data.get("decay_rate", 0.1),
                        use_ml_scoring=data.get("use_ml_scoring", False),
                        ml_model_path=data.get("ml_model_path"),
                        ml_weight=data.get("ml_weight", 0.5),
                    )
            except Exception as e:
                logger.error(f"Error loading scoring config: {e}")

        return ScoringConfig()

    def save_config(self):
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "hot_threshold": self.config.hot_threshold,
            "warm_threshold": self.config.warm_threshold,
            "lukewarm_threshold": self.config.lukewarm_threshold,
            "category_multipliers": self.config.category_multipliers,
            "source_multipliers": self.config.source_multipliers,
            "signal_weight_overrides": self.config.signal_weight_overrides,
            "enable_score_decay": self.config.enable_score_decay,
            "decay_days": self.config.decay_days,
            "decay_rate": self.config.decay_rate,
            "use_ml_scoring": self.config.use_ml_scoring,
            "ml_model_path": self.config.ml_model_path,
            "ml_weight": self.config.ml_weight,
            "updated_at": self.config.updated_at.isoformat(),
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def update_thresholds(self, hot: int, warm: int, lukewarm: int):
        """Update tier thresholds."""
        self.config.hot_threshold = hot
        self.config.warm_threshold = warm
        self.config.lukewarm_threshold = lukewarm
        self.config.updated_at = datetime.now()
        self.save_config()

    def set_category_multiplier(self, category: str, multiplier: float):
        """Set multiplier for a signal category."""
        self.config.category_multipliers[category] = multiplier
        self.config.updated_at = datetime.now()
        self.save_config()

    def set_source_multiplier(self, source: str, multiplier: float):
        """Set multiplier for a lead source."""
        self.config.source_multipliers[source] = multiplier
        self.config.updated_at = datetime.now()
        self.save_config()

    def override_signal_weight(self, phrase: str, weight: int):
        """Override weight for a specific signal phrase."""
        self.config.signal_weight_overrides[phrase] = weight
        self.config.updated_at = datetime.now()
        self.save_config()

    def get_effective_weight(self, phrase: str, default_weight: int, category: str) -> int:
        """Get effective weight for a signal considering overrides and multipliers."""
        # Check for explicit override
        if phrase in self.config.signal_weight_overrides:
            weight = self.config.signal_weight_overrides[phrase]
        else:
            weight = default_weight

        # Apply category multiplier
        multiplier = self.config.category_multipliers.get(category, 1.0)
        return int(weight * multiplier)

    def get_tier(self, score: int) -> str:
        """Get tier based on score and current thresholds."""
        if score < 0:
            return "negative"
        elif score >= self.config.hot_threshold:
            return "hot"
        elif score >= self.config.warm_threshold:
            return "warm"
        elif score >= self.config.lukewarm_threshold:
            return "lukewarm"
        else:
            return "cold"


# === Conversion Tracking for ML ===

@dataclass
class ConversionEvent:
    """Record of a lead conversion for ML training."""

    lead_id: int
    converted: bool  # Did they become a client?
    conversion_type: str  # "buyer", "seller", "investor", "referral"
    signals_at_conversion: List[str]  # What signals they had
    score_at_conversion: int
    days_to_conversion: int
    source: str
    recorded_at: datetime = field(default_factory=datetime.now)


class ConversionTracker:
    """Track conversions for ML model training."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize conversion tracker."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "conversions.json"
        self.conversions: List[ConversionEvent] = []
        self._load_data()

    def _load_data(self):
        """Load conversion data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    for conv_data in data.get("conversions", []):
                        self.conversions.append(ConversionEvent(
                            lead_id=conv_data["lead_id"],
                            converted=conv_data["converted"],
                            conversion_type=conv_data.get("conversion_type", ""),
                            signals_at_conversion=conv_data.get("signals_at_conversion", []),
                            score_at_conversion=conv_data.get("score_at_conversion", 0),
                            days_to_conversion=conv_data.get("days_to_conversion", 0),
                            source=conv_data.get("source", ""),
                        ))
            except Exception as e:
                logger.error(f"Error loading conversion data: {e}")

    def _save_data(self):
        """Save conversion data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "conversions": [
                {
                    "lead_id": c.lead_id,
                    "converted": c.converted,
                    "conversion_type": c.conversion_type,
                    "signals_at_conversion": c.signals_at_conversion,
                    "score_at_conversion": c.score_at_conversion,
                    "days_to_conversion": c.days_to_conversion,
                    "source": c.source,
                    "recorded_at": c.recorded_at.isoformat(),
                }
                for c in self.conversions
            ]
        }
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def record_conversion(
        self,
        lead_id: int,
        converted: bool,
        conversion_type: str = "",
        signals: List[str] = None,
        score: int = 0,
        days: int = 0,
        source: str = ""
    ):
        """Record a conversion (or non-conversion) event."""
        event = ConversionEvent(
            lead_id=lead_id,
            converted=converted,
            conversion_type=conversion_type,
            signals_at_conversion=signals or [],
            score_at_conversion=score,
            days_to_conversion=days,
            source=source,
        )
        self.conversions.append(event)
        self._save_data()

    def get_conversion_rate_by_tier(self) -> Dict[str, float]:
        """Calculate conversion rate by tier."""
        tier_conversions: Dict[str, List[bool]] = {}

        for conv in self.conversions:
            # Determine tier at conversion
            if conv.score_at_conversion >= 150:
                tier = "hot"
            elif conv.score_at_conversion >= 75:
                tier = "warm"
            elif conv.score_at_conversion >= 25:
                tier = "lukewarm"
            else:
                tier = "cold"

            if tier not in tier_conversions:
                tier_conversions[tier] = []
            tier_conversions[tier].append(conv.converted)

        rates = {}
        for tier, conversions in tier_conversions.items():
            if conversions:
                rates[tier] = sum(conversions) / len(conversions)
            else:
                rates[tier] = 0.0

        return rates

    def get_signal_effectiveness(self) -> Dict[str, Dict[str, Any]]:
        """Analyze which signals correlate with conversions."""
        signal_stats: Dict[str, Dict[str, int]] = {}

        for conv in self.conversions:
            for signal in conv.signals_at_conversion:
                if signal not in signal_stats:
                    signal_stats[signal] = {"converted": 0, "not_converted": 0}

                if conv.converted:
                    signal_stats[signal]["converted"] += 1
                else:
                    signal_stats[signal]["not_converted"] += 1

        # Calculate effectiveness
        effectiveness = {}
        for signal, stats in signal_stats.items():
            total = stats["converted"] + stats["not_converted"]
            if total > 0:
                effectiveness[signal] = {
                    "conversion_rate": stats["converted"] / total,
                    "total_occurrences": total,
                    "conversions": stats["converted"],
                }

        return effectiveness

    def suggest_weight_adjustments(self) -> Dict[str, int]:
        """Suggest signal weight adjustments based on conversion data."""
        effectiveness = self.get_signal_effectiveness()
        suggestions = {}

        for signal, stats in effectiveness.items():
            if stats["total_occurrences"] < 5:
                continue  # Not enough data

            rate = stats["conversion_rate"]

            # Suggest adjustments based on conversion rate
            if rate > 0.5:
                suggestions[signal] = 20  # Boost weight
            elif rate > 0.3:
                suggestions[signal] = 10  # Slight boost
            elif rate < 0.1:
                suggestions[signal] = -10  # Reduce weight

        return suggestions
