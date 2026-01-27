"""Agent management for brokerage teams."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class AgentStatus(Enum):
    """Agent status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    PROBATION = "probation"
    TERMINATED = "terminated"


class AgentRole(Enum):
    """Agent roles."""
    AGENT = "agent"
    TEAM_LEAD = "team_lead"
    BROKER = "broker"
    ADMIN = "admin"
    ISA = "isa"  # Inside Sales Agent


@dataclass
class AgentSchedule:
    """Agent availability schedule."""
    monday: List[str] = field(default_factory=lambda: ["09:00-17:00"])
    tuesday: List[str] = field(default_factory=lambda: ["09:00-17:00"])
    wednesday: List[str] = field(default_factory=lambda: ["09:00-17:00"])
    thursday: List[str] = field(default_factory=lambda: ["09:00-17:00"])
    friday: List[str] = field(default_factory=lambda: ["09:00-17:00"])
    saturday: List[str] = field(default_factory=list)
    sunday: List[str] = field(default_factory=list)


@dataclass
class Agent:
    """A real estate agent."""
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    license_number: str = ""
    license_expiry: datetime = None
    status: AgentStatus = AgentStatus.ACTIVE
    role: AgentRole = AgentRole.AGENT
    team_id: str = ""
    manager_id: str = ""
    hire_date: datetime = None
    specialties: List[str] = field(default_factory=list)
    areas_served: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=lambda: ["English"])
    bio: str = ""
    photo_url: str = ""
    max_leads: int = 0  # 0 = unlimited
    current_lead_count: int = 0
    schedule: AgentSchedule = field(default_factory=AgentSchedule)
    commission_plan_id: str = ""
    ytd_volume: float = 0
    ytd_closings: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def can_receive_leads(self) -> bool:
        if self.status != AgentStatus.ACTIVE:
            return False
        if self.max_leads > 0 and self.current_lead_count >= self.max_leads:
            return False
        return True


