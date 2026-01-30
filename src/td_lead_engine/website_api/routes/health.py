"""Health check routes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "healthy", "service": "td-lead-engine-api", "version": "1.0.0"}


@router.get("/ready")
async def ready():
    """Readiness check - verifies database is accessible."""
    from ..services.ingestion import get_db_connection

    conn = None
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        return {"status": "not_ready", "detail": str(e)}
    finally:
        if conn:
            conn.close()
