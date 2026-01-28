"""Pydantic models for lead ingestion request/response."""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class EventData(BaseModel):
    form_id: Optional[str] = None
    page_path: Optional[str] = None
    referrer: Optional[str] = None
    calculator_type: Optional[str] = None
    calculator_inputs: Optional[Dict[str, Any]] = None
    calculator_result: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None


class Attribution(BaseModel):
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content: Optional[str] = None
    utm_term: Optional[str] = None
    gclid: Optional[str] = None
    msclkid: Optional[str] = None
    fbclid: Optional[str] = None
    landing_page: Optional[str] = None
    referrer: Optional[str] = None
    referrer_domain: Optional[str] = None


class SessionInfo(BaseModel):
    session_id: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None


class LeadIngestRequest(BaseModel):
    lead_id: Optional[str] = None
    timestamp: Optional[str] = None
    event_name: str = Field(
        ...,
        description="Type of event: contact_submit, calculator_submit, home_value_request, newsletter_signup, schedule_showing, schedule_consultation, page_view",
    )
    source: str = "website"
    contact: ContactInfo = ContactInfo()
    event_data: EventData = EventData()
    attribution: Attribution = Attribution()
    session: SessionInfo = SessionInfo()


class LeadIngestResponse(BaseModel):
    success: bool
    lead_id: Optional[str] = None
    is_new: Optional[bool] = None
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: str