@dataclass
class Team:
    """A team of agents."""
    id: str
    name: str
    leader_id: str = ""
    description: str = ""
    specialties: List[str] = field(default_factory=list)
    areas_served: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class AgentManager:
    """Manage agents and teams."""
    
    def __init__(self, storage_path: str = "data/team"):
        self.storage_path = storage_path
        self.agents: Dict[str, Agent] = {}
        self.teams: Dict[str, Team] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load agents
        agents_file = f"{self.storage_path}/agents.json"
        if os.path.exists(agents_file):
            with open(agents_file, 'r') as f:
                data = json.load(f)
                for a in data:
                    schedule_data = a.get('schedule', {})
                    schedule = AgentSchedule(
                        monday=schedule_data.get('monday', ["09:00-17:00"]),
                        tuesday=schedule_data.get('tuesday', ["09:00-17:00"]),
                        wednesday=schedule_data.get('wednesday', ["09:00-17:00"]),
                        thursday=schedule_data.get('thursday', ["09:00-17:00"]),
                        friday=schedule_data.get('friday', ["09:00-17:00"]),
                        saturday=schedule_data.get('saturday', []),
                        sunday=schedule_data.get('sunday', [])
                    )
                    
                    agent = Agent(
                        id=a['id'],
                        first_name=a['first_name'],
                        last_name=a['last_name'],
                        email=a['email'],
                        phone=a.get('phone', ''),
                        license_number=a.get('license_number', ''),
                        license_expiry=datetime.fromisoformat(a['license_expiry']) if a.get('license_expiry') else None,
                        status=AgentStatus(a.get('status', 'active')),
                        role=AgentRole(a.get('role', 'agent')),
                        team_id=a.get('team_id', ''),
                        manager_id=a.get('manager_id', ''),
                        hire_date=datetime.fromisoformat(a['hire_date']) if a.get('hire_date') else None,
                        specialties=a.get('specialties', []),
                        areas_served=a.get('areas_served', []),
                        languages=a.get('languages', ['English']),
                        bio=a.get('bio', ''),
                        photo_url=a.get('photo_url', ''),
                        max_leads=a.get('max_leads', 0),
                        current_lead_count=a.get('current_lead_count', 0),
                        schedule=schedule,
                        commission_plan_id=a.get('commission_plan_id', ''),
                        ytd_volume=a.get('ytd_volume', 0),
                        ytd_closings=a.get('ytd_closings', 0),
                        created_at=datetime.fromisoformat(a['created_at'])
                    )
                    self.agents[agent.id] = agent
        
        # Load teams
        teams_file = f"{self.storage_path}/teams.json"
        if os.path.exists(teams_file):
            with open(teams_file, 'r') as f:
                data = json.load(f)
                for t in data:
                    team = Team(
                        id=t['id'],
                        name=t['name'],
                        leader_id=t.get('leader_id', ''),
                        description=t.get('description', ''),
                        specialties=t.get('specialties', []),
                        areas_served=t.get('areas_served', []),
                        created_at=datetime.fromisoformat(t['created_at'])
                    )
                    self.teams[team.id] = team
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save agents
        agents_data = [
            {
                'id': a.id,
                'first_name': a.first_name,
                'last_name': a.last_name,
                'email': a.email,
                'phone': a.phone,
                'license_number': a.license_number,
                'license_expiry': a.license_expiry.isoformat() if a.license_expiry else None,
                'status': a.status.value,
                'role': a.role.value,
                'team_id': a.team_id,
                'manager_id': a.manager_id,
                'hire_date': a.hire_date.isoformat() if a.hire_date else None,
                'specialties': a.specialties,
                'areas_served': a.areas_served,
                'languages': a.languages,
                'bio': a.bio,
                'photo_url': a.photo_url,
                'max_leads': a.max_leads,
                'current_lead_count': a.current_lead_count,
                'schedule': {
                    'monday': a.schedule.monday,
                    'tuesday': a.schedule.tuesday,
                    'wednesday': a.schedule.wednesday,
                    'thursday': a.schedule.thursday,
                    'friday': a.schedule.friday,
                    'saturday': a.schedule.saturday,
                    'sunday': a.schedule.sunday
                },
                'commission_plan_id': a.commission_plan_id,
                'ytd_volume': a.ytd_volume,
                'ytd_closings': a.ytd_closings,
                'created_at': a.created_at.isoformat()
            }
            for a in self.agents.values()
        ]
        
        with open(f"{self.storage_path}/agents.json", 'w') as f:
            json.dump(agents_data, f, indent=2)
        
        # Save teams
        teams_data = [
            {
                'id': t.id,
                'name': t.name,
                'leader_id': t.leader_id,
                'description': t.description,
                'specialties': t.specialties,
                'areas_served': t.areas_served,
                'created_at': t.created_at.isoformat()
            }
            for t in self.teams.values()
        ]
        
        with open(f"{self.storage_path}/teams.json", 'w') as f:
            json.dump(teams_data, f, indent=2)
    
    def add_agent(
        self,
        first_name: str,
        last_name: str,
        email: str,
        **kwargs
    ) -> Agent:
        """Add a new agent."""
        agent = Agent(
            id=str(uuid.uuid4())[:12],
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=kwargs.get('phone', ''),
            license_number=kwargs.get('license_number', ''),
            license_expiry=kwargs.get('license_expiry'),
            role=kwargs.get('role', AgentRole.AGENT),
            team_id=kwargs.get('team_id', ''),
            manager_id=kwargs.get('manager_id', ''),
            hire_date=kwargs.get('hire_date', datetime.now()),
            specialties=kwargs.get('specialties', []),
            areas_served=kwargs.get('areas_served', []),
            languages=kwargs.get('languages', ['English']),
            bio=kwargs.get('bio', ''),
            max_leads=kwargs.get('max_leads', 0),
            commission_plan_id=kwargs.get('commission_plan_id', '')
        )
        self.agents[agent.id] = agent
        self._save_data()
        return agent
    
    def update_agent(self, agent_id: str, **kwargs) -> Optional[Agent]:
        """Update agent details."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        self._save_data()
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)
    
    def get_agent_by_email(self, email: str) -> Optional[Agent]:
        """Get an agent by email."""
        for agent in self.agents.values():
            if agent.email.lower() == email.lower():
                return agent
        return None
    
    def get_active_agents(self) -> List[Agent]:
        """Get all active agents."""
        return [a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]
    
    def get_available_agents(self) -> List[Agent]:
        """Get agents available to receive leads."""
        return [a for a in self.agents.values() if a.can_receive_leads]
    
    def create_team(self, name: str, leader_id: str = "", **kwargs) -> Team:
        """Create a new team."""
        team = Team(
            id=str(uuid.uuid4())[:12],
            name=name,
            leader_id=leader_id,
            description=kwargs.get('description', ''),
            specialties=kwargs.get('specialties', []),
            areas_served=kwargs.get('areas_served', [])
        )
        self.teams[team.id] = team
        self._save_data()
        return team
    
    def get_team(self, team_id: str) -> Optional[Team]:
        """Get a team by ID."""
        return self.teams.get(team_id)
    
    def get_team_members(self, team_id: str) -> List[Agent]:
        """Get all members of a team."""
        return [a for a in self.agents.values() if a.team_id == team_id]
    
    def assign_to_team(self, agent_id: str, team_id: str) -> bool:
        """Assign an agent to a team."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        
        agent.team_id = team_id
        self._save_data()
        return True
    
    def increment_lead_count(self, agent_id: str):
        """Increment agent's lead count."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.current_lead_count += 1
            self._save_data()
    
    def record_closing(self, agent_id: str, volume: float):
        """Record a closing for an agent."""
        agent = self.agents.get(agent_id)
        if agent:
            agent.ytd_closings += 1
            agent.ytd_volume += volume
            if agent.current_lead_count > 0:
                agent.current_lead_count -= 1
            self._save_data()
    
    def is_available_now(self, agent_id: str) -> bool:
        """Check if agent is available right now."""
        agent = self.agents.get(agent_id)
        if not agent or agent.status != AgentStatus.ACTIVE:
            return False
        
        now = datetime.now()
        day_name = now.strftime('%A').lower()
        schedule = getattr(agent.schedule, day_name, [])
        
        current_time = now.strftime('%H:%M')
        
        for slot in schedule:
            if '-' in slot:
                start, end = slot.split('-')
                if start <= current_time <= end:
                    return True
        
        return False
    
    def get_agents_by_specialty(self, specialty: str) -> List[Agent]:
        """Get agents with a specific specialty."""
        return [
            a for a in self.agents.values()
            if a.status == AgentStatus.ACTIVE and specialty.lower() in [s.lower() for s in a.specialties]
        ]
    
    def get_agents_by_area(self, area: str) -> List[Agent]:
        """Get agents serving a specific area."""
        return [
            a for a in self.agents.values()
            if a.status == AgentStatus.ACTIVE and area.lower() in [ar.lower() for ar in a.areas_served]
        ]
    
    def get_team_stats(self, team_id: str) -> Dict:
        """Get statistics for a team."""
        members = self.get_team_members(team_id)
        team = self.teams.get(team_id)
        
        return {
            'team_id': team_id,
            'team_name': team.name if team else 'Unknown',
            'member_count': len(members),
            'active_members': len([m for m in members if m.status == AgentStatus.ACTIVE]),
            'total_leads': sum(m.current_lead_count for m in members),
            'ytd_closings': sum(m.ytd_closings for m in members),
            'ytd_volume': sum(m.ytd_volume for m in members),
            'avg_volume_per_agent': sum(m.ytd_volume for m in members) / len(members) if members else 0
        }
