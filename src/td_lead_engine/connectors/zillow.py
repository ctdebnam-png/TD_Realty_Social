"""Zillow/real estate portal lead capture connector.

This connector handles leads from:
- Zillow Premier Agent inquiries
- Realtor.com leads
- Homes.com inquiries
- Direct website form submissions

These typically come as email notifications or CRM exports.
"""

import csv
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from email import policy
from email.parser import BytesParser

from .base import BaseConnector, ImportResult, RawLead


class ZillowConnector(BaseConnector):
    """Import leads from Zillow Premier Agent and similar portals."""

    source_name = "zillow"

    # Email subject patterns that indicate lead emails
    LEAD_EMAIL_PATTERNS = [
        r"new lead from zillow",
        r"zillow premier agent",
        r"new inquiry",
        r"someone is interested",
        r"buyer lead",
        r"seller lead",
        r"home valuation request",
        r"realtor\.com lead",
        r"homes\.com inquiry",
    ]

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Zillow export CSV or email export folder."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            if path.suffix.lower() == ".csv":
                return self._import_from_csv(path)
            elif path.suffix.lower() in [".eml", ".msg"]:
                return self._import_from_email(path)
            elif path.is_dir():
                return self._import_from_folder(path)
            else:
                result.add_error(f"Unsupported file type: {path.suffix}")
                return result
        except Exception as e:
            result.add_error(f"Import failed: {str(e)}")
            return result

    def _import_from_csv(self, csv_path: Path) -> ImportResult:
        """Import from Zillow Premier Agent CSV export."""
        result = ImportResult(source=self.source_name)

        # Zillow export column mappings
        column_maps = {
            # Zillow Premier Agent format
            "Contact Name": "name",
            "Email": "email",
            "Phone": "phone",
            "Message": "notes",
            "Property Address": "property_interest",
            "Lead Type": "lead_type",
            "Source": "source_detail",
            "Date": "date",
            # Realtor.com format
            "First Name": "first_name",
            "Last Name": "last_name",
            "Email Address": "email",
            "Phone Number": "phone",
            "Comments": "notes",
            "Listing Address": "property_interest",
        }

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        lead = self._parse_csv_row(row, column_maps, row_num)
                        if lead:
                            result.leads.append(lead)
                    except Exception as e:
                        result.add_warning(f"Row {row_num}: {e}")

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _parse_csv_row(
        self,
        row: Dict[str, str],
        column_maps: Dict[str, str],
        row_num: int
    ) -> Optional[RawLead]:
        """Parse a CSV row into a RawLead."""
        # Map columns
        mapped = {}
        for csv_col, field in column_maps.items():
            if csv_col in row and row[csv_col]:
                mapped[field] = row[csv_col].strip()

        # Handle split name fields
        if "first_name" in mapped or "last_name" in mapped:
            first = mapped.get("first_name", "")
            last = mapped.get("last_name", "")
            mapped["name"] = f"{first} {last}".strip()

        # Build notes with context
        notes_parts = []
        if mapped.get("notes"):
            notes_parts.append(mapped["notes"])
        if mapped.get("property_interest"):
            notes_parts.append(f"Interested in: {mapped['property_interest']}")
        if mapped.get("lead_type"):
            notes_parts.append(f"Lead type: {mapped['lead_type']}")

        if not mapped.get("name") and not mapped.get("email") and not mapped.get("phone"):
            return None

        return RawLead(
            source="zillow",
            source_id=f"zillow_row_{row_num}",
            name=mapped.get("name"),
            email=mapped.get("email", "").lower() if mapped.get("email") else None,
            phone=mapped.get("phone"),
            notes="\n".join(notes_parts) if notes_parts else None,
            raw_data=dict(row)
        )

    def _import_from_email(self, email_path: Path) -> ImportResult:
        """Import lead from a single email file."""
        result = ImportResult(source=self.source_name)

        try:
            with open(email_path, 'rb') as f:
                msg = BytesParser(policy=policy.default).parse(f)

            lead = self._parse_lead_email(msg)
            if lead:
                result.leads.append(lead)
            else:
                result.add_warning(f"Could not extract lead from: {email_path.name}")

        except Exception as e:
            result.add_error(f"Error parsing email: {e}")

        return result

    def _import_from_folder(self, folder_path: Path) -> ImportResult:
        """Import from a folder of email files or CSVs."""
        result = ImportResult(source=self.source_name)

        # Process CSV files
        for csv_file in folder_path.glob("*.csv"):
            csv_result = self._import_from_csv(csv_file)
            result.leads.extend(csv_result.leads)
            result.warnings.extend(csv_result.warnings)

        # Process email files
        for email_file in folder_path.glob("*.eml"):
            email_result = self._import_from_email(email_file)
            result.leads.extend(email_result.leads)
            result.warnings.extend(email_result.warnings)

        return result

    def _parse_lead_email(self, msg) -> Optional[RawLead]:
        """Extract lead info from a Zillow/portal notification email."""
        subject = msg.get("Subject", "").lower()

        # Check if this looks like a lead email
        is_lead_email = any(
            re.search(pattern, subject)
            for pattern in self.LEAD_EMAIL_PATTERNS
        )

        if not is_lead_email:
            return None

        # Get email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()

        # Extract lead details from body
        name = self._extract_field(body, ["name:", "contact:", "from:"])
        email = self._extract_email(body)
        phone = self._extract_phone(body)
        message = self._extract_field(body, ["message:", "comments:", "inquiry:"])
        property_addr = self._extract_field(body, ["property:", "address:", "listing:"])

        if not any([name, email, phone]):
            return None

        notes_parts = []
        if message:
            notes_parts.append(message)
        if property_addr:
            notes_parts.append(f"Property interest: {property_addr}")

        return RawLead(
            source="zillow",
            source_id=msg.get("Message-ID"),
            name=name,
            email=email,
            phone=phone,
            notes="\n".join(notes_parts) if notes_parts else None,
            raw_data={"subject": msg.get("Subject"), "date": msg.get("Date")}
        )

    def _extract_field(self, text: str, labels: List[str]) -> Optional[str]:
        """Extract a field value following a label."""
        for label in labels:
            pattern = rf"{re.escape(label)}\s*(.+?)(?:\n|$)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email address from text."""
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(pattern, text)
        return match.group(0).lower() if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text."""
        # Match various phone formats
        patterns = [
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\d{10}',
            r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None


class RealtorDotComConnector(ZillowConnector):
    """Import from Realtor.com (same format as Zillow)."""
    source_name = "realtor.com"


class HomesDotComConnector(ZillowConnector):
    """Import from Homes.com (same format as Zillow)."""
    source_name = "homes.com"
