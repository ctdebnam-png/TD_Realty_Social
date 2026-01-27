"""Task scheduler for automated lead processing."""

import json
import threading
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class TaskFrequency(Enum):
    """Frequency options for scheduled tasks."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Uses cron_expression


@dataclass
class ScheduledTask:
    """Configuration for a scheduled task."""

    id: str
    name: str
    task_type: str  # "score_all", "import", "export", "cleanup", "notify"
    frequency: TaskFrequency
    enabled: bool = True

    # Schedule details
    hour: int = 6  # Default 6 AM
    minute: int = 0
    day_of_week: int = 0  # 0 = Monday, 6 = Sunday
    day_of_month: int = 1

    # Task-specific config
    config: Dict[str, Any] = field(default_factory=dict)

    # Execution tracking
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_result: Optional[str] = None
    run_count: int = 0

    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0
    executed_at: datetime = field(default_factory=datetime.now)


class TaskScheduler:
    """Manages scheduled tasks for lead automation."""

    # Built-in task types
    TASK_TYPES = {
        "score_all": "Score all leads in the database",
        "import_watch": "Watch a directory for new import files",
        "export_hot": "Export hot leads to CSV",
        "export_all": "Export all leads to CSV",
        "cleanup_old": "Archive old cold leads",
        "daily_digest": "Send daily lead digest notification",
        "weekly_report": "Generate weekly lead report",
        "backup_db": "Backup the database",
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the scheduler."""
        self.config_path = config_path or Path.home() / ".td-lead-engine" / "scheduler.json"
        self.tasks: Dict[str, ScheduledTask] = {}
        self.task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._load_config()
        self._register_default_handlers()

    def _load_config(self):
        """Load scheduled tasks from config file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get("tasks", []):
                        task = ScheduledTask(
                            id=task_data["id"],
                            name=task_data["name"],
                            task_type=task_data["task_type"],
                            frequency=TaskFrequency(task_data["frequency"]),
                            enabled=task_data.get("enabled", True),
                            hour=task_data.get("hour", 6),
                            minute=task_data.get("minute", 0),
                            day_of_week=task_data.get("day_of_week", 0),
                            day_of_month=task_data.get("day_of_month", 1),
                            config=task_data.get("config", {}),
                        )
                        self.tasks[task.id] = task
                        self._calculate_next_run(task)
            except Exception as e:
                logger.error(f"Error loading scheduler config: {e}")

    def _save_config(self):
        """Save scheduled tasks to config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "task_type": task.task_type,
                    "frequency": task.frequency.value,
                    "enabled": task.enabled,
                    "hour": task.hour,
                    "minute": task.minute,
                    "day_of_week": task.day_of_week,
                    "day_of_month": task.day_of_month,
                    "config": task.config,
                }
                for task in self.tasks.values()
            ]
        }
        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _register_default_handlers(self):
        """Register handlers for built-in task types."""
        self.task_handlers = {
            "score_all": self._handle_score_all,
            "export_hot": self._handle_export_hot,
            "export_all": self._handle_export_all,
            "cleanup_old": self._handle_cleanup_old,
            "daily_digest": self._handle_daily_digest,
            "backup_db": self._handle_backup_db,
        }

    def register_handler(self, task_type: str, handler: Callable):
        """Register a custom task handler."""
        self.task_handlers[task_type] = handler

    def create_task(
        self,
        task_id: str,
        name: str,
        task_type: str,
        frequency: TaskFrequency,
        hour: int = 6,
        minute: int = 0,
        day_of_week: int = 0,
        config: Optional[Dict[str, Any]] = None
    ) -> ScheduledTask:
        """Create a new scheduled task."""
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            frequency=frequency,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            config=config or {},
        )
        self._calculate_next_run(task)
        self.tasks[task_id] = task
        self._save_config()
        logger.info(f"Created scheduled task: {task_id}")
        return task

    def delete_task(self, task_id: str) -> bool:
        """Delete a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_config()
            logger.info(f"Deleted scheduled task: {task_id}")
            return True
        return False

    def enable_task(self, task_id: str, enabled: bool = True) -> bool:
        """Enable or disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = enabled
            self._save_config()
            return True
        return False

    def list_tasks(self) -> List[ScheduledTask]:
        """List all scheduled tasks."""
        return list(self.tasks.values())

    def run_task_now(self, task_id: str) -> TaskResult:
        """Run a task immediately."""
        if task_id not in self.tasks:
            return TaskResult(
                task_id=task_id,
                success=False,
                message=f"Task not found: {task_id}"
            )

        task = self.tasks[task_id]
        return self._execute_task(task)

    def _calculate_next_run(self, task: ScheduledTask):
        """Calculate the next run time for a task."""
        now = datetime.now()

        if task.frequency == TaskFrequency.HOURLY:
            # Next hour at specified minute
            next_run = now.replace(minute=task.minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(hours=1)

        elif task.frequency == TaskFrequency.DAILY:
            # Today or tomorrow at specified time
            next_run = now.replace(
                hour=task.hour, minute=task.minute, second=0, microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)

        elif task.frequency == TaskFrequency.WEEKLY:
            # Next occurrence of day_of_week at specified time
            days_ahead = task.day_of_week - now.weekday()
            if days_ahead < 0:
                days_ahead += 7
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(
                hour=task.hour, minute=task.minute, second=0, microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(weeks=1)

        elif task.frequency == TaskFrequency.MONTHLY:
            # Next occurrence of day_of_month at specified time
            next_run = now.replace(
                day=min(task.day_of_month, 28),  # Avoid month boundary issues
                hour=task.hour,
                minute=task.minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

        else:
            next_run = now + timedelta(hours=1)

        task.next_run = next_run

    def _execute_task(self, task: ScheduledTask) -> TaskResult:
        """Execute a scheduled task."""
        start_time = time.time()

        handler = self.task_handlers.get(task.task_type)
        if not handler:
            return TaskResult(
                task_id=task.id,
                success=False,
                message=f"No handler for task type: {task.task_type}"
            )

        try:
            result_data = handler(task)
            duration = time.time() - start_time

            task.last_run = datetime.now()
            task.run_count += 1
            task.last_result = "success"
            self._calculate_next_run(task)
            self._save_config()

            return TaskResult(
                task_id=task.id,
                success=True,
                message="Task completed successfully",
                data=result_data,
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            task.last_run = datetime.now()
            task.last_result = f"error: {str(e)}"
            self._save_config()

            logger.error(f"Task {task.id} failed: {e}")

            return TaskResult(
                task_id=task.id,
                success=False,
                message=str(e),
                duration_seconds=duration
            )

    def start(self):
        """Start the scheduler background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")

    def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            now = datetime.now()

            for task in self.tasks.values():
                if not task.enabled:
                    continue
                if not task.next_run:
                    self._calculate_next_run(task)
                    continue
                if now >= task.next_run:
                    logger.info(f"Running scheduled task: {task.id}")
                    self._execute_task(task)

            # Sleep for 1 minute before next check
            time.sleep(60)

    # === Built-in task handlers ===

    def _handle_score_all(self, task: ScheduledTask) -> Dict[str, Any]:
        """Score all leads."""
        from ..storage.database import LeadDatabase
        from ..core.scorer import LeadScorer

        db = LeadDatabase()
        scorer = LeadScorer()
        count = db.score_all_leads(scorer)

        return {"leads_scored": count}

    def _handle_export_hot(self, task: ScheduledTask) -> Dict[str, Any]:
        """Export hot leads to CSV."""
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        export_path = Path(task.config.get(
            "export_path",
            str(Path.home() / "td-lead-exports" / f"hot_leads_{datetime.now().strftime('%Y%m%d')}.csv")
        ))
        export_path.parent.mkdir(parents=True, exist_ok=True)

        count = db.export_to_csv(export_path, tier="hot")

        return {"leads_exported": count, "path": str(export_path)}

    def _handle_export_all(self, task: ScheduledTask) -> Dict[str, Any]:
        """Export all leads to CSV."""
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        export_path = Path(task.config.get(
            "export_path",
            str(Path.home() / "td-lead-exports" / f"all_leads_{datetime.now().strftime('%Y%m%d')}.csv")
        ))
        export_path.parent.mkdir(parents=True, exist_ok=True)

        count = db.export_to_csv(export_path)

        return {"leads_exported": count, "path": str(export_path)}

    def _handle_cleanup_old(self, task: ScheduledTask) -> Dict[str, Any]:
        """Archive old cold leads."""
        # Implementation would archive leads older than X days with cold tier
        days_threshold = task.config.get("days_threshold", 90)
        return {"message": f"Would archive cold leads older than {days_threshold} days"}

    def _handle_daily_digest(self, task: ScheduledTask) -> Dict[str, Any]:
        """Generate and send daily digest."""
        from ..storage.database import LeadDatabase
        from .webhooks import WebhookManager, WebhookEvent

        db = LeadDatabase()
        stats = db.get_stats()
        hot_leads = db.get_hot_leads(limit=10)

        digest_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "stats": stats,
            "top_hot_leads": [
                {"name": l.display_name, "score": l.score, "source": l.source}
                for l in hot_leads
            ],
        }

        # Trigger webhook
        webhook_manager = WebhookManager()
        webhook_manager.trigger(WebhookEvent.DAILY_DIGEST, digest_data)

        return digest_data

    def _handle_backup_db(self, task: ScheduledTask) -> Dict[str, Any]:
        """Backup the database."""
        import shutil
        from ..storage.database import LeadDatabase

        db = LeadDatabase()
        backup_dir = Path(task.config.get(
            "backup_dir",
            str(Path.home() / "td-lead-backups")
        ))
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"leads_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db.db_path, backup_path)

        return {"backup_path": str(backup_path)}


# === Convenience functions ===

def setup_default_schedule(scheduler: TaskScheduler):
    """Set up recommended default scheduled tasks."""

    # Daily scoring at 6 AM
    scheduler.create_task(
        task_id="daily_scoring",
        name="Daily Lead Scoring",
        task_type="score_all",
        frequency=TaskFrequency.DAILY,
        hour=6,
        minute=0,
    )

    # Daily digest at 8 AM
    scheduler.create_task(
        task_id="daily_digest",
        name="Daily Lead Digest",
        task_type="daily_digest",
        frequency=TaskFrequency.DAILY,
        hour=8,
        minute=0,
    )

    # Weekly hot leads export on Monday at 7 AM
    scheduler.create_task(
        task_id="weekly_export",
        name="Weekly Hot Leads Export",
        task_type="export_hot",
        frequency=TaskFrequency.WEEKLY,
        hour=7,
        minute=0,
        day_of_week=0,  # Monday
    )

    # Daily database backup at 3 AM
    scheduler.create_task(
        task_id="daily_backup",
        name="Daily Database Backup",
        task_type="backup_db",
        frequency=TaskFrequency.DAILY,
        hour=3,
        minute=0,
    )
