"""Nextdoor data connector.

Imports leads from:
- Nextdoor business messages
- Nextdoor recommendations/reviews
- Nextdoor post engagement
"""

import json
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import BaseConnector, ImportResult, RawLead


class NextdoorConnector(BaseConnector):
    """Import leads from Nextdoor for Business."""

    source_name = "nextdoor"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Nextdoor export."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            if path.suffix.lower() == ".json":
                return self._import_from_json(path)
            elif path.suffix.lower() == ".csv":
                return self._import_from_csv(path)
            elif path.is_dir():
                return self._import_from_folder(path)
            else:
                result.add_error(f"Unsupported file type: {path.suffix}")
                return result
        except Exception as e:
            result.add_error(f"Import failed: {str(e)}")
            return result

    def _import_from_folder(self, folder_path: Path) -> ImportResult:
        """Import from Nextdoor data export folder."""
        result = ImportResult(source=self.source_name)

        # Process any JSON/CSV files
        for json_file in folder_path.glob("*.json"):
            json_result = self._import_from_json(json_file)
            result.leads.extend(json_result.leads)

        for csv_file in folder_path.glob("*.csv"):
            csv_result = self._import_from_csv(csv_file)
            result.leads.extend(csv_result.leads)

        return result

    def _import_from_json(self, json_path: Path) -> ImportResult:
        """Import from Nextdoor JSON export."""
        result = ImportResult(source=self.source_name)

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle different export formats
            if "messages" in data:
                for msg in data["messages"]:
                    lead = self._parse_message(msg)
                    if lead:
                        result.leads.append(lead)

            if "recommendations" in data:
                for rec in data["recommendations"]:
                    lead = self._parse_recommendation(rec)
                    if lead:
                        result.leads.append(lead)

            if "leads" in data:
                for lead_data in data["leads"]:
                    lead = self._parse_lead(lead_data)
                    if lead:
                        result.leads.append(lead)

        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON: {e}")
        except Exception as e:
            result.add_error(f"Error reading file: {e}")

        return result

    def _import_from_csv(self, csv_path: Path) -> ImportResult:
        """Import from Nextdoor CSV export."""
        result = ImportResult(source=self.source_name)

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    lead = self._parse_csv_row(row, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _parse_message(self, msg: Dict[str, Any]) -> Optional[RawLead]:
        """Parse a Nextdoor message."""
        sender = msg.get("sender", msg.get("from", {}))

        if isinstance(sender, str):
            name = sender
        else:
            name = sender.get("name", sender.get("displayName"))

        content = msg.get("content", msg.get("text", msg.get("message", "")))
        neighborhood = msg.get("neighborhood", "")

        if not name:
            return None

        notes = f"Nextdoor message"
        if neighborhood:
            notes += f" from {neighborhood}"

        return RawLead(
            source="nextdoor",
            source_id=msg.get("id"),
            name=name,
            messages=[content] if content else [],
            notes=notes,
            raw_data=msg
        )

    def _parse_recommendation(self, rec: Dict[str, Any]) -> Optional[RawLead]:
        """Parse a Nextdoor recommendation/review."""
        author = rec.get("author", rec.get("reviewer", {}))

        if isinstance(author, str):
            name = author
        else:
            name = author.get("name", author.get("displayName"))

        text = rec.get("text", rec.get("content", rec.get("review", "")))
        neighborhood = rec.get("neighborhood", "")
        rating = rec.get("rating")

        if not name:
            return None

        notes = f"Nextdoor recommendation"
        if rating:
            notes += f" ({rating} stars)"
        if neighborhood:
            notes += f" from {neighborhood}"
        if text:
            notes += f"\n{text}"

        return RawLead(
            source="nextdoor",
            source_id=rec.get("id"),
            name=name,
            notes=notes,
            raw_data=rec
        )

    def _parse_lead(self, lead_data: Dict[str, Any]) -> Optional[RawLead]:
        """Parse a Nextdoor lead object."""
        name = lead_data.get("name", lead_data.get("contact_name"))
        email = lead_data.get("email", "")
        phone = lead_data.get("phone", lead_data.get("phone_number", ""))
        message = lead_data.get("message", lead_data.get("inquiry", ""))
        neighborhood = lead_data.get("neighborhood", "")

        if not any([name, email, phone]):
            return None

        notes = ""
        if neighborhood:
            notes = f"Neighborhood: {neighborhood}"
        if message:
            notes = f"{notes}\n{message}".strip() if notes else message

        return RawLead(
            source="nextdoor",
            source_id=lead_data.get("id"),
            name=name,
            email=email.lower() if email else None,
            phone=phone or None,
            notes=notes or None,
            raw_data=lead_data
        )

    def _parse_csv_row(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a Nextdoor CSV row."""
        name = row.get("Name", row.get("Contact Name", "")).strip()
        email = row.get("Email", "").strip().lower()
        phone = row.get("Phone", "").strip()
        message = row.get("Message", row.get("Inquiry", "")).strip()
        neighborhood = row.get("Neighborhood", "").strip()

        if not any([name, email, phone]):
            return None

        notes = ""
        if neighborhood:
            notes = f"Neighborhood: {neighborhood}"
        if message:
            notes = f"{notes}\n{message}".strip() if notes else message

        return RawLead(
            source="nextdoor",
            source_id=f"nd_{row_num}",
            name=name or None,
            email=email or None,
            phone=phone or None,
            notes=notes or None,
            raw_data=dict(row)
        )
