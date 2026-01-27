"""Nurture campaign management."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

from .templates import TemplateEngine

logger = logging.getLogger(__name__)


class CampaignStatus(Enum):
    """Campaign status values."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DRAFT = "draft"


class StepType(Enum):
    """Types of campaign steps."""
    EMAIL = "email"
    SMS = "sms"
    TASK = "task"  # Creates a follow-up task
    WAIT = "wait"  # Wait period


@dataclass
class CampaignStep:
    """A step in a nurture campaign."""

    order: int
    step_type: StepType
    template_name: Optional[str]  # For email/sms
    delay_days: int  # Days to wait before this step
    delay_hours: int = 0

    # For task steps
    task_title: Optional[str] = None
    task_description: Optional[str] = None

    # Conditions
    skip_if_responded: bool = True
    skip_if_converted: bool = True


@dataclass
class NurtureCampaign:
    """A lead nurturing campaign."""

    id: str
    name: str
    description: str
    category: str  # "buyer", "seller", "nurture"
    steps: List[CampaignStep]
    status: CampaignStatus = CampaignStatus.DRAFT

    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "steps": [
                {
                    "order": s.order,
                    "step_type": s.step_type.value,
                    "template_name": s.template_name,
                    "delay_days": s.delay_days,
                    "delay_hours": s.delay_hours,
                    "task_title": s.task_title,
                    "task_description": s.task_description,
                    "skip_if_responded": s.skip_if_responded,
                    "skip_if_converted": s.skip_if_converted
                }
                for s in self.steps
            ],
            "status": self.status.value,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NurtureCampaign':
        """Create from dictionary."""
        steps = [
            CampaignStep(
                order=s["order"],
                step_type=StepType(s["step_type"]),
                template_name=s.get("template_name"),
                delay_days=s["delay_days"],
                delay_hours=s.get("delay_hours", 0),
                task_title=s.get("task_title"),
                task_description=s.get("task_description"),
                skip_if_responded=s.get("skip_if_responded", True),
                skip_if_converted=s.get("skip_if_converted", True)
            )
            for s in data["steps"]
        ]

        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=data["category"],
            steps=steps,
            status=CampaignStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class CampaignEnrollment:
    """A lead's enrollment in a campaign."""

    id: str
    campaign_id: str
    lead_id: str
    lead_name: str
    lead_email: Optional[str]
    lead_phone: Optional[str]

    current_step: int = 0
    started_at: datetime = field(default_factory=datetime.now)
    next_action_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    is_active: bool = True
    has_responded: bool = False
    is_converted: bool = False

    step_history: List[Dict[str, Any]] = field(default_factory=list)


