"""Lead validation and spam detection."""

import re
import uuid
from datetime import datetime, timezone

DISPOSABLE_DOMAINS = {
    "mailinator.com", "tempmail.com", "throwaway.email",
    "guerrillamail.com", "10minutemail.com", "fakeinbox.com",
    "yopmail.com", "sharklasers.com", "guerrillamailblock.com",
    "grr.la", "dispostable.com", "trashmail.com",
}

SPAM_PHRASES = [
    "bitcoin", "cryptocurrency", "forex trading",
    "click here now", "act fast", "limited time",
    "make money fast", "work from home opportunity",
    "nigerian prince", "wire transfer",
]


def validate_and_normalize(payload: dict) -> dict:
    """Validate and normalize an ingestion payload.

    Raises ValueError for spam or invalid data.
    """
    # Generate ID if missing
    if not payload.get("lead_id"):
        payload["lead_id"] = str(uuid.uuid4())

    # Set timestamp if missing
    if not payload.get("timestamp"):
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()

    # Require at least email or phone
    contact = payload.get("contact", {})
    email = contact.get("email", "")
    phone = contact.get("phone", "")

    if not email and not phone:
        raise ValueError("At least one of contact.email or contact.phone is required")

    # Validate email format and domain
    if email:
        email = email.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise ValueError("Invalid email format")
        domain = email.split("@")[-1]
        if domain in DISPOSABLE_DOMAINS:
            raise ValueError("Disposable email addresses not accepted")
        contact["email"] = email

    # Validate phone
    if phone:
        digits = re.sub(r"\D", "", phone)
        if digits and len(set(digits)) == 1:
            raise ValueError("Invalid phone number")
        if digits and len(digits) < 7:
            raise ValueError("Phone number too short")

    # Validate event_name
    valid_events = {
        "contact_submit", "calculator_submit", "home_value_request",
        "newsletter_signup", "schedule_showing", "schedule_consultation",
        "page_view", "property_inquiry", "saved_search", "blog_subscription",
    }
    if payload.get("event_name") not in valid_events:
        raise ValueError(f"Invalid event_name. Must be one of: {', '.join(sorted(valid_events))}")

    # Sanitize message
    event_data = payload.get("event_data", {})
    message = event_data.get("message", "")
    if message:
        # Strip HTML
        message = re.sub(r"<[^>]+>", "", message)
        # Normalize whitespace
        message = re.sub(r"\s+", " ", message).strip()
        # Check for spam
        message_lower = message.lower()
        for phrase in SPAM_PHRASES:
            if phrase in message_lower:
                raise ValueError("Message flagged as potential spam")
        # Check for excessive URLs
        url_count = len(re.findall(r"https?://", message))
        if url_count > 5:
            raise ValueError("Message contains too many URLs")
        # Limit length
        event_data["message"] = message[:2000]

    # Sanitize name fields
    for field in ("first_name", "last_name"):
        val = contact.get(field, "")
        if val:
            val = re.sub(r"<[^>]+>", "", val).strip()[:100]
            contact[field] = val

    return payload
