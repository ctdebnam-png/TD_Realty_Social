"""Open house follow-up automation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid

from .manager import OpenHouseManager, OpenHouseAttendee


class FollowUpType(Enum):
    """Types of follow-up actions."""
    THANK_YOU_EMAIL = "thank_you_email"
    PROPERTY_INFO = "property_info"
    SIMILAR_LISTINGS = "similar_listings"
    MARKET_UPDATE = "market_update"
    SCHEDULE_SHOWING = "schedule_showing"
    BUYER_CONSULTATION = "buyer_consultation"
    PHONE_CALL = "phone_call"
    TEXT_MESSAGE = "text_message"
    FEEDBACK_REQUEST = "feedback_request"


class FollowUpStatus(Enum):
    """Follow-up status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class FollowUpAction:
    """A follow-up action for an open house attendee."""
    id: str
    attendee_id: str
    open_house_id: str
    follow_up_type: FollowUpType
    status: FollowUpStatus = FollowUpStatus.PENDING
    scheduled_for: datetime = None
    completed_at: datetime = None
    content: Dict = field(default_factory=dict)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass 
class FollowUpSequence:
    """A sequence of follow-up actions."""
    id: str
    name: str
    description: str = ""
    steps: List[Dict] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class OpenHouseFollowUp:
    """Manage open house follow-up automation."""
    
    def __init__(
        self,
        open_house_manager: OpenHouseManager,
        storage_path: str = "data/oh_followup"
    ):
        self.oh_manager = open_house_manager
        self.storage_path = storage_path
        self.actions: Dict[str, FollowUpAction] = {}
        self.sequences: Dict[str, FollowUpSequence] = {}
        
        self._load_data()
        self._create_default_sequences()
    
    def _load_data(self):
        """Load follow-up data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load actions
        actions_file = f"{self.storage_path}/actions.json"
        if os.path.exists(actions_file):
            with open(actions_file, 'r') as f:
                data = json.load(f)
                for action_data in data:
                    action = FollowUpAction(
                        id=action_data['id'],
                        attendee_id=action_data['attendee_id'],
                        open_house_id=action_data['open_house_id'],
                        follow_up_type=FollowUpType(action_data['follow_up_type']),
                        status=FollowUpStatus(action_data['status']),
                        scheduled_for=datetime.fromisoformat(action_data['scheduled_for']) if action_data.get('scheduled_for') else None,
                        completed_at=datetime.fromisoformat(action_data['completed_at']) if action_data.get('completed_at') else None,
                        content=action_data.get('content', {}),
                        notes=action_data.get('notes', ''),
                        created_at=datetime.fromisoformat(action_data['created_at']) if action_data.get('created_at') else datetime.now()
                    )
                    self.actions[action.id] = action
        
        # Load sequences
        sequences_file = f"{self.storage_path}/sequences.json"
        if os.path.exists(sequences_file):
            with open(sequences_file, 'r') as f:
                data = json.load(f)
                for seq_data in data:
                    sequence = FollowUpSequence(
                        id=seq_data['id'],
                        name=seq_data['name'],
                        description=seq_data.get('description', ''),
                        steps=seq_data.get('steps', []),
                        is_active=seq_data.get('is_active', True),
                        created_at=datetime.fromisoformat(seq_data['created_at']) if seq_data.get('created_at') else datetime.now()
                    )
                    self.sequences[sequence.id] = sequence
    
    def _save_data(self):
        """Save follow-up data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save actions
        actions_data = [
            {
                'id': a.id,
                'attendee_id': a.attendee_id,
                'open_house_id': a.open_house_id,
                'follow_up_type': a.follow_up_type.value,
                'status': a.status.value,
                'scheduled_for': a.scheduled_for.isoformat() if a.scheduled_for else None,
                'completed_at': a.completed_at.isoformat() if a.completed_at else None,
                'content': a.content,
                'notes': a.notes,
                'created_at': a.created_at.isoformat()
            }
            for a in self.actions.values()
        ]
        
        with open(f"{self.storage_path}/actions.json", 'w') as f:
            json.dump(actions_data, f, indent=2)
        
        # Save sequences
        sequences_data = [
            {
                'id': s.id,
                'name': s.name,
                'description': s.description,
                'steps': s.steps,
                'is_active': s.is_active,
                'created_at': s.created_at.isoformat()
            }
            for s in self.sequences.values()
        ]
        
        with open(f"{self.storage_path}/sequences.json", 'w') as f:
            json.dump(sequences_data, f, indent=2)
    
    def _create_default_sequences(self):
        """Create default follow-up sequences."""
        if self.sequences:
            return
        
        # Hot lead sequence (working with agent = No, preapproved = Yes)
        hot_lead_sequence = FollowUpSequence(
            id="seq_hot_lead",
            name="Hot Lead Follow-Up",
            description="For qualified buyers not working with an agent",
            steps=[
                {
                    'delay_hours': 0,
                    'type': FollowUpType.THANK_YOU_EMAIL.value,
                    'subject': "Thanks for visiting {property_address}!",
                    'template': 'hot_lead_thank_you'
                },
                {
                    'delay_hours': 2,
                    'type': FollowUpType.PHONE_CALL.value,
                    'script': 'hot_lead_call'
                },
                {
                    'delay_hours': 24,
                    'type': FollowUpType.SIMILAR_LISTINGS.value,
                    'subject': "Similar homes you might love",
                    'template': 'similar_listings'
                },
                {
                    'delay_hours': 72,
                    'type': FollowUpType.BUYER_CONSULTATION.value,
                    'subject': "Let's find your perfect home",
                    'template': 'consultation_invite'
                }
            ]
        )
        self.sequences[hot_lead_sequence.id] = hot_lead_sequence
        
        # Warm lead sequence (interested but not preapproved)
        warm_lead_sequence = FollowUpSequence(
            id="seq_warm_lead",
            name="Warm Lead Follow-Up",
            description="For interested buyers who need financing help",
            steps=[
                {
                    'delay_hours': 1,
                    'type': FollowUpType.THANK_YOU_EMAIL.value,
                    'subject': "Great meeting you at {property_address}!",
                    'template': 'warm_lead_thank_you'
                },
                {
                    'delay_hours': 24,
                    'type': FollowUpType.PROPERTY_INFO.value,
                    'subject': "More details about {property_address}",
                    'template': 'property_details'
                },
                {
                    'delay_hours': 48,
                    'type': FollowUpType.TEXT_MESSAGE.value,
                    'message': "Hi {first_name}! Just checking in - would you like me to connect you with a great lender to explore your options?"
                },
                {
                    'delay_hours': 168,
                    'type': FollowUpType.MARKET_UPDATE.value,
                    'subject': "Weekly market update for your search area",
                    'template': 'market_update'
                }
            ]
        )
        self.sequences[warm_lead_sequence.id] = warm_lead_sequence
        
        # General follow-up sequence
        general_sequence = FollowUpSequence(
            id="seq_general",
            name="General Follow-Up",
            description="Standard follow-up for all attendees",
            steps=[
                {
                    'delay_hours': 2,
                    'type': FollowUpType.THANK_YOU_EMAIL.value,
                    'subject': "Thank you for visiting {property_address}",
                    'template': 'general_thank_you'
                },
                {
                    'delay_hours': 72,
                    'type': FollowUpType.FEEDBACK_REQUEST.value,
                    'subject': "What did you think of {property_address}?",
                    'template': 'feedback_request'
                }
            ]
        )
        self.sequences[general_sequence.id] = general_sequence
        
        self._save_data()
    
    def start_follow_up(
        self,
        attendee: OpenHouseAttendee,
        sequence_id: str = None
    ) -> List[FollowUpAction]:
        """Start follow-up sequence for an attendee."""
        # Determine which sequence to use
        if not sequence_id:
            sequence_id = self._get_best_sequence(attendee)
        
        sequence = self.sequences.get(sequence_id)
        if not sequence or not sequence.is_active:
            return []
        
        actions = []
        base_time = datetime.now()
        
        for step in sequence.steps:
            delay_hours = step.get('delay_hours', 0)
            scheduled_time = base_time + timedelta(hours=delay_hours)
            
            action = FollowUpAction(
                id=str(uuid.uuid4())[:12],
                attendee_id=attendee.id,
                open_house_id=attendee.open_house_id,
                follow_up_type=FollowUpType(step['type']),
                status=FollowUpStatus.SCHEDULED,
                scheduled_for=scheduled_time,
                content=step
            )
            
            self.actions[action.id] = action
            actions.append(action)
        
        self._save_data()
        return actions
    
    def _get_best_sequence(self, attendee: OpenHouseAttendee) -> str:
        """Determine the best follow-up sequence for an attendee."""
        # Hot lead: not working with agent and preapproved
        if not attendee.working_with_agent and attendee.preapproved:
            return "seq_hot_lead"
        
        # Warm lead: not working with agent
        if not attendee.working_with_agent:
            return "seq_warm_lead"
        
        # Default to general sequence
        return "seq_general"
    
    def get_pending_actions(
        self,
        open_house_id: str = None,
        before: datetime = None
    ) -> List[FollowUpAction]:
        """Get pending follow-up actions."""
        actions = []
        check_time = before or datetime.now()
        
        for action in self.actions.values():
            if action.status not in [FollowUpStatus.PENDING, FollowUpStatus.SCHEDULED]:
                continue
            
            if open_house_id and action.open_house_id != open_house_id:
                continue
            
            if action.scheduled_for and action.scheduled_for <= check_time:
                actions.append(action)
        
        actions.sort(key=lambda a: a.scheduled_for or datetime.min)
        return actions
    
    def execute_action(self, action_id: str) -> bool:
        """Execute a follow-up action."""
        action = self.actions.get(action_id)
        if not action:
            return False
        
        # Get attendee info
        attendee = None
        oh = self.oh_manager.get_open_house(action.open_house_id)
        if oh:
            for a in oh.attendees:
                if a.id == action.attendee_id:
                    attendee = a
                    break
        
        if not attendee:
            action.status = FollowUpStatus.FAILED
            action.notes = "Attendee not found"
            self._save_data()
            return False
        
        # Execute based on type
        success = False
        if action.follow_up_type == FollowUpType.THANK_YOU_EMAIL:
            success = self._send_thank_you_email(attendee, action)
        elif action.follow_up_type == FollowUpType.PROPERTY_INFO:
            success = self._send_property_info(attendee, action)
        elif action.follow_up_type == FollowUpType.SIMILAR_LISTINGS:
            success = self._send_similar_listings(attendee, action)
        elif action.follow_up_type == FollowUpType.MARKET_UPDATE:
            success = self._send_market_update(attendee, action)
        elif action.follow_up_type == FollowUpType.PHONE_CALL:
            success = self._create_call_task(attendee, action)
        elif action.follow_up_type == FollowUpType.TEXT_MESSAGE:
            success = self._send_text_message(attendee, action)
        elif action.follow_up_type == FollowUpType.FEEDBACK_REQUEST:
            success = self._send_feedback_request(attendee, action)
        elif action.follow_up_type == FollowUpType.BUYER_CONSULTATION:
            success = self._send_consultation_invite(attendee, action)
        elif action.follow_up_type == FollowUpType.SCHEDULE_SHOWING:
            success = self._send_showing_invite(attendee, action)
        else:
            success = True  # Unknown type, mark as complete
        
        if success:
            action.status = FollowUpStatus.COMPLETED
            action.completed_at = datetime.now()
        else:
            action.status = FollowUpStatus.FAILED
        
        self._save_data()
        return success
    
    def _send_thank_you_email(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send thank you email."""
        # Would integrate with email module
        # For now, return True to simulate success
        return True
    
    def _send_property_info(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send property information email."""
        return True
    
    def _send_similar_listings(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send similar listings email."""
        return True
    
    def _send_market_update(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send market update email."""
        return True
    
    def _create_call_task(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Create a task to call the attendee."""
        # Would integrate with task module
        return True
    
    def _send_text_message(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send text message."""
        # Would integrate with SMS module
        return True
    
    def _send_feedback_request(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send feedback request email."""
        return True
    
    def _send_consultation_invite(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send buyer consultation invite."""
        return True
    
    def _send_showing_invite(self, attendee: OpenHouseAttendee, action: FollowUpAction) -> bool:
        """Send private showing invite."""
        return True
    
    def skip_action(self, action_id: str, reason: str = "") -> bool:
        """Skip a follow-up action."""
        action = self.actions.get(action_id)
        if not action:
            return False
        
        action.status = FollowUpStatus.SKIPPED
        action.notes = reason
        self._save_data()
        return True
    
    def get_attendee_actions(self, attendee_id: str) -> List[FollowUpAction]:
        """Get all follow-up actions for an attendee."""
        actions = [a for a in self.actions.values() if a.attendee_id == attendee_id]
        actions.sort(key=lambda a: a.scheduled_for or datetime.min)
        return actions
    
    def get_open_house_summary(self, open_house_id: str) -> Dict:
        """Get follow-up summary for an open house."""
        actions = [a for a in self.actions.values() if a.open_house_id == open_house_id]
        
        by_status = {}
        for status in FollowUpStatus:
            by_status[status.value] = len([a for a in actions if a.status == status])
        
        by_type = {}
        for ftype in FollowUpType:
            by_type[ftype.value] = len([a for a in actions if a.follow_up_type == ftype])
        
        return {
            'total_actions': len(actions),
            'by_status': by_status,
            'by_type': by_type,
            'pending': by_status.get('pending', 0) + by_status.get('scheduled', 0),
            'completed': by_status.get('completed', 0),
            'completion_rate': (by_status.get('completed', 0) / len(actions) * 100) if actions else 0
        }
    
    def create_sequence(
        self,
        name: str,
        steps: List[Dict],
        description: str = ""
    ) -> FollowUpSequence:
        """Create a custom follow-up sequence."""
        sequence = FollowUpSequence(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            steps=steps
        )
        self.sequences[sequence.id] = sequence
        self._save_data()
        return sequence
    
    def get_sequences(self) -> List[FollowUpSequence]:
        """Get all follow-up sequences."""
        return list(self.sequences.values())
    
    def process_pending_actions(self) -> Dict:
        """Process all pending follow-up actions that are due."""
        pending = self.get_pending_actions()
        results = {
            'processed': 0,
            'succeeded': 0,
            'failed': 0
        }
        
        for action in pending:
            results['processed'] += 1
            if self.execute_action(action.id):
                results['succeeded'] += 1
            else:
                results['failed'] += 1
        
        return results
    
    def generate_follow_up_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Generate a follow-up performance report."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        actions = [
            a for a in self.actions.values()
            if a.created_at >= start and a.created_at <= end
        ]
        
        completed = [a for a in actions if a.status == FollowUpStatus.COMPLETED]
        
        # Calculate response times
        response_times = []
        for action in completed:
            if action.scheduled_for and action.completed_at:
                delay = (action.completed_at - action.scheduled_for).total_seconds() / 3600
                response_times.append(delay)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Type breakdown
        type_stats = {}
        for ftype in FollowUpType:
            type_actions = [a for a in actions if a.follow_up_type == ftype]
            type_completed = [a for a in type_actions if a.status == FollowUpStatus.COMPLETED]
            type_stats[ftype.value] = {
                'total': len(type_actions),
                'completed': len(type_completed),
                'rate': (len(type_completed) / len(type_actions) * 100) if type_actions else 0
            }
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'summary': {
                'total_actions': len(actions),
                'completed': len(completed),
                'completion_rate': (len(completed) / len(actions) * 100) if actions else 0,
                'avg_response_time_hours': round(avg_response_time, 2)
            },
            'by_type': type_stats
        }
