"""Reminder system for tasks."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable

from .task_manager import TaskManager, Task, TaskStatus, TaskPriority

logger = logging.getLogger(__name__)


class ReminderSystem:
    """Send reminders for upcoming and overdue tasks."""

    def __init__(self, task_manager: TaskManager):
        """Initialize reminder system."""
        self.task_manager = task_manager
        self.notification_handlers: List[Callable] = []

    def add_notification_handler(self, handler: Callable[[Task, str], None]):
        """Add a notification handler function.

        Handler receives (task, message) and should send the notification.
        """
        self.notification_handlers.append(handler)

    def check_and_send_reminders(self) -> List[Task]:
        """Check for tasks needing reminders and send them."""
        tasks_reminded = []

        # Get tasks needing reminders
        tasks = self.task_manager.get_tasks_needing_reminder()

        for task in tasks:
            message = self._format_reminder_message(task)
            self._send_notification(task, message)
            tasks_reminded.append(task)

        # Also check for overdue tasks
        overdue = self.task_manager.get_overdue_tasks()
        for task in overdue:
            message = self._format_overdue_message(task)
            self._send_notification(task, message)
            if task not in tasks_reminded:
                tasks_reminded.append(task)

        return tasks_reminded

    def _format_reminder_message(self, task: Task) -> str:
        """Format a reminder message for a task."""
        time_until = task.due_date - datetime.now()
        hours = time_until.total_seconds() / 3600

        if hours < 1:
            time_str = f"{int(time_until.total_seconds() / 60)} minutes"
        else:
            time_str = f"{hours:.1f} hours"

        lead_info = f" for {task.lead_name}" if task.lead_name else ""

        return f"Reminder: {task.title}{lead_info} is due in {time_str}"

    def _format_overdue_message(self, task: Task) -> str:
        """Format an overdue notification message."""
        time_overdue = datetime.now() - task.due_date
        hours = time_overdue.total_seconds() / 3600

        if hours < 24:
            time_str = f"{hours:.1f} hours"
        else:
            time_str = f"{hours / 24:.1f} days"

        lead_info = f" for {task.lead_name}" if task.lead_name else ""

        return f"OVERDUE: {task.title}{lead_info} was due {time_str} ago"

    def _send_notification(self, task: Task, message: str):
        """Send notification through all registered handlers."""
        for handler in self.notification_handlers:
            try:
                handler(task, message)
            except Exception as e:
                logger.error(f"Notification handler error: {e}")

    def get_morning_briefing(self) -> Dict[str, Any]:
        """Generate a morning briefing of tasks."""
        summary = self.task_manager.get_daily_summary()
        due_today = self.task_manager.get_due_tasks()
        overdue = self.task_manager.get_overdue_tasks()

        # Group by priority
        urgent = [t for t in due_today if t.priority == TaskPriority.URGENT]
        high = [t for t in due_today if t.priority == TaskPriority.HIGH]
        medium = [t for t in due_today if t.priority == TaskPriority.MEDIUM]

        briefing = {
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "summary": {
                "total_due": len(due_today),
                "overdue": len(overdue),
                "urgent": len(urgent),
                "high_priority": len(high)
            },
            "overdue_tasks": [
                {
                    "title": t.title,
                    "lead": t.lead_name,
                    "due": t.due_date.strftime("%Y-%m-%d %H:%M"),
                    "type": t.task_type.value
                }
                for t in overdue[:5]
            ],
            "urgent_tasks": [
                {
                    "title": t.title,
                    "lead": t.lead_name,
                    "due": t.due_date.strftime("%H:%M"),
                    "type": t.task_type.value
                }
                for t in urgent
            ],
            "today_schedule": [
                {
                    "time": t.due_date.strftime("%H:%M"),
                    "title": t.title,
                    "lead": t.lead_name,
                    "type": t.task_type.value,
                    "priority": t.priority.value
                }
                for t in sorted(due_today, key=lambda x: x.due_date)[:10]
            ]
        }

        return briefing

    def format_briefing_text(self, briefing: Dict[str, Any]) -> str:
        """Format morning briefing as text."""
        lines = [
            f"Good morning! Here's your briefing for {briefing['date']}",
            "",
            f"Tasks due today: {briefing['summary']['total_due']}",
            f"Overdue tasks: {briefing['summary']['overdue']}",
            f"Urgent items: {briefing['summary']['urgent']}",
            ""
        ]

        if briefing['overdue_tasks']:
            lines.append("OVERDUE:")
            for task in briefing['overdue_tasks']:
                lines.append(f"  - {task['title']} ({task['lead'] or 'No lead'})")
            lines.append("")

        if briefing['urgent_tasks']:
            lines.append("URGENT TODAY:")
            for task in briefing['urgent_tasks']:
                lines.append(f"  - {task['time']}: {task['title']} ({task['lead'] or 'No lead'})")
            lines.append("")

        if briefing['today_schedule']:
            lines.append("TODAY'S SCHEDULE:")
            for task in briefing['today_schedule']:
                priority_marker = "!" if task['priority'] in ['urgent', 'high'] else " "
                lines.append(f"  {priority_marker} {task['time']}: {task['title']}")

        return "\n".join(lines)

    def format_briefing_slack(self, briefing: Dict[str, Any]) -> Dict[str, Any]:
        """Format morning briefing for Slack."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Good Morning! {briefing['date']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Tasks Today:* {briefing['summary']['total_due']}"},
                    {"type": "mrkdwn", "text": f"*Overdue:* {briefing['summary']['overdue']}"},
                    {"type": "mrkdwn", "text": f"*Urgent:* {briefing['summary']['urgent']}"},
                    {"type": "mrkdwn", "text": f"*High Priority:* {briefing['summary']['high_priority']}"}
                ]
            }
        ]

        if briefing['overdue_tasks']:
            overdue_text = "\n".join(
                f"- {t['title']} ({t['lead'] or 'No lead'})"
                for t in briefing['overdue_tasks']
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*OVERDUE:*\n{overdue_text}"
                }
            })

        if briefing['urgent_tasks']:
            urgent_text = "\n".join(
                f"- {t['time']}: {t['title']}"
                for t in briefing['urgent_tasks']
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*URGENT:*\n{urgent_text}"
                }
            })

        if briefing['today_schedule']:
            schedule_text = "\n".join(
                f"{'*' if t['priority'] in ['urgent', 'high'] else ''}{t['time']}: {t['title']}{'*' if t['priority'] in ['urgent', 'high'] else ''}"
                for t in briefing['today_schedule'][:8]
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Today's Schedule:*\n{schedule_text}"
                }
            })

        return {"blocks": blocks}


