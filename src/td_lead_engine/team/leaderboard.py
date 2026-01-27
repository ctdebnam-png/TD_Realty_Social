"""Performance leaderboards for teams."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class LeaderboardMetric(Enum):
    """Metrics for leaderboards."""
    VOLUME = "volume"
    CLOSINGS = "closings"
    LEADS_CONVERTED = "leads_converted"
    RESPONSE_TIME = "response_time"
    APPOINTMENTS = "appointments"
    SHOWINGS = "showings"
    COMMISSION = "commission"
    CONVERSION_RATE = "conversion_rate"


class LeaderboardPeriod(Enum):
    """Leaderboard time periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ALL_TIME = "all_time"


@dataclass
class LeaderboardEntry:
    """An entry in the leaderboard."""
    rank: int
    agent_id: str
    agent_name: str
    value: float
    change: int = 0  # Change in rank from previous period
    trend: str = "same"  # up, down, same


@dataclass
class LeaderboardSnapshot:
    """A snapshot of a leaderboard."""
    id: str
    metric: LeaderboardMetric
    period: LeaderboardPeriod
    entries: List[LeaderboardEntry]
    snapshot_date: datetime
    created_at: datetime = field(default_factory=datetime.now)


class Leaderboard:
    """Performance leaderboards."""
    
    def __init__(
        self,
        agent_manager,
        storage_path: str = "data/team"
    ):
        self.agent_manager = agent_manager
        self.storage_path = storage_path
        self.snapshots: Dict[str, LeaderboardSnapshot] = {}
        self.performance_data: Dict[str, Dict] = {}  # agent_id -> metrics
        
        self._load_data()
    
    def _load_data(self):
        """Load leaderboard data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/leaderboard.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.performance_data = data.get('performance_data', {})
                
                for s in data.get('snapshots', [])[-100:]:  # Keep last 100
                    entries = [
                        LeaderboardEntry(
                            rank=e['rank'],
                            agent_id=e['agent_id'],
                            agent_name=e['agent_name'],
                            value=e['value'],
                            change=e.get('change', 0),
                            trend=e.get('trend', 'same')
                        )
                        for e in s['entries']
                    ]
                    snapshot = LeaderboardSnapshot(
                        id=s['id'],
                        metric=LeaderboardMetric(s['metric']),
                        period=LeaderboardPeriod(s['period']),
                        entries=entries,
                        snapshot_date=datetime.fromisoformat(s['snapshot_date']),
                        created_at=datetime.fromisoformat(s['created_at'])
                    )
                    self.snapshots[snapshot.id] = snapshot
    
    def _save_data(self):
        """Save leaderboard data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        snapshots_data = [
            {
                'id': s.id,
                'metric': s.metric.value,
                'period': s.period.value,
                'entries': [
                    {
                        'rank': e.rank,
                        'agent_id': e.agent_id,
                        'agent_name': e.agent_name,
                        'value': e.value,
                        'change': e.change,
                        'trend': e.trend
                    }
                    for e in s.entries
                ],
                'snapshot_date': s.snapshot_date.isoformat(),
                'created_at': s.created_at.isoformat()
            }
            for s in list(self.snapshots.values())[-100:]
        ]
        
        with open(f"{self.storage_path}/leaderboard.json", 'w') as f:
            json.dump({
                'snapshots': snapshots_data,
                'performance_data': self.performance_data
            }, f, indent=2)
    
    def record_performance(
        self,
        agent_id: str,
        metric: LeaderboardMetric,
        value: float,
        date: datetime = None
    ):
        """Record a performance metric for an agent."""
        date = date or datetime.now()
        date_key = date.strftime('%Y-%m-%d')
        
        if agent_id not in self.performance_data:
            self.performance_data[agent_id] = {}
        
        if date_key not in self.performance_data[agent_id]:
            self.performance_data[agent_id][date_key] = {}
        
        metric_key = metric.value
        if metric_key not in self.performance_data[agent_id][date_key]:
            self.performance_data[agent_id][date_key][metric_key] = 0
        
        self.performance_data[agent_id][date_key][metric_key] += value
        self._save_data()
    
    def get_leaderboard(
        self,
        metric: LeaderboardMetric,
        period: LeaderboardPeriod = LeaderboardPeriod.MONTHLY,
        team_id: str = "",
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get current leaderboard."""
        # Calculate date range
        now = datetime.now()
        if period == LeaderboardPeriod.DAILY:
            start_date = now.replace(hour=0, minute=0, second=0)
        elif period == LeaderboardPeriod.WEEKLY:
            start_date = now - timedelta(days=now.weekday())
        elif period == LeaderboardPeriod.MONTHLY:
            start_date = now.replace(day=1)
        elif period == LeaderboardPeriod.QUARTERLY:
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            start_date = now.replace(month=quarter_month, day=1)
        elif period == LeaderboardPeriod.YEARLY:
            start_date = now.replace(month=1, day=1)
        else:
            start_date = datetime.min
        
        # Get agents
        if team_id:
            agents = self.agent_manager.get_team_members(team_id)
        else:
            agents = self.agent_manager.get_active_agents()
        
        # Calculate totals
        agent_totals = []
        for agent in agents:
            total = 0
            
            if agent.id in self.performance_data:
                for date_key, metrics in self.performance_data[agent.id].items():
                    try:
                        date = datetime.strptime(date_key, '%Y-%m-%d')
                        if date >= start_date:
                            total += metrics.get(metric.value, 0)
                    except ValueError:
                        continue
            
            # Also include data from agent manager for certain metrics
            if metric == LeaderboardMetric.VOLUME:
                total = max(total, agent.ytd_volume)
            elif metric == LeaderboardMetric.CLOSINGS:
                total = max(total, agent.ytd_closings)
            
            agent_totals.append((agent, total))
        
        # Sort by value (response time is better when lower)
        reverse = metric != LeaderboardMetric.RESPONSE_TIME
        agent_totals.sort(key=lambda x: x[1], reverse=reverse)
        
        # Get previous snapshot for comparison
        previous = self._get_previous_snapshot(metric, period)
        previous_ranks = {}
        if previous:
            for entry in previous.entries:
                previous_ranks[entry.agent_id] = entry.rank
        
        # Build leaderboard
        entries = []
        for i, (agent, value) in enumerate(agent_totals[:limit]):
            rank = i + 1
            prev_rank = previous_ranks.get(agent.id, rank)
            change = prev_rank - rank
            
            if change > 0:
                trend = "up"
            elif change < 0:
                trend = "down"
            else:
                trend = "same"
            
            entries.append(LeaderboardEntry(
                rank=rank,
                agent_id=agent.id,
                agent_name=agent.full_name,
                value=round(value, 2),
                change=change,
                trend=trend
            ))
        
        return entries
    
    def _get_previous_snapshot(
        self,
        metric: LeaderboardMetric,
        period: LeaderboardPeriod
    ) -> Optional[LeaderboardSnapshot]:
        """Get previous snapshot for comparison."""
        matching = [
            s for s in self.snapshots.values()
            if s.metric == metric and s.period == period
        ]
        
        if len(matching) >= 2:
            matching.sort(key=lambda s: s.snapshot_date, reverse=True)
            return matching[1]  # Second most recent
        
        return None
    
    def save_snapshot(
        self,
        metric: LeaderboardMetric,
        period: LeaderboardPeriod,
        team_id: str = ""
    ) -> LeaderboardSnapshot:
        """Save a leaderboard snapshot."""
        import uuid
        entries = self.get_leaderboard(metric, period, team_id)
        
        snapshot = LeaderboardSnapshot(
            id=str(uuid.uuid4())[:12],
            metric=metric,
            period=period,
            entries=entries,
            snapshot_date=datetime.now()
        )
        
        self.snapshots[snapshot.id] = snapshot
        self._save_data()
        return snapshot
    
    def get_agent_rankings(self, agent_id: str) -> Dict:
        """Get an agent's rankings across all metrics."""
        rankings = {}
        
        for metric in LeaderboardMetric:
            for period in [LeaderboardPeriod.MONTHLY, LeaderboardPeriod.YEARLY]:
                leaderboard = self.get_leaderboard(metric, period, limit=100)
                
                for entry in leaderboard:
                    if entry.agent_id == agent_id:
                        key = f"{metric.value}_{period.value}"
                        rankings[key] = {
                            'rank': entry.rank,
                            'value': entry.value,
                            'trend': entry.trend,
                            'change': entry.change
                        }
                        break
        
        return rankings
    
    def get_top_performers(
        self,
        period: LeaderboardPeriod = LeaderboardPeriod.MONTHLY,
        team_id: str = ""
    ) -> Dict:
        """Get top performer for each metric."""
        top_performers = {}
        
        for metric in LeaderboardMetric:
            leaderboard = self.get_leaderboard(metric, period, team_id, limit=1)
            if leaderboard:
                top = leaderboard[0]
                top_performers[metric.value] = {
                    'agent_id': top.agent_id,
                    'agent_name': top.agent_name,
                    'value': top.value
                }
        
        return top_performers
    
    def generate_leaderboard_report(
        self,
        period: LeaderboardPeriod = LeaderboardPeriod.MONTHLY,
        team_id: str = ""
    ) -> Dict:
        """Generate comprehensive leaderboard report."""
        leaderboards = {}
        
        for metric in LeaderboardMetric:
            entries = self.get_leaderboard(metric, period, team_id)
            leaderboards[metric.value] = [
                {
                    'rank': e.rank,
                    'agent': e.agent_name,
                    'value': e.value,
                    'trend': e.trend
                }
                for e in entries
            ]
        
        return {
            'period': period.value,
            'generated_at': datetime.now().isoformat(),
            'top_performers': self.get_top_performers(period, team_id),
            'leaderboards': leaderboards
        }
