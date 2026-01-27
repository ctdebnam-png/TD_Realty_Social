"""Base connector class for lead imports."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class RawLead:
    """Raw lead data from an import source."""

    source: str  # instagram, facebook, csv, manual
    source_id: Optional[str] = None  # Unique ID from source platform
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    notes: Optional[str] = None
    messages: List[str] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)
    profile_url: Optional[str] = None
    imported_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Get best available name for display."""
        return self.name or self.username or self.email or "Unknown"

    @property
    def all_text(self) -> str:
        """Get all text content for scoring."""
        parts = [self.bio, self.notes]
        parts.extend(self.messages)
        parts.extend(self.comments)
        return " ".join(filter(None, parts))


@dataclass
class ImportResult:
    """Result of an import operation."""

    source: str
    leads: List[RawLead] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    success: bool = True

    @property
    def count(self) -> int:
        """Number of leads imported."""
        return len(self.leads)

    def add_error(self, error: str):
        """Add an error and mark as failed."""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str):
        """Add a warning (doesn't fail import)."""
        self.warnings.append(warning)


class BaseConnector(ABC):
    """Base class for all import connectors."""

    source_name: str = "unknown"

    @abstractmethod
    def import_from_path(self, path: Path) -> ImportResult:
        """Import leads from a file or directory path."""
        pass

    def validate_path(self, path: Path) -> Optional[str]:
        """Validate the import path. Returns error message or None."""
        if not path.exists():
            return f"Path does not exist: {path}"
        return None
