"""Workflow automation engine."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid
import threading
import time


class WorkflowStatus(Enum):
    """Workflow status."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class StepType(Enum):
    """Workflow step types."""
    ACTION = "action"
    CONDITION = "condition"
    DELAY = "delay"
    SPLIT = "split"  # A/B test
    MERGE = "merge"
    END = "end"


class ExecutionStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    id: str
    name: str
    step_type: StepType
    config: Dict = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)  # IDs of next steps
    conditions: Dict = field(default_factory=dict)  # For conditional branching
    position: Dict = field(default_factory=dict)  # x, y for visual editor


@dataclass
class Workflow:
    """A complete workflow definition."""
    id: str
    name: str
    description: str = ""
    trigger_type: str = ""  # lead_created, status_changed, etc.
    trigger_config: Dict = field(default_factory=dict)
    steps: Dict[str, WorkflowStep] = field(default_factory=dict)
    entry_step_id: str = ""
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    executions_count: int = 0
    success_count: int = 0


@dataclass
class WorkflowExecution:
    """A single execution of a workflow."""
    id: str
    workflow_id: str
    lead_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = None
    resume_at: datetime = None  # For delays
    context: Dict = field(default_factory=dict)  # Runtime data
    step_history: List[Dict] = field(default_factory=list)
    error: str = ""


