"""FastAPI application factory for the website lead ingestion API."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .middleware.cors import ALLOWED_ORIGINS
from .routes.health import router as health_router
from .routes.leads import router as leads_router
from .routes.dashboard import router as dashboard_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting TD Lead Engine API")
    # Run migrations on startup
    try:
        from ..storage.migrations import run_migrations
        run_migrations(settings.db_path)
        logger.info("Database migrations applied")
    except Exception as e:
        logger.warning(f"Migration check: {e}")

    # Start background task runner if notifications enabled
    runner = None
    if settings.notifications_enabled:
        try:
            from ..tasks.scheduler import get_task_runner
            runner = get_task_runner()
            runner.start()
            logger.info("Background task runner started")
        except Exception as e:
            logger.warning(f"Task runner failed to start: {e}")

    yield

    # Shutdown
    if runner:
        runner.stop()
    logger.info("TD Lead Engine API shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TD Lead Engine API",
        description="Website lead ingestion and CRM backend for TD Realty Ohio",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # Routes
    app.include_router(health_router)
    app.include_router(leads_router)
    app.include_router(dashboard_router)

    return app


# Module-level app instance for uvicorn
app = create_app()
