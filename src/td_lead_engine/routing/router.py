"""Lead routing system for team distribution."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class RoutingMethod(Enum):
    """Lead routing methods."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    RULES_BASED = "rules_based"
    CAPACITY = "capacity"
    SKILLS = "skills"


@dataclass
class Agent:
    """Team member who can receive leads."""

    id: str
    name: str
    email: str
    phone: str = ""

    # Capacity and availability
    status: AgentStatus = AgentStatus.AVAILABLE
    max_leads_per_day: int = 10
    current_lead_count: int = 0
    last_assigned: Optional[datetime] = None

    # Specializations
    specialties: List[str] = field(default_factory=list)  # "buyers", "sellers", "luxury", "investors"
    areas: List[str] = field(default_factory=list)  # "Dublin", "Powell", etc.
    languages: List[str] = field(default_factory=lambda: ["English"])
    min_price: int = 0
    max_price: int = 10000000

    # Performance metrics
    conversion_rate: float = 0.0
    response_time_avg: float = 0.0  # minutes
    rating: float = 5.0

    # Weighting for distribution
    weight: float = 1.0

    def can_accept_lead(self) -> bool:
        """Check if agent can accept new leads."""
        if self.status != AgentStatus.AVAILABLE:
            return False
        if self.current_lead_count >= self.max_leads_per_day:
            return False
        return True

    def matches_lead(self, lead: Dict[str, Any]) -> float:
        """Calculate match score for a lead (0-1)."""
        score = 0.0
        factors = 0

        # Area match
        lead_area = lead.get("area", "").lower()
        if lead_area:
            factors += 1
            if any(area.lower() == lead_area for area in self.areas):
                score += 1.0
            elif any(lead_area in area.lower() for area in self.areas):
                score += 0.5

        # Price range match
        lead_price = lead.get("price_range", 0) or lead.get("property_value", 0)
        if lead_price:
            factors += 1
            if self.min_price <= lead_price <= self.max_price:
                score += 1.0
            elif lead_price < self.min_price * 0.8 or lead_price > self.max_price * 1.2:
                score += 0.3

        # Lead type match
        lead_type = lead.get("type", "").lower()  # buyer, seller, investor
        if lead_type:
            factors += 1
            if lead_type in [s.lower() for s in self.specialties]:
                score += 1.0
            elif "all" in [s.lower() for s in self.specialties]:
                score += 0.7

        # Language match
        lead_language = lead.get("preferred_language", "English")
        if lead_language:
            factors += 1
            if lead_language in self.languages:
                score += 1.0

        return score / factors if factors > 0 else 0.5


@dataclass
class RoutingRule:
    """Rule for routing leads to specific agents."""

    id: str
    name: str
    priority: int  # Lower = higher priority
    conditions: Dict[str, Any]
    action: str  # "assign_agent", "assign_pool", "notify"
    target: str  # Agent ID or pool name
    active: bool = True

    def matches(self, lead: Dict[str, Any]) -> bool:
        """Check if lead matches this rule's conditions."""
        for field, condition in self.conditions.items():
            lead_value = lead.get(field)

            if isinstance(condition, dict):
                # Complex conditions
                if "equals" in condition and lead_value != condition["equals"]:
                    return False
                if "contains" in condition:
                    if not lead_value or condition["contains"].lower() not in str(lead_value).lower():
                        return False
                if "greater_than" in condition:
                    if not lead_value or lead_value <= condition["greater_than"]:
                        return False
                if "less_than" in condition:
                    if not lead_value or lead_value >= condition["less_than"]:
                        return False
                if "in" in condition:
                    if not lead_value or lead_value not in condition["in"]:
                        return False
            else:
                # Simple equality
                if lead_value != condition:
                    return False

        return True


@dataclass
class Assignment:
    """Record of a lead assignment."""

    id: str
    lead_id: str
    agent_id: str
    agent_name: str
    assigned_at: datetime
    routing_method: RoutingMethod
    rule_id: Optional[str] = None
    match_score: float = 0.0
    accepted: Optional[bool] = None
    accepted_at: Optional[datetime] = None
    reassigned: bool = False


