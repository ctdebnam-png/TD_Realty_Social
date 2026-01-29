"""Lead ingestion processing logic."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from ..config import settings
from .validation import validate_and_normalize


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection."""
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def ingest_lead(payload: dict) -> Tuple[dict, bool]:
    """Process an incoming website lead event.

    Returns (response_dict, is_new_lead).
    """
    # Validate and normalize
    payload = validate_and_normalize(payload)

    conn = get_db_connection()
    try:
        contact = payload.get("contact", {})
        email = contact.get("email")
        phone = contact.get("phone")

        # Find existing lead by email or phone (dedup)
        lead_id = None
        is_new = False

        if email:
            cursor = conn.execute(
                "SELECT id FROM leads WHERE email = ? COLLATE NOCASE LIMIT 1",
                (email,),
            )
            row = cursor.fetchone()
            if row:
                lead_id = row[0]

        if lead_id is None and phone:
            digits = "".join(c for c in phone if c.isdigit())
            if len(digits) >= 10:
                cursor = conn.execute(
                    "SELECT id FROM leads WHERE phone LIKE ? LIMIT 1",
                    (f"%{digits[-10:]}%",),
                )
                row = cursor.fetchone()
                if row:
                    lead_id = row[0]

        now = datetime.now(timezone.utc).isoformat()
        name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()

        if lead_id:
            # Update existing lead
            conn.execute(
                "UPDATE leads SET last_seen_at = ?, updated_at = ? WHERE id = ?",
                (now, now, lead_id),
            )
            # Update name if we have one and existing doesn't
            if name:
                conn.execute(
                    "UPDATE leads SET name = COALESCE(NULLIF(name, ''), ?) WHERE id = ?",
                    (name, lead_id),
                )
        else:
            # Create new lead
            is_new = True
            cursor = conn.execute(
                """INSERT INTO leads (
                    source, name, email, phone, lead_source,
                    first_seen_at, last_seen_at, status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'website', ?, ?, 'new', ?, ?)""",
                ("website", name or None, email, phone, now, now, now, now),
            )
            lead_id = cursor.lastrowid

        # Record event
        event_data = payload.get("event_data", {})
        session = payload.get("session", {})
        conn.execute(
            """INSERT INTO lead_events (
                lead_id, event_name, event_value, calculator_type,
                inputs_summary, page_path, session_id, device_type,
                city, region, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lead_id,
                payload.get("event_name"),
                json.dumps(event_data.get("calculator_result")) if event_data.get("calculator_result") else None,
                event_data.get("calculator_type"),
                json.dumps(event_data.get("calculator_inputs")) if event_data.get("calculator_inputs") else None,
                event_data.get("page_path"),
                session.get("session_id"),
                session.get("device_type"),
                session.get("city"),
                session.get("region"),
                payload.get("timestamp", now),
            ),
        )

        # Record attribution (every touch — supports multi-touch tracking)
        attribution = payload.get("attribution", {})
        if attribution and any(attribution.values()):
            conn.execute(
                """INSERT INTO lead_attribution (
                    lead_id, utm_source, utm_medium, utm_campaign,
                    utm_content, utm_term, gclid, msclkid, fbclid,
                    landing_page, referrer, referrer_domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    lead_id,
                    attribution.get("utm_source"),
                    attribution.get("utm_medium"),
                    attribution.get("utm_campaign"),
                    attribution.get("utm_content"),
                    attribution.get("utm_term"),
                    attribution.get("gclid"),
                    attribution.get("msclkid"),
                    attribution.get("fbclid"),
                    attribution.get("landing_page"),
                    attribution.get("referrer"),
                    attribution.get("referrer_domain"),
                ),
            )

        # Store message as note if provided
        message = event_data.get("message")
        if message:
            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            conn.execute(
                """UPDATE leads SET notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || char(10) || ?
                END WHERE id = ?""",
                (
                    f"[{timestamp_str}] [website] {message}",
                    f"[{timestamp_str}] [website] {message}",
                    lead_id,
                ),
            )

        conn.commit()

        return {
            "success": True,
            "lead_id": str(lead_id),
            "is_new": is_new,
            "message": "Lead ingested successfully" if is_new else "Event added to existing lead",
        }, is_new
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
