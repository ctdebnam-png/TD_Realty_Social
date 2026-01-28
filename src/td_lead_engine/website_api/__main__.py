"""Run with: python -m td_lead_engine.website_api"""

import uvicorn
from .main import create_app
from .config import settings

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host=settings.host, port=settings.port)
