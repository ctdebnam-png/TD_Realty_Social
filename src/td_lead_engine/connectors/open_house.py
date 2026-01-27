"""Open house lead capture and QR code generation."""

import json
import logging
import os
import qrcode
import io
import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class OpenHouseEvent:
    """Open house event."""

    id: str
    property_address: str
    property_city: str
    property_state: str = "OH"
    property_zip: str = ""

    listing_price: int = 0
    listing_mls: str = ""

    date: datetime = None
    start_time: str = ""  # "2:00 PM"
    end_time: str = ""    # "4:00 PM"

    host_name: str = ""
    host_phone: str = ""
    host_email: str = ""

    # Sign-in tracking
    sign_ins: List[Dict[str, Any]] = field(default_factory=list)

    # Marketing
    qr_code_url: str = ""
    sign_in_url: str = ""

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OpenHouseSignIn:
    """Visitor sign-in at open house."""

    id: str
    open_house_id: str
    property_address: str

    # Contact info
    name: str
    email: str = ""
    phone: str = ""

    # Buyer info
    is_working_with_agent: bool = False
    agent_name: str = ""
    is_pre_approved: bool = False
    lender_name: str = ""

    # Interest level
    interest_level: str = ""  # "very interested", "interested", "just looking"
    timeline: str = ""        # "ASAP", "1-3 months", "3-6 months", "6+ months"
    price_range: str = ""

    # Marketing consent
    consent_to_contact: bool = True
    consent_to_newsletter: bool = False

    # Notes
    notes: str = ""
    feedback: str = ""

    signed_in_at: datetime = field(default_factory=datetime.now)


