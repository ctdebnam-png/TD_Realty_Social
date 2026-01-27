"""Storage layer for leads database."""

from .database import LeadDatabase
from .models import Lead, LeadStatus, InteractionType

__all__ = ["LeadDatabase", "Lead", "LeadStatus", "InteractionType"]
