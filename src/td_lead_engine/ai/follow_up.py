"""AI-powered follow-up advisor."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any


class FollowUpPriority(Enum):
    """Priority levels for follow-up actions."""
    CRITICAL = "critical"  # Must do today
    HIGH = "high"          # Should do today
    MEDIUM = "medium"      # This week
    LOW = "low"            # When convenient


class FollowUpChannel(Enum):
    """Communication channel for follow-up."""
    PHONE = "phone"
    EMAIL = "email"
    TEXT = "text"
    VIDEO_CALL = "video_call"
    IN_PERSON = "in_person"


@dataclass
class FollowUpAction:
    """A recommended follow-up action."""
    id: str
    lead_id: str
    lead_name: str
    priority: FollowUpPriority
    channel: FollowUpChannel
    subject: str
    suggested_message: str
    talking_points: List[str]
    best_time: str
    deadline: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class FollowUpAdvisor:
    """AI advisor for lead follow-ups."""

    def __init__(self):
        # Optimal contact times by lead characteristics
        self.optimal_times = {
            'professional': {'start': 12, 'end': 13, 'days': ['tue', 'wed', 'thu']},  # Lunch hour
            'stay_at_home': {'start': 10, 'end': 14, 'days': ['mon', 'tue', 'wed', 'thu', 'fri']},
            'evening_available': {'start': 18, 'end': 20, 'days': ['mon', 'tue', 'wed', 'thu']},
            'weekend_only': {'start': 10, 'end': 16, 'days': ['sat', 'sun']},
            'default': {'start': 10, 'end': 18, 'days': ['tue', 'wed', 'thu']}
        }
        
        # Channel effectiveness by scenario
        self.channel_preferences = {
            'hot_lead': FollowUpChannel.PHONE,
            'new_inquiry': FollowUpChannel.PHONE,
            'listing_follow_up': FollowUpChannel.EMAIL,
            'showing_follow_up': FollowUpChannel.TEXT,
            'market_update': FollowUpChannel.EMAIL,
            're_engagement': FollowUpChannel.TEXT,
            'nurture': FollowUpChannel.EMAIL,
            'urgent': FollowUpChannel.PHONE
        }

    def get_follow_up_plan(self, lead: Dict) -> FollowUpAction:
        """Generate a follow-up action plan for a lead."""
        import uuid
        
        lead_id = lead.get('id', '')
        lead_name = lead.get('name', 'Lead')
        score = lead.get('score', 0)
        stage = lead.get('stage', 'new')
        last_contact = lead.get('last_contact_date')
        lead_type = lead.get('lead_type', 'buyer')
        
        # Determine scenario
        scenario = self._determine_scenario(lead)
        
        # Get priority
        priority = self._calculate_priority(lead, scenario)
        
        # Get best channel
        channel = self._get_best_channel(lead, scenario)
        
        # Get best time
        best_time = self._get_best_contact_time(lead)
        
        # Generate subject and message
        subject, message = self._generate_message(lead, scenario)
        
        # Generate talking points
        talking_points = self._generate_talking_points(lead, scenario)
        
        # Calculate deadline
        deadline = self._calculate_deadline(priority)
        
        return FollowUpAction(
            id=str(uuid.uuid4()),
            lead_id=lead_id,
            lead_name=lead_name,
            priority=priority,
            channel=channel,
            subject=subject,
            suggested_message=message,
            talking_points=talking_points,
            best_time=best_time,
            deadline=deadline,
            context={
                'scenario': scenario,
                'score': score,
                'stage': stage,
                'lead_type': lead_type
            }
        )

    def get_daily_follow_ups(
        self,
        leads: List[Dict],
        limit: int = 20
    ) -> List[FollowUpAction]:
        """Get prioritized follow-up list for the day."""
        actions = []
        
        for lead in leads:
            if self._needs_follow_up(lead):
                action = self.get_follow_up_plan(lead)
                actions.append(action)
        
        # Sort by priority
        priority_order = {
            FollowUpPriority.CRITICAL: 0,
            FollowUpPriority.HIGH: 1,
            FollowUpPriority.MEDIUM: 2,
            FollowUpPriority.LOW: 3
        }
        
        actions.sort(key=lambda a: (priority_order[a.priority], -a.context.get('score', 0)))
        
        return actions[:limit]

    def _determine_scenario(self, lead: Dict) -> str:
        """Determine the follow-up scenario."""
        score = lead.get('score', 0)
        stage = lead.get('stage', 'new')
        days_since_contact = self._days_since_contact(lead)
        last_activity = lead.get('last_activity_type')
        
        if score >= 80:
            return 'hot_lead'
        elif stage == 'new' and days_since_contact <= 1:
            return 'new_inquiry'
        elif last_activity == 'showing_completed':
            return 'showing_follow_up'
        elif last_activity == 'listing_viewed':
            return 'listing_follow_up'
        elif days_since_contact >= 14:
            return 're_engagement'
        elif stage in ['nurturing', 'long_term']:
            return 'nurture'
        else:
            return 'general'

    def _calculate_priority(self, lead: Dict, scenario: str) -> FollowUpPriority:
        """Calculate follow-up priority."""
        score = lead.get('score', 0)
        days_since_contact = self._days_since_contact(lead)
        
        if scenario == 'hot_lead' or score >= 85:
            return FollowUpPriority.CRITICAL
        elif scenario in ['new_inquiry', 'showing_follow_up'] or score >= 70:
            return FollowUpPriority.HIGH
        elif days_since_contact >= 7 and score >= 50:
            return FollowUpPriority.MEDIUM
        else:
            return FollowUpPriority.LOW

    def _get_best_channel(self, lead: Dict, scenario: str) -> FollowUpChannel:
        """Determine best communication channel."""
        # Check lead preferences
        preferred_channel = lead.get('preferred_contact_method')
        if preferred_channel:
            channel_map = {
                'phone': FollowUpChannel.PHONE,
                'email': FollowUpChannel.EMAIL,
                'text': FollowUpChannel.TEXT
            }
            if preferred_channel.lower() in channel_map:
                return channel_map[preferred_channel.lower()]
        
        # Use scenario-based defaults
        return self.channel_preferences.get(scenario, FollowUpChannel.EMAIL)

    def _get_best_contact_time(self, lead: Dict) -> str:
        """Determine best time to contact."""
        availability = lead.get('availability_type', 'default')
        occupation = lead.get('occupation', '').lower()
        
        # Infer availability from occupation
        if not availability or availability == 'default':
            if any(term in occupation for term in ['executive', 'manager', 'professional', 'engineer']):
                availability = 'professional'
            elif any(term in occupation for term in ['teacher', 'nurse', 'shift']):
                availability = 'evening_available'
        
        times = self.optimal_times.get(availability, self.optimal_times['default'])
        
        return f"{times['start']}:00 - {times['end']}:00 on {', '.join(times['days'][:3]).title()}"

    def _generate_message(self, lead: Dict, scenario: str) -> tuple:
        """Generate subject and message for follow-up."""
        name = lead.get('name', '').split()[0] if lead.get('name') else 'there'
        lead_type = lead.get('lead_type', 'buyer')
        
        templates = {
            'hot_lead': (
                "Quick follow-up",
                f"Hi {name}, I wanted to reach out personally - I noticed you've been actively searching and I'd love to help you find the perfect home. Do you have 15 minutes to chat about what you're looking for?"
            ),
            'new_inquiry': (
                "Thanks for reaching out!",
                f"Hi {name}! Thanks for your interest in {'finding a home' if lead_type == 'buyer' else 'selling your home'}. I'd love to learn more about your needs. When would be a good time to connect?"
            ),
            'showing_follow_up': (
                "Thoughts on the showing?",
                f"Hi {name}, I hope you enjoyed the showing! I'd love to hear your thoughts. What did you think of the property? Anything else you'd like to see?"
            ),
            'listing_follow_up': (
                "More info on the listing",
                f"Hi {name}, I noticed you were looking at some listings. I have some great options that match your criteria. Want me to send you more details?"
            ),
            're_engagement': (
                "Still looking for your dream home?",
                f"Hi {name}, it's been a while since we connected! I wanted to check in - are you still in the market? The Columbus area has some great new options."
            ),
            'nurture': (
                "Market update for you",
                f"Hi {name}, I wanted to share some interesting market updates that might be relevant to your search. Let me know if you'd like to discuss!"
            ),
            'general': (
                "Checking in",
                f"Hi {name}, just wanted to touch base and see how your {'home search' if lead_type == 'buyer' else 'selling process'} is going. Anything I can help with?"
            )
        }
        
        return templates.get(scenario, templates['general'])

    def _generate_talking_points(self, lead: Dict, scenario: str) -> List[str]:
        """Generate talking points for the conversation."""
        points = []
        lead_type = lead.get('lead_type', 'buyer')
        
        if scenario == 'hot_lead':
            points.extend([
                "Confirm their timeline and urgency",
                "Understand their must-haves vs. nice-to-haves",
                "Discuss pre-approval status (if buyer)",
                "Offer to schedule showings this week"
            ])
        elif scenario == 'new_inquiry':
            points.extend([
                "Thank them for reaching out",
                "Ask about their ideal timeline",
                "Understand their motivation for moving",
                "Explain your process and how you can help"
            ])
        elif scenario == 'showing_follow_up':
            points.extend([
                "Get their overall impression",
                "Ask what they liked and didn't like",
                "Gauge their interest level (1-10)",
                "Discuss next steps or other options"
            ])
        
        # Add lead-type specific points
        if lead_type == 'buyer':
            if not lead.get('preapproved'):
                points.append("Discuss mortgage pre-approval")
            if lead.get('search_criteria'):
                points.append("Review and refine search criteria")
        elif lead_type == 'seller':
            if not lead.get('cma_sent'):
                points.append("Offer free CMA/home valuation")
            points.append("Discuss timeline for listing")
        
        return points[:6]

    def _calculate_deadline(self, priority: FollowUpPriority) -> datetime:
        """Calculate deadline based on priority."""
        now = datetime.now()
        
        if priority == FollowUpPriority.CRITICAL:
            return now + timedelta(hours=4)
        elif priority == FollowUpPriority.HIGH:
            return now + timedelta(hours=24)
        elif priority == FollowUpPriority.MEDIUM:
            return now + timedelta(days=3)
        else:
            return now + timedelta(days=7)

    def _needs_follow_up(self, lead: Dict) -> bool:
        """Determine if a lead needs follow-up."""
        stage = lead.get('stage', '')
        
        # Don't follow up on closed or lost leads
        if stage in ['closed', 'lost', 'unqualified']:
            return False
        
        days_since = self._days_since_contact(lead)
        score = lead.get('score', 0)
        
        # Hot leads always need attention
        if score >= 80:
            return days_since >= 1
        
        # Warm leads - every few days
        if score >= 50:
            return days_since >= 3
        
        # Cold leads - weekly
        return days_since >= 7

    def _days_since_contact(self, lead: Dict) -> int:
        """Calculate days since last contact."""
        last_contact = lead.get('last_contact_date')
        if not last_contact:
            created = lead.get('created_at')
            last_contact = created
        
        if not last_contact:
            return 30
        
        if isinstance(last_contact, str):
            try:
                last_contact = datetime.fromisoformat(last_contact.replace('Z', '+00:00'))
            except:
                return 30
        
        return (datetime.now() - last_contact.replace(tzinfo=None)).days
