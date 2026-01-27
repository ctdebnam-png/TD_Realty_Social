"""Automated prospecting engine - finds leads from public data sources."""

from .sources import DataSourceManager
from .signals import SignalDetector, LeadSignal
from .scoring import ProspectScorer
from .pipeline import ProspectPipeline
from .fsbo import FSBOCollector
from .expired import ExpiredListingCollector
from .distressed import DistressedPropertyCollector
from .absentee import AbsenteeOwnerCollector
from .equity import HighEquityCollector
from .life_events import LifeEventCollector

__all__ = [
    'DataSourceManager',
    'SignalDetector',
    'LeadSignal',
    'ProspectScorer',
    'ProspectPipeline',
    'FSBOCollector',
    'ExpiredListingCollector',
    'DistressedPropertyCollector',
    'AbsenteeOwnerCollector',
    'HighEquityCollector',
    'LifeEventCollector'
]
