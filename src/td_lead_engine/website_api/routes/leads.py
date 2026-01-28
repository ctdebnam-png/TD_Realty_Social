"""Lead ingestion route."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from ..middleware.auth import verify_signature
from ..schemas.lead import LeadIngestRequest, LeadIngestResponse, ErrorResponse
from ..services.ingestion import ingest_lead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/leads", tags=["leads"])


@router.post(
    "/ingest",
    response_model=LeadIngestResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def ingest(request: Request, _auth=Depends(verify_signature)):
    """Ingest a website lead event.

    Accepts contact form submissions, calculator results, home value requests,
    and other website interaction events.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "validation_error", "detail": "Invalid JSON body"},
        )

    try:
        result, is_new = ingest_lead(body)
        return LeadIngestResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"success": False, "error": "validation_error", "detail": str(e)},
        )
    except Exception as e:
        logger.exception("Lead ingestion error")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "error": "server_error", "detail": "Internal processing error"},
        )
