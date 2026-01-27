"""Bulk import functionality."""

import csv
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import io

from ..storage import Database
from ..storage.models import Lead
from ..core import ScoringEngine

logger = logging.getLogger(__name__)


class BulkImporter:
    """Import leads from various formats."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize importer."""
        self.db = Database(db_path) if db_path else Database()
        self.scoring_engine = ScoringEngine()

    def import_csv(
        self,
        file_path: str,
        source: str = "csv_import",
        auto_score: bool = True,
        skip_duplicates: bool = True,
        column_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Import leads from CSV file.

        Default column mapping expects:
        - name (required)
        - email
        - phone
        - bio/notes/message
        - tags

        Custom mapping example:
        {"Name": "name", "Email Address": "email", "Phone Number": "phone"}
        """
        results = {
            "imported": 0,
            "skipped_duplicates": 0,
            "errors": 0,
            "error_details": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    try:
                        # Apply column mapping
                        if column_mapping:
                            mapped_row = {}
                            for csv_col, lead_field in column_mapping.items():
                                if csv_col in row:
                                    mapped_row[lead_field] = row[csv_col]
                            row = mapped_row

                        lead = self._parse_csv_row(row, source)
                        if not lead:
                            results["errors"] += 1
                            results["error_details"].append({
                                "row": row_num,
                                "error": "Missing required field (name)"
                            })
                            continue

                        # Check for duplicates
                        if skip_duplicates and self._is_duplicate(lead):
                            results["skipped_duplicates"] += 1
                            continue

                        # Score if bio exists
                        if auto_score and lead.bio:
                            score_result = self.scoring_engine.score(lead.bio)
                            lead.score = score_result["score"]
                            lead.tier = score_result["tier"]
                            lead.score_breakdown = json.dumps(score_result)

                        self.db.add_lead(lead)
                        results["imported"] += 1

                    except Exception as e:
                        results["errors"] += 1
                        results["error_details"].append({
                            "row": row_num,
                            "error": str(e)
                        })

        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            results["file_error"] = str(e)

        return results

    def import_json(
        self,
        file_path: str,
        source: str = "json_import",
        auto_score: bool = True,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """Import leads from JSON file.

        Expects format:
        {"leads": [{"name": "...", "email": "...", ...}, ...]}
        or
        [{"name": "...", "email": "...", ...}, ...]
        """
        results = {
            "imported": 0,
            "skipped_duplicates": 0,
            "errors": 0,
            "error_details": []
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both formats
            if isinstance(data, dict):
                leads_data = data.get("leads", [])
            else:
                leads_data = data

            for i, lead_data in enumerate(leads_data):
                try:
                    lead = self._parse_json_lead(lead_data, source)
                    if not lead:
                        results["errors"] += 1
                        continue

                    if skip_duplicates and self._is_duplicate(lead):
                        results["skipped_duplicates"] += 1
                        continue

                    if auto_score and lead.bio:
                        score_result = self.scoring_engine.score(lead.bio)
                        lead.score = score_result["score"]
                        lead.tier = score_result["tier"]
                        lead.score_breakdown = json.dumps(score_result)

                    self.db.add_lead(lead)
                    results["imported"] += 1

                except Exception as e:
                    results["errors"] += 1
                    results["error_details"].append({"index": i, "error": str(e)})

        except Exception as e:
            logger.error(f"Error reading JSON file: {e}")
            results["file_error"] = str(e)

        return results

    def import_from_crm(
        self,
        file_path: str,
        crm: str,
        auto_score: bool = True
    ) -> Dict[str, Any]:
        """Import leads from CRM export file.

        Supported: hubspot, salesforce, followupboss, kvcore
        """
        if crm == "hubspot":
            return self._import_hubspot(file_path, auto_score)
        elif crm == "salesforce":
            return self._import_salesforce(file_path, auto_score)
        elif crm == "followupboss":
            return self._import_followupboss(file_path, auto_score)
        else:
            return {"error": f"Unsupported CRM: {crm}"}

    def _import_hubspot(self, file_path: str, auto_score: bool) -> Dict[str, Any]:
        """Import from HubSpot export."""
        column_mapping = {
            "First Name": "first_name",
            "Last Name": "last_name",
            "Email": "email",
            "Phone Number": "phone",
            "Notes": "bio",
            "Lead Source": "source_detail"
        }

        results = {
            "imported": 0,
            "skipped_duplicates": 0,
            "errors": 0
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        first = row.get("First Name", "")
                        last = row.get("Last Name", "")
                        name = f"{first} {last}".strip()

                        if not name:
                            continue

                        lead = Lead(
                            name=name,
                            email=row.get("Email"),
                            phone=row.get("Phone Number"),
                            bio=row.get("Notes", ""),
                            source="hubspot_import"
                        )

                        if auto_score and lead.bio:
                            score_result = self.scoring_engine.score(lead.bio)
                            lead.score = score_result["score"]
                            lead.tier = score_result["tier"]

                        self.db.add_lead(lead)
                        results["imported"] += 1

                    except Exception as e:
                        results["errors"] += 1

        except Exception as e:
            results["file_error"] = str(e)

        return results

    def _import_salesforce(self, file_path: str, auto_score: bool) -> Dict[str, Any]:
        """Import from Salesforce export."""
        results = {"imported": 0, "errors": 0}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        first = row.get("FirstName", "")
                        last = row.get("LastName", "")
                        name = f"{first} {last}".strip()

                        if not name:
                            continue

                        lead = Lead(
                            name=name,
                            email=row.get("Email"),
                            phone=row.get("Phone"),
                            bio=row.get("Description", ""),
                            source="salesforce_import"
                        )

                        if auto_score and lead.bio:
                            score_result = self.scoring_engine.score(lead.bio)
                            lead.score = score_result["score"]
                            lead.tier = score_result["tier"]

                        self.db.add_lead(lead)
                        results["imported"] += 1

                    except Exception:
                        results["errors"] += 1

        except Exception as e:
            results["file_error"] = str(e)

        return results

    def _import_followupboss(self, file_path: str, auto_score: bool) -> Dict[str, Any]:
        """Import from Follow Up Boss export."""
        results = {"imported": 0, "errors": 0}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        first = row.get("firstName", row.get("First Name", ""))
                        last = row.get("lastName", row.get("Last Name", ""))
                        name = f"{first} {last}".strip()

                        if not name:
                            continue

                        lead = Lead(
                            name=name,
                            email=row.get("emails", row.get("Email", "")),
                            phone=row.get("phones", row.get("Phone", "")),
                            bio=row.get("notes", ""),
                            source="followupboss_import",
                            tags=row.get("tags", "")
                        )

                        if auto_score and lead.bio:
                            score_result = self.scoring_engine.score(lead.bio)
                            lead.score = score_result["score"]
                            lead.tier = score_result["tier"]

                        self.db.add_lead(lead)
                        results["imported"] += 1

                    except Exception:
                        results["errors"] += 1

        except Exception as e:
            results["file_error"] = str(e)

        return results

    def import_from_text(
        self,
        text: str,
        source: str = "text_import"
    ) -> Dict[str, Any]:
        """Import leads from pasted text.

        Tries to parse:
        - One contact per line
        - Name, email, phone patterns
        """
        import re

        results = {"imported": 0, "errors": 0}

        lines = text.strip().split("\n")

        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        phone_pattern = r'[\d\-\(\)\s\.]{10,}'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # Extract email
                email_match = re.search(email_pattern, line)
                email = email_match.group(0) if email_match else None

                # Extract phone
                phone_match = re.search(phone_pattern, line)
                phone = phone_match.group(0).strip() if phone_match else None

                # Everything else is potentially name
                name = line
                if email:
                    name = name.replace(email, "")
                if phone:
                    name = name.replace(phone, "")

                # Clean up name
                name = re.sub(r'[,\-\|]', ' ', name)
                name = ' '.join(name.split()).strip()

                if not name and not email:
                    continue

                lead = Lead(
                    name=name or "Unknown",
                    email=email,
                    phone=phone,
                    source=source
                )

                self.db.add_lead(lead)
                results["imported"] += 1

            except Exception:
                results["errors"] += 1

        return results

    def _parse_csv_row(self, row: Dict[str, str], source: str) -> Optional[Lead]:
        """Parse a CSV row into a Lead object."""
        # Try to find name
        name = (
            row.get("name") or
            row.get("Name") or
            row.get("full_name") or
            row.get("Full Name") or
            f"{row.get('first_name', row.get('First Name', ''))} {row.get('last_name', row.get('Last Name', ''))}".strip()
        )

        if not name:
            return None

        email = row.get("email") or row.get("Email") or row.get("email_address") or row.get("Email Address")
        phone = row.get("phone") or row.get("Phone") or row.get("phone_number") or row.get("Phone Number")
        bio = row.get("bio") or row.get("Bio") or row.get("notes") or row.get("Notes") or row.get("message") or row.get("Message")
        tags = row.get("tags") or row.get("Tags")

        return Lead(
            name=name,
            email=email,
            phone=phone,
            bio=bio,
            source=source,
            tags=tags
        )

    def _parse_json_lead(self, data: Dict[str, Any], source: str) -> Optional[Lead]:
        """Parse JSON lead data into Lead object."""
        name = data.get("name") or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()

        if not name:
            return None

        return Lead(
            name=name,
            email=data.get("email"),
            phone=data.get("phone"),
            username=data.get("username"),
            bio=data.get("bio") or data.get("notes"),
            source=source,
            source_id=data.get("source_id") or data.get("id"),
            tags=",".join(data.get("tags", [])) if isinstance(data.get("tags"), list) else data.get("tags"),
            followers=data.get("followers", 0)
        )

    def _is_duplicate(self, lead: Lead) -> bool:
        """Check if lead is a duplicate."""
        # Check by email
        if lead.email:
            existing = self.db.search_leads(limit=1)
            for existing_lead in self.db.search_leads(limit=10000):
                if existing_lead.email and existing_lead.email.lower() == lead.email.lower():
                    return True

        # Check by phone
        if lead.phone:
            phone_digits = "".join(c for c in lead.phone if c.isdigit())
            if len(phone_digits) >= 10:
                for existing_lead in self.db.search_leads(limit=10000):
                    if existing_lead.phone:
                        existing_digits = "".join(c for c in existing_lead.phone if c.isdigit())
                        if phone_digits[-10:] == existing_digits[-10:]:
                            return True

        return False

    def preview_import(self, file_path: str, rows: int = 5) -> Dict[str, Any]:
        """Preview first few rows of an import file."""
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r') as f:
                    data = json.load(f)

                if isinstance(data, dict):
                    leads = data.get("leads", [])[:rows]
                else:
                    leads = data[:rows]

                return {
                    "format": "json",
                    "total_records": len(data if isinstance(data, list) else data.get("leads", [])),
                    "preview": leads
                }

            else:  # Assume CSV
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    preview = [row for _, row in zip(range(rows), reader)]

                # Count total
                with open(file_path, 'r', encoding='utf-8') as f:
                    total = sum(1 for _ in f) - 1  # Minus header

                return {
                    "format": "csv",
                    "columns": list(preview[0].keys()) if preview else [],
                    "total_records": total,
                    "preview": preview
                }

        except Exception as e:
            return {"error": str(e)}
