"""Calendar integrations for scheduling."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

import requests

logger = logging.getLogger(__name__)


@dataclass
class Appointment:
    """Scheduled appointment."""

    id: str
    title: str
    lead_id: Optional[str]
    lead_name: str
    lead_email: Optional[str]
    lead_phone: Optional[str]

    start_time: datetime
    end_time: datetime
    duration_minutes: int

    appointment_type: str  # "showing", "listing_presentation", "buyer_consultation", "phone_call"
    location: str = ""
    notes: str = ""

    # Status
    status: str = "scheduled"  # scheduled, confirmed, cancelled, completed, no_show
    reminder_sent: bool = False

    # External calendar
    calendar_event_id: Optional[str] = None
    calendar_provider: Optional[str] = None  # "google", "calendly"

    created_at: datetime = field(default_factory=datetime.now)


class CalendlyIntegration:
    """Integration with Calendly for scheduling."""

    def __init__(self):
        """Initialize Calendly integration."""
        self.api_key = os.environ.get("CALENDLY_API_KEY")
        self.user_uri = os.environ.get("CALENDLY_USER_URI")
        self.base_url = "https://api.calendly.com"

        # Event type URLs for booking links
        self.event_types = {
            "buyer_consultation": os.environ.get("CALENDLY_BUYER_CONSULT_URL"),
            "seller_consultation": os.environ.get("CALENDLY_SELLER_CONSULT_URL"),
            "showing": os.environ.get("CALENDLY_SHOWING_URL"),
            "phone_call": os.environ.get("CALENDLY_PHONE_URL"),
        }

    def get_booking_link(self, event_type: str, lead_email: Optional[str] = None) -> Optional[str]:
        """Get booking link for an event type."""
        base_url = self.event_types.get(event_type)
        if not base_url:
            return None

        if lead_email:
            return f"{base_url}?email={lead_email}"

        return base_url

    def get_scheduled_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get scheduled events from Calendly."""
        if not self.api_key:
            logger.warning("Calendly API key not configured")
            return []

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {
                "user": self.user_uri,
                "min_start_time": start_date.isoformat() + "Z",
                "max_start_time": end_date.isoformat() + "Z",
                "status": "active"
            }

            response = requests.get(
                f"{self.base_url}/scheduled_events",
                headers=headers,
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("collection", [])

        except Exception as e:
            logger.error(f"Calendly API error: {e}")

        return []

    def get_invitee_info(self, event_uri: str) -> Optional[Dict[str, Any]]:
        """Get invitee information for an event."""
        if not self.api_key:
            return None

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(
                f"{event_uri}/invitees",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                invitees = data.get("collection", [])
                return invitees[0] if invitees else None

        except Exception as e:
            logger.error(f"Calendly invitee error: {e}")

        return None

    def parse_webhook_event(self, payload: Dict[str, Any]) -> Optional[Appointment]:
        """Parse Calendly webhook payload into Appointment."""
        try:
            event = payload.get("payload", {})
            invitee = event.get("invitee", {})

            start_time = datetime.fromisoformat(
                event.get("scheduled_event", {}).get("start_time", "").replace("Z", "+00:00")
            )
            end_time = datetime.fromisoformat(
                event.get("scheduled_event", {}).get("end_time", "").replace("Z", "+00:00")
            )

            duration = int((end_time - start_time).total_seconds() / 60)

            return Appointment(
                id=str(uuid.uuid4())[:8],
                title=event.get("scheduled_event", {}).get("name", "Appointment"),
                lead_id=None,
                lead_name=invitee.get("name", ""),
                lead_email=invitee.get("email"),
                lead_phone=self._extract_phone_from_questions(invitee.get("questions_and_answers", [])),
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration,
                appointment_type=self._infer_appointment_type(event.get("scheduled_event", {}).get("name", "")),
                location=event.get("scheduled_event", {}).get("location", {}).get("location", ""),
                calendar_event_id=event.get("scheduled_event", {}).get("uri"),
                calendar_provider="calendly"
            )

        except Exception as e:
            logger.error(f"Error parsing Calendly webhook: {e}")
            return None

    def _extract_phone_from_questions(self, questions: List[Dict]) -> Optional[str]:
        """Extract phone number from Calendly questions."""
        for q in questions:
            question = q.get("question", "").lower()
            if "phone" in question or "number" in question or "mobile" in question:
                return q.get("answer")
        return None

    def _infer_appointment_type(self, event_name: str) -> str:
        """Infer appointment type from event name."""
        name_lower = event_name.lower()
        if "show" in name_lower:
            return "showing"
        elif "seller" in name_lower or "list" in name_lower or "cma" in name_lower:
            return "listing_presentation"
        elif "buyer" in name_lower or "consult" in name_lower:
            return "buyer_consultation"
        elif "call" in name_lower or "phone" in name_lower:
            return "phone_call"
        return "meeting"


class GoogleCalendarIntegration:
    """Integration with Google Calendar."""

    def __init__(self):
        """Initialize Google Calendar integration."""
        self.client_id = os.environ.get("GOOGLE_CLIENT_ID")
        self.client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
        self.calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        self._credentials = None
        self._service = None

    def _get_service(self):
        """Get or create Google Calendar service."""
        if self._service:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            # Load credentials from stored tokens
            token_path = Path.home() / ".td-lead-engine" / "google_token.json"

            if token_path.exists():
                self._credentials = Credentials.from_authorized_user_file(str(token_path))

            if self._credentials:
                self._service = build("calendar", "v3", credentials=self._credentials)

            return self._service

        except ImportError:
            logger.warning("Google API client not installed")
            return None
        except Exception as e:
            logger.error(f"Google Calendar error: {e}")
            return None

    def create_event(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        attendee_email: Optional[str] = None,
        location: str = "",
        description: str = ""
    ) -> Optional[str]:
        """Create a calendar event."""
        service = self._get_service()
        if not service:
            return None

        try:
            end_time = start_time + timedelta(minutes=duration_minutes)

            event = {
                "summary": title,
                "location": location,
                "description": description,
                "start": {
                    "dateTime": start_time.isoformat(),
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": end_time.isoformat(),
                    "timeZone": "America/New_York"
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": [
                        {"method": "email", "minutes": 24 * 60},
                        {"method": "popup", "minutes": 30}
                    ]
                }
            }

            if attendee_email:
                event["attendees"] = [{"email": attendee_email}]

            created_event = service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                sendUpdates="all" if attendee_email else "none"
            ).execute()

            return created_event.get("id")

        except Exception as e:
            logger.error(f"Error creating Google Calendar event: {e}")
            return None

    def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get calendar events."""
        service = self._get_service()
        if not service:
            return []

        try:
            events_result = service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + "Z",
                timeMax=end_date.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            return events_result.get("items", [])

        except Exception as e:
            logger.error(f"Error getting Google Calendar events: {e}")
            return []

    def get_free_busy(self, start_date: datetime, end_date: datetime) -> List[Dict[str, datetime]]:
        """Get busy time slots."""
        service = self._get_service()
        if not service:
            return []

        try:
            body = {
                "timeMin": start_date.isoformat() + "Z",
                "timeMax": end_date.isoformat() + "Z",
                "items": [{"id": self.calendar_id}]
            }

            freebusy = service.freebusy().query(body=body).execute()
            calendars = freebusy.get("calendars", {})
            busy_slots = calendars.get(self.calendar_id, {}).get("busy", [])

            return [
                {
                    "start": datetime.fromisoformat(slot["start"].replace("Z", "+00:00")),
                    "end": datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
                }
                for slot in busy_slots
            ]

        except Exception as e:
            logger.error(f"Error getting free/busy: {e}")
            return []


class AppointmentManager:
    """Manage appointments across calendar integrations."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize appointment manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "appointments.json"
        self.appointments: Dict[str, Appointment] = {}
        self.calendly = CalendlyIntegration()
        self.google = GoogleCalendarIntegration()
        self._load_data()

    def _load_data(self):
        """Load appointments from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for appt_data in data.get("appointments", []):
                        appt = Appointment(
                            id=appt_data["id"],
                            title=appt_data["title"],
                            lead_id=appt_data.get("lead_id"),
                            lead_name=appt_data["lead_name"],
                            lead_email=appt_data.get("lead_email"),
                            lead_phone=appt_data.get("lead_phone"),
                            start_time=datetime.fromisoformat(appt_data["start_time"]),
                            end_time=datetime.fromisoformat(appt_data["end_time"]),
                            duration_minutes=appt_data["duration_minutes"],
                            appointment_type=appt_data["appointment_type"],
                            location=appt_data.get("location", ""),
                            notes=appt_data.get("notes", ""),
                            status=appt_data.get("status", "scheduled"),
                            calendar_event_id=appt_data.get("calendar_event_id"),
                            calendar_provider=appt_data.get("calendar_provider"),
                            created_at=datetime.fromisoformat(appt_data["created_at"])
                        )
                        self.appointments[appt.id] = appt

            except Exception as e:
                logger.error(f"Error loading appointments: {e}")

    def _save_data(self):
        """Save appointments to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "appointments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "lead_id": a.lead_id,
                    "lead_name": a.lead_name,
                    "lead_email": a.lead_email,
                    "lead_phone": a.lead_phone,
                    "start_time": a.start_time.isoformat(),
                    "end_time": a.end_time.isoformat(),
                    "duration_minutes": a.duration_minutes,
                    "appointment_type": a.appointment_type,
                    "location": a.location,
                    "notes": a.notes,
                    "status": a.status,
                    "calendar_event_id": a.calendar_event_id,
                    "calendar_provider": a.calendar_provider,
                    "created_at": a.created_at.isoformat()
                }
                for a in self.appointments.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def schedule_appointment(
        self,
        lead_id: str,
        lead_name: str,
        lead_email: Optional[str],
        lead_phone: Optional[str],
        appointment_type: str,
        start_time: datetime,
        duration_minutes: int = 60,
        location: str = "",
        notes: str = "",
        add_to_google: bool = True
    ) -> Appointment:
        """Schedule a new appointment."""
        end_time = start_time + timedelta(minutes=duration_minutes)

        # Create title based on type
        type_titles = {
            "showing": f"Property Showing - {lead_name}",
            "listing_presentation": f"Listing Presentation - {lead_name}",
            "buyer_consultation": f"Buyer Consultation - {lead_name}",
            "phone_call": f"Phone Call - {lead_name}",
            "meeting": f"Meeting - {lead_name}"
        }
        title = type_titles.get(appointment_type, f"Appointment - {lead_name}")

        appt = Appointment(
            id=str(uuid.uuid4())[:8],
            title=title,
            lead_id=lead_id,
            lead_name=lead_name,
            lead_email=lead_email,
            lead_phone=lead_phone,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            appointment_type=appointment_type,
            location=location,
            notes=notes
        )

        # Add to Google Calendar
        if add_to_google:
            event_id = self.google.create_event(
                title=title,
                start_time=start_time,
                duration_minutes=duration_minutes,
                attendee_email=lead_email,
                location=location,
                description=notes
            )
            if event_id:
                appt.calendar_event_id = event_id
                appt.calendar_provider = "google"

        self.appointments[appt.id] = appt
        self._save_data()

        return appt

    def get_booking_link(self, appointment_type: str, lead_email: Optional[str] = None) -> Optional[str]:
        """Get a Calendly booking link."""
        return self.calendly.get_booking_link(appointment_type, lead_email)

    def update_status(self, appointment_id: str, status: str) -> bool:
        """Update appointment status."""
        if appointment_id not in self.appointments:
            return False

        self.appointments[appointment_id].status = status
        self._save_data()
        return True

    def get_upcoming(self, days: int = 7) -> List[Appointment]:
        """Get upcoming appointments."""
        now = datetime.now()
        cutoff = now + timedelta(days=days)

        upcoming = [
            a for a in self.appointments.values()
            if a.start_time >= now and a.start_time <= cutoff
            and a.status not in ["cancelled", "completed"]
        ]

        return sorted(upcoming, key=lambda a: a.start_time)

    def get_today(self) -> List[Appointment]:
        """Get today's appointments."""
        today = datetime.now().date()

        return sorted(
            [a for a in self.appointments.values() if a.start_time.date() == today],
            key=lambda a: a.start_time
        )

    def get_by_lead(self, lead_id: str) -> List[Appointment]:
        """Get all appointments for a lead."""
        return sorted(
            [a for a in self.appointments.values() if a.lead_id == lead_id],
            key=lambda a: a.start_time,
            reverse=True
        )

    def get_needs_reminder(self, hours_before: int = 24) -> List[Appointment]:
        """Get appointments needing reminders."""
        now = datetime.now()
        reminder_window = now + timedelta(hours=hours_before)

        return [
            a for a in self.appointments.values()
            if a.start_time <= reminder_window
            and a.start_time > now
            and not a.reminder_sent
            and a.status == "scheduled"
        ]

    def mark_reminder_sent(self, appointment_id: str):
        """Mark that reminder was sent."""
        if appointment_id in self.appointments:
            self.appointments[appointment_id].reminder_sent = True
            self._save_data()

    def sync_from_calendly(self, start_date: datetime, end_date: datetime):
        """Sync appointments from Calendly."""
        events = self.calendly.get_scheduled_events(start_date, end_date)

        for event in events:
            event_uri = event.get("uri")

            # Check if already synced
            existing = [
                a for a in self.appointments.values()
                if a.calendar_event_id == event_uri
            ]
            if existing:
                continue

            # Get invitee info and create appointment
            invitee = self.calendly.get_invitee_info(event_uri)
            if invitee:
                appt = Appointment(
                    id=str(uuid.uuid4())[:8],
                    title=event.get("name", "Appointment"),
                    lead_id=None,
                    lead_name=invitee.get("name", ""),
                    lead_email=invitee.get("email"),
                    lead_phone=None,
                    start_time=datetime.fromisoformat(event.get("start_time", "").replace("Z", "+00:00")),
                    end_time=datetime.fromisoformat(event.get("end_time", "").replace("Z", "+00:00")),
                    duration_minutes=30,
                    appointment_type="meeting",
                    calendar_event_id=event_uri,
                    calendar_provider="calendly"
                )
                self.appointments[appt.id] = appt

        self._save_data()

    def get_availability(self, date: datetime, duration_minutes: int = 60) -> List[Dict[str, datetime]]:
        """Get available time slots for a date."""
        # Business hours: 9 AM to 6 PM
        business_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
        business_end = date.replace(hour=18, minute=0, second=0, microsecond=0)

        # Get busy slots from Google Calendar
        busy_slots = self.google.get_free_busy(business_start, business_end)

        # Get appointments for the day
        day_appts = [
            a for a in self.appointments.values()
            if a.start_time.date() == date.date()
            and a.status not in ["cancelled"]
        ]

        for appt in day_appts:
            busy_slots.append({
                "start": appt.start_time,
                "end": appt.end_time
            })

        # Sort busy slots
        busy_slots.sort(key=lambda x: x["start"])

        # Find available slots
        available = []
        current = business_start

        for busy in busy_slots:
            if current + timedelta(minutes=duration_minutes) <= busy["start"]:
                available.append({
                    "start": current,
                    "end": busy["start"]
                })
            current = max(current, busy["end"])

        # Check end of day
        if current + timedelta(minutes=duration_minutes) <= business_end:
            available.append({
                "start": current,
                "end": business_end
            })

        return available