class CampaignManager:
    """Manage nurture campaigns and enrollments."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize campaign manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "campaigns.json"
        self.campaigns: Dict[str, NurtureCampaign] = {}
        self.enrollments: Dict[str, CampaignEnrollment] = {}
        self.template_engine = TemplateEngine()
        self._load_data()
        self._create_default_campaigns()

    def _load_data(self):
        """Load campaigns and enrollments from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for camp_data in data.get("campaigns", []):
                        campaign = NurtureCampaign.from_dict(camp_data)
                        self.campaigns[campaign.id] = campaign

                    for enroll_data in data.get("enrollments", []):
                        enrollment = CampaignEnrollment(
                            id=enroll_data["id"],
                            campaign_id=enroll_data["campaign_id"],
                            lead_id=enroll_data["lead_id"],
                            lead_name=enroll_data["lead_name"],
                            lead_email=enroll_data.get("lead_email"),
                            lead_phone=enroll_data.get("lead_phone"),
                            current_step=enroll_data["current_step"],
                            started_at=datetime.fromisoformat(enroll_data["started_at"]),
                            next_action_at=datetime.fromisoformat(enroll_data["next_action_at"]) if enroll_data.get("next_action_at") else None,
                            completed_at=datetime.fromisoformat(enroll_data["completed_at"]) if enroll_data.get("completed_at") else None,
                            is_active=enroll_data["is_active"],
                            has_responded=enroll_data.get("has_responded", False),
                            is_converted=enroll_data.get("is_converted", False),
                            step_history=enroll_data.get("step_history", [])
                        )
                        self.enrollments[enrollment.id] = enrollment

            except Exception as e:
                logger.error(f"Error loading campaigns: {e}")

    def _save_data(self):
        """Save campaigns and enrollments to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "campaigns": [c.to_dict() for c in self.campaigns.values()],
            "enrollments": [
                {
                    "id": e.id,
                    "campaign_id": e.campaign_id,
                    "lead_id": e.lead_id,
                    "lead_name": e.lead_name,
                    "lead_email": e.lead_email,
                    "lead_phone": e.lead_phone,
                    "current_step": e.current_step,
                    "started_at": e.started_at.isoformat(),
                    "next_action_at": e.next_action_at.isoformat() if e.next_action_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "is_active": e.is_active,
                    "has_responded": e.has_responded,
                    "is_converted": e.is_converted,
                    "step_history": e.step_history
                }
                for e in self.enrollments.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _create_default_campaigns(self):
        """Create default nurture campaigns if none exist."""
        if self.campaigns:
            return

        # New Buyer Campaign
        self.campaigns["new_buyer"] = NurtureCampaign(
            id="new_buyer",
            name="New Buyer Welcome",
            description="7-day drip for new buyer leads",
            category="buyer",
            status=CampaignStatus.ACTIVE,
            steps=[
                CampaignStep(order=1, step_type=StepType.EMAIL, template_name="buyer_welcome", delay_days=0),
                CampaignStep(order=2, step_type=StepType.TASK, delay_days=1, task_title="Call new buyer lead", task_description="Follow up on welcome email"),
                CampaignStep(order=3, step_type=StepType.SMS, template_name="initial_followup", delay_days=2),
                CampaignStep(order=4, step_type=StepType.EMAIL, template_name="buyer_market_update", delay_days=5),
                CampaignStep(order=5, step_type=StepType.TASK, delay_days=7, task_title="Check-in call", task_description="Weekly check-in with buyer lead"),
            ]
        )

        # New Seller Campaign
        self.campaigns["new_seller"] = NurtureCampaign(
            id="new_seller",
            name="New Seller Welcome",
            description="7-day drip for seller CMA requests",
            category="seller",
            status=CampaignStatus.ACTIVE,
            steps=[
                CampaignStep(order=1, step_type=StepType.EMAIL, template_name="seller_cma", delay_days=0),
                CampaignStep(order=2, step_type=StepType.TASK, delay_days=0, task_title="Call seller lead", task_description="Discuss CMA, schedule listing appointment"),
                CampaignStep(order=3, step_type=StepType.SMS, template_name="initial_followup", delay_days=1),
                CampaignStep(order=4, step_type=StepType.EMAIL, template_name="seller_tips", delay_days=4),
                CampaignStep(order=5, step_type=StepType.TASK, delay_days=7, task_title="Follow up call", task_description="Check on seller's timeline"),
            ]
        )

        # Long-term Nurture Campaign
        self.campaigns["long_term_nurture"] = NurtureCampaign(
            id="long_term_nurture",
            name="Long-term Nurture",
            description="Monthly touchpoints for not-ready-yet leads",
            category="nurture",
            status=CampaignStatus.ACTIVE,
            steps=[
                CampaignStep(order=1, step_type=StepType.EMAIL, template_name="check_in", delay_days=0),
                CampaignStep(order=2, step_type=StepType.EMAIL, template_name="buyer_market_update", delay_days=30),
                CampaignStep(order=3, step_type=StepType.SMS, template_name="check_in", delay_days=60),
                CampaignStep(order=4, step_type=StepType.EMAIL, template_name="check_in", delay_days=90),
                CampaignStep(order=5, step_type=StepType.TASK, delay_days=90, task_title="Quarterly check-in call", task_description="Personal touch point"),
            ]
        )

        self._save_data()

    def create_campaign(
        self,
        name: str,
        description: str,
        category: str,
        steps: List[Dict[str, Any]]
    ) -> NurtureCampaign:
        """Create a new campaign."""
        campaign_id = str(uuid.uuid4())[:8]

        campaign_steps = [
            CampaignStep(
                order=i + 1,
                step_type=StepType(s["step_type"]),
                template_name=s.get("template_name"),
                delay_days=s["delay_days"],
                delay_hours=s.get("delay_hours", 0),
                task_title=s.get("task_title"),
                task_description=s.get("task_description"),
                skip_if_responded=s.get("skip_if_responded", True),
                skip_if_converted=s.get("skip_if_converted", True)
            )
            for i, s in enumerate(steps)
        ]

        campaign = NurtureCampaign(
            id=campaign_id,
            name=name,
            description=description,
            category=category,
            steps=campaign_steps,
            status=CampaignStatus.DRAFT
        )

        self.campaigns[campaign_id] = campaign
        self._save_data()

        return campaign

    def enroll_lead(
        self,
        campaign_id: str,
        lead_id: str,
        lead_name: str,
        lead_email: Optional[str] = None,
        lead_phone: Optional[str] = None
    ) -> Optional[CampaignEnrollment]:
        """Enroll a lead in a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return None

        # Check if already enrolled in this campaign
        for enrollment in self.enrollments.values():
            if enrollment.lead_id == lead_id and enrollment.campaign_id == campaign_id and enrollment.is_active:
                logger.info(f"Lead {lead_id} already enrolled in campaign {campaign_id}")
                return enrollment

        enrollment_id = str(uuid.uuid4())[:8]

        # Calculate first action time
        first_step = campaign.steps[0] if campaign.steps else None
        next_action = datetime.now()
        if first_step:
            next_action = datetime.now() + timedelta(days=first_step.delay_days, hours=first_step.delay_hours)

        enrollment = CampaignEnrollment(
            id=enrollment_id,
            campaign_id=campaign_id,
            lead_id=lead_id,
            lead_name=lead_name,
            lead_email=lead_email,
            lead_phone=lead_phone,
            next_action_at=next_action
        )

        self.enrollments[enrollment_id] = enrollment
        self._save_data()

        logger.info(f"Enrolled lead {lead_name} in campaign {campaign.name}")
        return enrollment

    def unenroll_lead(self, enrollment_id: str) -> bool:
        """Remove a lead from a campaign."""
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment:
            return False

        enrollment.is_active = False
        self._save_data()
        return True

    def mark_responded(self, lead_id: str) -> int:
        """Mark that a lead has responded (affects all their active enrollments)."""
        count = 0
        for enrollment in self.enrollments.values():
            if enrollment.lead_id == lead_id and enrollment.is_active:
                enrollment.has_responded = True
                count += 1

        if count > 0:
            self._save_data()
        return count

    def mark_converted(self, lead_id: str) -> int:
        """Mark that a lead has converted."""
        count = 0
        for enrollment in self.enrollments.values():
            if enrollment.lead_id == lead_id and enrollment.is_active:
                enrollment.is_converted = True
                enrollment.is_active = False
                enrollment.completed_at = datetime.now()
                count += 1

        if count > 0:
            self._save_data()
        return count

    def get_due_actions(self) -> List[Dict[str, Any]]:
        """Get all campaign actions that are due to be executed."""
        now = datetime.now()
        due_actions = []

        for enrollment in self.enrollments.values():
            if not enrollment.is_active:
                continue
            if not enrollment.next_action_at or enrollment.next_action_at > now:
                continue

            campaign = self.campaigns.get(enrollment.campaign_id)
            if not campaign:
                continue

            if enrollment.current_step >= len(campaign.steps):
                # Campaign completed
                enrollment.is_active = False
                enrollment.completed_at = now
                continue

            step = campaign.steps[enrollment.current_step]

            # Check skip conditions
            if step.skip_if_responded and enrollment.has_responded:
                self._advance_enrollment(enrollment, campaign, "skipped_responded")
                continue
            if step.skip_if_converted and enrollment.is_converted:
                enrollment.is_active = False
                enrollment.completed_at = now
                continue

            due_actions.append({
                "enrollment": enrollment,
                "campaign": campaign,
                "step": step,
                "lead_id": enrollment.lead_id,
                "lead_name": enrollment.lead_name,
                "lead_email": enrollment.lead_email,
                "lead_phone": enrollment.lead_phone
            })

        self._save_data()
        return due_actions

    def execute_step(
        self,
        enrollment_id: str,
        success: bool = True,
        notes: str = None
    ):
        """Mark a step as executed and advance to next."""
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment:
            return

        campaign = self.campaigns.get(enrollment.campaign_id)
        if not campaign:
            return

        result = "success" if success else "failed"
        if notes:
            result += f": {notes}"

        self._advance_enrollment(enrollment, campaign, result)
        self._save_data()

    def _advance_enrollment(
        self,
        enrollment: CampaignEnrollment,
        campaign: NurtureCampaign,
        result: str
    ):
        """Advance enrollment to next step."""
        # Record history
        enrollment.step_history.append({
            "step": enrollment.current_step,
            "executed_at": datetime.now().isoformat(),
            "result": result
        })

        # Move to next step
        enrollment.current_step += 1

        if enrollment.current_step >= len(campaign.steps):
            # Campaign complete
            enrollment.is_active = False
            enrollment.completed_at = datetime.now()
            enrollment.next_action_at = None
        else:
            # Calculate next action time
            next_step = campaign.steps[enrollment.current_step]
            enrollment.next_action_at = datetime.now() + timedelta(
                days=next_step.delay_days,
                hours=next_step.delay_hours
            )

    def get_campaign_stats(self, campaign_id: str) -> Dict[str, Any]:
        """Get statistics for a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}

        enrollments = [e for e in self.enrollments.values() if e.campaign_id == campaign_id]

        active = len([e for e in enrollments if e.is_active])
        completed = len([e for e in enrollments if e.completed_at])
        responded = len([e for e in enrollments if e.has_responded])
        converted = len([e for e in enrollments if e.is_converted])

        return {
            "campaign_name": campaign.name,
            "total_enrolled": len(enrollments),
            "active": active,
            "completed": completed,
            "responded": responded,
            "converted": converted,
            "response_rate": (responded / len(enrollments) * 100) if enrollments else 0,
            "conversion_rate": (converted / len(enrollments) * 100) if enrollments else 0
        }

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all campaigns with basic info."""
        return [
            {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "status": c.status.value,
                "steps": len(c.steps)
            }
            for c in self.campaigns.values()
        ]
