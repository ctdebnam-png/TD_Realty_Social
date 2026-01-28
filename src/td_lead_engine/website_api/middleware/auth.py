"""HMAC/shared-secret authentication middleware."""

import hmac
import hashlib
from fastapi import Request, HTTPException
from ..config import settings


async def verify_signature(request: Request):
    """Validate requests using HMAC-SHA256 signature or shared secret.

    Header options (checked in order):
    1. X-TD-Signature: HMAC-SHA256 of request body using TD_API_SECRET
    2. X-TD-Secret: Direct match against TD_API_SECRET
    """
    body = await request.body()

    # Option 1: HMAC signature
    signature = request.headers.get("X-TD-Signature")
    if signature:
        expected = hmac.new(
            settings.api_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(signature, expected):
            return True

    # Option 2: Direct secret
    secret = request.headers.get("X-TD-Secret")
    if secret and hmac.compare_digest(secret, settings.api_secret):
        return True

    raise HTTPException(
        status_code=401,
        detail={"success": False, "error": "auth_error", "detail": "Invalid or missing authentication"},
    )
