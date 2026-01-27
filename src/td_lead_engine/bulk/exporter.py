"""Bulk export functionality."""

import csv
import json
import logging
import io
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from ..storage import Database

logger = logging.getLogger(__name__)


class BulkExporter:
    """Export leads in various formats."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize exporter."""
        self.db = Database(db_path) if db_path else Database()

    def export_csv(
        self,
        output_path: Optional[str] = None,
        tier: Optional[str] = None,
        source: Optional[str] = None,
        status: Optional[str] = None,
        include_score_breakdown: bool = False
    ) -> str:
        """Export leads to CSV file.

        Returns: Path to exported file or CSV string if no path specified.
        """
        leads = self.db.search_leads(tier=tier, source=source, limit=10000)

        if status:
            leads = [l for l in leads if l.status == status]

        # Define columns
        columns = [
            "id", "name", "email", "phone", "source", "score", "tier",
            "status", "tags", "bio", "notes", "created_at", "updated_at"
        ]

        if include_score_breakdown:
            columns.append("score_breakdown")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            row = {
                "id": lead.id,
                "name": lead.name,
                "email": lead.email or "",
                "phone": lead.phone or "",
                "source": lead.source,
                "score": lead.score,
                "tier": lead.tier,
                "status": lead.status or "",
                "tags": lead.tags or "",
                "bio": lead.bio or "",
                "notes": lead.notes or "",
                "created_at": lead.created_at,
                "updated_at": lead.updated_at
            }

            if include_score_breakdown:
                row["score_breakdown"] = lead.score_breakdown or ""

            writer.writerow(row)

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            logger.info(f"Exported {len(leads)} leads to {output_path}")
            return output_path
        else:
            return csv_content

    def export_json(
        self,
        output_path: Optional[str] = None,
        tier: Optional[str] = None,
        source: Optional[str] = None,
        pretty: bool = True
    ) -> str:
        """Export leads to JSON file."""
        leads = self.db.search_leads(tier=tier, source=source, limit=10000)

        data = {
            "exported_at": datetime.now().isoformat(),
            "total_leads": len(leads),
            "filters": {
                "tier": tier,
                "source": source
            },
            "leads": [
                {
                    "id": lead.id,
                    "name": lead.name,
                    "email": lead.email,
                    "phone": lead.phone,
                    "username": lead.username,
                    "bio": lead.bio,
                    "source": lead.source,
                    "source_id": lead.source_id,
                    "score": lead.score,
                    "tier": lead.tier,
                    "status": lead.status,
                    "tags": lead.tags.split(",") if lead.tags else [],
                    "notes": lead.notes,
                    "followers": lead.followers,
                    "score_breakdown": json.loads(lead.score_breakdown) if lead.score_breakdown else None,
                    "created_at": lead.created_at,
                    "updated_at": lead.updated_at
                }
                for lead in leads
            ]
        }

        json_content = json.dumps(data, indent=2 if pretty else None)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            logger.info(f"Exported {len(leads)} leads to {output_path}")
            return output_path
        else:
            return json_content

    def export_for_crm(
        self,
        crm: str,
        output_path: Optional[str] = None,
        tier: Optional[str] = None
    ) -> str:
        """Export leads in CRM-specific format.

        Supported CRMs: hubspot, salesforce, followupboss, kvcore
        """
        leads = self.db.search_leads(tier=tier, limit=10000)

        if crm == "hubspot":
            return self._export_hubspot(leads, output_path)
        elif crm == "salesforce":
            return self._export_salesforce(leads, output_path)
        elif crm == "followupboss":
            return self._export_followupboss(leads, output_path)
        elif crm == "kvcore":
            return self._export_kvcore(leads, output_path)
        else:
            raise ValueError(f"Unsupported CRM: {crm}")

    def _export_hubspot(self, leads: List, output_path: Optional[str]) -> str:
        """Export in HubSpot import format."""
        columns = [
            "First Name", "Last Name", "Email", "Phone Number",
            "Lead Status", "Lead Score", "Lead Source",
            "Notes", "Create Date"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            name_parts = lead.name.split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            # Map status to HubSpot lifecycle stage
            status_map = {
                "new": "NEW",
                "contacted": "OPEN",
                "qualified": "IN_PROGRESS",
                "nurturing": "OPEN",
                "converted": "CLOSED WON",
                "lost": "CLOSED LOST"
            }

            writer.writerow({
                "First Name": first_name,
                "Last Name": last_name,
                "Email": lead.email or "",
                "Phone Number": lead.phone or "",
                "Lead Status": status_map.get(lead.status, "NEW"),
                "Lead Score": lead.score,
                "Lead Source": f"TD Lead Engine - {lead.source}",
                "Notes": f"{lead.bio or ''}\n{lead.notes or ''}".strip(),
                "Create Date": lead.created_at
            })

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            return output_path
        return csv_content

    def _export_salesforce(self, leads: List, output_path: Optional[str]) -> str:
        """Export in Salesforce import format."""
        columns = [
            "FirstName", "LastName", "Email", "Phone",
            "Status", "Rating", "LeadSource", "Description"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            name_parts = lead.name.split(" ", 1)

            # Map tier to Salesforce rating
            tier_to_rating = {
                "hot": "Hot",
                "warm": "Warm",
                "lukewarm": "Cold",
                "cold": "Cold"
            }

            writer.writerow({
                "FirstName": name_parts[0],
                "LastName": name_parts[1] if len(name_parts) > 1 else "",
                "Email": lead.email or "",
                "Phone": lead.phone or "",
                "Status": "Open - Not Contacted" if lead.status == "new" else "Working - Contacted",
                "Rating": tier_to_rating.get(lead.tier, "Cold"),
                "LeadSource": f"Social Media - {lead.source}",
                "Description": lead.bio or ""
            })

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            return output_path
        return csv_content

    def _export_followupboss(self, leads: List, output_path: Optional[str]) -> str:
        """Export in Follow Up Boss import format."""
        columns = [
            "firstName", "lastName", "emails", "phones",
            "stage", "source", "tags", "notes"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            name_parts = lead.name.split(" ", 1)

            # Map to FUB stages
            stage_map = {
                "new": "New Lead",
                "contacted": "Attempted Contact",
                "qualified": "Active Buyer",
                "nurturing": "Nurture",
                "converted": "Past Client"
            }

            writer.writerow({
                "firstName": name_parts[0],
                "lastName": name_parts[1] if len(name_parts) > 1 else "",
                "emails": lead.email or "",
                "phones": lead.phone or "",
                "stage": stage_map.get(lead.status, "New Lead"),
                "source": f"TD Lead Engine: {lead.source}",
                "tags": lead.tags or "",
                "notes": f"Score: {lead.score} ({lead.tier})\n{lead.bio or ''}"
            })

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            return output_path
        return csv_content

    def _export_kvcore(self, leads: List, output_path: Optional[str]) -> str:
        """Export in kvCORE import format."""
        columns = [
            "first_name", "last_name", "email", "phone_mobile",
            "lead_type", "lead_source", "tags", "notes"
        ]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            name_parts = lead.name.split(" ", 1)

            writer.writerow({
                "first_name": name_parts[0],
                "last_name": name_parts[1] if len(name_parts) > 1 else "",
                "email": lead.email or "",
                "phone_mobile": lead.phone or "",
                "lead_type": "Buyer",  # Would need to detect
                "lead_source": lead.source,
                "tags": f"{lead.tier},{lead.tags or ''}".strip(","),
                "notes": lead.bio or ""
            })

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            return output_path
        return csv_content

    def export_for_mailchimp(
        self,
        output_path: Optional[str] = None,
        tier: Optional[str] = None
    ) -> str:
        """Export leads for Mailchimp import."""
        leads = self.db.search_leads(tier=tier, limit=10000)
        leads = [l for l in leads if l.email]  # Email required

        columns = ["Email Address", "First Name", "Last Name", "Tags"]

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for lead in leads:
            name_parts = lead.name.split(" ", 1)

            tags = [lead.tier, lead.source]
            if lead.tags:
                tags.extend(lead.tags.split(","))

            writer.writerow({
                "Email Address": lead.email,
                "First Name": name_parts[0],
                "Last Name": name_parts[1] if len(name_parts) > 1 else "",
                "Tags": ",".join(tags)
            })

        csv_content = output.getvalue()

        if output_path:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                f.write(csv_content)
            return output_path
        return csv_content

    def export_hot_leads_report(self, output_path: Optional[str] = None) -> str:
        """Export hot leads report for daily review."""
        leads = self.db.search_leads(tier="hot", limit=100)

        lines = [
            f"HOT LEADS REPORT - {datetime.now().strftime('%Y-%m-%d')}",
            "=" * 60,
            f"Total Hot Leads: {len(leads)}",
            "",
        ]

        for i, lead in enumerate(leads, 1):
            lines.extend([
                f"{i}. {lead.name}",
                f"   Score: {lead.score} | Source: {lead.source}",
                f"   Email: {lead.email or 'N/A'} | Phone: {lead.phone or 'N/A'}",
                f"   Status: {lead.status or 'new'}",
            ])

            if lead.bio:
                bio_preview = lead.bio[:100] + "..." if len(lead.bio) > 100 else lead.bio
                lines.append(f"   Bio: {bio_preview}")

            lines.append("")

        report = "\n".join(lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            return output_path
        return report
