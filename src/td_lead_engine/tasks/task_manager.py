"""Task management system for lead follow-ups."""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    URGENT = "urgent"      # Do today
    HIGH = "high"          # Do within 2 days
    MEDIUM = "medium"      # Do within a week
    LOW = "low"            # Do when time permits


class TaskStatus(Enum):
    """Task status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    SNOOZED = "snoozed"


class TaskType(Enum):
    """Types of follow-up tasks."""
    CALL = "call"
    EMAIL = "email"
    TEXT = "text"
    SOCIAL_DM = "social_dm"
    MEETING = "meeting"
    SHOWING = "showing"
    FOLLOW_UP = "follow_up"
    SEND_INFO = "send_info"
    CHECK_IN = "check_in"
    CUSTOM = "custom"


@dataclass
class Task:
    """A follow-up task for a lead."""

    id: str
    lead_id: Optional[str]
    lead_name: Optional[str]

    title: str
    description: Optional[str]
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus

    due_date: datetime
    reminder_date: Optional[datetime] = None

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    notes: Optional[str] = None
    outcome: Optional[str] = None  # Result of completed task

    # Recurrence
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # "daily", "weekly", "monthly"
    recurrence_end: Optional[datetime] = None

    # Context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        # Convert enums and datetimes
        data['task_type'] = self.task_type.value
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        data['due_date'] = self.due_date.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.reminder_date:
            data['reminder_date'] = self.reminder_date.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.recurrence_end:
            data['recurrence_end'] = self.recurrence_end.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create from dictionary."""
        # Convert strings back to enums and datetimes
        data['task_type'] = TaskType(data['task_type'])
        data['priority'] = TaskPriority(data['priority'])
        data['status'] = TaskStatus(data['status'])
        data['due_date'] = datetime.fromisoformat(data['due_date'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('reminder_date'):
            data['reminder_date'] = datetime.fromisoformat(data['reminder_date'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        if data.get('recurrence_end'):
            data['recurrence_end'] = datetime.fromisoformat(data['recurrence_end'])
        return cls(**data)


class TaskManager:
    """Manage follow-up tasks for leads."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize task manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "tasks.json"
        self.tasks: Dict[str, Task] = {}
        self._load_data()

    def _load_data(self):
        """Load tasks from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = Task.from_dict(task_data)
                        self.tasks[task.id] = task
            except Exception as e:
                logger.error(f"Error loading tasks: {e}")

    def _save_data(self):
        """Save tasks to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": [task.to_dict() for task in self.tasks.values()],
            "updated_at": datetime.now().isoformat()
        }
        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def create_task(
        self,
        title: str,
        task_type: TaskType,
        due_date: datetime,
        lead_id: Optional[str] = None,
        lead_name: Optional[str] = None,
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        reminder_minutes_before: int = 60,
        is_recurring: bool = False,
        recurrence_pattern: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Task:
        """Create a new task."""
        task_id = str(uuid.uuid4())[:8]

        reminder_date = None
        if reminder_minutes_before > 0:
            reminder_date = due_date - timedelta(minutes=reminder_minutes_before)

        task = Task(
            id=task_id,
            lead_id=lead_id,
            lead_name=lead_name,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            due_date=due_date,
            reminder_date=reminder_date,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern,
            context=context or {}
        )

        self.tasks[task_id] = task
        self._save_data()

        logger.info(f"Created task: {title} (due: {due_date})")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def update_task(self, task_id: str, **updates) -> Optional[Task]:
        """Update a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now()
        self._save_data()

        return task

    def complete_task(self, task_id: str, outcome: Optional[str] = None) -> Optional[Task]:
        """Mark a task as completed."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        task.updated_at = datetime.now()
        if outcome:
            task.outcome = outcome

        # Handle recurring tasks
        if task.is_recurring and task.recurrence_pattern:
            self._create_next_occurrence(task)

        self._save_data()
        return task

    def _create_next_occurrence(self, task: Task):
        """Create the next occurrence of a recurring task."""
        if task.recurrence_end and datetime.now() >= task.recurrence_end:
            return  # Recurrence has ended

        # Calculate next due date
        if task.recurrence_pattern == "daily":
            next_due = task.due_date + timedelta(days=1)
        elif task.recurrence_pattern == "weekly":
            next_due = task.due_date + timedelta(weeks=1)
        elif task.recurrence_pattern == "monthly":
            next_due = task.due_date + timedelta(days=30)
        elif task.recurrence_pattern == "biweekly":
            next_due = task.due_date + timedelta(weeks=2)
        else:
            return

        # Create new task
        self.create_task(
            title=task.title,
            task_type=task.task_type,
            due_date=next_due,
            lead_id=task.lead_id,
            lead_name=task.lead_name,
            description=task.description,
            priority=task.priority,
            is_recurring=True,
            recurrence_pattern=task.recurrence_pattern,
            context=task.context
        )

    def snooze_task(self, task_id: str, hours: int = 24) -> Optional[Task]:
        """Snooze a task for a specified number of hours."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.SNOOZED
        task.due_date = datetime.now() + timedelta(hours=hours)
        task.reminder_date = task.due_date - timedelta(hours=1)
        task.updated_at = datetime.now()

        self._save_data()
        return task

    def cancel_task(self, task_id: str) -> Optional[Task]:
        """Cancel a task."""
        task = self.tasks.get(task_id)
        if not task:
            return None

        task.status = TaskStatus.CANCELLED
        task.updated_at = datetime.now()

        self._save_data()
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a task permanently."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_data()
            return True
        return False

    def get_tasks_for_lead(self, lead_id: str) -> List[Task]:
        """Get all tasks for a specific lead."""
        return [
            task for task in self.tasks.values()
            if task.lead_id == lead_id
        ]

    def get_due_tasks(self, include_overdue: bool = True) -> List[Task]:
        """Get tasks that are due today."""
        now = datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59)

        tasks = []
        for task in self.tasks.values():
            if task.status not in [TaskStatus.PENDING, TaskStatus.SNOOZED]:
                continue

            if task.due_date <= today_end:
                if include_overdue or task.due_date >= now.replace(hour=0, minute=0, second=0):
                    tasks.append(task)

        return sorted(tasks, key=lambda t: (t.priority.value, t.due_date))

    def get_overdue_tasks(self) -> List[Task]:
        """Get overdue tasks."""
        now = datetime.now()

        return [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.SNOOZED]
            and task.due_date < now
        ]

    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """Get tasks due in the next N days."""
        now = datetime.now()
        end_date = now + timedelta(days=days)

        tasks = [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.PENDING, TaskStatus.SNOOZED]
            and now <= task.due_date <= end_date
        ]

        return sorted(tasks, key=lambda t: t.due_date)

    def get_tasks_needing_reminder(self) -> List[Task]:
        """Get tasks that need reminders sent now."""
        now = datetime.now()

        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
            and task.reminder_date
            and task.reminder_date <= now <= task.due_date
        ]

    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """Get all pending tasks of a specific priority."""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
            and task.priority == priority
        ]

    def get_tasks_by_type(self, task_type: TaskType) -> List[Task]:
        """Get all pending tasks of a specific type."""
        return [
            task for task in self.tasks.values()
            if task.status == TaskStatus.PENDING
            and task.task_type == task_type
        ]

    def get_daily_summary(self) -> Dict[str, Any]:
        """Get a summary of today's tasks."""
        due_today = self.get_due_tasks()
        overdue = self.get_overdue_tasks()
        upcoming_week = self.get_upcoming_tasks(7)

        # Count by type
        type_counts = {}
        for task in due_today:
            ttype = task.task_type.value
            type_counts[ttype] = type_counts.get(ttype, 0) + 1

        # Count by priority
        priority_counts = {}
        for task in due_today:
            prio = task.priority.value
            priority_counts[prio] = priority_counts.get(prio, 0) + 1

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "due_today": len(due_today),
            "overdue": len(overdue),
            "upcoming_week": len(upcoming_week),
            "by_type": type_counts,
            "by_priority": priority_counts,
            "urgent_tasks": [t.to_dict() for t in due_today if t.priority == TaskPriority.URGENT],
            "high_priority": [t.to_dict() for t in due_today if t.priority == TaskPriority.HIGH],
        }

    def create_follow_up_sequence(
        self,
        lead_id: str,
        lead_name: str,
        sequence_type: str = "new_lead"
    ) -> List[Task]:
        """Create a standard follow-up sequence for a lead."""
        now = datetime.now()
        tasks = []

        sequences = {
            "new_lead": [
                (TaskType.CALL, "Initial call", 0, TaskPriority.HIGH),
                (TaskType.EMAIL, "Send intro email", 0, TaskPriority.HIGH),
                (TaskType.FOLLOW_UP, "Follow up if no response", 2, TaskPriority.MEDIUM),
                (TaskType.TEXT, "Text check-in", 5, TaskPriority.MEDIUM),
                (TaskType.EMAIL, "Value-add email", 7, TaskPriority.LOW),
            ],
            "hot_lead": [
                (TaskType.CALL, "Urgent - call hot lead", 0, TaskPriority.URGENT),
                (TaskType.FOLLOW_UP, "Follow up call", 1, TaskPriority.HIGH),
                (TaskType.MEETING, "Schedule meeting", 2, TaskPriority.HIGH),
            ],
            "nurture": [
                (TaskType.EMAIL, "Monthly market update", 0, TaskPriority.LOW),
                (TaskType.CHECK_IN, "Quarterly check-in", 90, TaskPriority.LOW),
            ],
            "post_showing": [
                (TaskType.CALL, "Post-showing feedback call", 0, TaskPriority.HIGH),
                (TaskType.EMAIL, "Send comparable properties", 1, TaskPriority.MEDIUM),
                (TaskType.FOLLOW_UP, "Decision follow-up", 3, TaskPriority.HIGH),
            ],
            "listing_prospect": [
                (TaskType.CALL, "Initial listing consultation call", 0, TaskPriority.HIGH),
                (TaskType.SEND_INFO, "Send CMA", 1, TaskPriority.HIGH),
                (TaskType.MEETING, "Schedule listing presentation", 2, TaskPriority.HIGH),
                (TaskType.FOLLOW_UP, "Follow up on CMA", 4, TaskPriority.MEDIUM),
            ]
        }

        sequence = sequences.get(sequence_type, sequences["new_lead"])

        for task_type, title, days_offset, priority in sequence:
            due_date = now + timedelta(days=days_offset)
            task = self.create_task(
                title=f"{title} - {lead_name}",
                task_type=task_type,
                due_date=due_date,
                lead_id=lead_id,
                lead_name=lead_name,
                priority=priority,
                context={"sequence": sequence_type}
            )
            tasks.append(task)

        return tasks

    def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        total = len(self.tasks)
        completed = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
        pending = len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING])
        overdue = len(self.get_overdue_tasks())

        # Completion rate
        completion_rate = (completed / total * 100) if total > 0 else 0

        # Average completion time
        completed_tasks = [t for t in self.tasks.values() if t.completed_at]
        avg_completion = None
        if completed_tasks:
            total_time = sum(
                (t.completed_at - t.created_at).total_seconds()
                for t in completed_tasks
            )
            avg_completion = total_time / len(completed_tasks) / 3600  # hours

        return {
            "total_tasks": total,
            "completed": completed,
            "pending": pending,
            "overdue": overdue,
            "completion_rate": round(completion_rate, 1),
            "avg_completion_hours": round(avg_completion, 1) if avg_completion else None
        }