class LeadRouter:
    """Route leads to team members based on rules and capacity."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize lead router."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "routing.json"
        self.agents: Dict[str, Agent] = {}
        self.rules: List[RoutingRule] = []
        self.assignments: List[Assignment] = []
        self.default_method = RoutingMethod.ROUND_ROBIN
        self._round_robin_index = 0
        self._load_data()

    def _load_data(self):
        """Load routing configuration and history."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for agent_data in data.get("agents", []):
                        agent = Agent(
                            id=agent_data["id"],
                            name=agent_data["name"],
                            email=agent_data["email"],
                            phone=agent_data.get("phone", ""),
                            status=AgentStatus(agent_data.get("status", "available")),
                            max_leads_per_day=agent_data.get("max_leads_per_day", 10),
                            current_lead_count=agent_data.get("current_lead_count", 0),
                            specialties=agent_data.get("specialties", []),
                            areas=agent_data.get("areas", []),
                            languages=agent_data.get("languages", ["English"]),
                            min_price=agent_data.get("min_price", 0),
                            max_price=agent_data.get("max_price", 10000000),
                            conversion_rate=agent_data.get("conversion_rate", 0),
                            weight=agent_data.get("weight", 1.0)
                        )
                        self.agents[agent.id] = agent

                    for rule_data in data.get("rules", []):
                        rule = RoutingRule(
                            id=rule_data["id"],
                            name=rule_data["name"],
                            priority=rule_data["priority"],
                            conditions=rule_data["conditions"],
                            action=rule_data["action"],
                            target=rule_data["target"],
                            active=rule_data.get("active", True)
                        )
                        self.rules.append(rule)

                    self.rules.sort(key=lambda r: r.priority)
                    self._round_robin_index = data.get("round_robin_index", 0)

            except Exception as e:
                logger.error(f"Error loading routing data: {e}")

    def _save_data(self):
        """Save routing configuration."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "email": a.email,
                    "phone": a.phone,
                    "status": a.status.value,
                    "max_leads_per_day": a.max_leads_per_day,
                    "current_lead_count": a.current_lead_count,
                    "specialties": a.specialties,
                    "areas": a.areas,
                    "languages": a.languages,
                    "min_price": a.min_price,
                    "max_price": a.max_price,
                    "conversion_rate": a.conversion_rate,
                    "weight": a.weight
                }
                for a in self.agents.values()
            ],
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "priority": r.priority,
                    "conditions": r.conditions,
                    "action": r.action,
                    "target": r.target,
                    "active": r.active
                }
                for r in self.rules
            ],
            "round_robin_index": self._round_robin_index,
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_agent(self, agent: Agent):
        """Add a team member."""
        self.agents[agent.id] = agent
        self._save_data()

    def remove_agent(self, agent_id: str) -> bool:
        """Remove a team member."""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_data()
            return True
        return False

    def update_agent_status(self, agent_id: str, status: AgentStatus):
        """Update agent availability status."""
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self._save_data()

    def add_rule(self, rule: RoutingRule):
        """Add a routing rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)
        self._save_data()

    def route_lead(
        self,
        lead: Dict[str, Any],
        method: Optional[RoutingMethod] = None
    ) -> Optional[Assignment]:
        """Route a lead to an appropriate agent."""
        if not self.agents:
            logger.warning("No agents available for routing")
            return None

        method = method or self.default_method
        lead_id = lead.get("id", str(uuid.uuid4())[:8])

        # Try rules-based routing first
        for rule in self.rules:
            if not rule.active:
                continue

            if rule.matches(lead):
                agent = self.agents.get(rule.target)
                if agent and agent.can_accept_lead():
                    return self._assign_lead(lead_id, agent, RoutingMethod.RULES_BASED, rule.id)

        # Fall back to selected method
        if method == RoutingMethod.ROUND_ROBIN:
            agent = self._round_robin_select()
        elif method == RoutingMethod.WEIGHTED:
            agent = self._weighted_select()
        elif method == RoutingMethod.SKILLS:
            agent = self._skills_based_select(lead)
        elif method == RoutingMethod.CAPACITY:
            agent = self._capacity_based_select()
        else:
            agent = self._round_robin_select()

        if agent:
            return self._assign_lead(lead_id, agent, method)

        return None

    def _assign_lead(
        self,
        lead_id: str,
        agent: Agent,
        method: RoutingMethod,
        rule_id: Optional[str] = None
    ) -> Assignment:
        """Create lead assignment."""
        assignment = Assignment(
            id=str(uuid.uuid4())[:8],
            lead_id=lead_id,
            agent_id=agent.id,
            agent_name=agent.name,
            assigned_at=datetime.now(),
            routing_method=method,
            rule_id=rule_id
        )

        agent.current_lead_count += 1
        agent.last_assigned = datetime.now()

        self.assignments.append(assignment)
        self._save_data()

        logger.info(f"Assigned lead {lead_id} to {agent.name} via {method.value}")
        return assignment

    def _round_robin_select(self) -> Optional[Agent]:
        """Select next agent in round-robin order."""
        available = [a for a in self.agents.values() if a.can_accept_lead()]
        if not available:
            return None

        self._round_robin_index = self._round_robin_index % len(available)
        agent = available[self._round_robin_index]
        self._round_robin_index = (self._round_robin_index + 1) % len(available)

        return agent

    def _weighted_select(self) -> Optional[Agent]:
        """Select agent based on weights."""
        available = [a for a in self.agents.values() if a.can_accept_lead()]
        if not available:
            return None

        total_weight = sum(a.weight for a in available)
        if total_weight == 0:
            return available[0]

        import random
        r = random.uniform(0, total_weight)
        cumulative = 0

        for agent in available:
            cumulative += agent.weight
            if r <= cumulative:
                return agent

        return available[-1]

    def _skills_based_select(self, lead: Dict[str, Any]) -> Optional[Agent]:
        """Select agent based on skills match."""
        available = [a for a in self.agents.values() if a.can_accept_lead()]
        if not available:
            return None

        # Score each agent
        scored = []
        for agent in available:
            score = agent.matches_lead(lead)
            scored.append((agent, score))

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[0][0] if scored else None

    def _capacity_based_select(self) -> Optional[Agent]:
        """Select agent with most capacity remaining."""
        available = [a for a in self.agents.values() if a.can_accept_lead()]
        if not available:
            return None

        # Sort by remaining capacity (highest first)
        available.sort(
            key=lambda a: a.max_leads_per_day - a.current_lead_count,
            reverse=True
        )

        return available[0]

    def reset_daily_counts(self):
        """Reset daily lead counts for all agents."""
        for agent in self.agents.values():
            agent.current_lead_count = 0
        self._save_data()

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get assignment stats for an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {}

        agent_assignments = [
            a for a in self.assignments
            if a.agent_id == agent_id
        ]

        last_30_days = datetime.now() - timedelta(days=30)
        recent_assignments = [
            a for a in agent_assignments
            if a.assigned_at >= last_30_days
        ]

        return {
            "agent_name": agent.name,
            "status": agent.status.value,
            "today_count": agent.current_lead_count,
            "max_per_day": agent.max_leads_per_day,
            "capacity_remaining": agent.max_leads_per_day - agent.current_lead_count,
            "total_assignments": len(agent_assignments),
            "last_30_days": len(recent_assignments),
            "avg_per_day": round(len(recent_assignments) / 30, 1),
            "conversion_rate": agent.conversion_rate,
            "specialties": agent.specialties,
            "areas": agent.areas
        }

    def get_routing_summary(self) -> Dict[str, Any]:
        """Get overall routing summary."""
        available_agents = len([a for a in self.agents.values() if a.can_accept_lead()])
        total_capacity = sum(a.max_leads_per_day for a in self.agents.values())
        used_capacity = sum(a.current_lead_count for a in self.agents.values())

        today = datetime.now().date()
        today_assignments = len([
            a for a in self.assignments
            if a.assigned_at.date() == today
        ])

        return {
            "total_agents": len(self.agents),
            "available_agents": available_agents,
            "total_capacity": total_capacity,
            "used_capacity": used_capacity,
            "remaining_capacity": total_capacity - used_capacity,
            "utilization_percent": round(used_capacity / total_capacity * 100, 1) if total_capacity > 0 else 0,
            "today_assignments": today_assignments,
            "active_rules": len([r for r in self.rules if r.active])
        }
