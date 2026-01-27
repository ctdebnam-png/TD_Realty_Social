"""Drip campaign management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class CampaignStatus(Enum):
    """Campaign status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class MessageType(Enum):
    """Message types in a drip campaign."""
    EMAIL = "email"
    SMS = "sms"
    TASK = "task"
    WAIT = "wait"


class TriggerType(Enum):
    """Campaign trigger types."""
    LEAD_CREATED = "lead_created"
    LEAD_TAGGED = "lead_tagged"
    FORM_SUBMITTED = "form_submitted"
    PROPERTY_VIEWED = "property_viewed"
    MANUAL = "manual"
    SCHEDULED = "scheduled"


@dataclass
class CampaignStep:
    """A step in a drip campaign."""
    id: str
    order: int
    message_type: MessageType
    delay_days: int = 0
    delay_hours: int = 0
    delay_minutes: int = 0
    template_id: str = ""
    subject: str = ""
    content: str = ""
    conditions: Dict = field(default_factory=dict)
    send_time: str = ""  # e.g., "09:00" - specific time to send
    send_days: List[str] = field(default_factory=list)  # e.g., ["monday", "wednesday"]


@dataclass
class CampaignEnrollment:
    """A lead enrolled in a campaign."""
    id: str
    campaign_id: str
    lead_id: str
    current_step: int = 0
    status: str = "active"  # active, completed, unsubscribed, paused
    enrolled_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None
    last_action_at: datetime = None
    next_action_at: datetime = None


