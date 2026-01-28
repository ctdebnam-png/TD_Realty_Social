"""Background task runner for periodic scoring and notifications."""

import json
import threading
import time
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class LeadTaskRunner:
    """Background task runner for re-scoring and tier change notifications."""

    def __init__(self, interval_seconds: int = 300, db_path: str = None):
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        self.notified_hot_leads: Set[int] = set()
        self.db_path = db_path or str(Path.home() / ".td-lead-engine" / "leads.db")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Task runner started (interval: {self.interval}s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)

    def _run_loop(self):
        while self.running:
            try:
                self._rescore_recent_leads()
            except Exception as e:
                logger.exception(f"Task runner error: {e}")
            time.sleep(self.interval)

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _rescore_recent_leads(self):
        """Re-score leads that have recent website events."""
        conn = self._get_conn()
        try:
            since = (datetime.now(timezone.utc) - timedelta(seconds=self.interval * 2)).isoformat()

            # Find leads with recent events
            cursor = conn.execute("""
                SELECT DISTINCT le.lead_id
                FROM lead_events le
                WHERE le.created_at > ?
            """, (since,))

            lead_ids = [row[0] for row in cursor.fetchall()]
            if not lead_ids:
                return

            from ..core.scorer import LeadScorer
            from .website_scorer import score_website_events_for_lead

            scorer = LeadScorer()

            for lead_id in lead_ids:
                cursor = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
                lead_row = cursor.fetchone()
                if not lead_row:
                    continue

                old_score = lead_row["score"] or 0
                old_tier = lead_row["tier"] or "cold"

                # Text-based score
                text_parts = [lead_row["notes"] or "", lead_row["bio"] or ""]
                if lead_row["messages_json"]:
                    try:
                        text_parts.extend(json.loads(lead_row["messages_json"]))
                    except Exception:
                        pass
                combined = " ".join(filter(None, text_parts))
                text_result = scorer.score_text(combined)

                # Website event score
                website_score = score_website_events_for_lead(conn, lead_id)

                new_score = text_result.total_score + website_score

                # Determine new tier
                if new_score >= 150:
                    new_tier = "hot"
                elif new_score >= 75:
                    new_tier = "warm"
                elif new_score >= 25:
                    new_tier = "lukewarm"
                elif new_score >= 0:
                    new_tier = "cold"
                else:
                    new_tier = "negative"

                if new_score != old_score:
                    conn.execute(
                        "UPDATE leads SET score = ?, tier = ?, updated_at = ? WHERE id = ?",
                        (new_score, new_tier, datetime.now(timezone.utc).isoformat(), lead_id),
                    )

                # Notify on tier upgrade to hot
                if new_tier == "hot" and old_tier != "hot" and lead_id not in self.notified_hot_leads:
                    self.notified_hot_leads.add(lead_id)
                    self._send_hot_lead_alert(dict(lead_row), new_score)

            conn.commit()
        finally:
            conn.close()

    def _send_hot_lead_alert(self, lead: dict, score: int):
        """Send notification for a newly hot lead."""
        try:
            from ..notifications.notifier import send_hot_lead_alert
            lead["score"] = score
            send_hot_lead_alert(lead)
        except ImportError:
            logger.debug("Notification module not available")
        except Exception as e:
            logger.warning(f"Failed to send hot lead alert: {e}")


_task_runner = None


def get_task_runner() -> LeadTaskRunner:
    global _task_runner
    if _task_runner is None:
        _task_runner = LeadTaskRunner()
    return _task_runner
