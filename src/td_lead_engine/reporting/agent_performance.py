"""Agent performance reporting."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class PerformanceMetric(Enum):
    """Performance metrics to track."""
    LEADS_ASSIGNED = "leads_assigned"
    LEADS_CONTACTED = "leads_contacted"
    LEADS_CONVERTED = "leads_converted"
    RESPONSE_TIME = "response_time"
    APPOINTMENTS_SET = "appointments_set"
    SHOWINGS_COMPLETED = "showings_completed"
    OFFERS_WRITTEN = "offers_written"
    CONTRACTS_SIGNED = "contracts_signed"
    CLOSINGS = "closings"
    VOLUME = "volume"
    COMMISSION = "commission"


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    agent_id: str
    agent_name: str
    period_start: datetime
    period_end: datetime
    leads_assigned: int = 0
    leads_contacted: int = 0
    leads_converted: int = 0
    avg_response_time_minutes: float = 0
    appointments_set: int = 0
    showings_completed: int = 0
    offers_written: int = 0
    contracts_signed: int = 0
    closings: int = 0
    volume: float = 0
    commission: float = 0
    contact_rate: float = 0
    conversion_rate: float = 0
    appointment_rate: float = 0


@dataclass
class LeaderboardEntry:
    """Entry in performance leaderboard."""
    rank: int
    agent_id: str
    agent_name: str
    metric_value: float
    change_from_previous: float = 0


class AgentPerformanceReport:
    """Generate agent performance reports."""
    
    def __init__(self, storage_path: str = "data/reporting"):
        self.storage_path = storage_path
        self.agent_data: Dict[str, Dict] = {}
        self.activities: List[Dict] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load agent performance data."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        agent_file = f"{self.storage_path}/agent_performance.json"
        if os.path.exists(agent_file):
            with open(agent_file, 'r') as f:
                data = json.load(f)
                self.agent_data = data.get('agents', {})
                self.activities = data.get('activities', [])
    
    def _save_data(self):
        """Save agent performance data."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        with open(f"{self.storage_path}/agent_performance.json", 'w') as f:
            json.dump({
                'agents': self.agent_data,
                'activities': self.activities[-10000:]  # Keep last 10k activities
            }, f, indent=2)
    
    def record_activity(
        self,
        agent_id: str,
        agent_name: str,
        activity_type: str,
        value: float = 1,
        metadata: Dict = None
    ):
        """Record an agent activity."""
        activity = {
            'agent_id': agent_id,
            'agent_name': agent_name,
            'type': activity_type,
            'value': value,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }
        self.activities.append(activity)
        
        # Update agent summary
        if agent_id not in self.agent_data:
            self.agent_data[agent_id] = {
                'name': agent_name,
                'totals': {}
            }
        
        if activity_type not in self.agent_data[agent_id]['totals']:
            self.agent_data[agent_id]['totals'][activity_type] = 0
        self.agent_data[agent_id]['totals'][activity_type] += value
        
        self._save_data()
    
    def record_lead_assigned(self, agent_id: str, agent_name: str, lead_id: str):
        """Record a lead assignment."""
        self.record_activity(agent_id, agent_name, 'leads_assigned', metadata={'lead_id': lead_id})
    
    def record_lead_contact(self, agent_id: str, agent_name: str, lead_id: str, response_time_minutes: float):
        """Record a lead contact."""
        self.record_activity(agent_id, agent_name, 'leads_contacted', metadata={
            'lead_id': lead_id,
            'response_time': response_time_minutes
        })
    
    def record_conversion(self, agent_id: str, agent_name: str, lead_id: str):
        """Record a lead conversion."""
        self.record_activity(agent_id, agent_name, 'leads_converted', metadata={'lead_id': lead_id})
    
    def record_appointment(self, agent_id: str, agent_name: str, lead_id: str):
        """Record an appointment set."""
        self.record_activity(agent_id, agent_name, 'appointments_set', metadata={'lead_id': lead_id})
    
    def record_showing(self, agent_id: str, agent_name: str, lead_id: str, property_id: str):
        """Record a showing completed."""
        self.record_activity(agent_id, agent_name, 'showings_completed', metadata={
            'lead_id': lead_id,
            'property_id': property_id
        })
    
    def record_closing(self, agent_id: str, agent_name: str, lead_id: str, volume: float, commission: float):
        """Record a closing."""
        self.record_activity(agent_id, agent_name, 'closings', metadata={'lead_id': lead_id})
        self.record_activity(agent_id, agent_name, 'volume', value=volume, metadata={'lead_id': lead_id})
        self.record_activity(agent_id, agent_name, 'commission', value=commission, metadata={'lead_id': lead_id})
    
    def get_agent_metrics(
        self,
        agent_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        if agent_id not in self.agent_data:
            return None
        
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        # Filter activities for this agent and period
        activities = [
            a for a in self.activities
            if a['agent_id'] == agent_id
            and start <= datetime.fromisoformat(a['timestamp']) <= end
        ]
        
        # Calculate metrics
        leads_assigned = sum(1 for a in activities if a['type'] == 'leads_assigned')
        leads_contacted = sum(1 for a in activities if a['type'] == 'leads_contacted')
        leads_converted = sum(1 for a in activities if a['type'] == 'leads_converted')
        appointments = sum(1 for a in activities if a['type'] == 'appointments_set')
        showings = sum(1 for a in activities if a['type'] == 'showings_completed')
        closings = sum(1 for a in activities if a['type'] == 'closings')
        volume = sum(a['value'] for a in activities if a['type'] == 'volume')
        commission = sum(a['value'] for a in activities if a['type'] == 'commission')
        
        # Calculate response times
        response_times = [
            a['metadata'].get('response_time', 0)
            for a in activities
            if a['type'] == 'leads_contacted' and a['metadata'].get('response_time')
        ]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        
        return AgentMetrics(
            agent_id=agent_id,
            agent_name=self.agent_data[agent_id]['name'],
            period_start=start,
            period_end=end,
            leads_assigned=leads_assigned,
            leads_contacted=leads_contacted,
            leads_converted=leads_converted,
            avg_response_time_minutes=round(avg_response, 1),
            appointments_set=appointments,
            showings_completed=showings,
            closings=closings,
            volume=volume,
            commission=commission,
            contact_rate=round(leads_contacted / leads_assigned * 100, 1) if leads_assigned else 0,
            conversion_rate=round(leads_converted / leads_assigned * 100, 1) if leads_assigned else 0,
            appointment_rate=round(appointments / leads_contacted * 100, 1) if leads_contacted else 0
        )
    
    def get_team_metrics(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[AgentMetrics]:
        """Get metrics for all agents."""
        metrics = []
        for agent_id in self.agent_data:
            agent_metrics = self.get_agent_metrics(agent_id, start_date, end_date)
            if agent_metrics:
                metrics.append(agent_metrics)
        return metrics
    
    def get_leaderboard(
        self,
        metric: PerformanceMetric,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 10
    ) -> List[LeaderboardEntry]:
        """Get leaderboard for a specific metric."""
        team_metrics = self.get_team_metrics(start_date, end_date)
        
        # Map metric to attribute
        metric_map = {
            PerformanceMetric.LEADS_ASSIGNED: 'leads_assigned',
            PerformanceMetric.LEADS_CONTACTED: 'leads_contacted',
            PerformanceMetric.LEADS_CONVERTED: 'leads_converted',
            PerformanceMetric.RESPONSE_TIME: 'avg_response_time_minutes',
            PerformanceMetric.APPOINTMENTS_SET: 'appointments_set',
            PerformanceMetric.SHOWINGS_COMPLETED: 'showings_completed',
            PerformanceMetric.CLOSINGS: 'closings',
            PerformanceMetric.VOLUME: 'volume',
            PerformanceMetric.COMMISSION: 'commission'
        }
        
        attr = metric_map.get(metric, 'leads_converted')
        
        # Sort by metric (response time is better when lower)
        reverse = metric != PerformanceMetric.RESPONSE_TIME
        sorted_metrics = sorted(team_metrics, key=lambda m: getattr(m, attr), reverse=reverse)
        
        leaderboard = []
        for i, m in enumerate(sorted_metrics[:limit]):
            leaderboard.append(LeaderboardEntry(
                rank=i + 1,
                agent_id=m.agent_id,
                agent_name=m.agent_name,
                metric_value=getattr(m, attr)
            ))
        
        return leaderboard
    
    def generate_performance_report(
        self,
        agent_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Generate a comprehensive performance report."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        if agent_id:
            metrics = [self.get_agent_metrics(agent_id, start, end)]
            metrics = [m for m in metrics if m]
        else:
            metrics = self.get_team_metrics(start, end)
        
        # Team totals
        total_assigned = sum(m.leads_assigned for m in metrics)
        total_contacted = sum(m.leads_contacted for m in metrics)
        total_converted = sum(m.leads_converted for m in metrics)
        total_volume = sum(m.volume for m in metrics)
        total_commission = sum(m.commission for m in metrics)
        total_closings = sum(m.closings for m in metrics)
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'team_summary': {
                'total_agents': len(metrics),
                'leads_assigned': total_assigned,
                'leads_contacted': total_contacted,
                'leads_converted': total_converted,
                'contact_rate': round(total_contacted / total_assigned * 100, 1) if total_assigned else 0,
                'conversion_rate': round(total_converted / total_assigned * 100, 1) if total_assigned else 0,
                'total_closings': total_closings,
                'total_volume': total_volume,
                'total_commission': total_commission,
                'avg_volume_per_agent': round(total_volume / len(metrics), 2) if metrics else 0
            },
            'agents': [
                {
                    'agent_id': m.agent_id,
                    'agent_name': m.agent_name,
                    'leads_assigned': m.leads_assigned,
                    'leads_contacted': m.leads_contacted,
                    'leads_converted': m.leads_converted,
                    'contact_rate': m.contact_rate,
                    'conversion_rate': m.conversion_rate,
                    'avg_response_time': m.avg_response_time_minutes,
                    'appointments': m.appointments_set,
                    'showings': m.showings_completed,
                    'closings': m.closings,
                    'volume': m.volume,
                    'commission': m.commission
                }
                for m in metrics
            ],
            'leaderboards': {
                'conversion': [
                    {'rank': e.rank, 'agent': e.agent_name, 'value': e.metric_value}
                    for e in self.get_leaderboard(PerformanceMetric.LEADS_CONVERTED, start, end, 5)
                ],
                'volume': [
                    {'rank': e.rank, 'agent': e.agent_name, 'value': e.metric_value}
                    for e in self.get_leaderboard(PerformanceMetric.VOLUME, start, end, 5)
                ],
                'response_time': [
                    {'rank': e.rank, 'agent': e.agent_name, 'value': e.metric_value}
                    for e in self.get_leaderboard(PerformanceMetric.RESPONSE_TIME, start, end, 5)
                ]
            }
        }
