"""Website lead connector - imports leads from JSON Lines, JSON, or CSV files."""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Iterator, Dict, Any

from .base import BaseConnector, ImportResult, RawLead


class WebsiteConnector(BaseConnector):
    """Import website leads from exported event files."""

    source_name = "website"

    def import_from_path(self, path: Path) -> ImportResult:
        """Import website leads from file."""
        result = ImportResult(source="website")
        error = self.validate_path(path)
        if error:
            result.add_error(error)
            return result

        try:
            if path.suffix == ".jsonl":
                parser = self._parse_jsonl
            elif path.suffix == ".json":
                parser = self._parse_json_array
            elif path.suffix == ".csv":
                parser = self._parse_csv
            else:
                result.add_error(f"Unsupported file format: {path.suffix}. Use .jsonl, .json, or .csv")
                return result

            for event_data in parser(path):
                try:
                    raw_lead = self._event_to_raw_lead(event_data)
                    if raw_lead:
                        result.leads.append(raw_lead)
                except Exception as e:
                    result.add_warning(f"Skipped event: {e}")

        except Exception as e:
            result.add_error(f"Failed to parse file: {e}")

        return result

    def _parse_jsonl(self, path: Path) -> Iterator[Dict[str, Any]]:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def _parse_json_array(self, path: Path) -> Iterator[Dict[str, Any]]:
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                yield from data
            else:
                yield data

    def _parse_csv(self, path: Path) -> Iterator[Dict[str, Any]]:
        with open(path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield {
                    "lead_id": row.get("lead_id"),
                    "timestamp": row.get("timestamp"),
                    "event_name": row.get("event_name", "contact_submit"),
                    "source": "website",
                    "contact": {
                        "email": row.get("email"),
                        "phone": row.get("phone"),
                        "first_name": row.get("first_name"),
                        "last_name": row.get("last_name"),
                    },
                    "event_data": {
                        "message": row.get("message"),
                        "page_path": row.get("page_path"),
                    },
                    "attribution": {
                        "utm_source": row.get("utm_source"),
                        "utm_medium": row.get("utm_medium"),
                        "utm_campaign": row.get("utm_campaign"),
                    },
                }

    def _event_to_raw_lead(self, event: dict) -> RawLead:
        """Convert a website event dict to a RawLead."""
        contact = event.get("contact", {})
        email = contact.get("email")
        phone = contact.get("phone")

        if not email and not phone:
            return None

        first = contact.get("first_name", "")
        last = contact.get("last_name", "")
        name = f"{first} {last}".strip() or None

        event_data = event.get("event_data", {})
        notes_parts = []
        if event.get("event_name"):
            notes_parts.append(f"[website] Event: {event['event_name']}")
        if event_data.get("message"):
            notes_parts.append(f"Message: {event_data['message']}")
        if event_data.get("page_path"):
            notes_parts.append(f"Page: {event_data['page_path']}")
        if event_data.get("calculator_type"):
            notes_parts.append(f"Calculator: {event_data['calculator_type']}")

        return RawLead(
            source="website",
            source_id=event.get("lead_id"),
            name=name,
            email=email.lower() if email else None,
            phone=phone,
            notes="\n".join(notes_parts) if notes_parts else None,
            raw_data=event,
        )
