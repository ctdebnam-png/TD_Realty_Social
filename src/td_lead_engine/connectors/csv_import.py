"""CSV/manual import connector."""

import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

from .base import BaseConnector, ImportResult, RawLead


class CSVConnector(BaseConnector):
    """Import leads from CSV files (manual contacts, exports, etc)."""

    source_name = "csv"

    # Standard column name mappings (case-insensitive)
    COLUMN_MAPPINGS = {
        "name": ["name", "full_name", "fullname", "contact_name", "contact"],
        "email": ["email", "email_address", "e-mail", "emailaddress"],
        "phone": ["phone", "phone_number", "phonenumber", "mobile", "cell", "telephone"],
        "notes": ["notes", "note", "comments", "comment", "description", "bio", "about"],
        "source_id": ["id", "source_id", "contact_id", "lead_id"],
        "username": ["username", "user_name", "handle", "social_handle"],
    }

    def import_from_path(self, path: Path) -> ImportResult:
        """Import from a CSV file."""
        result = ImportResult(source=self.source_name)

        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        if not path.suffix.lower() == ".csv":
            result.add_error(f"Expected .csv file, got: {path.suffix}")
            return result

        try:
            with open(path, 'r', encoding='utf-8-sig', newline='') as f:
                # Try to detect delimiter
                sample = f.read(4096)
                f.seek(0)

                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel  # Default to standard CSV

                reader = csv.DictReader(f, dialect=dialect)

                if not reader.fieldnames:
                    result.add_error("CSV file has no headers")
                    return result

                # Map columns
                column_map = self._map_columns(reader.fieldnames)

                if not column_map:
                    result.add_warning(
                        f"Could not map any standard columns. Headers found: {reader.fieldnames}"
                    )

                row_num = 1
                for row in reader:
                    row_num += 1
                    try:
                        lead = self._parse_row(row, column_map, row_num)
                        if lead:
                            result.leads.append(lead)
                    except Exception as e:
                        result.add_warning(f"Error parsing row {row_num}: {e}")

            if not result.leads:
                result.add_warning("No valid leads found in CSV")

        except UnicodeDecodeError:
            # Try with latin-1 encoding
            try:
                result = self._import_with_encoding(path, 'latin-1')
            except Exception as e:
                result.add_error(f"Could not read CSV with any encoding: {e}")
        except Exception as e:
            result.add_error(f"Error reading CSV: {e}")

        return result

    def _import_with_encoding(self, path: Path, encoding: str) -> ImportResult:
        """Import with specific encoding."""
        result = ImportResult(source=self.source_name)

        with open(path, 'r', encoding=encoding, newline='') as f:
            reader = csv.DictReader(f)
            column_map = self._map_columns(reader.fieldnames or [])

            row_num = 1
            for row in reader:
                row_num += 1
                try:
                    lead = self._parse_row(row, column_map, row_num)
                    if lead:
                        result.leads.append(lead)
                except Exception as e:
                    result.add_warning(f"Error parsing row {row_num}: {e}")

        return result

    def _map_columns(self, fieldnames: List[str]) -> Dict[str, str]:
        """Map CSV columns to standard field names."""
        column_map = {}
        fieldnames_lower = {f.lower().strip(): f for f in fieldnames}

        for standard_name, possible_names in self.COLUMN_MAPPINGS.items():
            for possible in possible_names:
                if possible in fieldnames_lower:
                    column_map[standard_name] = fieldnames_lower[possible]
                    break

        return column_map

    def _parse_row(
        self,
        row: Dict[str, Any],
        column_map: Dict[str, str],
        row_num: int
    ) -> Optional[RawLead]:
        """Parse a single CSV row into a RawLead."""

        def get_value(field: str) -> Optional[str]:
            if field in column_map:
                val = row.get(column_map[field], "").strip()
                return val if val else None
            return None

        name = get_value("name")
        email = get_value("email")
        phone = get_value("phone")
        notes = get_value("notes")
        source_id = get_value("source_id")
        username = get_value("username")

        # Must have at least one identifying field
        if not any([name, email, phone, username]):
            return None

        # Clean phone number
        if phone:
            phone = self._clean_phone(phone)

        # Clean email
        if email:
            email = email.lower().strip()

        return RawLead(
            source="manual",  # Mark CSV imports as manual
            source_id=source_id or f"csv_row_{row_num}",
            name=name,
            email=email,
            phone=phone,
            username=username,
            notes=notes,
            raw_data=dict(row)
        )

    def _clean_phone(self, phone: str) -> str:
        """Clean and normalize phone number."""
        # Remove common formatting characters
        cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')

        # Handle US numbers
        if len(cleaned) == 10:
            return f"+1{cleaned}"
        elif len(cleaned) == 11 and cleaned.startswith("1"):
            return f"+{cleaned}"

        return cleaned if cleaned else phone


class ManualConnector(CSVConnector):
    """Alias for CSVConnector for clarity."""

    source_name = "manual"
