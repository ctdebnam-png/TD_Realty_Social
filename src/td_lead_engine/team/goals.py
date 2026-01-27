"""Goal tracking for agents and teams."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class GoalType(Enum):
    """Types of goals."""
    LEADS_CONTACTED = "leads_contacted"
    APPOINTMENTS_SET = "appointments_set"
    SHOWINGS = "showings"
    OFFERS_WRITTEN = "offers_written"
    CONTRACTS = "contracts"
    CLOSINGS = "closings"
    VOLUME = "volume"
    COMMISSION = "commission"
    RESPONSE_TIME = "response_time"
    CONVERSION_RATE = "conversion_rate"


class GoalPeriod(Enum):
    """Goal periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class GoalStatus(Enum):
    """Goal status."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    MISSED = "missed"


@dataclass
class Goal:
    """A goal for an agent or team."""
    id: str
    name: str
    goal_type: GoalType
    target_value: float
    current_value: float = 0
    period: GoalPeriod = GoalPeriod.MONTHLY
    agent_id: str = ""
    team_id: str = ""
    start_date: datetime = None
    end_date: datetime = None
    status: GoalStatus = GoalStatus.NOT_STARTED
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def progress_percentage(self) -> float:
        if self.target_value == 0:
            return 0
        return min(100, round(self.current_value / self.target_value * 100, 1))
    
    @property
    def is_achieved(self) -> bool:
        return self.current_value >= self.target_value


@dataclass
class GoalProgress:
    """Progress update for a goal."""
    id: str
    goal_id: str
    value: float
    notes: str = ""
    recorded_at: datetime = field(default_factory=datetime.now)


class GoalTracker:
    """Track goals for agents and teams."""
    
    def __init__(self, storage_path: str = "data/team"):
        self.storage_path = storage_path
        self.goals: Dict[str, Goal] = {}
        self.progress_history: List[GoalProgress] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load goals from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/goals.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for g in data.get('goals', []):
                    goal = Goal(
                        id=g['id'],
                        name=g['name'],
                        goal_type=GoalType(g['goal_type']),
                        target_value=g['target_value'],
                        current_value=g.get('current_value', 0),
                        period=GoalPeriod(g.get('period', 'monthly')),
                        agent_id=g.get('agent_id', ''),
                        team_id=g.get('team_id', ''),
                        start_date=datetime.fromisoformat(g['start_date']) if g.get('start_date') else None,
                        end_date=datetime.fromisoformat(g['end_date']) if g.get('end_date') else None,
                        status=GoalStatus(g.get('status', 'not_started')),
                        created_at=datetime.fromisoformat(g['created_at'])
                    )
                    self.goals[goal.id] = goal
                
                for p in data.get('progress_history', [])[-10000:]:
                    progress = GoalProgress(
                        id=p['id'],
                        goal_id=p['goal_id'],
                        value=p['value'],
                        notes=p.get('notes', ''),
                        recorded_at=datetime.fromisoformat(p['recorded_at'])
                    )
                    self.progress_history.append(progress)
    
    def _save_data(self):
        """Save goals to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        goals_data = [
            {
                'id': g.id,
                'name': g.name,
                'goal_type': g.goal_type.value,
                'target_value': g.target_value,
                'current_value': g.current_value,
                'period': g.period.value,
                'agent_id': g.agent_id,
                'team_id': g.team_id,
                'start_date': g.start_date.isoformat() if g.start_date else None,
                'end_date': g.end_date.isoformat() if g.end_date else None,
                'status': g.status.value,
                'created_at': g.created_at.isoformat()
            }
            for g in self.goals.values()
        ]
        
        progress_data = [
            {
                'id': p.id,
                'goal_id': p.goal_id,
                'value': p.value,
                'notes': p.notes,
                'recorded_at': p.recorded_at.isoformat()
            }
            for p in self.progress_history[-10000:]
        ]
        
        with open(f"{self.storage_path}/goals.json", 'w') as f:
            json.dump({
                'goals': goals_data,
                'progress_history': progress_data
            }, f, indent=2)
    
    def create_goal(
        self,
        name: str,
        goal_type: GoalType,
        target_value: float,
        period: GoalPeriod = GoalPeriod.MONTHLY,
        agent_id: str = "",
        team_id: str = "",
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Goal:
        """Create a new goal."""
        # Calculate dates based on period if not provided
        now = datetime.now()
        if not start_date:
            if period == GoalPeriod.DAILY:
                start_date = now.replace(hour=0, minute=0, second=0)
            elif period == GoalPeriod.WEEKLY:
                start_date = now - timedelta(days=now.weekday())
            elif period == GoalPeriod.MONTHLY:
                start_date = now.replace(day=1)
            elif period == GoalPeriod.QUARTERLY:
                quarter_month = ((now.month - 1) // 3) * 3 + 1
                start_date = now.replace(month=quarter_month, day=1)
            else:  # YEARLY
                start_date = now.replace(month=1, day=1)
        
        if not end_date:
            if period == GoalPeriod.DAILY:
                end_date = start_date + timedelta(days=1)
            elif period == GoalPeriod.WEEKLY:
                end_date = start_date + timedelta(weeks=1)
            elif period == GoalPeriod.MONTHLY:
                end_date = (start_date + timedelta(days=32)).replace(day=1)
            elif period == GoalPeriod.QUARTERLY:
                end_date = (start_date + timedelta(days=93)).replace(day=1)
            else:  # YEARLY
                end_date = start_date.replace(year=start_date.year + 1)
        
        goal = Goal(
            id=str(uuid.uuid4())[:12],
            name=name,
            goal_type=goal_type,
            target_value=target_value,
            period=period,
            agent_id=agent_id,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            status=GoalStatus.IN_PROGRESS
        )
        
        self.goals[goal.id] = goal
        self._save_data()
        return goal
    
    def update_progress(self, goal_id: str, value: float, notes: str = ""):
        """Update goal progress."""
        goal = self.goals.get(goal_id)
        if not goal:
            return
        
        goal.current_value = value
        
        # Update status
        if goal.is_achieved:
            goal.status = GoalStatus.ACHIEVED
        elif datetime.now() > goal.end_date:
            goal.status = GoalStatus.MISSED
        else:
            goal.status = GoalStatus.IN_PROGRESS
        
        # Record progress
        progress = GoalProgress(
            id=str(uuid.uuid4())[:12],
            goal_id=goal_id,
            value=value,
            notes=notes
        )
        self.progress_history.append(progress)
        
        self._save_data()
    
    def increment_progress(self, goal_id: str, increment: float = 1, notes: str = ""):
        """Increment goal progress."""
        goal = self.goals.get(goal_id)
        if goal:
            self.update_progress(goal_id, goal.current_value + increment, notes)
    
    def get_agent_goals(self, agent_id: str, active_only: bool = True) -> List[Goal]:
        """Get goals for an agent."""
        goals = [g for g in self.goals.values() if g.agent_id == agent_id]
        if active_only:
            now = datetime.now()
            goals = [g for g in goals if g.start_date <= now <= g.end_date]
        return goals
    
    def get_team_goals(self, team_id: str, active_only: bool = True) -> List[Goal]:
        """Get goals for a team."""
        goals = [g for g in self.goals.values() if g.team_id == team_id]
        if active_only:
            now = datetime.now()
            goals = [g for g in goals if g.start_date <= now <= g.end_date]
        return goals
    
    def get_goal_progress_history(self, goal_id: str) -> List[GoalProgress]:
        """Get progress history for a goal."""
        return [p for p in self.progress_history if p.goal_id == goal_id]
    
    def get_goal_summary(self, goal_id: str) -> Optional[Dict]:
        """Get detailed summary for a goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return None
        
        history = self.get_goal_progress_history(goal_id)
        
        # Calculate trend
        if len(history) >= 2:
            recent = history[-5:]
            if len(recent) >= 2:
                trend = (recent[-1].value - recent[0].value) / len(recent)
            else:
                trend = 0
        else:
            trend = 0
        
        # Days remaining
        days_remaining = max(0, (goal.end_date - datetime.now()).days)
        
        # Required daily rate to achieve
        remaining_value = goal.target_value - goal.current_value
        required_daily = remaining_value / days_remaining if days_remaining > 0 else remaining_value
        
        return {
            'goal_id': goal.id,
            'name': goal.name,
            'type': goal.goal_type.value,
            'target': goal.target_value,
            'current': goal.current_value,
            'progress_pct': goal.progress_percentage,
            'status': goal.status.value,
            'is_achieved': goal.is_achieved,
            'days_remaining': days_remaining,
            'remaining_value': max(0, remaining_value),
            'required_daily_rate': round(required_daily, 2),
            'trend': round(trend, 2),
            'on_track': trend >= required_daily if days_remaining > 0 else goal.is_achieved
        }
    
    def create_standard_goals(
        self,
        agent_id: str = "",
        team_id: str = "",
        period: GoalPeriod = GoalPeriod.MONTHLY
    ) -> List[Goal]:
        """Create a standard set of goals."""
        goals = []
        
        standard_goals = [
            (GoalType.LEADS_CONTACTED, "Leads Contacted", 50),
            (GoalType.APPOINTMENTS_SET, "Appointments Set", 20),
            (GoalType.SHOWINGS, "Showings Completed", 15),
            (GoalType.OFFERS_WRITTEN, "Offers Written", 5),
            (GoalType.CLOSINGS, "Closings", 2),
        ]
        
        for goal_type, name, target in standard_goals:
            goal = self.create_goal(
                name=name,
                goal_type=goal_type,
                target_value=target,
                period=period,
                agent_id=agent_id,
                team_id=team_id
            )
            goals.append(goal)
        
        return goals
    
    def get_performance_vs_goals(self, agent_id: str = "", team_id: str = "") -> Dict:
        """Get performance compared to goals."""
        if agent_id:
            goals = self.get_agent_goals(agent_id)
        elif team_id:
            goals = self.get_team_goals(team_id)
        else:
            goals = list(self.goals.values())
        
        achieved = [g for g in goals if g.status == GoalStatus.ACHIEVED]
        missed = [g for g in goals if g.status == GoalStatus.MISSED]
        in_progress = [g for g in goals if g.status == GoalStatus.IN_PROGRESS]
        
        return {
            'total_goals': len(goals),
            'achieved': len(achieved),
            'missed': len(missed),
            'in_progress': len(in_progress),
            'achievement_rate': round(len(achieved) / len(goals) * 100, 1) if goals else 0,
            'goals_detail': [self.get_goal_summary(g.id) for g in goals]
        }
