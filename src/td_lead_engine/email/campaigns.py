"""Drip campaign management system."""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any


class CampaignStatus(Enum):
    """Campaign status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CampaignType(Enum):
    """Types of drip campaigns."""
    BUYER_NURTURE = "buyer_nurture"
    SELLER_NURTURE = "seller_nurture"
    NEW_LEAD_WELCOME = "new_lead_welcome"
    HOT_LEAD_FOLLOW_UP = "hot_lead_follow_up"
    COLD_LEAD_REACTIVATION = "cold_lead_reactivation"
    POST_SHOWING = "post_showing"
    POST_CLOSING = "post_closing"
    ANNIVERSARY = "anniversary"
    MARKET_UPDATE = "market_update"
    CUSTOM = "custom"


@dataclass
class CampaignEmail:
    """An email in a drip campaign."""
    id: str
    campaign_id: str
    sequence_number: int
    subject: str
    template_id: str
    delay_days: int = 0
    delay_hours: int = 0
    send_time: str = "09:00"  # Preferred send time
    conditions: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class CampaignEnrollment:
    """A contact enrolled in a campaign."""
    id: str
    campaign_id: str
    contact_email: str
    contact_name: str
    contact_data: Dict[str, Any] = field(default_factory=dict)
    enrolled_at: datetime = field(default_factory=datetime.now)
    current_step: int = 0
    status: str = "active"  # active, completed, unsubscribed, paused
    last_email_sent: Optional[datetime] = None
    next_email_scheduled: Optional[datetime] = None
    emails_sent: int = 0
    emails_opened: int = 0
    emails_clicked: int = 0


@dataclass
class DripCampaign:
    """A drip email campaign."""
    id: str
    name: str
    description: str
    campaign_type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    emails: List[CampaignEmail] = field(default_factory=list)
    enrollment_criteria: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    stats: Dict[str, int] = field(default_factory=lambda: {
        'total_enrolled': 0,
        'active_enrollments': 0,
        'completed': 0,
        'unsubscribed': 0,
        'total_emails_sent': 0,
        'total_opens': 0,
        'total_clicks': 0
    })

    def add_email(
        self,
        subject: str,
        template_id: str,
        delay_days: int = 0,
        delay_hours: int = 0,
        send_time: str = "09:00",
        conditions: Optional[Dict] = None
    ) -> CampaignEmail:
        """Add an email to the campaign."""
        email = CampaignEmail(
            id=str(uuid.uuid4()),
            campaign_id=self.id,
            sequence_number=len(self.emails) + 1,
            subject=subject,
            template_id=template_id,
            delay_days=delay_days,
            delay_hours=delay_hours,
            send_time=send_time,
            conditions=conditions or {}
        )
        self.emails.append(email)
        self.updated_at = datetime.now()
        return email

    def get_next_email(self, current_step: int) -> Optional[CampaignEmail]:
        """Get the next email in the sequence."""
        for email in self.emails:
            if email.sequence_number == current_step + 1 and email.is_active:
                return email
        return None

    def get_email_count(self) -> int:
        """Get total number of active emails."""
        return len([e for e in self.emails if e.is_active])


class CampaignManager:
    """Manages drip campaigns."""

    def __init__(self, data_dir: str = "data/campaigns"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.campaigns: Dict[str, DripCampaign] = {}
        self.enrollments: Dict[str, CampaignEnrollment] = {}
        self._load_data()

    def _load_data(self):
        """Load campaigns from files."""
        campaigns_file = os.path.join(self.data_dir, "campaigns.json")
        if os.path.exists(campaigns_file):
            with open(campaigns_file) as f:
                data = json.load(f)
                for item in data:
                    item['campaign_type'] = CampaignType(item['campaign_type'])
                    item['status'] = CampaignStatus(item['status'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    item['updated_at'] = datetime.fromisoformat(item['updated_at'])
                    emails = []
                    for e in item.get('emails', []):
                        emails.append(CampaignEmail(**e))
                    item['emails'] = emails
                    self.campaigns[item['id']] = DripCampaign(**item)

        enrollments_file = os.path.join(self.data_dir, "enrollments.json")
        if os.path.exists(enrollments_file):
            with open(enrollments_file) as f:
                data = json.load(f)
                for item in data:
                    item['enrolled_at'] = datetime.fromisoformat(item['enrolled_at'])
                    if item.get('last_email_sent'):
                        item['last_email_sent'] = datetime.fromisoformat(item['last_email_sent'])
                    if item.get('next_email_scheduled'):
                        item['next_email_scheduled'] = datetime.fromisoformat(item['next_email_scheduled'])
                    self.enrollments[item['id']] = CampaignEnrollment(**item)

    def _save_data(self):
        """Save campaigns to files."""
        campaigns_file = os.path.join(self.data_dir, "campaigns.json")
        with open(campaigns_file, 'w') as f:
            data = []
            for campaign in self.campaigns.values():
                item = asdict(campaign)
                item['campaign_type'] = campaign.campaign_type.value
                item['status'] = campaign.status.value
                item['created_at'] = campaign.created_at.isoformat()
                item['updated_at'] = campaign.updated_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

        enrollments_file = os.path.join(self.data_dir, "enrollments.json")
        with open(enrollments_file, 'w') as f:
            data = []
            for enrollment in self.enrollments.values():
                item = asdict(enrollment)
                item['enrolled_at'] = enrollment.enrolled_at.isoformat()
                if enrollment.last_email_sent:
                    item['last_email_sent'] = enrollment.last_email_sent.isoformat()
                if enrollment.next_email_scheduled:
                    item['next_email_scheduled'] = enrollment.next_email_scheduled.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    def create_campaign(
        self,
        name: str,
        description: str,
        campaign_type: CampaignType,
        enrollment_criteria: Optional[Dict] = None
    ) -> DripCampaign:
        """Create a new drip campaign."""
        campaign = DripCampaign(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            campaign_type=campaign_type,
            enrollment_criteria=enrollment_criteria or {}
        )
        self.campaigns[campaign.id] = campaign
        self._save_data()
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[DripCampaign]:
        """Get a campaign by ID."""
        return self.campaigns.get(campaign_id)

    def update_campaign(self, campaign_id: str, **updates) -> Optional[DripCampaign]:
        """Update a campaign."""
        if campaign_id not in self.campaigns:
            return None
        campaign = self.campaigns[campaign_id]
        for key, value in updates.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)
        campaign.updated_at = datetime.now()
        self._save_data()
        return campaign

    def activate_campaign(self, campaign_id: str) -> bool:
        """Activate a campaign."""
        campaign = self.get_campaign(campaign_id)
        if campaign and campaign.status in [CampaignStatus.DRAFT, CampaignStatus.PAUSED]:
            campaign.status = CampaignStatus.ACTIVE
            self._save_data()
            return True
        return False

    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        campaign = self.get_campaign(campaign_id)
        if campaign and campaign.status == CampaignStatus.ACTIVE:
            campaign.status = CampaignStatus.PAUSED
            self._save_data()
            return True
        return False

    def get_active_campaigns(self) -> List[DripCampaign]:
        """Get all active campaigns."""
        return [c for c in self.campaigns.values() if c.status == CampaignStatus.ACTIVE]

    def get_campaigns_by_type(self, campaign_type: CampaignType) -> List[DripCampaign]:
        """Get campaigns by type."""
        return [c for c in self.campaigns.values() if c.campaign_type == campaign_type]

    def enroll_contact(
        self,
        campaign_id: str,
        contact_email: str,
        contact_name: str,
        contact_data: Optional[Dict] = None
    ) -> Optional[CampaignEnrollment]:
        """Enroll a contact in a campaign."""
        campaign = self.get_campaign(campaign_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return None

        # Check if already enrolled
        for enrollment in self.enrollments.values():
            if (enrollment.campaign_id == campaign_id and
                enrollment.contact_email == contact_email and
                enrollment.status == "active"):
                return None  # Already enrolled

        # Calculate first email time
        first_email = campaign.get_next_email(0)
        next_scheduled = None
        if first_email:
            next_scheduled = datetime.now() + timedelta(
                days=first_email.delay_days,
                hours=first_email.delay_hours
            )

        enrollment = CampaignEnrollment(
            id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            contact_email=contact_email,
            contact_name=contact_name,
            contact_data=contact_data or {},
            next_email_scheduled=next_scheduled
        )

        self.enrollments[enrollment.id] = enrollment

        # Update campaign stats
        campaign.stats['total_enrolled'] += 1
        campaign.stats['active_enrollments'] += 1

        self._save_data()
        return enrollment

    def unenroll_contact(self, enrollment_id: str, reason: str = "unsubscribed") -> bool:
        """Remove a contact from a campaign."""
        if enrollment_id in self.enrollments:
            enrollment = self.enrollments[enrollment_id]
            enrollment.status = reason

            campaign = self.get_campaign(enrollment.campaign_id)
            if campaign:
                campaign.stats['active_enrollments'] -= 1
                if reason == "unsubscribed":
                    campaign.stats['unsubscribed'] += 1
                elif reason == "completed":
                    campaign.stats['completed'] += 1

            self._save_data()
            return True
        return False

    def get_enrollment(self, enrollment_id: str) -> Optional[CampaignEnrollment]:
        """Get an enrollment by ID."""
        return self.enrollments.get(enrollment_id)

    def get_enrollments_for_campaign(self, campaign_id: str) -> List[CampaignEnrollment]:
        """Get all enrollments for a campaign."""
        return [e for e in self.enrollments.values() if e.campaign_id == campaign_id]

    def get_active_enrollments(self) -> List[CampaignEnrollment]:
        """Get all active enrollments."""
        return [e for e in self.enrollments.values() if e.status == "active"]

    def get_due_emails(self, before: Optional[datetime] = None) -> List[Dict]:
        """Get enrollments with emails due to be sent."""
        if before is None:
            before = datetime.now()

        due = []
        for enrollment in self.get_active_enrollments():
            if enrollment.next_email_scheduled and enrollment.next_email_scheduled <= before:
                campaign = self.get_campaign(enrollment.campaign_id)
                if campaign:
                    next_email = campaign.get_next_email(enrollment.current_step)
                    if next_email:
                        due.append({
                            'enrollment': enrollment,
                            'campaign': campaign,
                            'email': next_email
                        })
        return due

    def advance_enrollment(
        self,
        enrollment_id: str,
        email_sent: bool = True,
        opened: bool = False,
        clicked: bool = False
    ):
        """Advance an enrollment to the next step."""
        enrollment = self.get_enrollment(enrollment_id)
        if not enrollment:
            return

        campaign = self.get_campaign(enrollment.campaign_id)
        if not campaign:
            return

        if email_sent:
            enrollment.current_step += 1
            enrollment.emails_sent += 1
            enrollment.last_email_sent = datetime.now()
            campaign.stats['total_emails_sent'] += 1

        if opened:
            enrollment.emails_opened += 1
            campaign.stats['total_opens'] += 1

        if clicked:
            enrollment.emails_clicked += 1
            campaign.stats['total_clicks'] += 1

        # Schedule next email
        next_email = campaign.get_next_email(enrollment.current_step)
        if next_email:
            enrollment.next_email_scheduled = datetime.now() + timedelta(
                days=next_email.delay_days,
                hours=next_email.delay_hours
            )
        else:
            # Campaign completed for this contact
            enrollment.status = "completed"
            enrollment.next_email_scheduled = None
            campaign.stats['active_enrollments'] -= 1
            campaign.stats['completed'] += 1

        self._save_data()

    # Pre-built campaign templates

    def create_buyer_nurture_campaign(self) -> DripCampaign:
        """Create a standard buyer nurture campaign."""
        campaign = self.create_campaign(
            name="Buyer Nurture Sequence",
            description="Long-term nurture sequence for buyer leads",
            campaign_type=CampaignType.BUYER_NURTURE
        )

        campaign.add_email(
            subject="Welcome! Let's Find Your Dream Home",
            template_id="buyer_welcome",
            delay_days=0
        )

        campaign.add_email(
            subject="What to Know About the Columbus Market",
            template_id="buyer_market_overview",
            delay_days=3
        )

        campaign.add_email(
            subject="Your Home Buying Checklist",
            template_id="buyer_checklist",
            delay_days=7
        )

        campaign.add_email(
            subject="Understanding the Mortgage Process",
            template_id="buyer_mortgage_guide",
            delay_days=14
        )

        campaign.add_email(
            subject="New Listings You Might Love",
            template_id="buyer_listings_update",
            delay_days=21
        )

        campaign.add_email(
            subject="Ready to Start Touring Homes?",
            template_id="buyer_tour_cta",
            delay_days=30
        )

        self._save_data()
        return campaign

    def create_seller_nurture_campaign(self) -> DripCampaign:
        """Create a standard seller nurture campaign."""
        campaign = self.create_campaign(
            name="Seller Nurture Sequence",
            description="Long-term nurture sequence for seller leads",
            campaign_type=CampaignType.SELLER_NURTURE
        )

        campaign.add_email(
            subject="Thinking About Selling? Here's What to Know",
            template_id="seller_welcome",
            delay_days=0
        )

        campaign.add_email(
            subject="What's Your Home Worth? Free CMA Report",
            template_id="seller_cma_offer",
            delay_days=3
        )

        campaign.add_email(
            subject="5 Tips to Maximize Your Home's Value",
            template_id="seller_value_tips",
            delay_days=7
        )

        campaign.add_email(
            subject="Understanding the Selling Process",
            template_id="seller_process_guide",
            delay_days=14
        )

        campaign.add_email(
            subject="Recent Sales in Your Area",
            template_id="seller_market_update",
            delay_days=21
        )

        campaign.add_email(
            subject="Ready for a Free Home Valuation?",
            template_id="seller_consultation_cta",
            delay_days=30
        )

        self._save_data()
        return campaign

    def create_post_closing_campaign(self) -> DripCampaign:
        """Create a post-closing follow-up campaign."""
        campaign = self.create_campaign(
            name="Post-Closing Follow-up",
            description="Stay in touch after closing",
            campaign_type=CampaignType.POST_CLOSING
        )

        campaign.add_email(
            subject="Congratulations on Your New Home!",
            template_id="closing_congrats",
            delay_days=0
        )

        campaign.add_email(
            subject="How's the New Place? Let Us Know!",
            template_id="closing_check_in",
            delay_days=14
        )

        campaign.add_email(
            subject="Your Review Would Mean the World",
            template_id="closing_review_request",
            delay_days=30
        )

        campaign.add_email(
            subject="Happy 6-Month Anniversary!",
            template_id="closing_6month",
            delay_days=180
        )

        campaign.add_email(
            subject="Happy Home-iversary!",
            template_id="closing_anniversary",
            delay_days=365
        )

        self._save_data()
        return campaign
