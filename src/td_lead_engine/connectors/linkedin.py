"""LinkedIn data connector.

Imports leads from:
- LinkedIn connections export
- LinkedIn messages export
- Sales Navigator exports
"""

import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import BaseConnector, ImportResult, RawLead


class LinkedInConnector(BaseConnector):
    """Import leads from LinkedIn data export."""

    source_name = "linkedin"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from LinkedIn data export folder or CSV."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            if path.suffix.lower() == ".csv":
                return self._import_from_csv(path)
            elif path.is_dir():
                return self._import_from_folder(path)
            else:
                result.add_error(f"Expected CSV file or folder, got: {path.suffix}")
                return result
        except Exception as e:
            result.add_error(f"Import failed: {str(e)}")
            return result

    def _import_from_folder(self, folder_path: Path) -> ImportResult:
        """Import from LinkedIn data export folder."""
        result = ImportResult(source=self.source_name)

        # LinkedIn export structure
        connections_file = folder_path / "Connections.csv"
        messages_file = folder_path / "messages.csv"

        if connections_file.exists():
            conn_result = self._import_connections(connections_file)
            result.leads.extend(conn_result.leads)
            result.warnings.extend(conn_result.warnings)

        if messages_file.exists():
            msg_result = self._import_messages(messages_file)
            # Merge message data with existing leads
            self._merge_messages(result.leads, msg_result.leads)

        if not result.leads:
            result.add_warning("No LinkedIn leads found")

        return result

    def _import_from_csv(self, csv_path: Path) -> ImportResult:
        """Detect CSV type and import accordingly."""
        result = ImportResult(source=self.source_name)

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []

                if "First Name" in headers and "Company" in headers:
                    # Connections export
                    return self._import_connections(csv_path)
                elif "CONVERSATION ID" in headers or "From" in headers:
                    # Messages export
                    return self._import_messages(csv_path)
                else:
                    # Try generic import
                    return self._import_generic_csv(csv_path)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")
            return result

    def _import_connections(self, csv_path: Path) -> ImportResult:
        """Import from LinkedIn Connections.csv."""
        result = ImportResult(source=self.source_name)

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    lead = self._parse_connection(row, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading connections: {e}")

        return result

    def _parse_connection(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a LinkedIn connection row."""
        first = row.get("First Name", "").strip()
        last = row.get("Last Name", "").strip()
        name = f"{first} {last}".strip()

        email = row.get("Email Address", "").strip().lower()
        company = row.get("Company", "").strip()
        position = row.get("Position", "").strip()
        connected_on = row.get("Connected On", "").strip()

        if not name:
            return None

        # Build profile context
        notes_parts = []
        if position:
            notes_parts.append(f"Position: {position}")
        if company:
            notes_parts.append(f"Company: {company}")
        if connected_on:
            notes_parts.append(f"Connected: {connected_on}")

        # Generate LinkedIn URL from name (approximation)
        username_guess = f"{first.lower()}-{last.lower()}".replace(" ", "-")

        return RawLead(
            source="linkedin",
            source_id=f"li_conn_{row_num}",
            name=name,
            email=email or None,
            username=username_guess,
            bio=f"{position} at {company}" if position and company else position or company,
            notes="\n".join(notes_parts) if notes_parts else None,
            profile_url=f"https://linkedin.com/in/{username_guess}",
            raw_data=dict(row)
        )

    def _import_messages(self, csv_path: Path) -> ImportResult:
        """Import from LinkedIn messages.csv."""
        result = ImportResult(source=self.source_name)

        conversations: Dict[str, List[str]] = {}

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    sender = row.get("From", row.get("FROM", "")).strip()
                    content = row.get("Content", row.get("CONTENT", "")).strip()

                    if sender and content:
                        if sender not in conversations:
                            conversations[sender] = []
                        conversations[sender].append(content)

            # Create leads from conversations
            for sender, messages in conversations.items():
                result.leads.append(RawLead(
                    source="linkedin",
                    name=sender,
                    messages=messages[:50],  # Limit messages
                    raw_data={"sender": sender, "message_count": len(messages)}
                ))

        except Exception as e:
            result.add_error(f"Error reading messages: {e}")

        return result

    def _import_generic_csv(self, csv_path: Path) -> ImportResult:
        """Import from a generic LinkedIn-style CSV."""
        result = ImportResult(source=self.source_name)

        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=2):
                    # Try to find name/email/company fields
                    name = (
                        row.get("Name") or
                        row.get("Full Name") or
                        f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
                    )
                    email = row.get("Email", row.get("Email Address", "")).strip().lower()

                    if name or email:
                        result.leads.append(RawLead(
                            source="linkedin",
                            source_id=f"li_generic_{row_num}",
                            name=name or None,
                            email=email or None,
                            raw_data=dict(row)
                        ))

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _merge_messages(self, connections: List[RawLead], message_leads: List[RawLead]):
        """Merge message data into connection leads."""
        # Create lookup by name
        conn_by_name = {lead.name.lower(): lead for lead in connections if lead.name}

        for msg_lead in message_leads:
            if msg_lead.name and msg_lead.name.lower() in conn_by_name:
                conn = conn_by_name[msg_lead.name.lower()]
                conn.messages.extend(msg_lead.messages)


class SalesNavigatorConnector(BaseConnector):
    """Import from LinkedIn Sales Navigator export."""

    source_name = "sales_navigator"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from Sales Navigator CSV export."""
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
                    lead = self._parse_lead(row, row_num)
                    if lead:
                        result.leads.append(lead)

        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _parse_lead(self, row: Dict[str, str], row_num: int) -> Optional[RawLead]:
        """Parse a Sales Navigator lead."""
        first = row.get("First Name", "").strip()
        last = row.get("Last Name", "").strip()
        name = f"{first} {last}".strip()

        email = row.get("Email", "").strip().lower()
        phone = row.get("Phone", row.get("Phone Number", "")).strip()
        company = row.get("Company", row.get("Account Name", "")).strip()
        title = row.get("Title", row.get("Job Title", "")).strip()
        linkedin_url = row.get("LinkedIn URL", row.get("Profile URL", "")).strip()

        if not name and not email:
            return None

        notes_parts = []
        if title:
            notes_parts.append(f"Title: {title}")
        if company:
            notes_parts.append(f"Company: {company}")

        # Sales Navigator specific fields
        if row.get("Lead Status"):
            notes_parts.append(f"SN Status: {row['Lead Status']}")
        if row.get("Tags"):
            notes_parts.append(f"Tags: {row['Tags']}")

        return RawLead(
            source="sales_navigator",
            source_id=row.get("Lead ID", f"sn_{row_num}"),
            name=name or None,
            email=email or None,
            phone=phone or None,
            bio=f"{title} at {company}" if title and company else title or company,
            notes="\n".join(notes_parts) if notes_parts else None,
            profile_url=linkedin_url or None,
            raw_data=dict(row)
        )
