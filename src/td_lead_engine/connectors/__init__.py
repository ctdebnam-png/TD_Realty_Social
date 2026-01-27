"""Connectors for importing leads from various sources."""

from .base import BaseConnector, ImportResult, RawLead
from .instagram import InstagramConnector
from .facebook import FacebookConnector
from .csv_import import CSVConnector, ManualConnector
from .zillow import ZillowConnector, RealtorDotComConnector, HomesDotComConnector
from .google import (
    GoogleBusinessConnector,
    GoogleContactsConnector,
    GoogleFormsConnector,
    GoogleAdsConnector,
)
from .linkedin import LinkedInConnector, SalesNavigatorConnector
from .nextdoor import NextdoorConnector

# Connector registry for CLI/API
CONNECTORS = {
    "instagram": InstagramConnector,
    "facebook": FacebookConnector,
    "csv": CSVConnector,
    "manual": ManualConnector,
    "zillow": ZillowConnector,
    "realtor.com": RealtorDotComConnector,
    "homes.com": HomesDotComConnector,
    "google_business": GoogleBusinessConnector,
    "google_contacts": GoogleContactsConnector,
    "google_forms": GoogleFormsConnector,
    "google_ads": GoogleAdsConnector,
    "linkedin": LinkedInConnector,
    "sales_navigator": SalesNavigatorConnector,
    "nextdoor": NextdoorConnector,
}


def get_connector(source: str) -> BaseConnector:
    """Get a connector instance by source name."""
    if source not in CONNECTORS:
        raise ValueError(f"Unknown source: {source}. Available: {list(CONNECTORS.keys())}")
    return CONNECTORS[source]()


__all__ = [
    "BaseConnector",
    "ImportResult",
    "RawLead",
    "InstagramConnector",
    "FacebookConnector",
    "CSVConnector",
    "ManualConnector",
    "ZillowConnector",
    "RealtorDotComConnector",
    "HomesDotComConnector",
    "GoogleBusinessConnector",
    "GoogleContactsConnector",
    "GoogleFormsConnector",
    "GoogleAdsConnector",
    "LinkedInConnector",
    "SalesNavigatorConnector",
    "NextdoorConnector",
    "CONNECTORS",
    "get_connector",
]
