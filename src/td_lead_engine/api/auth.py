"""API authentication and authorization."""

import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from flask import request, jsonify, g

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manage API keys for authentication."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize API key manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "api_keys.json"
        self.keys: Dict[str, Dict[str, Any]] = {}
        self._load_keys()

    def _load_keys(self):
        """Load API keys from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    self.keys = json.load(f)
            except Exception as e:
                logger.error(f"Error loading API keys: {e}")
                self.keys = {}

    def _save_keys(self):
        """Save API keys to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_path, 'w') as f:
            json.dump(self.keys, f, indent=2)

    def generate_key(
        self,
        name: str,
        scopes: List[str] = None,
        expires_days: Optional[int] = None,
        rate_limit: int = 1000
    ) -> Dict[str, str]:
        """Generate a new API key."""
        # Generate secure key
        key_id = secrets.token_hex(8)
        key_secret = secrets.token_hex(32)

        # Hash the secret for storage
        key_hash = hashlib.sha256(key_secret.encode()).hexdigest()

        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

        self.keys[key_id] = {
            "name": name,
            "key_hash": key_hash,
            "scopes": scopes or ["read"],
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "rate_limit": rate_limit,
            "request_count": 0,
            "last_used": None,
            "active": True
        }

        self._save_keys()

        # Return full key (only time it's visible)
        return {
            "key_id": key_id,
            "key_secret": key_secret,
            "full_key": f"td_{key_id}_{key_secret}",
            "name": name,
            "scopes": scopes or ["read"],
            "expires_at": expires_at
        }

    def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its metadata."""
        try:
            # Parse key format: td_<key_id>_<key_secret>
            if not api_key.startswith("td_"):
                return None

            parts = api_key.split("_")
            if len(parts) != 3:
                return None

            key_id = parts[1]
            key_secret = parts[2]

            if key_id not in self.keys:
                return None

            key_data = self.keys[key_id]

            # Check if active
            if not key_data.get("active", True):
                return None

            # Check expiration
            if key_data.get("expires_at"):
                expires = datetime.fromisoformat(key_data["expires_at"])
                if datetime.now() > expires:
                    return None

            # Verify secret
            key_hash = hashlib.sha256(key_secret.encode()).hexdigest()
            if key_hash != key_data["key_hash"]:
                return None

            # Update usage stats
            key_data["request_count"] = key_data.get("request_count", 0) + 1
            key_data["last_used"] = datetime.now().isoformat()
            self._save_keys()

            return {
                "key_id": key_id,
                "name": key_data["name"],
                "scopes": key_data["scopes"],
                "rate_limit": key_data.get("rate_limit", 1000)
            }

        except Exception as e:
            logger.error(f"Key validation error: {e}")
            return None

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key."""
        if key_id in self.keys:
            self.keys[key_id]["active"] = False
            self._save_keys()
            return True
        return False

    def list_keys(self) -> List[Dict[str, Any]]:
        """List all API keys (without secrets)."""
        return [
            {
                "key_id": key_id,
                "name": data["name"],
                "scopes": data["scopes"],
                "created_at": data["created_at"],
                "expires_at": data.get("expires_at"),
                "active": data.get("active", True),
                "request_count": data.get("request_count", 0),
                "last_used": data.get("last_used")
            }
            for key_id, data in self.keys.items()
        ]


# Global key manager instance
_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Get the global API key manager."""
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager


def generate_api_key(
    name: str,
    scopes: List[str] = None,
    expires_days: Optional[int] = None
) -> Dict[str, str]:
    """Generate a new API key."""
    return get_key_manager().generate_key(name, scopes, expires_days)


def require_api_key(scopes: List[str] = None):
    """Decorator to require API key authentication."""
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get API key from header or query param
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                api_key = request.args.get("api_key")

            if not api_key:
                return jsonify({
                    "error": "API key required",
                    "message": "Provide API key via X-API-Key header or api_key query parameter"
                }), 401

            # Validate key
            key_data = get_key_manager().validate_key(api_key)
            if not key_data:
                return jsonify({
                    "error": "Invalid API key",
                    "message": "The provided API key is invalid or expired"
                }), 401

            # Check scopes if required
            if scopes:
                key_scopes = key_data.get("scopes", [])
                if not any(s in key_scopes for s in scopes) and "admin" not in key_scopes:
                    return jsonify({
                        "error": "Insufficient permissions",
                        "message": f"This endpoint requires one of: {scopes}"
                    }), 403

            # Store key data in request context
            g.api_key = key_data

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_webhook_signature(secret_env_var: str = "WEBHOOK_SECRET"):
    """Decorator to require webhook signature verification."""
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            secret = os.environ.get(secret_env_var)
            if not secret:
                # No secret configured, skip verification
                return f(*args, **kwargs)

            signature = request.headers.get("X-Webhook-Signature")
            if not signature:
                return jsonify({"error": "Missing webhook signature"}), 401

            # Calculate expected signature
            payload = request.get_data()
            expected = hmac.new(
                secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()

            expected_sig = f"sha256={expected}"

            if not hmac.compare_digest(signature, expected_sig):
                return jsonify({"error": "Invalid webhook signature"}), 401

            return f(*args, **kwargs)

        return decorated_function
    return decorator


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self):
        """Initialize rate limiter."""
        self.requests: Dict[str, List[datetime]] = {}
        self.window_seconds = 60

    def is_allowed(self, key_id: str, limit: int) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)

        if key_id not in self.requests:
            self.requests[key_id] = []

        # Clean old requests
        self.requests[key_id] = [
            t for t in self.requests[key_id]
            if t > window_start
        ]

        # Check limit
        if len(self.requests[key_id]) >= limit:
            return False

        # Record request
        self.requests[key_id].append(now)
        return True

    def get_remaining(self, key_id: str, limit: int) -> int:
        """Get remaining requests in window."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)

        if key_id not in self.requests:
            return limit

        recent = [t for t in self.requests[key_id] if t > window_start]
        return max(0, limit - len(recent))


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit():
    """Decorator to apply rate limiting."""
    def decorator(f: Callable):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key_data = getattr(g, 'api_key', None)
            if not key_data:
                return f(*args, **kwargs)

            key_id = key_data.get("key_id", "anonymous")
            limit = key_data.get("rate_limit", 1000)

            limiter = get_rate_limiter()
            if not limiter.is_allowed(key_id, limit):
                remaining = limiter.get_remaining(key_id, limit)
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit}/minute",
                    "remaining": remaining
                }), 429

            return f(*args, **kwargs)

        return decorated_function
    return decorator
