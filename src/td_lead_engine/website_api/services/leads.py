"""Lead service for dashboard API routes."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import settings


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    return conn


class LeadService:
    """Service layer for lead read/write operations."""

    def list_leads(
        self,
        source: Optional[str] = None,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        conn = _get_conn()
        try:
            query = "SELECT l.* FROM leads l"
            params = []
            joins = []
            wheres = []

            if utm_campaign:
                joins.append("JOIN lead_attribution la ON la.lead_id = l.id")
                wheres.append("la.utm_campaign = ?")
                params.append(utm_campaign)

            if source:
                wheres.append("(l.source = ? OR l.lead_source = ?)")
                params.extend([source, source])
            if tier:
                wheres.append("l.tier = ?")
                params.append(tier)
            if status:
                wheres.append("l.status = ?")
                params.append(status)

            if joins:
                query += " " + " ".join(joins)
            if wheres:
                query += " WHERE " + " AND ".join(wheres)

            query += " ORDER BY l.score DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            leads = []
            for row in cursor.fetchall():
                signals = []
                if row["score_breakdown"]:
                    try:
                        breakdown = json.loads(row["score_breakdown"])
                        signals = [m["phrase"] for m in breakdown.get("matches", [])[:5]]
                    except Exception:
                        pass
                leads.append({
                    "id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "score": row["score"],
                    "tier": row["tier"],
                    "status": row["status"],
                    "source": row["source"],
                    "signals": signals,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })
            return {"leads": leads, "count": len(leads)}
        finally:
            conn.close()

    def get_lead_detail(self, lead_id: int) -> dict:
        conn = _get_conn()
        try:
            cursor = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            if not row:
                return {"error": "Lead not found"}

            signals = []
            category_scores = {}
            if row["score_breakdown"]:
                try:
                    breakdown = json.loads(row["score_breakdown"])
                    signals = breakdown.get("matches", [])
                    category_scores = breakdown.get("category_scores", {})
                except Exception:
                    pass

            # Get attribution
            attr_cursor = conn.execute(
                "SELECT * FROM lead_attribution WHERE lead_id = ? LIMIT 1", (lead_id,)
            )
            attr_row = attr_cursor.fetchone()
            attribution = None
            if attr_row:
                attribution = {
                    "utm_source": attr_row["utm_source"],
                    "utm_medium": attr_row["utm_medium"],
                    "utm_campaign": attr_row["utm_campaign"],
                    "utm_content": attr_row["utm_content"],
                    "utm_term": attr_row["utm_term"],
                    "gclid": attr_row["gclid"],
                    "landing_page": attr_row["landing_page"],
                    "referrer_domain": attr_row["referrer_domain"],
                }

            return {
                "lead": {
                    "id": row["id"],
                    "name": row["name"],
                    "email": row["email"],
                    "phone": row["phone"],
                    "username": row["username"],
                    "profile_url": row["profile_url"],
                    "bio": row["bio"],
                    "notes": row["notes"],
                    "score": row["score"],
                    "tier": row["tier"],
                    "status": row["status"],
                    "source": row["source"],
                    "signals": signals,
                    "category_scores": category_scores,
                    "attribution": attribution,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            }
        finally:
            conn.close()

    def get_lead_events(self, lead_id: int) -> dict:
        conn = _get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM lead_events WHERE lead_id = ? ORDER BY created_at DESC",
                (lead_id,),
            )
            events = []
            for row in cursor.fetchall():
                events.append({
                    "id": row["id"],
                    "event_name": row["event_name"],
                    "event_value": row["event_value"],
                    "calculator_type": row["calculator_type"],
                    "page_path": row["page_path"],
                    "session_id": row["session_id"],
                    "device_type": row["device_type"],
                    "city": row["city"],
                    "region": row["region"],
                    "created_at": row["created_at"],
                })
            return {"events": events}
        finally:
            conn.close()

    def get_lead_attribution(self, lead_id: int) -> dict:
        conn = _get_conn()
        try:
            cursor = conn.execute(
                "SELECT * FROM lead_attribution WHERE lead_id = ?", (lead_id,)
            )
            attributions = []
            for row in cursor.fetchall():
                attributions.append({
                    "utm_source": row["utm_source"],
                    "utm_medium": row["utm_medium"],
                    "utm_campaign": row["utm_campaign"],
                    "utm_content": row["utm_content"],
                    "utm_term": row["utm_term"],
                    "gclid": row["gclid"],
                    "landing_page": row["landing_page"],
                    "referrer_domain": row["referrer_domain"],
                    "created_at": row["created_at"],
                })
            return {"attributions": attributions}
        finally:
            conn.close()

    def update_status(self, lead_id: int, status: str) -> dict:
        conn = _get_conn()
        try:
            conn.execute(
                "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.now().isoformat(), lead_id),
            )
            conn.commit()
            return {"success": True, "status": status}
        finally:
            conn.close()

    def add_note(self, lead_id: int, note: str) -> dict:
        conn = _get_conn()
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn.execute(
                """UPDATE leads SET notes = CASE
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE notes || char(10) || ?
                END, updated_at = ? WHERE id = ?""",
                (
                    f"[{timestamp}] {note}",
                    f"[{timestamp}] {note}",
                    datetime.now().isoformat(),
                    lead_id,
                ),
            )
            conn.commit()
            return {"success": True}
        finally:
            conn.close()
