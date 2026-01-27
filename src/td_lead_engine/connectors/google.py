"""Google data sources connector.

Imports leads from:
- Google Business Profile (formerly Google My Business) messages
- Google Forms submissions
- Google Contacts export
- Google Ads lead form exports
"""

import csv
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .base import BaseConnector, ImportResult, RawLead


class GoogleBusinessConnector(BaseConnector):
    """Import leads from Google Business Profile."""

    source_name = "google_business"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Google Business takeout or message export."""
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
                return self._import_from_takeout(path)
            else:
                result.add_error(f"Unsupported file type: {path.suffix}")
                return result
        except Exception as e:
            result.add_error(f"Import failed: {str(e)}")
            return result

    def _import_from_takeout(self, folder_path: Path) -> ImportResult:
        """Import from Google Takeout folder structure."""
        result = ImportResult(source=self.source_name)

        # Look for Business Profile data
        business_paths = [
            folder_path / "Google Business Profile",
            folder_path / "My Business",
            folder_path / "Google My Business",
        ]

        for bp in business_paths:
            if bp.exists():
                # Import messages
                messages_file = bp / "Messages.json"
                if messages_file.exists():
                    json_result = self._import_from_json(messages_file)
                    result.leads.extend(json_result.leads)

                # Import reviews (reviewers are potential leads)
                reviews_file = bp / "Reviews.json"
                if reviews_file.exists():
                    reviews_result = self._import_reviews(reviews_file)
                    result.leads.extend(reviews_result.leads)

        # Also check for Google Contacts
        contacts_path = folder_path / "Contacts" / "All Contacts" / "All Contacts.csv"
        if contacts_path.exists():
            contacts_result = GoogleContactsConnector().import_from_path(contacts_path)
            result.leads.extend(contacts_result.leads)

        if not result.leads:
            result.add_warning("No Google Business leads found in takeout")

        return result

    def _import_from_json(self, json_path: Path) -> ImportResult:
        """Import from Google Business Messages JSON."""
        result = ImportResult(source=self.source_name)

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            conversations = data if isinstance(data, list) else data.get("conversations", [])

            for conv in conversations:
                lead = self._parse_conversation(conv)
                if lead:
                    result.leads.append(lead)

        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON: {e}")
        except Exception as e:
            result.add_error(f"Error reading file: {e}")

        return result

    def _import_from_csv(self, csv_path: Path) -> ImportResult:
        """Import from Google Business leads CSV export."""
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

    def _parse_conversation(self, conv: Dict[str, Any]) -> Optional[RawLead]:
        """Parse a Google Business conversation into a lead."""
        # Extract customer info
        customer = conv.get("customer", conv.get("participant", {}))
        name = customer.get("displayName", customer.get("name"))
        phone = customer.get("phoneNumber")

        # Collect messages
        messages = []
        for msg in conv.get("messages", []):
            if msg.get("sender") != "business":
                content = msg.get("text", msg.get("content", ""))
                if content:
                    messages.append(content)

        if not name and not phone and not messages:
            return None

        return RawLead(
            source="google_business",
            source_id=conv.get("conversationId"),
            name=name,
            phone=phone,
            messages=messages,
            raw_data=conv
        )

    def _parse_csv_row(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a CSV row into a lead."""
        name = row.get("Name", row.get("Customer Name", "")).strip()
        email = row.get("Email", "").strip().lower()
        phone = row.get("Phone", row.get("Phone Number", "")).strip()
        message = row.get("Message", row.get("Inquiry", "")).strip()

        if not any([name, email, phone]):
            return None

        return RawLead(
            source="google_business",
            source_id=f"gbp_row_{row_num}",
            name=name or None,
            email=email or None,
            phone=phone or None,
            notes=message or None,
            raw_data=dict(row)
        )

    def _import_reviews(self, reviews_path: Path) -> ImportResult:
        """Import reviewers as potential leads."""
        result = ImportResult(source=self.source_name)

        try:
            with open(reviews_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            reviews = data if isinstance(data, list) else data.get("reviews", [])

            for review in reviews:
                reviewer = review.get("reviewer", {})
                name = reviewer.get("displayName")
                rating = review.get("starRating", review.get("rating"))
                comment = review.get("comment", review.get("text", ""))

                if name:
                    notes = f"Google Review: {rating} stars"
                    if comment:
                        notes += f"\n{comment}"

                    result.leads.append(RawLead(
                        source="google_business",
                        source_id=review.get("reviewId"),
                        name=name,
                        notes=notes,
                        raw_data=review
                    ))

        except Exception as e:
            result.add_warning(f"Error reading reviews: {e}")

        return result


class GoogleContactsConnector(BaseConnector):
    """Import from Google Contacts export."""

    source_name = "google_contacts"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Google Contacts CSV export."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        if not path.suffix.lower() == ".csv":
            result.add_error("Expected CSV file")
            return result

        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    lead = self._parse_contact(row, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _parse_contact(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a Google Contacts row."""
        # Google Contacts export column names
        first = row.get("First Name", row.get("Given Name", "")).strip()
        last = row.get("Last Name", row.get("Family Name", "")).strip()
        name = f"{first} {last}".strip()

        # Can have multiple email fields
        email = None
        for key in ["E-mail 1 - Value", "Email", "E-mail Address"]:
            if key in row and row[key]:
                email = row[key].strip().lower()
                break

        # Can have multiple phone fields
        phone = None
        for key in ["Phone 1 - Value", "Phone", "Mobile Phone"]:
            if key in row and row[key]:
                phone = row[key].strip()
                break

        notes = row.get("Notes", "").strip()

        if not any([name, email, phone]):
            return None

        return RawLead(
            source="google_contacts",
            source_id=f"gc_{row_num}",
            name=name or None,
            email=email,
            phone=phone,
            notes=notes or None,
            raw_data=dict(row)
        )


class GoogleFormsConnector(BaseConnector):
    """Import from Google Forms responses."""

    source_name = "google_forms"

    # Common form field patterns for real estate
    FIELD_PATTERNS = {
        "name": ["name", "full name", "your name", "contact name"],
        "email": ["email", "email address", "e-mail"],
        "phone": ["phone", "phone number", "mobile", "cell"],
        "notes": ["message", "comments", "questions", "tell us more", "how can we help"],
        "timeline": ["timeline", "when", "timeframe", "move date"],
        "budget": ["budget", "price range", "how much"],
        "location": ["area", "location", "neighborhood", "where"],
    }

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Google Forms CSV export."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        if not path.suffix.lower() == ".csv":
            result.add_error("Expected CSV file from Google Forms")
            return result

        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                # Map form fields to standard fields
                field_map = self._map_form_fields(headers)

                for row_num, row in enumerate(reader, start=2):
                    lead = self._parse_response(row, field_map, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _map_form_fields(self, headers: List[str]) -> Dict[str, str]:
        """Map form headers to standard field names."""
        field_map = {}

        for header in headers:
            header_lower = header.lower()
            for field, patterns in self.FIELD_PATTERNS.items():
                if any(p in header_lower for p in patterns):
                    field_map[header] = field
                    break

        return field_map

    def _parse_response(
        self,
        row: Dict[str, str],
        field_map: Dict[str, str],
        row_num: int
    ) -> Optional[RawLead]:
        """Parse a form response into a lead."""
        mapped = {}
        extra_notes = []

        for header, value in row.items():
            if not value:
                continue

            field = field_map.get(header)
            if field:
                if field == "notes":
                    extra_notes.append(f"{header}: {value}")
                elif field in ["timeline", "budget", "location"]:
                    extra_notes.append(f"{header}: {value}")
                else:
                    mapped[field] = value.strip()
            elif header != "Timestamp":
                # Include unmapped fields in notes
                extra_notes.append(f"{header}: {value}")

        if not any([mapped.get("name"), mapped.get("email"), mapped.get("phone")]):
            return None

        notes = "\n".join(extra_notes) if extra_notes else None

        return RawLead(
            source="google_forms",
            source_id=f"gf_{row_num}_{row.get('Timestamp', '')}",
            name=mapped.get("name"),
            email=mapped.get("email", "").lower() if mapped.get("email") else None,
            phone=mapped.get("phone"),
            notes=notes,
            raw_data=dict(row)
        )


class GoogleAdsConnector(BaseConnector):
    """Import from Google Ads lead form extensions."""

    source_name = "google_ads"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Google Ads lead export."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    lead = self._parse_ad_lead(row, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _parse_ad_lead(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a Google Ads lead form submission."""
        # Google Ads lead form columns
        name = row.get("Full Name", row.get("Name", "")).strip()
        email = row.get("Email", row.get("User Email", "")).strip().lower()
        phone = row.get("Phone Number", row.get("Phone", "")).strip()

        # Campaign info for context
        campaign = row.get("Campaign", "")
        ad_group = row.get("Ad Group", "")

        if not any([name, email, phone]):
            return None

        notes = f"Google Ads Lead - Campaign: {campaign}" if campaign else "Google Ads Lead"
        if ad_group:
            notes += f", Ad Group: {ad_group}"

        return RawLead(
            source="google_ads",
            source_id=row.get("Lead ID", f"gads_{row_num}"),
            name=name or None,
            email=email or None,
            phone=phone or None,
            notes=notes,
            raw_data=dict(row)
        )
