"""SQLite database for lead storage with deduplication."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator, Tuple

from .models import Lead, LeadStatus, Interaction, InteractionType
from ..connectors.base import RawLead
from ..core.scorer import LeadScorer, ScoringResult


class LeadDatabase:
    """SQLite database for storing and managing leads."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection."""
        if db_path is None:
            db_path = Path.home() / ".td-lead-engine" / "leads.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get a database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    source_id TEXT,

                    name TEXT,
                    email TEXT,
                    phone TEXT,
                    username TEXT,
                    profile_url TEXT,

                    bio TEXT,
                    notes TEXT,
                    messages_json TEXT,
                    comments_json TEXT,

                    score INTEGER DEFAULT 0,
                    tier TEXT DEFAULT 'cold',
                    score_breakdown TEXT,

                    status TEXT DEFAULT 'new',
                    tags TEXT,

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_scored_at TIMESTAMP,
                    last_contacted_at TIMESTAMP,

                    raw_data_json TEXT,

                    UNIQUE(source, source_id)
                )
            """)

            # Interactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    content TEXT,
                    metadata_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (lead_id) REFERENCES leads(id)
                )
            """)

            # Indexes for common queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_leads_phone ON leads(phone)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interactions_lead ON interactions(lead_id)
            """)

    def _row_to_lead(self, row: sqlite3.Row) -> Lead:
        """Convert a database row to a Lead object."""
        return Lead(
            id=row["id"],
            source=row["source"],
            source_id=row["source_id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            username=row["username"],
            profile_url=row["profile_url"],
            bio=row["bio"],
            notes=row["notes"],
            messages_json=row["messages_json"],
            comments_json=row["comments_json"],
            score=row["score"] or 0,
            tier=row["tier"] or "cold",
            score_breakdown=row["score_breakdown"],
            status=LeadStatus(row["status"]) if row["status"] else LeadStatus.NEW,
            tags=row["tags"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            last_scored_at=datetime.fromisoformat(row["last_scored_at"]) if row["last_scored_at"] else None,
            last_contacted_at=datetime.fromisoformat(row["last_contacted_at"]) if row["last_contacted_at"] else None,
            raw_data_json=row["raw_data_json"],
        )

    # === DEDUPLICATION ===

    def find_duplicate(self, raw_lead: RawLead) -> Optional[Lead]:
        """Find an existing lead that matches the raw lead (deduplication)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Check by source + source_id first (strongest match)
            if raw_lead.source_id:
                cursor.execute(
                    "SELECT * FROM leads WHERE source = ? AND source_id = ?",
                    (raw_lead.source, raw_lead.source_id)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_lead(row)

            # Check by email (strong match)
            if raw_lead.email:
                cursor.execute(
                    "SELECT * FROM leads WHERE email = ? COLLATE NOCASE",
                    (raw_lead.email.lower(),)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_lead(row)

            # Check by phone (strong match)
            if raw_lead.phone:
                # Normalize phone for comparison
                phone_digits = ''.join(c for c in raw_lead.phone if c.isdigit())
                cursor.execute("SELECT * FROM leads WHERE phone LIKE ?", (f"%{phone_digits[-10:]}%",))
                row = cursor.fetchone()
                if row:
                    return self._row_to_lead(row)

            # Check by username + source (moderate match)
            if raw_lead.username:
                cursor.execute(
                    "SELECT * FROM leads WHERE username = ? COLLATE NOCASE AND source = ?",
                    (raw_lead.username.lower(), raw_lead.source)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_lead(row)

            return None

    # === CRUD OPERATIONS ===

    def insert_lead(self, raw_lead: RawLead) -> Tuple[Lead, bool]:
        """
        Insert or update a lead from raw import data.
        Returns (lead, is_new) tuple.
        """
        existing = self.find_duplicate(raw_lead)

        if existing:
            # Merge data into existing lead
            return self._merge_lead(existing, raw_lead), False
        else:
            # Create new lead
            return self._create_lead(raw_lead), True

    def _create_lead(self, raw_lead: RawLead) -> Lead:
        """Create a new lead from raw data."""
        now = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO leads (
                    source, source_id, name, email, phone, username, profile_url,
                    bio, notes, messages_json, comments_json, raw_data_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                raw_lead.source,
                raw_lead.source_id,
                raw_lead.name,
                raw_lead.email.lower() if raw_lead.email else None,
                raw_lead.phone,
                raw_lead.username,
                raw_lead.profile_url,
                raw_lead.bio,
                raw_lead.notes,
                json.dumps(raw_lead.messages) if raw_lead.messages else None,
                json.dumps(raw_lead.comments) if raw_lead.comments else None,
                json.dumps(raw_lead.raw_data) if raw_lead.raw_data else None,
                now.isoformat(),
                now.isoformat(),
            ))

            lead_id = cursor.lastrowid

            # Log interaction
            cursor.execute("""
                INSERT INTO interactions (lead_id, interaction_type, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (lead_id, InteractionType.IMPORT.value, f"Imported from {raw_lead.source}", now.isoformat()))

        return self.get_lead(lead_id)

    def _merge_lead(self, existing: Lead, raw_lead: RawLead) -> Lead:
        """Merge new raw data into an existing lead."""
        now = datetime.now()

        # Merge fields (prefer non-null values, update if new has data)
        updates = []
        params = []

        if raw_lead.name and not existing.name:
            updates.append("name = ?")
            params.append(raw_lead.name)

        if raw_lead.email and not existing.email:
            updates.append("email = ?")
            params.append(raw_lead.email.lower())

        if raw_lead.phone and not existing.phone:
            updates.append("phone = ?")
            params.append(raw_lead.phone)

        if raw_lead.bio:
            # Append bio
            new_bio = f"{existing.bio or ''}\n{raw_lead.bio}".strip()
            updates.append("bio = ?")
            params.append(new_bio)

        if raw_lead.notes:
            # Append notes
            new_notes = f"{existing.notes or ''}\n{raw_lead.notes}".strip()
            updates.append("notes = ?")
            params.append(new_notes)

        # Merge messages
        if raw_lead.messages:
            existing_msgs = json.loads(existing.messages_json) if existing.messages_json else []
            merged_msgs = list(set(existing_msgs + raw_lead.messages))
            updates.append("messages_json = ?")
            params.append(json.dumps(merged_msgs))

        # Merge comments
        if raw_lead.comments:
            existing_comments = json.loads(existing.comments_json) if existing.comments_json else []
            merged_comments = list(set(existing_comments + raw_lead.comments))
            updates.append("comments_json = ?")
            params.append(json.dumps(merged_comments))

        updates.append("updated_at = ?")
        params.append(now.isoformat())

        if updates:
            params.append(existing.id)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE leads SET {', '.join(updates)} WHERE id = ?",
                    params
                )

                # Log merge
                cursor.execute("""
                    INSERT INTO interactions (lead_id, interaction_type, content, created_at)
                    VALUES (?, ?, ?, ?)
                """, (existing.id, InteractionType.IMPORT.value, f"Merged data from {raw_lead.source}", now.isoformat()))

        return self.get_lead(existing.id)

    def get_lead(self, lead_id: int) -> Optional[Lead]:
        """Get a lead by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
            row = cursor.fetchone()
            return self._row_to_lead(row) if row else None

    def update_lead(self, lead: Lead) -> Lead:
        """Update a lead in the database."""
        lead.updated_at = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE leads SET
                    name = ?, email = ?, phone = ?, username = ?, profile_url = ?,
                    bio = ?, notes = ?, messages_json = ?, comments_json = ?,
                    score = ?, tier = ?, score_breakdown = ?,
                    status = ?, tags = ?,
                    updated_at = ?, last_scored_at = ?, last_contacted_at = ?
                WHERE id = ?
            """, (
                lead.name, lead.email, lead.phone, lead.username, lead.profile_url,
                lead.bio, lead.notes, lead.messages_json, lead.comments_json,
                lead.score, lead.tier, lead.score_breakdown,
                lead.status.value, lead.tags,
                lead.updated_at.isoformat(),
                lead.last_scored_at.isoformat() if lead.last_scored_at else None,
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
                lead.id
            ))

        return lead

    def delete_lead(self, lead_id: int) -> bool:
        """Delete a lead and its interactions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM interactions WHERE lead_id = ?", (lead_id,))
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            return cursor.rowcount > 0

    # === SCORING ===

    def score_lead(self, lead: Lead, scorer: Optional[LeadScorer] = None) -> Lead:
        """Score a single lead and update the database."""
        if scorer is None:
            scorer = LeadScorer()

        # Build text for scoring
        messages = json.loads(lead.messages_json) if lead.messages_json else []
        comments = json.loads(lead.comments_json) if lead.comments_json else []

        result = scorer.score_lead(
            notes=lead.notes or "",
            bio=lead.bio or "",
            messages=messages,
            comments=comments
        )

        # Update lead
        lead.score = result.total_score
        lead.tier = result.tier
        lead.score_breakdown = json.dumps({
            "matches": [
                {"phrase": m.signal.phrase, "weight": m.signal.weight, "category": m.signal.category.value}
                for m in result.matches
            ],
            "category_scores": {k.value: v for k, v in result.category_scores.items()}
        })
        lead.last_scored_at = datetime.now()

        return self.update_lead(lead)

    def score_all_leads(self, scorer: Optional[LeadScorer] = None) -> int:
        """Score all leads in the database. Returns count scored."""
        if scorer is None:
            scorer = LeadScorer()

        leads = self.get_all_leads()
        for lead in leads:
            self.score_lead(lead, scorer)

        return len(leads)

    # === QUERIES ===

    def get_all_leads(
        self,
        status: Optional[LeadStatus] = None,
        tier: Optional[str] = None,
        min_score: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[Lead]:
        """Get leads with optional filters."""
        query = "SELECT * FROM leads WHERE 1=1"
        params: List[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if tier:
            query += " AND tier = ?"
            params.append(tier)

        if min_score is not None:
            query += " AND score >= ?"
            params.append(min_score)

        query += " ORDER BY score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_lead(row) for row in cursor.fetchall()]

    def get_hot_leads(self, limit: int = 50) -> List[Lead]:
        """Get leads in the hot tier."""
        return self.get_all_leads(tier="hot", limit=limit)

    def get_warm_leads(self, limit: int = 100) -> List[Lead]:
        """Get leads in the warm tier."""
        return self.get_all_leads(tier="warm", limit=limit)

    def search_leads(self, query: str, limit: int = 100) -> List[Lead]:
        """Search leads by name, email, phone, or notes."""
        search_term = f"%{query}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM leads
                WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?
                   OR username LIKE ? OR notes LIKE ? OR bio LIKE ?
                ORDER BY score DESC
                LIMIT ?
            """, (search_term,) * 6 + (limit,))
            return [self._row_to_lead(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM leads")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT tier, COUNT(*) FROM leads GROUP BY tier")
            tier_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT source, COUNT(*) FROM leads GROUP BY source")
            source_counts = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute("SELECT AVG(score), MAX(score), MIN(score) FROM leads")
            score_stats = cursor.fetchone()

            return {
                "total_leads": total,
                "by_tier": tier_counts,
                "by_status": status_counts,
                "by_source": source_counts,
                "score_avg": round(score_stats[0] or 0, 1),
                "score_max": score_stats[1] or 0,
                "score_min": score_stats[2] or 0,
            }

    # === INTERACTIONS ===

    def add_interaction(
        self,
        lead_id: int,
        interaction_type: InteractionType,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Interaction:
        """Add an interaction record for a lead."""
        now = datetime.now()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions (lead_id, interaction_type, content, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                lead_id,
                interaction_type.value,
                content,
                json.dumps(metadata) if metadata else None,
                now.isoformat()
            ))

            return Interaction(
                id=cursor.lastrowid,
                lead_id=lead_id,
                interaction_type=interaction_type,
                content=content,
                metadata_json=json.dumps(metadata) if metadata else None,
                created_at=now
            )

    def get_interactions(self, lead_id: int, limit: int = 100) -> List[Interaction]:
        """Get interactions for a lead."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM interactions
                WHERE lead_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (lead_id, limit))

            interactions = []
            for row in cursor.fetchall():
                interactions.append(Interaction(
                    id=row["id"],
                    lead_id=row["lead_id"],
                    interaction_type=InteractionType(row["interaction_type"]),
                    content=row["content"],
                    metadata_json=row["metadata_json"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
                ))
            return interactions

    # === EXPORT ===

    def export_to_csv(self, path: Path, tier: Optional[str] = None) -> int:
        """Export leads to CSV. Returns count exported."""
        import csv

        leads = self.get_all_leads(tier=tier, limit=100000)

        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Name", "Email", "Phone", "Username",
                "Score", "Tier", "Status", "Source", "Notes", "Profile URL"
            ])

            for lead in leads:
                writer.writerow([
                    lead.id,
                    lead.name or "",
                    lead.email or "",
                    lead.phone or "",
                    lead.username or "",
                    lead.score,
                    lead.tier,
                    lead.status.value,
                    lead.source,
                    (lead.notes or "")[:200],  # Truncate notes
                    lead.profile_url or ""
                ])

        return len(leads)