@dataclass
class DripCampaign:
    """A drip campaign."""
    id: str
    name: str
    description: str = ""
    trigger_type: TriggerType = TriggerType.MANUAL
    trigger_conditions: Dict = field(default_factory=dict)
    steps: List[CampaignStep] = field(default_factory=list)
    status: CampaignStatus = CampaignStatus.DRAFT
    goal: str = ""
    tags: List[str] = field(default_factory=list)
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class CampaignManager:
    """Manage drip campaigns."""
    
    def __init__(self, storage_path: str = "data/drip_campaigns"):
        self.storage_path = storage_path
        self.campaigns: Dict[str, DripCampaign] = {}
        self.enrollments: Dict[str, CampaignEnrollment] = {}
        self.trigger_handlers: Dict[TriggerType, List[Callable]] = {}
        
        self._load_data()
        self._create_default_campaigns()
    
    def _load_data(self):
        """Load campaigns from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load campaigns
        campaigns_file = f"{self.storage_path}/campaigns.json"
        if os.path.exists(campaigns_file):
            with open(campaigns_file, 'r') as f:
                data = json.load(f)
                for c in data:
                    steps = [
                        CampaignStep(
                            id=s['id'],
                            order=s['order'],
                            message_type=MessageType(s['message_type']),
                            delay_days=s.get('delay_days', 0),
                            delay_hours=s.get('delay_hours', 0),
                            delay_minutes=s.get('delay_minutes', 0),
                            template_id=s.get('template_id', ''),
                            subject=s.get('subject', ''),
                            content=s.get('content', ''),
                            conditions=s.get('conditions', {}),
                            send_time=s.get('send_time', ''),
                            send_days=s.get('send_days', [])
                        )
                        for s in c.get('steps', [])
                    ]
                    campaign = DripCampaign(
                        id=c['id'],
                        name=c['name'],
                        description=c.get('description', ''),
                        trigger_type=TriggerType(c.get('trigger_type', 'manual')),
                        trigger_conditions=c.get('trigger_conditions', {}),
                        steps=steps,
                        status=CampaignStatus(c.get('status', 'draft')),
                        goal=c.get('goal', ''),
                        tags=c.get('tags', []),
                        created_by=c.get('created_by', ''),
                        created_at=datetime.fromisoformat(c['created_at']),
                        updated_at=datetime.fromisoformat(c.get('updated_at', c['created_at']))
                    )
                    self.campaigns[campaign.id] = campaign
        
        # Load enrollments
        enrollments_file = f"{self.storage_path}/enrollments.json"
        if os.path.exists(enrollments_file):
            with open(enrollments_file, 'r') as f:
                data = json.load(f)
                for e in data:
                    enrollment = CampaignEnrollment(
                        id=e['id'],
                        campaign_id=e['campaign_id'],
                        lead_id=e['lead_id'],
                        current_step=e.get('current_step', 0),
                        status=e.get('status', 'active'),
                        enrolled_at=datetime.fromisoformat(e['enrolled_at']),
                        completed_at=datetime.fromisoformat(e['completed_at']) if e.get('completed_at') else None,
                        last_action_at=datetime.fromisoformat(e['last_action_at']) if e.get('last_action_at') else None,
                        next_action_at=datetime.fromisoformat(e['next_action_at']) if e.get('next_action_at') else None
                    )
                    self.enrollments[enrollment.id] = enrollment
    
    def _save_data(self):
        """Save campaigns to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save campaigns
        campaigns_data = [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'trigger_type': c.trigger_type.value,
                'trigger_conditions': c.trigger_conditions,
                'steps': [
                    {
                        'id': s.id,
                        'order': s.order,
                        'message_type': s.message_type.value,
                        'delay_days': s.delay_days,
                        'delay_hours': s.delay_hours,
                        'delay_minutes': s.delay_minutes,
                        'template_id': s.template_id,
                        'subject': s.subject,
                        'content': s.content,
                        'conditions': s.conditions,
                        'send_time': s.send_time,
                        'send_days': s.send_days
                    }
                    for s in c.steps
                ],
                'status': c.status.value,
                'goal': c.goal,
                'tags': c.tags,
                'created_by': c.created_by,
                'created_at': c.created_at.isoformat(),
                'updated_at': c.updated_at.isoformat()
            }
            for c in self.campaigns.values()
        ]
        
        with open(f"{self.storage_path}/campaigns.json", 'w') as f:
            json.dump(campaigns_data, f, indent=2)
        
        # Save enrollments
        enrollments_data = [
            {
                'id': e.id,
                'campaign_id': e.campaign_id,
                'lead_id': e.lead_id,
                'current_step': e.current_step,
                'status': e.status,
                'enrolled_at': e.enrolled_at.isoformat(),
                'completed_at': e.completed_at.isoformat() if e.completed_at else None,
                'last_action_at': e.last_action_at.isoformat() if e.last_action_at else None,
                'next_action_at': e.next_action_at.isoformat() if e.next_action_at else None
            }
            for e in self.enrollments.values()
        ]
        
        with open(f"{self.storage_path}/enrollments.json", 'w') as f:
            json.dump(enrollments_data, f, indent=2)
    
    def _create_default_campaigns(self):
        """Create default drip campaigns."""
        if self.campaigns:
            return
        
        # New buyer nurture campaign
        buyer_campaign = self.create_campaign(
            name="New Buyer Nurture",
            description="Welcome and nurture new buyer leads",
            trigger_type=TriggerType.LEAD_CREATED,
            trigger_conditions={'lead_type': 'buyer'},
            goal="Convert to active buyer client"
        )
        
        self.add_step(buyer_campaign.id, MessageType.EMAIL, 0, 0, 0,
            subject="Welcome to Your Home Search Journey!",
            content="Hi {first_name},\n\nThank you for reaching out about finding your new home...")
        
        self.add_step(buyer_campaign.id, MessageType.EMAIL, 2, 0, 0,
            subject="5 Tips for First-Time Home Buyers",
            content="Hi {first_name},\n\nBuying a home is exciting! Here are 5 tips...")
        
        self.add_step(buyer_campaign.id, MessageType.SMS, 4, 0, 0,
            content="Hi {first_name}! Just checking in - have you had a chance to start your home search?")
        
        self.add_step(buyer_campaign.id, MessageType.EMAIL, 7, 0, 0,
            subject="Understanding the Home Buying Process",
            content="Hi {first_name},\n\nLet me walk you through what to expect...")
        
        self.add_step(buyer_campaign.id, MessageType.TASK, 10, 0, 0,
            content="Follow up call with {first_name} {last_name}")
        
        # Seller nurture campaign  
        seller_campaign = self.create_campaign(
            name="Seller Home Valuation",
            description="Nurture leads who requested home valuations",
            trigger_type=TriggerType.FORM_SUBMITTED,
            trigger_conditions={'form_type': 'home_valuation'},
            goal="Schedule listing appointment"
        )
        
        self.add_step(seller_campaign.id, MessageType.EMAIL, 0, 0, 0,
            subject="Your Home Valuation Report",
            content="Hi {first_name},\n\nThank you for requesting a home valuation...")
        
        self.add_step(seller_campaign.id, MessageType.EMAIL, 3, 0, 0,
            subject="What's Happening in Your Neighborhood",
            content="Hi {first_name},\n\nHere's a quick market update for your area...")
        
        self.add_step(seller_campaign.id, MessageType.SMS, 5, 0, 0,
            content="Hi {first_name}! Did you receive your home valuation? Happy to discuss in detail.")
        
        self.activate_campaign(buyer_campaign.id)
        self.activate_campaign(seller_campaign.id)
    
    def create_campaign(
        self,
        name: str,
        description: str = "",
        trigger_type: TriggerType = TriggerType.MANUAL,
        trigger_conditions: Dict = None,
        goal: str = "",
        tags: List[str] = None,
        created_by: str = ""
    ) -> DripCampaign:
        """Create a new drip campaign."""
        campaign = DripCampaign(
            id=str(uuid.uuid4())[:12],
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_conditions=trigger_conditions or {},
            goal=goal,
            tags=tags or [],
            created_by=created_by
        )
        self.campaigns[campaign.id] = campaign
        self._save_data()
        return campaign
    
    def add_step(
        self,
        campaign_id: str,
        message_type: MessageType,
        delay_days: int = 0,
        delay_hours: int = 0,
        delay_minutes: int = 0,
        **kwargs
    ) -> Optional[CampaignStep]:
        """Add a step to a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        order = len(campaign.steps) + 1
        step = CampaignStep(
            id=str(uuid.uuid4())[:8],
            order=order,
            message_type=message_type,
            delay_days=delay_days,
            delay_hours=delay_hours,
            delay_minutes=delay_minutes,
            template_id=kwargs.get('template_id', ''),
            subject=kwargs.get('subject', ''),
            content=kwargs.get('content', ''),
            conditions=kwargs.get('conditions', {}),
            send_time=kwargs.get('send_time', ''),
            send_days=kwargs.get('send_days', [])
        )
        campaign.steps.append(step)
        campaign.updated_at = datetime.now()
        self._save_data()
        return step
    
    def activate_campaign(self, campaign_id: str) -> bool:
        """Activate a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.ACTIVE
        campaign.updated_at = datetime.now()
        self._save_data()
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.PAUSED
        campaign.updated_at = datetime.now()
        self._save_data()
        return True
    
    def enroll_lead(
        self,
        campaign_id: str,
        lead_id: str
    ) -> Optional[CampaignEnrollment]:
        """Enroll a lead in a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return None
        
        # Check if already enrolled
        for enrollment in self.enrollments.values():
            if enrollment.campaign_id == campaign_id and enrollment.lead_id == lead_id:
                if enrollment.status == 'active':
                    return None  # Already enrolled
        
        # Calculate next action time based on first step
        next_action = datetime.now()
        if campaign.steps:
            first_step = campaign.steps[0]
            next_action += timedelta(
                days=first_step.delay_days,
                hours=first_step.delay_hours,
                minutes=first_step.delay_minutes
            )
        
        enrollment = CampaignEnrollment(
            id=str(uuid.uuid4())[:12],
            campaign_id=campaign_id,
            lead_id=lead_id,
            next_action_at=next_action
        )
        self.enrollments[enrollment.id] = enrollment
        self._save_data()
        return enrollment
    
    def unenroll_lead(self, enrollment_id: str, reason: str = "manual") -> bool:
        """Remove a lead from a campaign."""
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment:
            return False
        
        enrollment.status = 'unsubscribed' if reason == 'unsubscribe' else 'paused'
        self._save_data()
        return True
    
    def advance_enrollment(self, enrollment_id: str) -> Optional[CampaignStep]:
        """Advance enrollment to next step."""
        enrollment = self.enrollments.get(enrollment_id)
        if not enrollment or enrollment.status != 'active':
            return None
        
        campaign = self.campaigns.get(enrollment.campaign_id)
        if not campaign:
            return None
        
        enrollment.last_action_at = datetime.now()
        enrollment.current_step += 1
        
        # Check if campaign is complete
        if enrollment.current_step >= len(campaign.steps):
            enrollment.status = 'completed'
            enrollment.completed_at = datetime.now()
            enrollment.next_action_at = None
            self._save_data()
            return None
        
        # Calculate next action time
        next_step = campaign.steps[enrollment.current_step]
        enrollment.next_action_at = datetime.now() + timedelta(
            days=next_step.delay_days,
            hours=next_step.delay_hours,
            minutes=next_step.delay_minutes
        )
        
        self._save_data()
        return next_step
    
    def get_pending_actions(self) -> List[Dict]:
        """Get all pending campaign actions."""
        pending = []
        now = datetime.now()
        
        for enrollment in self.enrollments.values():
            if enrollment.status != 'active':
                continue
            
            if enrollment.next_action_at and enrollment.next_action_at <= now:
                campaign = self.campaigns.get(enrollment.campaign_id)
                if campaign and campaign.status == CampaignStatus.ACTIVE:
                    step = campaign.steps[enrollment.current_step] if enrollment.current_step < len(campaign.steps) else None
                    if step:
                        pending.append({
                            'enrollment_id': enrollment.id,
                            'lead_id': enrollment.lead_id,
                            'campaign_id': enrollment.campaign_id,
                            'campaign_name': campaign.name,
                            'step': step,
                            'scheduled_for': enrollment.next_action_at
                        })
        
        return pending
    
    def get_campaign_stats(self, campaign_id: str) -> Dict:
        """Get statistics for a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        enrollments = [e for e in self.enrollments.values() if e.campaign_id == campaign_id]
        
        return {
            'campaign_id': campaign_id,
            'name': campaign.name,
            'status': campaign.status.value,
            'total_enrolled': len(enrollments),
            'active': len([e for e in enrollments if e.status == 'active']),
            'completed': len([e for e in enrollments if e.status == 'completed']),
            'unsubscribed': len([e for e in enrollments if e.status == 'unsubscribed']),
            'steps': len(campaign.steps),
            'completion_rate': round(
                len([e for e in enrollments if e.status == 'completed']) / len(enrollments) * 100, 1
            ) if enrollments else 0
        }
    
    def get_lead_campaigns(self, lead_id: str) -> List[Dict]:
        """Get all campaigns a lead is enrolled in."""
        enrollments = [e for e in self.enrollments.values() if e.lead_id == lead_id]
        
        result = []
        for enrollment in enrollments:
            campaign = self.campaigns.get(enrollment.campaign_id)
            if campaign:
                result.append({
                    'enrollment_id': enrollment.id,
                    'campaign_id': campaign.id,
                    'campaign_name': campaign.name,
                    'status': enrollment.status,
                    'current_step': enrollment.current_step,
                    'total_steps': len(campaign.steps),
                    'enrolled_at': enrollment.enrolled_at.isoformat(),
                    'next_action': enrollment.next_action_at.isoformat() if enrollment.next_action_at else None
                })
        
        return result