class WorkflowEngine:
    """Engine for executing workflows."""
    
    def __init__(self, storage_path: str = "data/workflows"):
        self.storage_path = storage_path
        self.workflows: Dict[str, Workflow] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.action_handlers: Dict[str, Callable] = {}
        self.condition_evaluators: Dict[str, Callable] = {}
        
        self._engine_thread: Optional[threading.Thread] = None
        self._running = False
        
        self._load_data()
        self._register_default_handlers()
    
    def _load_data(self):
        """Load workflows and executions from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load workflows
        workflows_file = f"{self.storage_path}/workflows.json"
        if os.path.exists(workflows_file):
            with open(workflows_file, 'r') as f:
                data = json.load(f)
                for wf_data in data:
                    steps = {}
                    for step_data in wf_data.get('steps', []):
                        step = WorkflowStep(
                            id=step_data['id'],
                            name=step_data['name'],
                            step_type=StepType(step_data['step_type']),
                            config=step_data.get('config', {}),
                            next_steps=step_data.get('next_steps', []),
                            conditions=step_data.get('conditions', {}),
                            position=step_data.get('position', {})
                        )
                        steps[step.id] = step
                    
                    workflow = Workflow(
                        id=wf_data['id'],
                        name=wf_data['name'],
                        description=wf_data.get('description', ''),
                        trigger_type=wf_data.get('trigger_type', ''),
                        trigger_config=wf_data.get('trigger_config', {}),
                        steps=steps,
                        entry_step_id=wf_data.get('entry_step_id', ''),
                        status=WorkflowStatus(wf_data.get('status', 'draft')),
                        created_at=datetime.fromisoformat(wf_data['created_at']) if wf_data.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(wf_data['updated_at']) if wf_data.get('updated_at') else datetime.now(),
                        executions_count=wf_data.get('executions_count', 0),
                        success_count=wf_data.get('success_count', 0)
                    )
                    self.workflows[workflow.id] = workflow
        
        # Load active executions
        executions_file = f"{self.storage_path}/executions.json"
        if os.path.exists(executions_file):
            with open(executions_file, 'r') as f:
                data = json.load(f)
                for exec_data in data:
                    if exec_data.get('status') in ['pending', 'running', 'waiting']:
                        execution = WorkflowExecution(
                            id=exec_data['id'],
                            workflow_id=exec_data['workflow_id'],
                            lead_id=exec_data['lead_id'],
                            status=ExecutionStatus(exec_data.get('status', 'pending')),
                            current_step_id=exec_data.get('current_step_id', ''),
                            started_at=datetime.fromisoformat(exec_data['started_at']) if exec_data.get('started_at') else datetime.now(),
                            completed_at=datetime.fromisoformat(exec_data['completed_at']) if exec_data.get('completed_at') else None,
                            resume_at=datetime.fromisoformat(exec_data['resume_at']) if exec_data.get('resume_at') else None,
                            context=exec_data.get('context', {}),
                            step_history=exec_data.get('step_history', []),
                            error=exec_data.get('error', '')
                        )
                        self.executions[execution.id] = execution
    
    def _save_data(self):
        """Save workflows and executions to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save workflows
        workflows_data = []
        for wf in self.workflows.values():
            steps_data = [
                {
                    'id': s.id,
                    'name': s.name,
                    'step_type': s.step_type.value,
                    'config': s.config,
                    'next_steps': s.next_steps,
                    'conditions': s.conditions,
                    'position': s.position
                }
                for s in wf.steps.values()
            ]
            workflows_data.append({
                'id': wf.id,
                'name': wf.name,
                'description': wf.description,
                'trigger_type': wf.trigger_type,
                'trigger_config': wf.trigger_config,
                'steps': steps_data,
                'entry_step_id': wf.entry_step_id,
                'status': wf.status.value,
                'created_at': wf.created_at.isoformat(),
                'updated_at': wf.updated_at.isoformat(),
                'executions_count': wf.executions_count,
                'success_count': wf.success_count
            })
        
        with open(f"{self.storage_path}/workflows.json", 'w') as f:
            json.dump(workflows_data, f, indent=2)
        
        # Save executions
        executions_data = [
            {
                'id': e.id,
                'workflow_id': e.workflow_id,
                'lead_id': e.lead_id,
                'status': e.status.value,
                'current_step_id': e.current_step_id,
                'started_at': e.started_at.isoformat(),
                'completed_at': e.completed_at.isoformat() if e.completed_at else None,
                'resume_at': e.resume_at.isoformat() if e.resume_at else None,
                'context': e.context,
                'step_history': e.step_history,
                'error': e.error
            }
            for e in self.executions.values()
        ]
        
        with open(f"{self.storage_path}/executions.json", 'w') as f:
            json.dump(executions_data, f, indent=2)
    
    def _register_default_handlers(self):
        """Register default action handlers and condition evaluators."""
        # Default action handlers
        self.action_handlers = {
            'send_email': self._action_send_email,
            'send_sms': self._action_send_sms,
            'create_task': self._action_create_task,
            'update_lead': self._action_update_lead,
            'add_tag': self._action_add_tag,
            'remove_tag': self._action_remove_tag,
            'assign_agent': self._action_assign_agent,
            'add_to_campaign': self._action_add_to_campaign,
            'log_activity': self._action_log_activity,
            'webhook': self._action_webhook,
            'notify_agent': self._action_notify_agent
        }
        
        # Default condition evaluators
        self.condition_evaluators = {
            'lead_score_above': self._condition_lead_score,
            'lead_status_is': self._condition_lead_status,
            'has_tag': self._condition_has_tag,
            'property_type_is': self._condition_property_type,
            'price_range_is': self._condition_price_range,
            'source_is': self._condition_source,
            'days_since_created': self._condition_days_since,
            'email_opened': self._condition_email_opened,
            'responded': self._condition_responded
        }
    
    def register_action_handler(self, action_type: str, handler: Callable):
        """Register a custom action handler."""
        self.action_handlers[action_type] = handler
    
    def register_condition_evaluator(self, condition_type: str, evaluator: Callable):
        """Register a custom condition evaluator."""
        self.condition_evaluators[condition_type] = evaluator
    
    def create_workflow(
        self,
        name: str,
        description: str = "",
        trigger_type: str = "",
        trigger_config: Dict = None
    ) -> Workflow:
        """Create a new workflow."""
        workflow = Workflow(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {}
        )
        self.workflows[workflow.id] = workflow
        self._save_data()
        return workflow
    
    def add_step(
        self,
        workflow_id: str,
        name: str,
        step_type: StepType,
        config: Dict = None,
        next_steps: List[str] = None,
        conditions: Dict = None,
        position: Dict = None
    ) -> Optional[WorkflowStep]:
        """Add a step to a workflow."""
        if workflow_id not in self.workflows:
            return None
        
        step = WorkflowStep(
            id=str(uuid.uuid4())[:8],
            name=name,
            step_type=step_type,
            config=config or {},
            next_steps=next_steps or [],
            conditions=conditions or {},
            position=position or {}
        )
        
        self.workflows[workflow_id].steps[step.id] = step
        self.workflows[workflow_id].updated_at = datetime.now()
        
        # Set as entry step if first step
        if not self.workflows[workflow_id].entry_step_id:
            self.workflows[workflow_id].entry_step_id = step.id
        
        self._save_data()
        return step
    
    def update_step(
        self,
        workflow_id: str,
        step_id: str,
        updates: Dict
    ) -> Optional[WorkflowStep]:
        """Update a workflow step."""
        if workflow_id not in self.workflows:
            return None
        if step_id not in self.workflows[workflow_id].steps:
            return None
        
        step = self.workflows[workflow_id].steps[step_id]
        for key, value in updates.items():
            if hasattr(step, key):
                setattr(step, key, value)
        
        self.workflows[workflow_id].updated_at = datetime.now()
        self._save_data()
        return step
    
    def remove_step(self, workflow_id: str, step_id: str) -> bool:
        """Remove a step from a workflow."""
        if workflow_id not in self.workflows:
            return False
        if step_id not in self.workflows[workflow_id].steps:
            return False
        
        del self.workflows[workflow_id].steps[step_id]
        
        # Update references to this step
        for step in self.workflows[workflow_id].steps.values():
            if step_id in step.next_steps:
                step.next_steps.remove(step_id)
        
        self._save_data()
        return True
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].status = WorkflowStatus.ACTIVE
            self._save_data()
            return True
        return False
    
    def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a workflow."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].status = WorkflowStatus.PAUSED
            self._save_data()
            return True
        return False
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            self._save_data()
            return True
        return False
    
    def start_execution(
        self,
        workflow_id: str,
        lead_id: str,
        context: Dict = None
    ) -> Optional[WorkflowExecution]:
        """Start executing a workflow for a lead."""
        if workflow_id not in self.workflows:
            return None
        
        workflow = self.workflows[workflow_id]
        if workflow.status != WorkflowStatus.ACTIVE:
            return None
        
        execution = WorkflowExecution(
            id=str(uuid.uuid4())[:8],
            workflow_id=workflow_id,
            lead_id=lead_id,
            status=ExecutionStatus.RUNNING,
            current_step_id=workflow.entry_step_id,
            context=context or {}
        )
        
        self.executions[execution.id] = execution
        workflow.executions_count += 1
        self._save_data()
        
        # Start processing
        self._process_execution(execution)
        
        return execution
    
    def _process_execution(self, execution: WorkflowExecution):
        """Process a workflow execution."""
        workflow = self.workflows.get(execution.workflow_id)
        if not workflow:
            execution.status = ExecutionStatus.FAILED
            execution.error = "Workflow not found"
            self._save_data()
            return
        
        while execution.status == ExecutionStatus.RUNNING:
            step = workflow.steps.get(execution.current_step_id)
            if not step:
                # End of workflow
                execution.status = ExecutionStatus.COMPLETED
                execution.completed_at = datetime.now()
                workflow.success_count += 1
                break
            
            try:
                result = self._execute_step(step, execution)
                
                # Record step in history
                execution.step_history.append({
                    'step_id': step.id,
                    'step_name': step.name,
                    'executed_at': datetime.now().isoformat(),
                    'result': result
                })
                
                if result.get('wait'):
                    # Delay step - pause execution
                    execution.status = ExecutionStatus.WAITING
                    execution.resume_at = result['resume_at']
                    break
                
                if result.get('error'):
                    execution.status = ExecutionStatus.FAILED
                    execution.error = result['error']
                    break
                
                # Determine next step
                next_step_id = self._get_next_step(step, execution, result)
                if next_step_id:
                    execution.current_step_id = next_step_id
                else:
                    # End of workflow
                    execution.status = ExecutionStatus.COMPLETED
                    execution.completed_at = datetime.now()
                    workflow.success_count += 1
                
            except Exception as e:
                execution.status = ExecutionStatus.FAILED
                execution.error = str(e)
                break
        
        self._save_data()
    
    def _execute_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict:
        """Execute a single workflow step."""
        if step.step_type == StepType.ACTION:
            return self._execute_action(step, execution)
        elif step.step_type == StepType.CONDITION:
            return self._evaluate_condition(step, execution)
        elif step.step_type == StepType.DELAY:
            return self._execute_delay(step, execution)
        elif step.step_type == StepType.SPLIT:
            return self._execute_split(step, execution)
        elif step.step_type == StepType.END:
            return {'end': True}
        
        return {}
    
    def _execute_action(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict:
        """Execute an action step."""
        action_type = step.config.get('action_type')
        handler = self.action_handlers.get(action_type)
        
        if not handler:
            return {'error': f"Unknown action type: {action_type}"}
        
        try:
            result = handler(step.config, execution)
            return result or {}
        except Exception as e:
            return {'error': str(e)}
    
    def _evaluate_condition(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict:
        """Evaluate a condition step."""
        condition_type = step.config.get('condition_type')
        evaluator = self.condition_evaluators.get(condition_type)
        
        if not evaluator:
            return {'error': f"Unknown condition type: {condition_type}"}
        
        try:
            result = evaluator(step.config, execution)
            return {'condition_result': result}
        except Exception as e:
            return {'error': str(e)}
    
    def _execute_delay(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict:
        """Execute a delay step."""
        delay_minutes = step.config.get('delay_minutes', 0)
        delay_hours = step.config.get('delay_hours', 0)
        delay_days = step.config.get('delay_days', 0)
        
        total_minutes = delay_minutes + (delay_hours * 60) + (delay_days * 24 * 60)
        resume_at = datetime.now() + timedelta(minutes=total_minutes)
        
        return {
            'wait': True,
            'resume_at': resume_at
        }
    
    def _execute_split(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict:
        """Execute an A/B split step."""
        # Simple 50/50 split based on lead_id hash
        split_value = hash(execution.lead_id) % 100
        split_threshold = step.config.get('split_percent', 50)
        
        branch = 'a' if split_value < split_threshold else 'b'
        return {'split_branch': branch}
    
    def _get_next_step(self, step: WorkflowStep, execution: WorkflowExecution, result: Dict) -> Optional[str]:
        """Determine the next step based on current step result."""
        if step.step_type == StepType.CONDITION:
            # Use condition result to choose branch
            if result.get('condition_result'):
                return step.conditions.get('true_step')
            else:
                return step.conditions.get('false_step')
        
        elif step.step_type == StepType.SPLIT:
            branch = result.get('split_branch', 'a')
            return step.conditions.get(f'{branch}_step')
        
        # Default: return first next step
        if step.next_steps:
            return step.next_steps[0]
        
        return None
    
    def resume_waiting_executions(self):
        """Resume executions that are done waiting."""
        now = datetime.now()
        
        for execution in self.executions.values():
            if execution.status == ExecutionStatus.WAITING:
                if execution.resume_at and execution.resume_at <= now:
                    execution.status = ExecutionStatus.RUNNING
                    self._process_execution(execution)
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution."""
        if execution_id in self.executions:
            self.executions[execution_id].status = ExecutionStatus.CANCELLED
            self.executions[execution_id].completed_at = datetime.now()
            self._save_data()
            return True
        return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self.workflows.get(workflow_id)
    
    def list_workflows(self, status: WorkflowStatus = None) -> List[Workflow]:
        """List all workflows."""
        workflows = list(self.workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows
    
    def get_executions(
        self,
        workflow_id: str = None,
        lead_id: str = None,
        status: ExecutionStatus = None
    ) -> List[WorkflowExecution]:
        """Get workflow executions."""
        executions = list(self.executions.values())
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        if lead_id:
            executions = [e for e in executions if e.lead_id == lead_id]
        if status:
            executions = [e for e in executions if e.status == status]
        
        return executions
    
    def start_engine(self, check_interval_seconds: int = 60):
        """Start the workflow engine."""
        if self._running:
            return
        
        self._running = True
        self._engine_thread = threading.Thread(
            target=self._engine_loop,
            args=(check_interval_seconds,),
            daemon=True
        )
        self._engine_thread.start()
    
    def stop_engine(self):
        """Stop the workflow engine."""
        self._running = False
        if self._engine_thread:
            self._engine_thread.join(timeout=5)
    
    def _engine_loop(self, interval: int):
        """Engine loop for processing waiting executions."""
        while self._running:
            try:
                self.resume_waiting_executions()
            except Exception:
                pass
            
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)
    
    # Default action handlers
    def _action_send_email(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Send email action."""
        # Would integrate with email module
        return {'sent': True, 'template': config.get('template')}
    
    def _action_send_sms(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Send SMS action."""
        return {'sent': True, 'template': config.get('template')}
    
    def _action_create_task(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Create task action."""
        return {'task_created': True, 'task_type': config.get('task_type')}
    
    def _action_update_lead(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Update lead action."""
        return {'updated': True, 'field': config.get('field')}
    
    def _action_add_tag(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Add tag to lead action."""
        return {'tag_added': config.get('tag')}
    
    def _action_remove_tag(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Remove tag from lead action."""
        return {'tag_removed': config.get('tag')}
    
    def _action_assign_agent(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Assign agent action."""
        return {'assigned': True, 'agent_id': config.get('agent_id')}
    
    def _action_add_to_campaign(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Add to campaign action."""
        return {'added': True, 'campaign_id': config.get('campaign_id')}
    
    def _action_log_activity(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Log activity action."""
        return {'logged': True, 'activity_type': config.get('activity_type')}
    
    def _action_webhook(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Webhook action."""
        # Would make HTTP request
        return {'sent': True, 'url': config.get('url')}
    
    def _action_notify_agent(self, config: Dict, execution: WorkflowExecution) -> Dict:
        """Notify agent action."""
        return {'notified': True, 'method': config.get('method', 'email')}
    
    # Default condition evaluators
    def _condition_lead_score(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate lead score condition."""
        threshold = config.get('threshold', 50)
        lead_score = execution.context.get('lead_score', 0)
        return lead_score >= threshold
    
    def _condition_lead_status(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate lead status condition."""
        expected_status = config.get('status')
        lead_status = execution.context.get('lead_status')
        return lead_status == expected_status
    
    def _condition_has_tag(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate has tag condition."""
        tag = config.get('tag')
        lead_tags = execution.context.get('tags', [])
        return tag in lead_tags
    
    def _condition_property_type(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate property type condition."""
        expected_type = config.get('property_type')
        lead_type = execution.context.get('property_type')
        return lead_type == expected_type
    
    def _condition_price_range(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate price range condition."""
        min_price = config.get('min_price', 0)
        max_price = config.get('max_price', float('inf'))
        lead_budget = execution.context.get('budget', 0)
        return min_price <= lead_budget <= max_price
    
    def _condition_source(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate lead source condition."""
        expected_source = config.get('source')
        lead_source = execution.context.get('source')
        return lead_source == expected_source
    
    def _condition_days_since(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate days since created condition."""
        days_threshold = config.get('days', 0)
        created_at = execution.context.get('created_at')
        if created_at:
            created_date = datetime.fromisoformat(created_at)
            days_since = (datetime.now() - created_date).days
            return days_since >= days_threshold
        return False
    
    def _condition_email_opened(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate email opened condition."""
        return execution.context.get('email_opened', False)
    
    def _condition_responded(self, config: Dict, execution: WorkflowExecution) -> bool:
        """Evaluate lead responded condition."""
        return execution.context.get('has_responded', False)
