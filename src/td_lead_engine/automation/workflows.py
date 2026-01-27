"""Workflow engine for automated lead nurturing and follow-ups."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowTrigger(Enum):
    """Events that can trigger a workflow."""

    LEAD_CREATED = "lead_created"
    LEAD_SCORED = "lead_scored"
    LEAD_BECOMES_HOT = "lead_becomes_hot"
    LEAD_BECOMES_WARM = "lead_becomes_warm"
    STATUS_CHANGED = "status_changed"
    NO_RESPONSE_DAYS = "no_response_days"  # X days without response
    MANUAL = "manual"


class WorkflowAction(Enum):
    """Actions that can be performed in a workflow."""

    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SLACK_NOTIFY = "slack_notify"
    ADD_TAG = "add_tag"
    REMOVE_TAG = "remove_tag"
    CHANGE_STATUS = "change_status"
    ADD_NOTE = "add_note"
    ASSIGN_TO = "assign_to"
    WEBHOOK = "webhook"
    WAIT = "wait"  # Wait X hours/days before next action


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    action: WorkflowAction
    config: Dict[str, Any] = field(default_factory=dict)
    delay_hours: int = 0  # Hours to wait before this step


@dataclass
class LeadWorkflow:
    """A workflow definition for automated lead handling."""

    id: str
    name: str
    description: str
    trigger: WorkflowTrigger
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    steps: List[WorkflowStep] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)

    # Conditions for when to run (optional filters)
    tier_filter: Optional[List[str]] = None  # Only run for these tiers
    source_filter: Optional[List[str]] = None  # Only run for these sources
    tag_filter: Optional[List[str]] = None  # Only run if lead has these tags


@dataclass
class WorkflowExecution:
    """Record of a workflow execution."""

    workflow_id: str
    lead_id: int
    current_step: int = 0
    status: str = "running"  # running, completed, failed, paused
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    next_step_at: Optional[datetime] = None
    step_results: List[Dict[str, Any]] = field(default_factory=list)


class WorkflowEngine:
    """Executes workflows for lead automation."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the workflow engine."""
        self.config_path = config_path or Path.home() / ".td-lead-engine" / "workflows.json"
        self.workflows: Dict[str, LeadWorkflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.action_handlers: Dict[WorkflowAction, Callable] = {}
        self._load_config()
        self._register_default_handlers()

    def _load_config(self):
        """Load workflow configurations."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for wf_data in data.get("workflows", []):
                        steps = [
                            WorkflowStep(
                                action=WorkflowAction(s["action"]),
                                config=s.get("config", {}),
                                delay_hours=s.get("delay_hours", 0)
                            )
                            for s in wf_data.get("steps", [])
                        ]
                        workflow = LeadWorkflow(
                            id=wf_data["id"],
                            name=wf_data["name"],
                            description=wf_data.get("description", ""),
                            trigger=WorkflowTrigger(wf_data["trigger"]),
                            trigger_config=wf_data.get("trigger_config", {}),
                            steps=steps,
                            enabled=wf_data.get("enabled", True),
                            tier_filter=wf_data.get("tier_filter"),
                            source_filter=wf_data.get("source_filter"),
                            tag_filter=wf_data.get("tag_filter"),
                        )
                        self.workflows[workflow.id] = workflow
            except Exception as e:
                logger.error(f"Error loading workflows: {e}")

    def _save_config(self):
        """Save workflow configurations."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "workflows": [
                {
                    "id": wf.id,
                    "name": wf.name,
                    "description": wf.description,
                    "trigger": wf.trigger.value,
                    "trigger_config": wf.trigger_config,
                    "steps": [
                        {
                            "action": s.action.value,
                            "config": s.config,
                            "delay_hours": s.delay_hours,
                        }
                        for s in wf.steps
                    ],
                    "enabled": wf.enabled,
                    "tier_filter": wf.tier_filter,
                    "source_filter": wf.source_filter,
                    "tag_filter": wf.tag_filter,
                }
                for wf in self.workflows.values()
            ]
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _register_default_handlers(self):
        """Register default action handlers."""
        self.action_handlers = {
            WorkflowAction.ADD_TAG: self._handle_add_tag,
            WorkflowAction.REMOVE_TAG: self._handle_remove_tag,
            WorkflowAction.CHANGE_STATUS: self._handle_change_status,
            WorkflowAction.ADD_NOTE: self._handle_add_note,
            WorkflowAction.SLACK_NOTIFY: self._handle_slack_notify,
            WorkflowAction.WEBHOOK: self._handle_webhook,
            WorkflowAction.SEND_EMAIL: self._handle_send_email,
            WorkflowAction.SEND_SMS: self._handle_send_sms,
            WorkflowAction.WAIT: self._handle_wait,
        }

    def register_action_handler(self, action: WorkflowAction, handler: Callable):
        """Register a custom action handler."""
        self.action_handlers[action] = handler

    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        trigger: WorkflowTrigger,
        steps: List[WorkflowStep],
        description: str = "",
        tier_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
    ) -> LeadWorkflow:
        """Create a new workflow."""
        workflow = LeadWorkflow(
            id=workflow_id,
            name=name,
            description=description,
            trigger=trigger,
            steps=steps,
            tier_filter=tier_filter,
            source_filter=source_filter,
        )
        self.workflows[workflow_id] = workflow
        self._save_config()
        logger.info(f"Created workflow: {workflow_id}")
        return workflow

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            self._save_config()
            return True
        return False

    def list_workflows(self) -> List[LeadWorkflow]:
        """List all workflows."""
        return list(self.workflows.values())

    def trigger_workflows(self, trigger: WorkflowTrigger, lead_data: Dict[str, Any]):
        """Trigger all workflows for an event."""
        for workflow in self.workflows.values():
            if not workflow.enabled:
                continue
            if workflow.trigger != trigger:
                continue

            # Check filters
            if workflow.tier_filter and lead_data.get("tier") not in workflow.tier_filter:
                continue
            if workflow.source_filter and lead_data.get("source") not in workflow.source_filter:
                continue

            # Start workflow execution
            self.start_workflow(workflow.id, lead_data["id"])

    def start_workflow(self, workflow_id: str, lead_id: int) -> Optional[WorkflowExecution]:
        """Start a workflow for a specific lead."""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            lead_id=lead_id,
        )

        exec_key = f"{workflow_id}_{lead_id}"
        self.executions[exec_key] = execution

        # Execute first step
        self._execute_next_step(execution, workflow)

        return execution

    def _execute_next_step(self, execution: WorkflowExecution, workflow: LeadWorkflow):
        """Execute the next step in a workflow."""
        if execution.current_step >= len(workflow.steps):
            execution.status = "completed"
            execution.completed_at = datetime.now()
            logger.info(f"Workflow {workflow.id} completed for lead {execution.lead_id}")
            return

        step = workflow.steps[execution.current_step]

        # Handle delay
        if step.delay_hours > 0:
            execution.next_step_at = datetime.now() + timedelta(hours=step.delay_hours)
            execution.status = "waiting"
            logger.info(
                f"Workflow {workflow.id} step {execution.current_step} "
                f"waiting {step.delay_hours} hours"
            )
            return

        # Execute action
        handler = self.action_handlers.get(step.action)
        if handler:
            try:
                result = handler(execution.lead_id, step.config)
                execution.step_results.append({
                    "step": execution.current_step,
                    "action": step.action.value,
                    "success": True,
                    "result": result,
                    "executed_at": datetime.now().isoformat(),
                })
            except Exception as e:
                execution.step_results.append({
                    "step": execution.current_step,
                    "action": step.action.value,
                    "success": False,
                    "error": str(e),
                    "executed_at": datetime.now().isoformat(),
                })
                logger.error(f"Workflow step failed: {e}")

        execution.current_step += 1
        self._execute_next_step(execution, workflow)

    # === Action Handlers ===

    def _handle_add_tag(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add a tag to a lead."""
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        lead = db.get_lead(lead_id)
        if lead:
            tags = lead.get_tags_list()
            new_tag = config.get("tag", "")
            if new_tag and new_tag not in tags:
                tags.append(new_tag)
                lead.set_tags_list(tags)
                db.update_lead(lead)
        return {"tag_added": config.get("tag")}

    def _handle_remove_tag(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a tag from a lead."""
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        lead = db.get_lead(lead_id)
        if lead:
            tags = lead.get_tags_list()
            tag_to_remove = config.get("tag", "")
            if tag_to_remove in tags:
                tags.remove(tag_to_remove)
                lead.set_tags_list(tags)
                db.update_lead(lead)
        return {"tag_removed": config.get("tag")}

    def _handle_change_status(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Change lead status."""
        from ..storage.database import LeadDatabase
        from ..storage.models import LeadStatus

        db = LeadDatabase()
        lead = db.get_lead(lead_id)
        if lead:
            new_status = config.get("status", "")
            try:
                lead.status = LeadStatus(new_status)
                db.update_lead(lead)
            except ValueError:
                pass
        return {"new_status": config.get("status")}

    def _handle_add_note(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Add a note to a lead."""
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        lead = db.get_lead(lead_id)
        if lead:
            note_text = config.get("note", "")
            current_notes = lead.notes or ""
            lead.notes = f"{current_notes}\n[Auto] {note_text}".strip()
            db.update_lead(lead)
        return {"note_added": config.get("note")}

    def _handle_slack_notify(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Send Slack notification."""
        from ..storage.database import LeadDatabase
        from .webhooks import WebhookManager, WebhookEvent

        db = LeadDatabase()
        lead = db.get_lead(lead_id)

        if lead:
            webhook_manager = WebhookManager()
            webhook_manager.trigger(
                WebhookEvent.LEAD_HOT,
                {
                    "lead_id": lead.id,
                    "name": lead.display_name,
                    "score": lead.score,
                    "tier": lead.tier,
                    "message": config.get("message", "New hot lead!"),
                }
            )
        return {"notification_sent": True}

    def _handle_webhook(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Send to custom webhook."""
        import urllib.request
        import json

        url = config.get("url")
        if not url:
            return {"error": "No webhook URL configured"}

        from ..storage.database import LeadDatabase
        db = LeadDatabase()
        lead = db.get_lead(lead_id)

        if lead:
            payload = json.dumps({
                "lead_id": lead.id,
                "name": lead.display_name,
                "email": lead.email,
                "phone": lead.phone,
                "score": lead.score,
                "tier": lead.tier,
            }).encode()

            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return {"status": resp.status}
            except Exception as e:
                return {"error": str(e)}

        return {"error": "Lead not found"}

    def _handle_send_email(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Send email (placeholder - requires integration setup)."""
        # This would integrate with SendGrid, Mailgun, etc.
        template = config.get("template", "default")
        return {
            "message": f"Email would be sent using template: {template}",
            "requires_setup": "Configure email integration in settings"
        }

    def _handle_send_sms(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Send SMS (placeholder - requires Twilio setup)."""
        # This would integrate with Twilio
        template = config.get("template", "default")
        return {
            "message": f"SMS would be sent using template: {template}",
            "requires_setup": "Configure Twilio in settings"
        }

    def _handle_wait(self, lead_id: int, config: Dict[str, Any]) -> Dict[str, Any]:
        """Wait action - handled in _execute_next_step."""
        return {"waiting": True}


# === Pre-built Workflow Templates ===

def create_hot_lead_workflow(engine: WorkflowEngine) -> LeadWorkflow:
    """Create a workflow for hot leads."""
    return engine.create_workflow(
        workflow_id="hot_lead_followup",
        name="Hot Lead Immediate Follow-up",
        trigger=WorkflowTrigger.LEAD_BECOMES_HOT,
        description="Immediately notify team and tag hot leads for follow-up",
        steps=[
            WorkflowStep(
                action=WorkflowAction.ADD_TAG,
                config={"tag": "priority"},
            ),
            WorkflowStep(
                action=WorkflowAction.SLACK_NOTIFY,
                config={"message": "New HOT lead requires immediate attention!"},
            ),
            WorkflowStep(
                action=WorkflowAction.ADD_NOTE,
                config={"note": "Auto-flagged as priority - needs immediate follow-up"},
            ),
        ],
        tier_filter=["hot"],
    )


def create_nurture_workflow(engine: WorkflowEngine) -> LeadWorkflow:
    """Create a lead nurturing workflow."""
    return engine.create_workflow(
        workflow_id="warm_lead_nurture",
        name="Warm Lead Nurturing Sequence",
        trigger=WorkflowTrigger.LEAD_BECOMES_WARM,
        description="Automated nurturing for warm leads",
        steps=[
            WorkflowStep(
                action=WorkflowAction.ADD_TAG,
                config={"tag": "nurturing"},
            ),
            WorkflowStep(
                action=WorkflowAction.SEND_EMAIL,
                config={"template": "intro_email"},
                delay_hours=0,
            ),
            WorkflowStep(
                action=WorkflowAction.WAIT,
                delay_hours=72,  # 3 days
            ),
            WorkflowStep(
                action=WorkflowAction.SEND_EMAIL,
                config={"template": "market_update"},
            ),
            WorkflowStep(
                action=WorkflowAction.WAIT,
                delay_hours=168,  # 7 days
            ),
            WorkflowStep(
                action=WorkflowAction.ADD_NOTE,
                config={"note": "Nurturing sequence completed - ready for personal outreach"},
            ),
            WorkflowStep(
                action=WorkflowAction.CHANGE_STATUS,
                config={"status": "qualified"},
            ),
        ],
        tier_filter=["warm"],
    )
