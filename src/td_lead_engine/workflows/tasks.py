"""Task management module."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class TaskPriority(Enum):
    """Task priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(Enum):
    """Common task types."""
    CALL = "call"
    EMAIL = "email"
    TEXT = "text"
    FOLLOW_UP = "follow_up"
    SHOWING = "showing"
    MEETING = "meeting"
    DOCUMENT = "document"
    RESEARCH = "research"
    REVIEW = "review"
    OTHER = "other"


@dataclass
class Task:
    """A task to be completed."""
    id: str
    title: str
    description: str = ""
    task_type: TaskType = TaskType.OTHER
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Associations
    lead_id: str = ""
    property_id: str = ""
    transaction_id: str = ""
    
    # Assignment
    assigned_to: str = ""  # Agent ID
    created_by: str = ""
    
    # Timing
    due_date: datetime = None
    reminder_date: datetime = None
    completed_at: datetime = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    notes: List[Dict] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)
    
    # Workflow
    workflow_id: str = ""
    automation_generated: bool = False
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskTemplate:
    """A reusable task template."""
    id: str
    name: str
    description: str = ""
    task_type: TaskType = TaskType.OTHER
    default_priority: TaskPriority = TaskPriority.MEDIUM
    due_days: int = 1  # Days from creation to due
    reminder_hours: int = 24  # Hours before due to remind
    tags: List[str] = field(default_factory=list)
    checklist: List[str] = field(default_factory=list)


