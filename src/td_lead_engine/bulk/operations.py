"""Bulk operations for leads."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from ..storage import Database
from ..storage.models import Lead
from ..core import ScoringEngine

logger = logging.getLogger(__name__)


class BulkOperations:
    """Perform bulk operations on leads."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize bulk operations."""
        self.db = Database(db_path) if db_path else Database()
        self.scoring_engine = ScoringEngine()

    def bulk_score(self, lead_ids: Optional[List[int]] = None, tier: Optional[str] = None) -> Dict[str, Any]:
        """Re-score multiple leads.

        Args:
            lead_ids: Specific lead IDs to score, or None for all
            tier: Only score leads in this tier
        """
        results = {"scored": 0, "errors": 0, "tier_changes": 0}

        if lead_ids:
            leads = [self.db.get_lead(lid) for lid in lead_ids]
            leads = [l for l in leads if l]
        else:
            leads = self.db.search_leads(tier=tier, limit=10000)

        for lead in leads:
            try:
                if not lead.bio:
                    continue

                old_tier = lead.tier
                score_result = self.scoring_engine.score(lead.bio)

                lead.score = score_result["score"]
                lead.tier = score_result["tier"]
                lead.score_breakdown = json.dumps(score_result)

                self.db.update_lead(lead)
                results["scored"] += 1

                if lead.tier != old_tier:
                    results["tier_changes"] += 1

            except Exception as e:
                logger.error(f"Error scoring lead {lead.id}: {e}")
                results["errors"] += 1

        return results

    def bulk_tag(self, lead_ids: List[int], tag: str, remove: bool = False) -> Dict[str, Any]:
        """Add or remove tag from multiple leads."""
        results = {"updated": 0, "errors": 0}

        for lead_id in lead_ids:
            try:
                lead = self.db.get_lead(lead_id)
                if not lead:
                    continue

                current_tags = set(lead.tags.split(",")) if lead.tags else set()
                current_tags.discard("")  # Remove empty strings

                if remove:
                    current_tags.discard(tag)
                else:
                    current_tags.add(tag)

                lead.tags = ",".join(sorted(current_tags))
                self.db.update_lead(lead)
                results["updated"] += 1

            except Exception as e:
                logger.error(f"Error tagging lead {lead_id}: {e}")
                results["errors"] += 1

        return results

    def bulk_update_status(self, lead_ids: List[int], status: str) -> Dict[str, Any]:
        """Update status for multiple leads."""
        valid_statuses = ["new", "contacted", "qualified", "nurturing", "converted", "lost"]

        if status not in valid_statuses:
            return {"error": f"Invalid status. Must be one of: {valid_statuses}"}

        results = {"updated": 0, "errors": 0}

        for lead_id in lead_ids:
            try:
                lead = self.db.get_lead(lead_id)
                if not lead:
                    continue

                lead.status = status
                self.db.update_lead(lead)
                results["updated"] += 1

            except Exception as e:
                logger.error(f"Error updating lead {lead_id}: {e}")
                results["errors"] += 1

        return results

    def bulk_assign(self, lead_ids: List[int], agent_id: str) -> Dict[str, Any]:
        """Assign multiple leads to an agent."""
        from ..routing import LeadRouter

        router = LeadRouter()
        results = {"assigned": 0, "errors": 0}

        for lead_id in lead_ids:
            try:
                lead = self.db.get_lead(lead_id)
                if not lead:
                    continue

                # Update lead notes with assignment
                assignment_note = f"Assigned to agent {agent_id} on {datetime.now().strftime('%Y-%m-%d')}"
                lead.notes = f"{lead.notes}\n{assignment_note}".strip() if lead.notes else assignment_note

                self.db.update_lead(lead)
                results["assigned"] += 1

            except Exception as e:
                logger.error(f"Error assigning lead {lead_id}: {e}")
                results["errors"] += 1

        return results

    def bulk_enroll_campaign(self, lead_ids: List[int], campaign_id: str) -> Dict[str, Any]:
        """Enroll multiple leads in a nurture campaign."""
        from ..nurturing import CampaignManager

        campaign_manager = CampaignManager()
        results = {"enrolled": 0, "errors": 0, "already_enrolled": 0}

        for lead_id in lead_ids:
            try:
                lead = self.db.get_lead(lead_id)
                if not lead:
                    continue

                enrollment = campaign_manager.enroll_lead(
                    campaign_id=campaign_id,
                    lead_id=str(lead_id),
                    lead_name=lead.name,
                    lead_email=lead.email,
                    lead_phone=lead.phone
                )

                if enrollment:
                    results["enrolled"] += 1
                else:
                    results["already_enrolled"] += 1

            except Exception as e:
                logger.error(f"Error enrolling lead {lead_id}: {e}")
                results["errors"] += 1

        return results

    def bulk_delete(self, lead_ids: List[int], confirm: bool = False) -> Dict[str, Any]:
        """Delete multiple leads."""
        if not confirm:
            return {
                "error": "Deletion requires confirmation",
                "lead_count": len(lead_ids),
                "message": "Set confirm=True to proceed with deletion"
            }

        results = {"deleted": 0, "errors": 0}

        for lead_id in lead_ids:
            try:
                self.db.delete_lead(lead_id)
                results["deleted"] += 1
            except Exception as e:
                logger.error(f"Error deleting lead {lead_id}: {e}")
                results["errors"] += 1

        return results

    def bulk_merge(self, primary_id: int, duplicate_ids: List[int]) -> Dict[str, Any]:
        """Merge duplicate leads into primary lead."""
        primary = self.db.get_lead(primary_id)
        if not primary:
            return {"error": "Primary lead not found"}

        merged_count = 0
        merged_data = []

        for dup_id in duplicate_ids:
            dup = self.db.get_lead(dup_id)
            if not dup or dup_id == primary_id:
                continue

            # Merge data (prefer primary, fill gaps from duplicate)
            if not primary.email and dup.email:
                primary.email = dup.email
            if not primary.phone and dup.phone:
                primary.phone = dup.phone
            if not primary.bio and dup.bio:
                primary.bio = dup.bio
            elif dup.bio and primary.bio:
                # Append unique info
                if dup.bio not in primary.bio:
                    primary.bio = f"{primary.bio}\n\n[Merged from duplicate]: {dup.bio}"

            # Merge tags
            primary_tags = set(primary.tags.split(",")) if primary.tags else set()
            dup_tags = set(dup.tags.split(",")) if dup.tags else set()
            primary_tags.update(dup_tags)
            primary_tags.discard("")
            primary.tags = ",".join(sorted(primary_tags))

            # Keep higher score
            if dup.score > primary.score:
                primary.score = dup.score
                primary.tier = dup.tier
                primary.score_breakdown = dup.score_breakdown

            # Append to notes
            merge_note = f"Merged duplicate (ID: {dup_id}, source: {dup.source}) on {datetime.now().strftime('%Y-%m-%d')}"
            primary.notes = f"{primary.notes}\n{merge_note}".strip() if primary.notes else merge_note

            merged_data.append({"id": dup_id, "source": dup.source, "email": dup.email})

            # Delete duplicate
            self.db.delete_lead(dup_id)
            merged_count += 1

        # Update primary
        self.db.update_lead(primary)

        return {
            "primary_id": primary_id,
            "merged_count": merged_count,
            "merged_data": merged_data
        }

    def find_duplicates(self) -> List[Dict[str, Any]]:
        """Find potential duplicate leads."""
        leads = self.db.search_leads(limit=10000)

        # Group by email
        by_email: Dict[str, List] = {}
        for lead in leads:
            if lead.email:
                email = lead.email.lower()
                if email not in by_email:
                    by_email[email] = []
                by_email[email].append(lead)

        # Group by phone
        by_phone: Dict[str, List] = {}
        for lead in leads:
            if lead.phone:
                # Normalize phone
                phone = "".join(c for c in lead.phone if c.isdigit())
                if len(phone) >= 10:
                    phone = phone[-10:]  # Last 10 digits
                    if phone not in by_phone:
                        by_phone[phone] = []
                    by_phone[phone].append(lead)

        duplicates = []

        # Email duplicates
        for email, email_leads in by_email.items():
            if len(email_leads) > 1:
                duplicates.append({
                    "match_type": "email",
                    "match_value": email,
                    "leads": [
                        {"id": l.id, "name": l.name, "source": l.source, "score": l.score}
                        for l in email_leads
                    ]
                })

        # Phone duplicates (not already matched by email)
        matched_ids = set()
        for dup in duplicates:
            for lead in dup["leads"]:
                matched_ids.add(lead["id"])

        for phone, phone_leads in by_phone.items():
            if len(phone_leads) > 1:
                # Check if any not already matched
                unmatched = [l for l in phone_leads if l.id not in matched_ids]
                if len(unmatched) > 1:
                    duplicates.append({
                        "match_type": "phone",
                        "match_value": phone,
                        "leads": [
                            {"id": l.id, "name": l.name, "source": l.source, "score": l.score}
                            for l in phone_leads
                        ]
                    })

        return duplicates

    def cleanup_old_leads(
        self,
        days_old: int = 365,
        status: Optional[str] = None,
        tier: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Clean up old leads based on criteria."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        leads = self.db.search_leads(limit=10000)

        to_delete = []
        for lead in leads:
            # Check age
            if lead.created_at:
                try:
                    created = datetime.strptime(lead.created_at[:10], "%Y-%m-%d")
                    if created > cutoff:
                        continue
                except:
                    continue

            # Check status filter
            if status and lead.status != status:
                continue

            # Check tier filter
            if tier and lead.tier != tier:
                continue

            to_delete.append(lead)

        result = {
            "criteria": {
                "days_old": days_old,
                "cutoff_date": cutoff_str,
                "status": status,
                "tier": tier
            },
            "leads_matched": len(to_delete),
            "dry_run": dry_run
        }

        if dry_run:
            result["preview"] = [
                {"id": l.id, "name": l.name, "created_at": l.created_at, "status": l.status}
                for l in to_delete[:20]
            ]
            result["message"] = "Dry run - no leads deleted. Set dry_run=False to delete."
        else:
            for lead in to_delete:
                self.db.delete_lead(lead.id)
            result["deleted"] = len(to_delete)

        return result