def create_slack_reminder_handler(webhook_url: str) -> Callable:
    """Create a Slack notification handler."""
    import requests

    def handler(task: Task, message: str):
        priority_emoji = {
            TaskPriority.URGENT: "🔴",
            TaskPriority.HIGH: "🟠",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.LOW: "🟢"
        }

        emoji = priority_emoji.get(task.priority, "📋")

        payload = {
            "text": f"{emoji} {message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{message}*"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {"type": "mrkdwn", "text": f"Type: {task.task_type.value}"},
                        {"type": "mrkdwn", "text": f"Priority: {task.priority.value}"},
                        {"type": "mrkdwn", "text": f"Due: {task.due_date.strftime('%Y-%m-%d %H:%M')}"}
                    ]
                }
            ]
        }

        try:
            requests.post(webhook_url, json=payload)
        except Exception as e:
            logger.error(f"Slack notification error: {e}")

    return handler


def create_sms_reminder_handler(twilio_config: Dict[str, str]) -> Callable:
    """Create a Twilio SMS notification handler."""
    from twilio.rest import Client

    client = Client(twilio_config['account_sid'], twilio_config['auth_token'])

    def handler(task: Task, message: str):
        try:
            client.messages.create(
                body=message,
                from_=twilio_config['from_number'],
                to=twilio_config['to_number']
            )
        except Exception as e:
            logger.error(f"SMS notification error: {e}")

    return handler
