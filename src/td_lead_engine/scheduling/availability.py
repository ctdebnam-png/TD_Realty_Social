"""Agent availability management."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time, date
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class DayOfWeek(Enum):
    """Days of the week."""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


@dataclass
class TimeBlock:
    """A block of time."""

    start: time
    end: time
    label: str = ""


@dataclass
class AgentAvailability:
    """Agent's availability settings."""

    agent_id: str
    agent_name: str

    # Regular weekly schedule
    weekly_schedule: Dict[int, List[TimeBlock]] = field(default_factory=dict)
    # 0=Monday, 6=Sunday -> list of available time blocks

    # Time off / blocked dates
    blocked_dates: List[date] = field(default_factory=list)
    vacation_ranges: List[tuple] = field(default_factory=list)  # [(start_date, end_date), ...]

    # Preferences
    max_showings_per_day: int = 8
    buffer_between_appointments: int = 15  # minutes
    advance_booking_days: int = 30
    min_notice_hours: int = 2

    # Default appointment duration
    default_showing_duration: int = 30
    default_consultation_duration: int = 60


class AvailabilityManager:
    """Manage agent availability and scheduling."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize availability manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "availability.json"
        self.agents: Dict[str, AgentAvailability] = {}
        self.appointments: Dict[str, List[Dict]] = {}  # agent_id -> appointments
        self._load_data()

    def _load_data(self):
        """Load availability data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for agent_id, agent_data in data.get("agents", {}).items():
                        weekly = {}
                        for day_str, blocks in agent_data.get("weekly_schedule", {}).items():
                            weekly[int(day_str)] = [
                                TimeBlock(
                                    start=time.fromisoformat(b["start"]),
                                    end=time.fromisoformat(b["end"]),
                                    label=b.get("label", "")
                                )
                                for b in blocks
                            ]

                        self.agents[agent_id] = AgentAvailability(
                            agent_id=agent_id,
                            agent_name=agent_data["agent_name"],
                            weekly_schedule=weekly,
                            blocked_dates=[
                                datetime.fromisoformat(d).date()
                                for d in agent_data.get("blocked_dates", [])
                            ],
                            max_showings_per_day=agent_data.get("max_showings_per_day", 8),
                            buffer_between_appointments=agent_data.get("buffer", 15)
                        )

                    self.appointments = data.get("appointments", {})

            except Exception as e:
                logger.error(f"Error loading availability: {e}")

    def _save_data(self):
        """Save availability data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "agents": {
                agent_id: {
                    "agent_name": agent.agent_name,
                    "weekly_schedule": {
                        str(day): [
                            {
                                "start": block.start.isoformat(),
                                "end": block.end.isoformat(),
                                "label": block.label
                            }
                            for block in blocks
                        ]
                        for day, blocks in agent.weekly_schedule.items()
                    },
                    "blocked_dates": [d.isoformat() for d in agent.blocked_dates],
                    "max_showings_per_day": agent.max_showings_per_day,
                    "buffer": agent.buffer_between_appointments
                }
                for agent_id, agent in self.agents.items()
            },
            "appointments": self.appointments,
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def setup_agent(
        self,
        agent_id: str,
        agent_name: str,
        default_schedule: bool = True
    ) -> AgentAvailability:
        """Set up a new agent with default availability."""
        agent = AgentAvailability(
            agent_id=agent_id,
            agent_name=agent_name
        )

        if default_schedule:
            # Default: M-F 9am-6pm, Sat 10am-4pm
            weekday_blocks = [
                TimeBlock(time(9, 0), time(12, 0), "Morning"),
                TimeBlock(time(13, 0), time(18, 0), "Afternoon")
            ]

            for day in range(5):  # Monday to Friday
                agent.weekly_schedule[day] = weekday_blocks.copy()

            # Saturday
            agent.weekly_schedule[5] = [
                TimeBlock(time(10, 0), time(16, 0), "Weekend")
            ]

            # Sunday - closed by default
            agent.weekly_schedule[6] = []

        self.agents[agent_id] = agent
        self.appointments[agent_id] = []
        self._save_data()

        return agent

    def set_weekly_schedule(
        self,
        agent_id: str,
        day: int,  # 0=Monday, 6=Sunday
        time_blocks: List[Dict[str, str]]
    ) -> bool:
        """Set agent's schedule for a specific day."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        agent.weekly_schedule[day] = [
            TimeBlock(
                start=time.fromisoformat(block["start"]),
                end=time.fromisoformat(block["end"]),
                label=block.get("label", "")
            )
            for block in time_blocks
        ]

        self._save_data()
        return True

    def block_date(self, agent_id: str, blocked_date: date, reason: str = "") -> bool:
        """Block a specific date."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        if blocked_date not in agent.blocked_dates:
            agent.blocked_dates.append(blocked_date)
            self._save_data()

        return True

    def unblock_date(self, agent_id: str, blocked_date: date) -> bool:
        """Unblock a specific date."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        if blocked_date in agent.blocked_dates:
            agent.blocked_dates.remove(blocked_date)
            self._save_data()

        return True

    def add_vacation(self, agent_id: str, start_date: date, end_date: date) -> bool:
        """Add vacation time."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        agent.vacation_ranges.append((start_date, end_date))
        self._save_data()
        return True

    def book_appointment(
        self,
        agent_id: str,
        appointment_date: date,
        start_time: time,
        duration: int,
        appointment_type: str,
        client_name: str,
        notes: str = ""
    ) -> Optional[str]:
        """Book an appointment."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        # Check availability
        if not self.is_available(agent_id, appointment_date, start_time, duration):
            return None

        appointment_id = f"{agent_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if agent_id not in self.appointments:
            self.appointments[agent_id] = []

        self.appointments[agent_id].append({
            "id": appointment_id,
            "date": appointment_date.isoformat(),
            "start_time": start_time.isoformat(),
            "duration": duration,
            "type": appointment_type,
            "client": client_name,
            "notes": notes,
            "created_at": datetime.now().isoformat()
        })

        self._save_data()
        return appointment_id

    def cancel_appointment(self, agent_id: str, appointment_id: str) -> bool:
        """Cancel an appointment."""
        if agent_id not in self.appointments:
            return False

        original_count = len(self.appointments[agent_id])
        self.appointments[agent_id] = [
            apt for apt in self.appointments[agent_id]
            if apt["id"] != appointment_id
        ]

        if len(self.appointments[agent_id]) < original_count:
            self._save_data()
            return True
        return False

    def is_available(
        self,
        agent_id: str,
        check_date: date,
        check_time: time,
        duration: int = 30
    ) -> bool:
        """Check if agent is available at a specific time."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        # Check blocked dates
        if check_date in agent.blocked_dates:
            return False

        # Check vacation
        for start, end in agent.vacation_ranges:
            if start <= check_date <= end:
                return False

        # Check weekly schedule
        day_of_week = check_date.weekday()
        day_blocks = agent.weekly_schedule.get(day_of_week, [])

        if not day_blocks:
            return False

        # Check if time falls within an available block
        in_schedule = False
        check_end = (datetime.combine(check_date, check_time) + timedelta(minutes=duration)).time()

        for block in day_blocks:
            if block.start <= check_time and check_end <= block.end:
                in_schedule = True
                break

        if not in_schedule:
            return False

        # Check existing appointments
        agent_appts = self.appointments.get(agent_id, [])
        for apt in agent_appts:
            if apt["date"] == check_date.isoformat():
                apt_start = time.fromisoformat(apt["start_time"])
                apt_end = (datetime.combine(check_date, apt_start) +
                          timedelta(minutes=apt["duration"] + agent.buffer_between_appointments)).time()

                # Check for overlap
                if not (check_end <= apt_start or check_time >= apt_end):
                    return False

        # Check max showings per day
        day_appointments = [a for a in agent_appts if a["date"] == check_date.isoformat()]
        if len(day_appointments) >= agent.max_showings_per_day:
            return False

        return True

    def get_available_slots(
        self,
        agent_id: str,
        target_date: date,
        slot_duration: int = 30
    ) -> List[Dict[str, Any]]:
        """Get available time slots for a date."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []

        # Check if date is blocked
        if target_date in agent.blocked_dates:
            return []

        for start, end in agent.vacation_ranges:
            if start <= target_date <= end:
                return []

        day_of_week = target_date.weekday()
        day_blocks = agent.weekly_schedule.get(day_of_week, [])

        if not day_blocks:
            return []

        available_slots = []

        for block in day_blocks:
            current = datetime.combine(target_date, block.start)
            block_end = datetime.combine(target_date, block.end)

            while current + timedelta(minutes=slot_duration) <= block_end:
                slot_time = current.time()

                if self.is_available(agent_id, target_date, slot_time, slot_duration):
                    available_slots.append({
                        "time": slot_time.isoformat(),
                        "end_time": (current + timedelta(minutes=slot_duration)).time().isoformat(),
                        "available": True
                    })

                current += timedelta(minutes=30)  # 30-minute increments

        return available_slots

    def get_agent_schedule(
        self,
        agent_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Get agent's schedule for a date range."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []

        schedule = []
        current = start_date

        while current <= end_date:
            day_of_week = current.weekday()
            day_name = DayOfWeek(day_of_week).name

            # Check if blocked
            is_blocked = current in agent.blocked_dates
            is_vacation = any(start <= current <= end for start, end in agent.vacation_ranges)

            # Get appointments
            day_appts = [
                a for a in self.appointments.get(agent_id, [])
                if a["date"] == current.isoformat()
            ]

            schedule.append({
                "date": current.isoformat(),
                "day": day_name,
                "available": not is_blocked and not is_vacation,
                "blocked": is_blocked,
                "vacation": is_vacation,
                "working_hours": [
                    {"start": b.start.isoformat(), "end": b.end.isoformat()}
                    for b in agent.weekly_schedule.get(day_of_week, [])
                ] if not is_blocked and not is_vacation else [],
                "appointments": [
                    {
                        "id": a["id"],
                        "time": a["start_time"],
                        "duration": a["duration"],
                        "type": a["type"],
                        "client": a["client"]
                    }
                    for a in sorted(day_appts, key=lambda x: x["start_time"])
                ]
            })

            current += timedelta(days=1)

        return schedule

    def get_availability_summary(self, agent_id: str, days: int = 7) -> Dict[str, Any]:
        """Get availability summary for upcoming days."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        today = datetime.now().date()
        summary = {
            "agent_id": agent_id,
            "agent_name": agent.agent_name,
            "days": []
        }

        total_slots = 0
        available_slots = 0

        for i in range(days):
            check_date = today + timedelta(days=i)
            slots = self.get_available_slots(agent_id, check_date)

            total_slots += 16  # Approximate max slots per day
            available_slots += len(slots)

            summary["days"].append({
                "date": check_date.isoformat(),
                "day": DayOfWeek(check_date.weekday()).name[:3],
                "available_slots": len(slots),
                "appointments": len([
                    a for a in self.appointments.get(agent_id, [])
                    if a["date"] == check_date.isoformat()
                ])
            })

        summary["total_available_slots"] = available_slots
        summary["utilization"] = f"{((total_slots - available_slots) / total_slots * 100):.0f}%" if total_slots > 0 else "0%"

        return summary

    def sync_with_calendar(self, agent_id: str, calendar_events: List[Dict]) -> int:
        """Sync availability with external calendar events."""
        agent = self.agents.get(agent_id)
        if not agent:
            return 0

        blocked_count = 0

        for event in calendar_events:
            event_date = datetime.fromisoformat(event["date"]).date()
            if event.get("all_day"):
                if event_date not in agent.blocked_dates:
                    agent.blocked_dates.append(event_date)
                    blocked_count += 1
            else:
                # Add as appointment
                start_time = time.fromisoformat(event["start_time"])
                duration = event.get("duration", 60)

                self.book_appointment(
                    agent_id,
                    event_date,
                    start_time,
                    duration,
                    event.get("type", "calendar_block"),
                    event.get("title", "Calendar Event"),
                    event.get("notes", "")
                )
                blocked_count += 1

        self._save_data()
        return blocked_count
