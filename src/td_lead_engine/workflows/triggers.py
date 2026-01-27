"""Workflow triggers module."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class TriggerType(Enum):
    """Types of workflow triggers."""
    # Lead triggers
    LEAD_CREATED = "lead_created"
    LEAD_UPDATED = "lead_updated"
    LEAD_STATUS_CHANGED = "lead_status_changed"
    LEAD_SCORE_CHANGED = "lead_score_changed"
    LEAD_ASSIGNED = "lead_assigned"
    LEAD_TAG_ADDED = "lead_tag_added"
    
    # Activity triggers
    FORM_SUBMITTED = "form_submitted"
    PAGE_VISITED = "page_visited"
    EMAIL_OPENED = "email_opened"
    EMAIL_CLICKED = "email_clicked"
    EMAIL_REPLIED = "email_replied"
    SMS_RECEIVED = "sms_received"
    CALL_COMPLETED = "call_completed"
    
    # Property triggers
    PROPERTY_VIEWED = "property_viewed"
    PROPERTY_SAVED = "property_saved"
    PROPERTY_INQUIRY = "property_inquiry"
    SHOWING_SCHEDULED = "showing_scheduled"
    SHOWING_COMPLETED = "showing_completed"
    
    # Time triggers
    SCHEDULE = "schedule"
    DATE_REACHED = "date_reached"
    INACTIVITY = "inactivity"
    
    # External triggers
    WEBHOOK = "webhook"
    API_CALL = "api_call"


@dataclass
class Trigger:
    """A workflow trigger configuration."""
    id: str
    name: str
    trigger_type: TriggerType
    workflow_id: str
    enabled: bool = True
    conditions: Dict = field(default_factory=dict)
    filter_criteria: Dict = field(default_factory=dict)
    cooldown_minutes: int = 0  # Minimum time between triggers for same lead
    max_triggers_per_lead: int = 0  # 0 = unlimited
    created_at: datetime = field(default_factory=datetime.now)
    last_triggered: datetime = None
    trigger_count: int = 0


@dataclass
class TriggerEvent:
    """An event that may trigger a workflow."""
    event_type: TriggerType
    lead_id: str
    data: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""


class TriggerManager:
    """Manage workflow triggers."""
    
    def __init__(
        self,
        storage_path: str = "data/triggers",
        workflow_start_callback: Callable = None
    ):
        self.storage_path = storage_path
        self.triggers: Dict[str, Trigger] = {}
        self.trigger_history: Dict[str, List[Dict]] = {}  # lead_id -> trigger history
        self.workflow_start_callback = workflow_start_callback
        
        self._load_data()
    
    def _load_data(self):
        """Load triggers from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        triggers_file = f"{self.storage_path}/triggers.json"
        if os.path.exists(triggers_file):
            with open(triggers_file, 'r') as f:
                data = json.load(f)
                for trigger_data in data:
                    trigger = Trigger(
                        id=trigger_data['id'],
                        name=trigger_data['name'],
                        trigger_type=TriggerType(trigger_data['trigger_type']),
                        workflow_id=trigger_data['workflow_id'],
                        enabled=trigger_data.get('enabled', True),
                        conditions=trigger_data.get('conditions', {}),
                        filter_criteria=trigger_data.get('filter_criteria', {}),
                        cooldown_minutes=trigger_data.get('cooldown_minutes', 0),
                        max_triggers_per_lead=trigger_data.get('max_triggers_per_lead', 0),
                        created_at=datetime.fromisoformat(trigger_data['created_at']) if trigger_data.get('created_at') else datetime.now(),
                        last_triggered=datetime.fromisoformat(trigger_data['last_triggered']) if trigger_data.get('last_triggered') else None,
                        trigger_count=trigger_data.get('trigger_count', 0)
                    )
                    self.triggers[trigger.id] = trigger
        
        # Load trigger history
        history_file = f"{self.storage_path}/trigger_history.json"
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                self.trigger_history = json.load(f)
    
    def _save_data(self):
        """Save triggers to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        triggers_data = [
            {
                'id': t.id,
                'name': t.name,
                'trigger_type': t.trigger_type.value,
                'workflow_id': t.workflow_id,
                'enabled': t.enabled,
                'conditions': t.conditions,
                'filter_criteria': t.filter_criteria,
                'cooldown_minutes': t.cooldown_minutes,
                'max_triggers_per_lead': t.max_triggers_per_lead,
                'created_at': t.created_at.isoformat(),
                'last_triggered': t.last_triggered.isoformat() if t.last_triggered else None,
                'trigger_count': t.trigger_count
            }
            for t in self.triggers.values()
        ]
        
        with open(f"{self.storage_path}/triggers.json", 'w') as f:
            json.dump(triggers_data, f, indent=2)
        
        # Save history (keep last 1000 per lead)
        trimmed_history = {}
        for lead_id, history in self.trigger_history.items():
            trimmed_history[lead_id] = history[-1000:]
        
        with open(f"{self.storage_path}/trigger_history.json", 'w') as f:
            json.dump(trimmed_history, f, indent=2)
    
    def create_trigger(
        self,
        name: str,
        trigger_type: TriggerType,
        workflow_id: str,
        conditions: Dict = None,
        filter_criteria: Dict = None,
        cooldown_minutes: int = 0,
        max_triggers_per_lead: int = 0
    ) -> Trigger:
        """Create a new trigger."""
        trigger = Trigger(
            id=str(uuid.uuid4())[:8],
            name=name,
            trigger_type=trigger_type,
            workflow_id=workflow_id,
            conditions=conditions or {},
            filter_criteria=filter_criteria or {},
            cooldown_minutes=cooldown_minutes,
            max_triggers_per_lead=max_triggers_per_lead
        )
        self.triggers[trigger.id] = trigger
        self._save_data()
        return trigger
    
    def update_trigger(self, trigger_id: str, updates: Dict) -> Optional[Trigger]:
        """Update a trigger."""
        if trigger_id not in self.triggers:
            return None
        
        trigger = self.triggers[trigger_id]
        for key, value in updates.items():
            if hasattr(trigger, key):
                if key == 'trigger_type' and isinstance(value, str):
                    value = TriggerType(value)
                setattr(trigger, key, value)
        
        self._save_data()
        return trigger
    
    def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger."""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]
            self._save_data()
            return True
        return False
    
    def enable_trigger(self, trigger_id: str) -> bool:
        """Enable a trigger."""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = True
            self._save_data()
            return True
        return False
    
    def disable_trigger(self, trigger_id: str) -> bool:
        """Disable a trigger."""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = False
            self._save_data()
            return True
        return False
    
    def process_event(self, event: TriggerEvent) -> List[str]:
        """Process an event and fire matching triggers."""
        fired_workflow_ids = []
        
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue
            
            if trigger.trigger_type != event.event_type:
                continue
            
            # Check conditions
            if not self._check_conditions(trigger, event):
                continue
            
            # Check filter criteria
            if not self._check_filter_criteria(trigger, event):
                continue
            
            # Check cooldown
            if not self._check_cooldown(trigger, event.lead_id):
                continue
            
            # Check max triggers
            if not self._check_max_triggers(trigger, event.lead_id):
                continue
            
            # Fire trigger
            self._fire_trigger(trigger, event)
            fired_workflow_ids.append(trigger.workflow_id)
        
        return fired_workflow_ids
    
    def _check_conditions(self, trigger: Trigger, event: TriggerEvent) -> bool:
        """Check if trigger conditions are met."""
        conditions = trigger.conditions
        
        if not conditions:
            return True
        
        # Status condition
        if 'status' in conditions:
            if event.data.get('status') != conditions['status']:
                return False
        
        # New status condition (for status changes)
        if 'new_status' in conditions:
            if event.data.get('new_status') != conditions['new_status']:
                return False
        
        # Score threshold
        if 'min_score' in conditions:
            if event.data.get('score', 0) < conditions['min_score']:
                return False
        
        # Source condition
        if 'source' in conditions:
            if event.data.get('source') != conditions['source']:
                return False
        
        # Tag condition
        if 'has_tag' in conditions:
            tags = event.data.get('tags', [])
            if conditions['has_tag'] not in tags:
                return False
        
        # Form ID condition
        if 'form_id' in conditions:
            if event.data.get('form_id') != conditions['form_id']:
                return False
        
        # Page URL condition
        if 'page_url_contains' in conditions:
            page_url = event.data.get('page_url', '')
            if conditions['page_url_contains'] not in page_url:
                return False
        
        return True
    
    def _check_filter_criteria(self, trigger: Trigger, event: TriggerEvent) -> bool:
        """Check if filter criteria are met."""
        criteria = trigger.filter_criteria
        
        if not criteria:
            return True
        
        # Lead type filter
        if 'lead_type' in criteria:
            if event.data.get('lead_type') != criteria['lead_type']:
                return False
        
        # Property type filter
        if 'property_type' in criteria:
            if event.data.get('property_type') != criteria['property_type']:
                return False
        
        # Price range filter
        if 'min_price' in criteria:
            if event.data.get('budget', 0) < criteria['min_price']:
                return False
        if 'max_price' in criteria:
            if event.data.get('budget', float('inf')) > criteria['max_price']:
                return False
        
        # Location filter
        if 'cities' in criteria:
            city = event.data.get('city', '').lower()
            if city not in [c.lower() for c in criteria['cities']]:
                return False
        
        return True
    
    def _check_cooldown(self, trigger: Trigger, lead_id: str) -> bool:
        """Check if cooldown period has passed."""
        if trigger.cooldown_minutes <= 0:
            return True
        
        history = self.trigger_history.get(lead_id, [])
        trigger_history = [h for h in history if h['trigger_id'] == trigger.id]
        
        if not trigger_history:
            return True
        
        last_triggered = datetime.fromisoformat(trigger_history[-1]['timestamp'])
        cooldown_end = last_triggered + timedelta(minutes=trigger.cooldown_minutes)
        
        return datetime.now() >= cooldown_end
    
    def _check_max_triggers(self, trigger: Trigger, lead_id: str) -> bool:
        """Check if max triggers limit reached."""
        if trigger.max_triggers_per_lead <= 0:
            return True
        
        history = self.trigger_history.get(lead_id, [])
        trigger_count = len([h for h in history if h['trigger_id'] == trigger.id])
        
        return trigger_count < trigger.max_triggers_per_lead
    
    def _fire_trigger(self, trigger: Trigger, event: TriggerEvent):
        """Fire a trigger and start workflow."""
        # Record in history
        if event.lead_id not in self.trigger_history:
            self.trigger_history[event.lead_id] = []
        
        self.trigger_history[event.lead_id].append({
            'trigger_id': trigger.id,
            'workflow_id': trigger.workflow_id,
            'timestamp': datetime.now().isoformat(),
            'event_type': event.event_type.value
        })
        
        # Update trigger stats
        trigger.last_triggered = datetime.now()
        trigger.trigger_count += 1
        
        self._save_data()
        
        # Start workflow
        if self.workflow_start_callback:
            context = {
                'lead_id': event.lead_id,
                'trigger_type': event.event_type.value,
                'trigger_data': event.data,
                'source': event.source
            }
            self.workflow_start_callback(trigger.workflow_id, event.lead_id, context)
    
    def get_triggers_for_workflow(self, workflow_id: str) -> List[Trigger]:
        """Get all triggers for a workflow."""
        return [t for t in self.triggers.values() if t.workflow_id == workflow_id]
    
    def get_triggers_by_type(self, trigger_type: TriggerType) -> List[Trigger]:
        """Get all triggers of a specific type."""
        return [t for t in self.triggers.values() if t.trigger_type == trigger_type]
    
    def get_lead_trigger_history(self, lead_id: str, limit: int = 50) -> List[Dict]:
        """Get trigger history for a lead."""
        history = self.trigger_history.get(lead_id, [])
        return history[-limit:]
    
    def emit_event(
        self,
        event_type: TriggerType,
        lead_id: str,
        data: Dict = None,
        source: str = ""
    ) -> List[str]:
        """Emit an event to be processed."""
        event = TriggerEvent(
            event_type=event_type,
            lead_id=lead_id,
            data=data or {},
            source=source
        )
        return self.process_event(event)
