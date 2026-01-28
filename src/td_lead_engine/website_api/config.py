"""Environment-based configuration for the API service."""

import os
from pathlib import Path


class Settings:
    """API configuration loaded from environment variables."""

    def __init__(self):
        self.api_secret = os.getenv("TD_API_SECRET", "dev-secret-change-me")
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


settings = Settings()