class TaskManager:
    """Manage tasks and assignments."""
    
    def __init__(self, storage_path: str = "data/tasks"):
        self.storage_path = storage_path
        self.tasks: Dict[str, Task] = {}
        self.templates: Dict[str, TaskTemplate] = {}
        
        self._load_data()
        self._create_default_templates()
    
    def _load_data(self):
        """Load tasks and templates from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load tasks
        tasks_file = f"{self.storage_path}/tasks.json"
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r') as f:
                data = json.load(f)
                for task_data in data:
                    task = Task(
                        id=task_data['id'],
                        title=task_data['title'],
                        description=task_data.get('description', ''),
                        task_type=TaskType(task_data.get('task_type', 'other')),
                        status=TaskStatus(task_data.get('status', 'pending')),
                        priority=TaskPriority(task_data.get('priority', 'medium')),
                        lead_id=task_data.get('lead_id', ''),
                        property_id=task_data.get('property_id', ''),
                        transaction_id=task_data.get('transaction_id', ''),
                        assigned_to=task_data.get('assigned_to', ''),
                        created_by=task_data.get('created_by', ''),
                        due_date=datetime.fromisoformat(task_data['due_date']) if task_data.get('due_date') else None,
                        reminder_date=datetime.fromisoformat(task_data['reminder_date']) if task_data.get('reminder_date') else None,
                        completed_at=datetime.fromisoformat(task_data['completed_at']) if task_data.get('completed_at') else None,
                        tags=task_data.get('tags', []),
                        notes=task_data.get('notes', []),
                        attachments=task_data.get('attachments', []),
                        workflow_id=task_data.get('workflow_id', ''),
                        automation_generated=task_data.get('automation_generated', False),
                        created_at=datetime.fromisoformat(task_data['created_at']) if task_data.get('created_at') else datetime.now(),
                        updated_at=datetime.fromisoformat(task_data['updated_at']) if task_data.get('updated_at') else datetime.now()
                    )
                    self.tasks[task.id] = task
        
        # Load templates
        templates_file = f"{self.storage_path}/templates.json"
        if os.path.exists(templates_file):
            with open(templates_file, 'r') as f:
                data = json.load(f)
                for template_data in data:
                    template = TaskTemplate(
                        id=template_data['id'],
                        name=template_data['name'],
                        description=template_data.get('description', ''),
                        task_type=TaskType(template_data.get('task_type', 'other')),
                        default_priority=TaskPriority(template_data.get('default_priority', 'medium')),
                        due_days=template_data.get('due_days', 1),
                        reminder_hours=template_data.get('reminder_hours', 24),
                        tags=template_data.get('tags', []),
                        checklist=template_data.get('checklist', [])
                    )
                    self.templates[template.id] = template
    
    def _save_data(self):
        """Save tasks and templates to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save tasks
        tasks_data = [
            {
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'task_type': t.task_type.value,
                'status': t.status.value,
                'priority': t.priority.value,
                'lead_id': t.lead_id,
                'property_id': t.property_id,
                'transaction_id': t.transaction_id,
                'assigned_to': t.assigned_to,
                'created_by': t.created_by,
                'due_date': t.due_date.isoformat() if t.due_date else None,
                'reminder_date': t.reminder_date.isoformat() if t.reminder_date else None,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'tags': t.tags,
                'notes': t.notes,
                'attachments': t.attachments,
                'workflow_id': t.workflow_id,
                'automation_generated': t.automation_generated,
                'created_at': t.created_at.isoformat(),
                'updated_at': t.updated_at.isoformat()
            }
            for t in self.tasks.values()
        ]
        
        with open(f"{self.storage_path}/tasks.json", 'w') as f:
            json.dump(tasks_data, f, indent=2)
        
        # Save templates
        templates_data = [
            {
                'id': t.id,
                'name': t.name,
                'description': t.description,
                'task_type': t.task_type.value,
                'default_priority': t.default_priority.value,
                'due_days': t.due_days,
                'reminder_hours': t.reminder_hours,
                'tags': t.tags,
                'checklist': t.checklist
            }
            for t in self.templates.values()
        ]
        
        with open(f"{self.storage_path}/templates.json", 'w') as f:
            json.dump(templates_data, f, indent=2)
    
    def _create_default_templates(self):
        """Create default task templates."""
        if self.templates:
            return
        
        default_templates = [
            TaskTemplate(
                id='new_lead_call',
                name='New Lead Follow-up Call',
                description='Initial call to new lead to qualify and understand needs',
                task_type=TaskType.CALL,
                default_priority=TaskPriority.HIGH,
                due_days=0,  # Same day
                reminder_hours=2,
                tags=['new_lead', 'follow_up'],
                checklist=[
                    'Introduce yourself and company',
                    'Confirm lead information',
                    'Ask about timeline',
                    'Understand budget',
                    'Schedule next steps'
                ]
            ),
            TaskTemplate(
                id='buyer_consultation',
                name='Buyer Consultation Meeting',
                description='Initial consultation with buyer to discuss needs and process',
                task_type=TaskType.MEETING,
                default_priority=TaskPriority.HIGH,
                due_days=3,
                reminder_hours=24,
                tags=['buyer', 'consultation'],
                checklist=[
                    'Review pre-approval status',
                    'Discuss needs and wants',
                    'Explain buying process',
                    'Sign buyer agreement',
                    'Set up MLS portal'
                ]
            ),
            TaskTemplate(
                id='listing_presentation',
                name='Listing Presentation',
                description='Present CMA and marketing plan to potential seller',
                task_type=TaskType.MEETING,
                default_priority=TaskPriority.HIGH,
                due_days=2,
                reminder_hours=24,
                tags=['seller', 'listing'],
                checklist=[
                    'Prepare CMA',
                    'Create marketing proposal',
                    'Tour the property',
                    'Present pricing strategy',
                    'Sign listing agreement'
                ]
            ),
            TaskTemplate(
                id='showing_follow_up',
                name='Post-Showing Follow-up',
                description='Follow up with buyer after property showing',
                task_type=TaskType.FOLLOW_UP,
                default_priority=TaskPriority.MEDIUM,
                due_days=1,
                reminder_hours=4,
                tags=['showing', 'follow_up'],
                checklist=[
                    'Ask for feedback',
                    'Rate interest level',
                    'Address concerns',
                    'Discuss next steps'
                ]
            ),
            TaskTemplate(
                id='contract_review',
                name='Review Contract',
                description='Review and prepare contract documents',
                task_type=TaskType.DOCUMENT,
                default_priority=TaskPriority.HIGH,
                due_days=1,
                reminder_hours=12,
                tags=['contract', 'document']
            ),
            TaskTemplate(
                id='market_update',
                name='Send Market Update',
                description='Send monthly market update to client',
                task_type=TaskType.EMAIL,
                default_priority=TaskPriority.LOW,
                due_days=7,
                reminder_hours=48,
                tags=['nurture', 'market_update']
            )
        ]
        
        for template in default_templates:
            self.templates[template.id] = template
        
        self._save_data()
    
    def create_task(
        self,
        title: str,
        description: str = "",
        task_type: TaskType = TaskType.OTHER,
        priority: TaskPriority = TaskPriority.MEDIUM,
        lead_id: str = "",
        property_id: str = "",
        assigned_to: str = "",
        created_by: str = "",
        due_date: datetime = None,
        tags: List[str] = None,
        workflow_id: str = "",
        automation_generated: bool = False
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            lead_id=lead_id,
            property_id=property_id,
            assigned_to=assigned_to,
            created_by=created_by,
            due_date=due_date or datetime.now() + timedelta(days=1),
            tags=tags or [],
            workflow_id=workflow_id,
            automation_generated=automation_generated
        )
        
        # Set reminder 24 hours before due
        if task.due_date:
            task.reminder_date = task.due_date - timedelta(hours=24)
        
        self.tasks[task.id] = task
        self._save_data()
        return task
    
    def create_from_template(
        self,
        template_id: str,
        lead_id: str = "",
        property_id: str = "",
        assigned_to: str = "",
        created_by: str = "",
        custom_title: str = None
    ) -> Optional[Task]:
        """Create a task from a template."""
        template = self.templates.get(template_id)
        if not template:
            return None
        
        due_date = datetime.now() + timedelta(days=template.due_days)
        reminder_date = due_date - timedelta(hours=template.reminder_hours)
        
        task = Task(
            id=str(uuid.uuid4())[:8],
            title=custom_title or template.name,
            description=template.description,
            task_type=template.task_type,
            priority=template.default_priority,
            lead_id=lead_id,
            property_id=property_id,
            assigned_to=assigned_to,
            created_by=created_by,
            due_date=due_date,
            reminder_date=reminder_date,
            tags=template.tags.copy()
        )
        
        # Add checklist as notes
        if template.checklist:
            task.notes.append({
                'type': 'checklist',
                'items': [{'text': item, 'completed': False} for item in template.checklist],
                'created_at': datetime.now().isoformat()
            })
        
        self.tasks[task.id] = task
        self._save_data()
        return task
    
    def update_task(self, task_id: str, updates: Dict) -> Optional[Task]:
        """Update a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                if key == 'task_type' and isinstance(value, str):
                    value = TaskType(value)
                elif key == 'status' and isinstance(value, str):
                    value = TaskStatus(value)
                elif key == 'priority' and isinstance(value, str):
                    value = TaskPriority(value)
                elif key in ['due_date', 'reminder_date'] and isinstance(value, str):
                    value = datetime.fromisoformat(value)
                setattr(task, key, value)
        
        task.updated_at = datetime.now()
        self._save_data()
        return task
    
    def complete_task(self, task_id: str) -> Optional[Task]:
        """Mark a task as completed."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        self._save_data()
        return task
    
    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Cancel a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now()
        self._save_data()
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_data()
            return True
        return False
    
    def add_note(self, task_id: str, note: str, author: str = "") -> Optional[Task]:
        """Add a note to a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        task.notes.append({
            'type': 'note',
            'text': note,
            'author': author,
            'created_at': datetime.now().isoformat()
        })
        task.updated_at = datetime.now()
        self._save_data()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks(
        self,
        assigned_to: str = None,
        lead_id: str = None,
        status: TaskStatus = None,
        priority: TaskPriority = None,
        task_type: TaskType = None,
        overdue_only: bool = False,
        due_today: bool = False,
        limit: int = 100
    ) -> List[Task]:
        """Get tasks with filters."""
        tasks = list(self.tasks.values())
        
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        if lead_id:
            tasks = [t for t in tasks if t.lead_id == lead_id]
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        else:
            # Default: exclude completed and cancelled
            tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]]
        
        if priority:
            tasks = [t for t in tasks if t.priority == priority]
        
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        
        now = datetime.now()
        if overdue_only:
            tasks = [t for t in tasks if t.due_date and t.due_date < now]
        
        if due_today:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            tasks = [t for t in tasks if t.due_date and today_start <= t.due_date < today_end]
        
        # Sort by due date and priority
        priority_order = {TaskPriority.URGENT: 0, TaskPriority.HIGH: 1, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
        tasks.sort(key=lambda t: (
            t.due_date or datetime.max,
            priority_order.get(t.priority, 2)
        ))
        
        return tasks[:limit]
    
    def get_overdue_tasks(self, assigned_to: str = None) -> List[Task]:
        """Get overdue tasks."""
        return self.get_tasks(assigned_to=assigned_to, overdue_only=True)
    
    def get_due_reminders(self) -> List[Task]:
        """Get tasks with reminders due now."""
        now = datetime.now()
        tasks = []
        
        for task in self.tasks.values():
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                continue
            
            if task.reminder_date and task.reminder_date <= now:
                # Check if not already reminded (would need a reminded_at field)
                tasks.append(task)
        
        return tasks
    
    def get_task_stats(self, assigned_to: str = None) -> Dict:
        """Get task statistics."""
        tasks = list(self.tasks.values())
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_start = today_start - timedelta(days=today_start.weekday())
        
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        overdue = [t for t in pending + in_progress if t.due_date and t.due_date < now]
        due_today = [t for t in pending + in_progress if t.due_date and today_start <= t.due_date < today_end]
        completed_this_week = [t for t in completed if t.completed_at and t.completed_at >= week_start]
        
        return {
            'total_pending': len(pending),
            'in_progress': len(in_progress),
            'completed': len(completed),
            'overdue': len(overdue),
            'due_today': len(due_today),
            'completed_this_week': len(completed_this_week),
            'by_priority': {
                'urgent': len([t for t in pending + in_progress if t.priority == TaskPriority.URGENT]),
                'high': len([t for t in pending + in_progress if t.priority == TaskPriority.HIGH]),
                'medium': len([t for t in pending + in_progress if t.priority == TaskPriority.MEDIUM]),
                'low': len([t for t in pending + in_progress if t.priority == TaskPriority.LOW])
            },
            'by_type': {
                task_type.value: len([t for t in pending + in_progress if t.task_type == task_type])
                for task_type in TaskType
            }
        }
    
    def create_template(
        self,
        name: str,
        description: str = "",
        task_type: TaskType = TaskType.OTHER,
        default_priority: TaskPriority = TaskPriority.MEDIUM,
        due_days: int = 1,
        reminder_hours: int = 24,
        tags: List[str] = None,
        checklist: List[str] = None
    ) -> TaskTemplate:
        """Create a task template."""
        template = TaskTemplate(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            task_type=task_type,
            default_priority=default_priority,
            due_days=due_days,
            reminder_hours=reminder_hours,
            tags=tags or [],
            checklist=checklist or []
        )
        self.templates[template.id] = template
        self._save_data()
        return template
    
    def get_templates(self) -> List[TaskTemplate]:
        """Get all task templates."""
        return list(self.templates.values())
