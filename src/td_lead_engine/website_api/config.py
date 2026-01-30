"""Environment-based configuration for the API service."""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class Settings:
    """API configuration loaded from environment variables."""

    def __init__(self):
        self.api_secret = os.getenv("TD_API_SECRET", "")
        if not self.api_secret:
            raise RuntimeError(
                "TD_API_SECRET environment variable is required. "
                "Generate one with: openssl rand -hex 32"
            )
        self.host = os.getenv("TD_API_HOST", "0.0.0.0")
        self.port = int(os.getenv("TD_API_PORT", "8000"))
        self.db_path = os.getenv(
            "TD_DATABASE_PATH",
            str(Path.home() / ".td-lead-engine" / "leads.db"),
        )
        self.notifications_enabled = (
            os.getenv("TD_NOTIFICATIONS_ENABLED", "false").lower() == "true"
        )
        self.debug = os.getenv("TD_ENGINE_ENV", "production") != "production"

        # CORS
        self.allowed_origins = [
            "https://tdrealtyohio.com",
            "https://www.tdrealtyohio.com",
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

        # Rate limiting
        self.rate_limit_per_minute = int(os.getenv("TD_RATE_LIMIT", "100"))


_settings = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


class _SettingsProxy:
    """Lazy proxy so settings aren't loaded until first access."""

    def __getattr__(self, name):
        return getattr(_get_settings(), name)


settings = _SettingsProxy()