class OpenHouseManager:
    """Manage open house events and lead capture."""

    def __init__(self, data_path: Optional[Path] = None, base_url: str = ""):
        """Initialize open house manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "open_houses.json"
        self.base_url = base_url or os.environ.get("TD_ENGINE_BASE_URL", "https://tdrealty.com")
        self.events: Dict[str, OpenHouseEvent] = {}
        self.sign_ins: Dict[str, OpenHouseSignIn] = {}
        self._load_data()

    def _load_data(self):
        """Load events from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for event_data in data.get("events", []):
                        event = OpenHouseEvent(
                            id=event_data["id"],
                            property_address=event_data["property_address"],
                            property_city=event_data["property_city"],
                            property_state=event_data.get("property_state", "OH"),
                            property_zip=event_data.get("property_zip", ""),
                            listing_price=event_data.get("listing_price", 0),
                            listing_mls=event_data.get("listing_mls", ""),
                            date=datetime.fromisoformat(event_data["date"]) if event_data.get("date") else None,
                            start_time=event_data.get("start_time", ""),
                            end_time=event_data.get("end_time", ""),
                            host_name=event_data.get("host_name", ""),
                            host_phone=event_data.get("host_phone", ""),
                            host_email=event_data.get("host_email", ""),
                            qr_code_url=event_data.get("qr_code_url", ""),
                            sign_in_url=event_data.get("sign_in_url", "")
                        )
                        self.events[event.id] = event

                    for signin_data in data.get("sign_ins", []):
                        signin = OpenHouseSignIn(
                            id=signin_data["id"],
                            open_house_id=signin_data["open_house_id"],
                            property_address=signin_data["property_address"],
                            name=signin_data["name"],
                            email=signin_data.get("email", ""),
                            phone=signin_data.get("phone", ""),
                            is_working_with_agent=signin_data.get("is_working_with_agent", False),
                            agent_name=signin_data.get("agent_name", ""),
                            is_pre_approved=signin_data.get("is_pre_approved", False),
                            interest_level=signin_data.get("interest_level", ""),
                            timeline=signin_data.get("timeline", ""),
                            consent_to_contact=signin_data.get("consent_to_contact", True),
                            signed_in_at=datetime.fromisoformat(signin_data["signed_in_at"])
                        )
                        self.sign_ins[signin.id] = signin

            except Exception as e:
                logger.error(f"Error loading open house data: {e}")

    def _save_data(self):
        """Save events to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "events": [
                {
                    "id": e.id,
                    "property_address": e.property_address,
                    "property_city": e.property_city,
                    "property_state": e.property_state,
                    "property_zip": e.property_zip,
                    "listing_price": e.listing_price,
                    "listing_mls": e.listing_mls,
                    "date": e.date.isoformat() if e.date else None,
                    "start_time": e.start_time,
                    "end_time": e.end_time,
                    "host_name": e.host_name,
                    "host_phone": e.host_phone,
                    "host_email": e.host_email,
                    "qr_code_url": e.qr_code_url,
                    "sign_in_url": e.sign_in_url
                }
                for e in self.events.values()
            ],
            "sign_ins": [
                {
                    "id": s.id,
                    "open_house_id": s.open_house_id,
                    "property_address": s.property_address,
                    "name": s.name,
                    "email": s.email,
                    "phone": s.phone,
                    "is_working_with_agent": s.is_working_with_agent,
                    "agent_name": s.agent_name,
                    "is_pre_approved": s.is_pre_approved,
                    "interest_level": s.interest_level,
                    "timeline": s.timeline,
                    "consent_to_contact": s.consent_to_contact,
                    "signed_in_at": s.signed_in_at.isoformat()
                }
                for s in self.sign_ins.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_event(
        self,
        property_address: str,
        property_city: str,
        date: datetime,
        start_time: str,
        end_time: str,
        listing_price: int = 0,
        host_name: str = "",
        host_email: str = ""
    ) -> OpenHouseEvent:
        """Create a new open house event."""
        event_id = str(uuid.uuid4())[:8]

        # Generate sign-in URL
        sign_in_url = f"{self.base_url}/open-house/{event_id}"

        event = OpenHouseEvent(
            id=event_id,
            property_address=property_address,
            property_city=property_city,
            date=date,
            start_time=start_time,
            end_time=end_time,
            listing_price=listing_price,
            host_name=host_name,
            host_email=host_email,
            sign_in_url=sign_in_url
        )

        self.events[event_id] = event
        self._save_data()

        return event

    def generate_qr_code(self, event_id: str) -> Optional[str]:
        """Generate QR code for event sign-in.

        Returns base64-encoded PNG image.
        """
        event = self.events.get(event_id)
        if not event:
            return None

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4
            )

            qr.add_data(event.sign_in_url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except ImportError:
            logger.warning("qrcode library not installed")
            return None
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None

    def record_sign_in(
        self,
        event_id: str,
        name: str,
        email: str = "",
        phone: str = "",
        is_working_with_agent: bool = False,
        agent_name: str = "",
        is_pre_approved: bool = False,
        interest_level: str = "",
        timeline: str = "",
        consent_to_contact: bool = True,
        notes: str = ""
    ) -> Optional[OpenHouseSignIn]:
        """Record a visitor sign-in."""
        event = self.events.get(event_id)
        if not event:
            return None

        signin = OpenHouseSignIn(
            id=str(uuid.uuid4())[:8],
            open_house_id=event_id,
            property_address=event.property_address,
            name=name,
            email=email,
            phone=phone,
            is_working_with_agent=is_working_with_agent,
            agent_name=agent_name,
            is_pre_approved=is_pre_approved,
            interest_level=interest_level,
            timeline=timeline,
            consent_to_contact=consent_to_contact,
            notes=notes
        )

        self.sign_ins[signin.id] = signin
        self._save_data()

        logger.info(f"Recorded sign-in: {name} at {event.property_address}")
        return signin

    def get_event_signins(self, event_id: str) -> List[OpenHouseSignIn]:
        """Get all sign-ins for an event."""
        return [s for s in self.sign_ins.values() if s.open_house_id == event_id]

    def get_qualified_leads(self, event_id: str) -> List[OpenHouseSignIn]:
        """Get qualified leads from an open house.

        Qualified = not working with agent AND interested.
        """
        signins = self.get_event_signins(event_id)

        return [
            s for s in signins
            if not s.is_working_with_agent
            and s.consent_to_contact
            and s.interest_level in ["very interested", "interested"]
        ]

    def convert_to_leads(self, event_id: str):
        """Convert open house sign-ins to leads in the database."""
        from ..storage import Database
        from ..storage.models import Lead
        from ..core import ScoringEngine

        db = Database()
        scoring_engine = ScoringEngine()

        signins = self.get_event_signins(event_id)
        event = self.events.get(event_id)

        created = 0
        for signin in signins:
            if not signin.consent_to_contact:
                continue

            # Build bio from sign-in data
            bio_parts = [f"Open house visitor at {signin.property_address}"]
            if signin.interest_level:
                bio_parts.append(f"Interest: {signin.interest_level}")
            if signin.timeline:
                bio_parts.append(f"Timeline: {signin.timeline}")
            if signin.is_pre_approved:
                bio_parts.append("Pre-approved for mortgage")
            if signin.notes:
                bio_parts.append(f"Notes: {signin.notes}")

            bio = ". ".join(bio_parts)

            lead = Lead(
                name=signin.name,
                email=signin.email,
                phone=signin.phone,
                bio=bio,
                source="open_house",
                source_id=signin.id
            )

            # Score the lead
            if bio:
                result = scoring_engine.score(bio)
                lead.score = result["score"]
                lead.tier = result["tier"]
                lead.score_breakdown = json.dumps(result)

            db.add_lead(lead)
            created += 1

        logger.info(f"Created {created} leads from open house {event_id}")
        return created


class QRCodeLandingManager:
    """Generate QR codes for various lead capture landing pages."""

    def __init__(self, base_url: str = ""):
        """Initialize QR code manager."""
        self.base_url = base_url or os.environ.get("TD_ENGINE_BASE_URL", "https://tdrealty.com")

    def generate_home_value_qr(self, agent_id: str = "") -> str:
        """Generate QR code for home value landing page."""
        url = f"{self.base_url}/home-value"
        if agent_id:
            url += f"?agent={agent_id}"
        return self._generate_qr(url)

    def generate_buyer_search_qr(self, agent_id: str = "") -> str:
        """Generate QR code for buyer search landing page."""
        url = f"{self.base_url}/buyer-search"
        if agent_id:
            url += f"?agent={agent_id}"
        return self._generate_qr(url)

    def generate_property_qr(self, mls_id: str) -> str:
        """Generate QR code for a specific property."""
        url = f"{self.base_url}/property/{mls_id}"
        return self._generate_qr(url)

    def generate_agent_contact_qr(self, agent_id: str) -> str:
        """Generate QR code for agent contact page."""
        url = f"{self.base_url}/contact/{agent_id}"
        return self._generate_qr(url)

    def generate_vcard_qr(self, name: str, phone: str, email: str, title: str = "Realtor") -> str:
        """Generate QR code with vCard for contact import."""
        vcard = f"""BEGIN:VCARD
VERSION:3.0
N:{name.split()[-1]};{name.split()[0]}
FN:{name}
TITLE:{title}
TEL;TYPE=CELL:{phone}
EMAIL:{email}
END:VCARD"""
        return self._generate_qr(vcard)

    def _generate_qr(self, data: str) -> str:
        """Generate QR code and return base64 PNG."""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_str}"

        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return ""
