"""Website event scoring logic."""

import json
import sqlite3
from datetime import datetime, timedelta, timezone

# Event base scores
WEBSITE_EVENT_SCORES = {
    "contact_submit": 75,
    "home_value_request": 80,
    "schedule_showing": 90,
    "schedule_consultation": 85,
    "calculator_submit": 40,
    "property_inquiry": 50,
    "saved_search": 35,
    "newsletter_signup": 15,
    "blog_subscription": 10,
    "page_view": 0,
}

CALCULATOR_MODIFIERS = {
    "commission_savings": {"threshold": 5000, "bonus": 20},
    "home_value": {"threshold": 200000, "bonus": 15},
    "mortgage": {"threshold": 250000, "bonus": 10},
}

REPEAT_ENGAGEMENT_THRESHOLDS = {2: 10, 3: 20, 5: 35}


def score_website_events_for_lead(conn: sqlite3.Connection, lead_id: int) -> int:
    """Calculate website event score for a lead."""
    cursor = conn.execute(
        "SELECT * FROM lead_events WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,),
    )
    events = cursor.fetchall()
    if not events:
        return 0

    score = 0
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_count = 0

    for event in events:
        # Base event score
        event_score = WEBSITE_EVENT_SCORES.get(event["event_name"], 0)
        score += event_score

        # Calculator modifiers
        if event["event_name"] == "calculator_submit" and event["calculator_type"]:
            modifier = CALCULATOR_MODIFIERS.get(event["calculator_type"], {})
            if modifier and event["event_value"]:
                try:
                    result = json.loads(event["event_value"])
                    result_value = (
                        result.get("savings")
                        or result.get("value")
                        or result.get("amount", 0)
                    )
                    if result_value >= modifier.get("threshold", float("inf")):
                        score += modifier.get("bonus", 0)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Count recent events
        try:
            event_time = event["created_at"]
            if isinstance(event_time, str):
                event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
            if event_time > seven_days_ago:
                recent_count += 1
        except Exception:
            pass

    # Repeat engagement bonus (take highest qualifying threshold)
    engagement_bonus = 0
    for threshold, bonus in sorted(REPEAT_ENGAGEMENT_THRESHOLDS.items()):
        if recent_count >= threshold:
            engagement_bonus = bonus
    score += engagement_bonus

    return score
