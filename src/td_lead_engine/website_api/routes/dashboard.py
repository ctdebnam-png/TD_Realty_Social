"""Dashboard-specific API routes for lead management."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..services.leads import LeadService

router = APIRouter(prefix="/v1/leads", tags=["dashboard"])


@router.get("")
async def list_leads(
    source: Optional[str] = None,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    utm_campaign: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
):
    """List leads with filtering."""
    service = LeadService()
    return service.list_leads(
        source=source,
        tier=tier,
        status=status,
        utm_campaign=utm_campaign,
        limit=limit,
        offset=offset,
    )


@router.get("/{lead_id}")
async def get_lead(lead_id: int):
    """Get single lead with full details."""
    service = LeadService()
    result = service.get_lead_detail(lead_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/{lead_id}/events")
async def get_lead_events(lead_id: int):
    """Get event timeline for a lead."""
    service = LeadService()
    return service.get_lead_events(lead_id)


@router.get("/{lead_id}/attribution")
async def get_lead_attribution(lead_id: int):
    """Get attribution data for a lead."""
    service = LeadService()
    return service.get_lead_attribution(lead_id)


@router.patch("/{lead_id}/status")
async def update_status(lead_id: int, payload: dict):
    """Update lead status."""
    valid_statuses = [
        "new", "contacted", "responded", "qualified",
        "nurturing", "appointment", "under_contract",
        "converted", "closed", "lost", "archived",
    ]
    status = payload.get("status")
    if status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")
    service = LeadService()
    return service.update_status(lead_id, status)


@router.post("/{lead_id}/notes")
async def add_note(lead_id: int, payload: dict):
    """Add a note to a lead."""
    note = payload.get("note", "").strip()
    if not note:
        raise HTTPException(400, "Note cannot be empty")
    service = LeadService()
    return service.add_note(lead_id, note)
