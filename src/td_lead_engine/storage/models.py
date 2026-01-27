"""Data models for lead storage."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any


class LeadStatus(Enum):
    """Status of a lead in the pipeline."""

    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    QUALIFIED = "qualified"
    NURTURING = "nurturing"
    CONVERTED = "converted"
    LOST = "lost"
    ARCHIVED = "archived"


class InteractionType(Enum):
    """Types of interactions with leads."""

    IMPORT = "import"
    SCORED = "scored"
    CONTACTED = "contacted"
    RESPONSE = "response"
    NOTE = "note"
    STATUS_CHANGE = "status_change"


@dataclass
class Lead:
    """A scored lead in the database."""

    id: Optional[int] = None
    source: str = "manual"
    source_id: Optional[str] = None

    # Contact info
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    profile_url: Optional[str] = None

    # Content for scoring
    bio: Optional[str] = None
    notes: Optional[str] = None
    messages_json: Optional[str] = None  # JSON array of messages
    comments_json: Optional[str] = None  # JSON array of comments

    # Scoring
    score: int = 0
    tier: str = "cold"
    score_breakdown: Optional[str] = None  # JSON object

    # Status
    status: LeadStatus = LeadStatus.NEW
    tags: Optional[str] = None  # Comma-separated tags

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_scored_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None

    # Raw data
    raw_data_json: Optional[str] = None

    @property
    def display_name(self) -> str:
        """Get best available name for display."""
        return self.name or self.username or self.email or f"Lead #{self.id}"

    @property
    def contact_info(self) -> str:
        """Get primary contact info."""
        if self.phone:
            return self.phone
        if self.email:
            return self.email
        if self.username:
            return f"@{self.username}"
        return "No contact"

    def get_tags_list(self) -> List[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def set_tags_list(self, tags: List[str]):
        """Set tags from a list."""
        self.tags = ",".join(tags) if tags else None


@dataclass
class Interaction:
    """Record of an interaction with a lead."""

    id: Optional[int] = None
    lead_id: int = 0
    interaction_type: InteractionType = InteractionType.NOTE
    content: Optional[str] = None
    metadata_json: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
