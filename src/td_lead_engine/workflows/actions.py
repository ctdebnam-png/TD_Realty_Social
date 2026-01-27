"""Workflow actions module."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import json
import os
import uuid
import requests


class ActionType(Enum):
    """Types of workflow actions."""
    # Communication
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SEND_PUSH = "send_push"
    MAKE_CALL = "make_call"
    
    # Lead management
    UPDATE_LEAD = "update_lead"
    CHANGE_STATUS = "change_status"
    UPDATE_SCORE = "update_score"
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    ASSIGN_AGENT = "assign_agent"
    
    # Task management
    CREATE_TASK = "create_task"
    COMPLETE_TASK = "complete_task"
    SCHEDULE_APPOINTMENT = "schedule_appointment"
    
    # Marketing
    ADD_TO_CAMPAIGN = "add_to_campaign"
    REMOVE_FROM_CAMPAIGN = "remove_from_campaign"
    ADD_TO_LIST = "add_to_list"
    
    # Activity
    LOG_ACTIVITY = "log_activity"
    ADD_NOTE = "add_note"
    
    # External
    WEBHOOK = "webhook"
    API_CALL = "api_call"
    SLACK_MESSAGE = "slack_message"
    
    # Notifications
    NOTIFY_AGENT = "notify_agent"
    NOTIFY_TEAM = "notify_team"
    
    # Property
    SEND_LISTINGS = "send_listings"
    SCHEDULE_SHOWING = "schedule_showing"


@dataclass
class Action:
    """An action to be executed."""
    id: str
    action_type: ActionType
    name: str
    config: Dict = field(default_factory=dict)
    enabled: bool = True
    retry_on_failure: bool = False
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ActionResult:
    """Result of an action execution."""
    action_id: str
    success: bool
    message: str = ""
    data: Dict = field(default_factory=dict)
    executed_at: datetime = field(default_factory=datetime.now)
    error: str = ""


class ActionExecutor:
    """Execute workflow actions."""
    
    def __init__(
        self,
        storage_path: str = "data/actions",
        email_handler: Callable = None,
        sms_handler: Callable = None,
        notification_handler: Callable = None
    ):
        self.storage_path = storage_path
        self.email_handler = email_handler
        self.sms_handler = sms_handler
        self.notification_handler = notification_handler
        
        self.action_handlers: Dict[ActionType, Callable] = {}
        self.execution_history: List[ActionResult] = []
        
        self._register_handlers()
        self._load_history()
    
    def _register_handlers(self):
        """Register action handlers."""
        self.action_handlers = {
            ActionType.SEND_EMAIL: self._execute_send_email,
            ActionType.SEND_SMS: self._execute_send_sms,
            ActionType.SEND_PUSH: self._execute_send_push,
            ActionType.UPDATE_LEAD: self._execute_update_lead,
            ActionType.CHANGE_STATUS: self._execute_change_status,
            ActionType.UPDATE_SCORE: self._execute_update_score,
            ActionType.ADD_TAG: self._execute_add_tag,
            ActionType.REMOVE_TAG: self._execute_remove_tag,
            ActionType.ASSIGN_AGENT: self._execute_assign_agent,
            ActionType.CREATE_TASK: self._execute_create_task,
            ActionType.SCHEDULE_APPOINTMENT: self._execute_schedule_appointment,
            ActionType.ADD_TO_CAMPAIGN: self._execute_add_to_campaign,
            ActionType.LOG_ACTIVITY: self._execute_log_activity,
            ActionType.ADD_NOTE: self._execute_add_note,
            ActionType.WEBHOOK: self._execute_webhook,
            ActionType.API_CALL: self._execute_api_call,
            ActionType.SLACK_MESSAGE: self._execute_slack_message,
            ActionType.NOTIFY_AGENT: self._execute_notify_agent,
            ActionType.NOTIFY_TEAM: self._execute_notify_team,
            ActionType.SEND_LISTINGS: self._execute_send_listings,
            ActionType.SCHEDULE_SHOWING: self._execute_schedule_showing
        }
    
    def _load_history(self):
        """Load execution history."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        history_file = f"{self.storage_path}/action_history.json"
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                data = json.load(f)
                self.execution_history = [
                    ActionResult(
                        action_id=r['action_id'],
                        success=r['success'],
                        message=r.get('message', ''),
                        data=r.get('data', {}),
                        executed_at=datetime.fromisoformat(r['executed_at']),
                        error=r.get('error', '')
                    )
                    for r in data[-1000:]  # Keep last 1000
                ]
    
    def _save_history(self):
        """Save execution history."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'action_id': r.action_id,
                'success': r.success,
                'message': r.message,
                'data': r.data,
                'executed_at': r.executed_at.isoformat(),
                'error': r.error
            }
            for r in self.execution_history[-1000:]
        ]
        
        with open(f"{self.storage_path}/action_history.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def register_handler(self, action_type: ActionType, handler: Callable):
        """Register a custom action handler."""
        self.action_handlers[action_type] = handler
    
    def execute(
        self,
        action: Action,
        context: Dict
    ) -> ActionResult:
        """Execute an action."""
        handler = self.action_handlers.get(action.action_type)
        
        if not handler:
            result = ActionResult(
                action_id=action.id,
                success=False,
                error=f"No handler for action type: {action.action_type.value}"
            )
            self.execution_history.append(result)
            self._save_history()
            return result
        
        retries = 0
        while True:
            try:
                result = handler(action.config, context)
                result.action_id = action.id
                self.execution_history.append(result)
                self._save_history()
                return result
                
            except Exception as e:
                if action.retry_on_failure and retries < action.max_retries:
                    retries += 1
                    continue
                
                result = ActionResult(
                    action_id=action.id,
                    success=False,
                    error=str(e)
                )
                self.execution_history.append(result)
                self._save_history()
                return result
    
    # Action handlers
    def _execute_send_email(self, config: Dict, context: Dict) -> ActionResult:
        """Send email action."""
        template_id = config.get('template_id')
        subject = config.get('subject', '')
        body = config.get('body', '')
        
        # Substitute variables
        lead_data = context.get('lead', {})
        subject = self._substitute_variables(subject, lead_data)
        body = self._substitute_variables(body, lead_data)
        
        if self.email_handler:
            self.email_handler(
                to=lead_data.get('email'),
                subject=subject,
                body=body,
                template_id=template_id
            )
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Email sent to {lead_data.get('email')}",
            data={'template_id': template_id, 'subject': subject}
        )
    
    def _execute_send_sms(self, config: Dict, context: Dict) -> ActionResult:
        """Send SMS action."""
        template_id = config.get('template_id')
        message = config.get('message', '')
        
        lead_data = context.get('lead', {})
        message = self._substitute_variables(message, lead_data)
        
        if self.sms_handler:
            self.sms_handler(
                to=lead_data.get('phone'),
                message=message
            )
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"SMS sent to {lead_data.get('phone')}",
            data={'message': message}
        )
    
    def _execute_send_push(self, config: Dict, context: Dict) -> ActionResult:
        """Send push notification action."""
        title = config.get('title', '')
        body = config.get('body', '')
        
        lead_data = context.get('lead', {})
        title = self._substitute_variables(title, lead_data)
        body = self._substitute_variables(body, lead_data)
        
        return ActionResult(
            action_id='',
            success=True,
            message="Push notification sent",
            data={'title': title, 'body': body}
        )
    
    def _execute_update_lead(self, config: Dict, context: Dict) -> ActionResult:
        """Update lead data action."""
        field = config.get('field')
        value = config.get('value')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Lead field '{field}' updated to '{value}'",
            data={'field': field, 'value': value}
        )
    
    def _execute_change_status(self, config: Dict, context: Dict) -> ActionResult:
        """Change lead status action."""
        new_status = config.get('status')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Lead status changed to '{new_status}'",
            data={'new_status': new_status}
        )
    
    def _execute_update_score(self, config: Dict, context: Dict) -> ActionResult:
        """Update lead score action."""
        adjustment = config.get('adjustment', 0)
        reason = config.get('reason', '')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Lead score adjusted by {adjustment}",
            data={'adjustment': adjustment, 'reason': reason}
        )
    
    def _execute_add_tag(self, config: Dict, context: Dict) -> ActionResult:
        """Add tag to lead action."""
        tag = config.get('tag')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Tag '{tag}' added to lead",
            data={'tag': tag}
        )
    
    def _execute_remove_tag(self, config: Dict, context: Dict) -> ActionResult:
        """Remove tag from lead action."""
        tag = config.get('tag')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Tag '{tag}' removed from lead",
            data={'tag': tag}
        )
    
    def _execute_assign_agent(self, config: Dict, context: Dict) -> ActionResult:
        """Assign agent to lead action."""
        agent_id = config.get('agent_id')
        assignment_method = config.get('method', 'direct')  # direct, round_robin, by_area
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Lead assigned to agent {agent_id}",
            data={'agent_id': agent_id, 'method': assignment_method}
        )
    
    def _execute_create_task(self, config: Dict, context: Dict) -> ActionResult:
        """Create task action."""
        task_type = config.get('task_type')
        due_days = config.get('due_days', 1)
        priority = config.get('priority', 'medium')
        description = config.get('description', '')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Task created: {task_type}",
            data={
                'task_type': task_type,
                'due_days': due_days,
                'priority': priority,
                'description': description
            }
        )
    
    def _execute_schedule_appointment(self, config: Dict, context: Dict) -> ActionResult:
        """Schedule appointment action."""
        appointment_type = config.get('type')
        duration_minutes = config.get('duration', 60)
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Appointment scheduled: {appointment_type}",
            data={'type': appointment_type, 'duration': duration_minutes}
        )
    
    def _execute_add_to_campaign(self, config: Dict, context: Dict) -> ActionResult:
        """Add to campaign action."""
        campaign_id = config.get('campaign_id')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Lead added to campaign {campaign_id}",
            data={'campaign_id': campaign_id}
        )
    
    def _execute_log_activity(self, config: Dict, context: Dict) -> ActionResult:
        """Log activity action."""
        activity_type = config.get('activity_type')
        details = config.get('details', '')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Activity logged: {activity_type}",
            data={'activity_type': activity_type, 'details': details}
        )
    
    def _execute_add_note(self, config: Dict, context: Dict) -> ActionResult:
        """Add note to lead action."""
        note = config.get('note', '')
        
        lead_data = context.get('lead', {})
        note = self._substitute_variables(note, lead_data)
        
        return ActionResult(
            action_id='',
            success=True,
            message="Note added to lead",
            data={'note': note}
        )
    
    def _execute_webhook(self, config: Dict, context: Dict) -> ActionResult:
        """Webhook action."""
        url = config.get('url')
        method = config.get('method', 'POST')
        headers = config.get('headers', {})
        payload = config.get('payload', {})
        
        # Add lead data to payload
        payload['lead'] = context.get('lead', {})
        payload['trigger'] = context.get('trigger', {})
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            return ActionResult(
                action_id='',
                success=response.status_code < 400,
                message=f"Webhook sent to {url}",
                data={'status_code': response.status_code}
            )
        except Exception as e:
            return ActionResult(
                action_id='',
                success=False,
                error=str(e)
            )
    
    def _execute_api_call(self, config: Dict, context: Dict) -> ActionResult:
        """External API call action."""
        url = config.get('url')
        method = config.get('method', 'GET')
        headers = config.get('headers', {})
        params = config.get('params', {})
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            return ActionResult(
                action_id='',
                success=response.status_code < 400,
                message=f"API call to {url}",
                data={'status_code': response.status_code, 'response': response.text[:500]}
            )
        except Exception as e:
            return ActionResult(
                action_id='',
                success=False,
                error=str(e)
            )
    
    def _execute_slack_message(self, config: Dict, context: Dict) -> ActionResult:
        """Slack message action."""
        webhook_url = config.get('webhook_url')
        message = config.get('message', '')
        channel = config.get('channel', '')
        
        lead_data = context.get('lead', {})
        message = self._substitute_variables(message, lead_data)
        
        payload = {
            'text': message
        }
        if channel:
            payload['channel'] = channel
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            return ActionResult(
                action_id='',
                success=response.status_code == 200,
                message="Slack message sent",
                data={'channel': channel}
            )
        except Exception as e:
            return ActionResult(
                action_id='',
                success=False,
                error=str(e)
            )
    
    def _execute_notify_agent(self, config: Dict, context: Dict) -> ActionResult:
        """Notify agent action."""
        method = config.get('method', 'email')  # email, sms, push, all
        message = config.get('message', '')
        
        lead_data = context.get('lead', {})
        message = self._substitute_variables(message, lead_data)
        
        if self.notification_handler:
            self.notification_handler(
                agent_id=context.get('agent_id'),
                method=method,
                message=message
            )
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Agent notified via {method}",
            data={'method': method, 'message': message}
        )
    
    def _execute_notify_team(self, config: Dict, context: Dict) -> ActionResult:
        """Notify team action."""
        team_id = config.get('team_id')
        message = config.get('message', '')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Team {team_id} notified",
            data={'team_id': team_id, 'message': message}
        )
    
    def _execute_send_listings(self, config: Dict, context: Dict) -> ActionResult:
        """Send property listings action."""
        count = config.get('count', 5)
        criteria = config.get('criteria', {})
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Sent {count} listings to lead",
            data={'count': count, 'criteria': criteria}
        )
    
    def _execute_schedule_showing(self, config: Dict, context: Dict) -> ActionResult:
        """Schedule showing action."""
        property_id = config.get('property_id')
        
        return ActionResult(
            action_id='',
            success=True,
            message=f"Showing scheduled for property {property_id}",
            data={'property_id': property_id}
        )
    
    def _substitute_variables(self, text: str, data: Dict) -> str:
        """Substitute variables in text."""
        if not text:
            return text
        
        variables = {
            '{{first_name}}': data.get('first_name', ''),
            '{{last_name}}': data.get('last_name', ''),
            '{{email}}': data.get('email', ''),
            '{{phone}}': data.get('phone', ''),
            '{{full_name}}': f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            '{{lead_source}}': data.get('source', ''),
            '{{property_type}}': data.get('property_type', ''),
            '{{price_range}}': data.get('price_range', ''),
            '{{city}}': data.get('city', ''),
            '{{agent_name}}': data.get('agent_name', ''),
        }
        
        for var, value in variables.items():
            text = text.replace(var, str(value))
        
        return text
    
    def get_execution_history(
        self,
        action_id: str = None,
        success_only: bool = False,
        limit: int = 100
    ) -> List[ActionResult]:
        """Get action execution history."""
        results = self.execution_history
        
        if action_id:
            results = [r for r in results if r.action_id == action_id]
        
        if success_only:
            results = [r for r in results if r.success]
        
        return results[-limit:]
