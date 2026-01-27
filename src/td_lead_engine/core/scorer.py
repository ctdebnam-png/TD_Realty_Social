"""Lead scoring engine - analyzes text for buying/selling intent."""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from .signals import IntentSignal, SignalCategory, INTENT_SIGNALS


@dataclass
class SignalMatch:
    """A matched intent signal in text."""

    signal: IntentSignal
    matched_text: str
    position: int


@dataclass
class ScoringResult:
    """Result of scoring a lead's text."""

    total_score: int
    matches: List[SignalMatch] = field(default_factory=list)
    category_scores: Dict[SignalCategory, int] = field(default_factory=dict)
    tier: str = "cold"
    is_negative: bool = False

    def __post_init__(self):
        """Calculate tier based on total score."""
        if self.total_score < 0:
            self.tier = "negative"
            self.is_negative = True
        elif self.total_score >= 150:
            self.tier = "hot"
        elif self.total_score >= 75:
            self.tier = "warm"
        elif self.total_score >= 25:
            self.tier = "lukewarm"
        else:
            self.tier = "cold"

    @property
    def primary_category(self) -> Optional[SignalCategory]:
        """Get the category with highest positive score."""
        positive_cats = {k: v for k, v in self.category_scores.items() if v > 0}
        if not positive_cats:
            return None
        return max(positive_cats, key=positive_cats.get)

    @property
    def summary(self) -> str:
        """Get a human-readable summary of the scoring."""
        if not self.matches:
            return "No intent signals detected"

        parts = []
        for match in sorted(self.matches, key=lambda m: m.signal.weight, reverse=True)[:3]:
            parts.append(f'"{match.signal.phrase}" (+{match.signal.weight})')

        return ", ".join(parts)


class LeadScorer:
    """Scores leads based on intent signals in their text/notes."""

    def __init__(self, signals: Optional[List[IntentSignal]] = None):
        """Initialize with optional custom signals list."""
        self.signals = signals or INTENT_SIGNALS
        # Pre-compile regex patterns for efficiency
        self._patterns: List[Tuple[re.Pattern, IntentSignal]] = []
        for signal in self.signals:
            # Create case-insensitive pattern with word boundaries
            pattern = re.compile(
                r'\b' + re.escape(signal.phrase) + r'\b',
                re.IGNORECASE
            )
            self._patterns.append((pattern, signal))

    def score_text(self, text: str) -> ScoringResult:
        """Score a single piece of text for intent signals."""
        if not text:
            return ScoringResult(total_score=0)

        matches: List[SignalMatch] = []
        seen_phrases: set = set()  # Dedupe same phrase matches

        for pattern, signal in self._patterns:
            for match in pattern.finditer(text):
                phrase_lower = signal.phrase.lower()
                if phrase_lower not in seen_phrases:
                    seen_phrases.add(phrase_lower)
                    matches.append(SignalMatch(
                        signal=signal,
                        matched_text=match.group(),
                        position=match.start()
                    ))

        # Calculate scores
        total_score = sum(m.signal.weight for m in matches)

        # Calculate category scores
        category_scores: Dict[SignalCategory, int] = {}
        for match in matches:
            cat = match.signal.category
            category_scores[cat] = category_scores.get(cat, 0) + match.signal.weight

        result = ScoringResult(
            total_score=total_score,
            matches=matches,
            category_scores=category_scores
        )

        return result

    def score_lead(
        self,
        notes: str = "",
        bio: str = "",
        messages: Optional[List[str]] = None,
        comments: Optional[List[str]] = None
    ) -> ScoringResult:
        """Score a lead from multiple text sources."""
        all_text_parts = [notes, bio]

        if messages:
            all_text_parts.extend(messages)
        if comments:
            all_text_parts.extend(comments)

        combined_text = " ".join(filter(None, all_text_parts))
        return self.score_text(combined_text)

    def explain_score(self, result: ScoringResult) -> str:
        """Get a detailed explanation of a scoring result."""
        lines = [
            f"Total Score: {result.total_score} ({result.tier.upper()})",
            "",
            "Matched Signals:"
        ]

        if not result.matches:
            lines.append("  (none)")
        else:
            for match in sorted(result.matches, key=lambda m: m.signal.weight, reverse=True):
                sign = "+" if match.signal.weight > 0 else ""
                lines.append(
                    f"  {sign}{match.signal.weight}: \"{match.signal.phrase}\" "
                    f"[{match.signal.category.value}]"
                )

        if result.category_scores:
            lines.extend(["", "Category Breakdown:"])
            for cat, score in sorted(
                result.category_scores.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                sign = "+" if score > 0 else ""
                lines.append(f"  {cat.value}: {sign}{score}")

        return "\n".join(lines)


def quick_score(text: str) -> int:
    """Quick helper to score text and return just the score."""
    scorer = LeadScorer()
    return scorer.score_text(text).total_score
