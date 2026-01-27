"""Lead routing and distribution."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
import os
import random


class RoutingStrategy(Enum):
    """Lead routing strategies."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    GEOGRAPHIC = "geographic"
    SPECIALTY = "specialty"
    HYBRID = "hybrid"


class RoutingCriteria(Enum):
    """Criteria for routing rules."""
    LEAD_SOURCE = "lead_source"
    LEAD_TYPE = "lead_type"
    PRICE_RANGE = "price_range"
    LOCATION = "location"
    LANGUAGE = "language"
    PROPERTY_TYPE = "property_type"


@dataclass
class RoutingRule:
    """A rule for routing leads."""
    id: str
    name: str
    criteria: RoutingCriteria
    value: str  # The value to match
    operator: str = "equals"  # equals, contains, greater_than, less_than
    agent_ids: List[str] = field(default_factory=list)
    team_id: str = ""
    priority: int = 0  # Higher = checked first
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class RoutingAssignment:
    """Record of a lead assignment."""
    id: str
    lead_id: str
    agent_id: str
    rule_id: str = ""
    strategy_used: RoutingStrategy = RoutingStrategy.ROUND_ROBIN
    assigned_at: datetime = field(default_factory=datetime.now)
    accepted: bool = False
    accepted_at: datetime = None
    rejected: bool = False
    rejection_reason: str = ""


class LeadRouter:
    """Route leads to agents based on rules and strategies."""
    
    def __init__(
        self,
        agent_manager,  # AgentManager instance
        default_strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN,
        storage_path: str = "data/team"
    ):
        self.agent_manager = agent_manager
        self.default_strategy = default_strategy
        self.storage_path = storage_path
        
        self.rules: Dict[str, RoutingRule] = {}
        self.assignments: Dict[str, RoutingAssignment] = {}
        self.round_robin_index: Dict[str, int] = {}  # team_id -> index
        self.agent_weights: Dict[str, int] = {}  # agent_id -> weight
        
        self._load_data()
    
    def _load_data(self):
        """Load routing data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/lead_routing.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for r in data.get('rules', []):
                    rule = RoutingRule(
                        id=r['id'],
                        name=r['name'],
                        criteria=RoutingCriteria(r['criteria']),
                        value=r['value'],
                        operator=r.get('operator', 'equals'),
                        agent_ids=r.get('agent_ids', []),
                        team_id=r.get('team_id', ''),
                        priority=r.get('priority', 0),
                        is_active=r.get('is_active', True),
                        created_at=datetime.fromisoformat(r['created_at'])
                    )
                    self.rules[rule.id] = rule
                
                self.round_robin_index = data.get('round_robin_index', {})
                self.agent_weights = data.get('agent_weights', {})
                
                for a in data.get('assignments', [])[-5000:]:  # Keep last 5000
                    assignment = RoutingAssignment(
                        id=a['id'],
                        lead_id=a['lead_id'],
                        agent_id=a['agent_id'],
                        rule_id=a.get('rule_id', ''),
                        strategy_used=RoutingStrategy(a.get('strategy_used', 'round_robin')),
                        assigned_at=datetime.fromisoformat(a['assigned_at']),
                        accepted=a.get('accepted', False),
                        accepted_at=datetime.fromisoformat(a['accepted_at']) if a.get('accepted_at') else None,
                        rejected=a.get('rejected', False),
                        rejection_reason=a.get('rejection_reason', '')
                    )
                    self.assignments[assignment.id] = assignment
    
    def _save_data(self):
        """Save routing data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        rules_data = [
            {
                'id': r.id,
                'name': r.name,
                'criteria': r.criteria.value,
                'value': r.value,
                'operator': r.operator,
                'agent_ids': r.agent_ids,
                'team_id': r.team_id,
                'priority': r.priority,
                'is_active': r.is_active,
                'created_at': r.created_at.isoformat()
            }
            for r in self.rules.values()
        ]
        
        assignments_data = [
            {
                'id': a.id,
                'lead_id': a.lead_id,
                'agent_id': a.agent_id,
                'rule_id': a.rule_id,
                'strategy_used': a.strategy_used.value,
                'assigned_at': a.assigned_at.isoformat(),
                'accepted': a.accepted,
                'accepted_at': a.accepted_at.isoformat() if a.accepted_at else None,
                'rejected': a.rejected,
                'rejection_reason': a.rejection_reason
            }
            for a in list(self.assignments.values())[-5000:]
        ]
        
        with open(f"{self.storage_path}/lead_routing.json", 'w') as f:
            json.dump({
                'rules': rules_data,
                'assignments': assignments_data,
                'round_robin_index': self.round_robin_index,
                'agent_weights': self.agent_weights
            }, f, indent=2)
    
    def add_rule(
        self,
        name: str,
        criteria: RoutingCriteria,
        value: str,
        agent_ids: List[str] = None,
        team_id: str = "",
        operator: str = "equals",
        priority: int = 0
    ) -> RoutingRule:
        """Add a routing rule."""
        import uuid
        rule = RoutingRule(
            id=str(uuid.uuid4())[:12],
            name=name,
            criteria=criteria,
            value=value,
            operator=operator,
            agent_ids=agent_ids or [],
            team_id=team_id,
            priority=priority
        )
        self.rules[rule.id] = rule
        self._save_data()
        return rule
    
    def set_agent_weight(self, agent_id: str, weight: int):
        """Set weight for weighted routing."""
        self.agent_weights[agent_id] = weight
        self._save_data()
    
    def route_lead(
        self,
        lead_data: Dict,
        strategy: RoutingStrategy = None,
        team_id: str = ""
    ) -> Optional[str]:
        """Route a lead to an agent. Returns agent_id or None."""
        strategy = strategy or self.default_strategy
        
        # First check rules
        matched_rule = self._match_rules(lead_data)
        if matched_rule:
            agent_id = self._route_by_rule(matched_rule, strategy)
            if agent_id:
                self._record_assignment(lead_data.get('id', ''), agent_id, matched_rule.id, strategy)
                return agent_id
        
        # Fall back to strategy-based routing
        available_agents = self._get_candidate_agents(lead_data, team_id)
        if not available_agents:
            return None
        
        agent_id = None
        
        if strategy == RoutingStrategy.ROUND_ROBIN:
            agent_id = self._route_round_robin(available_agents, team_id)
        elif strategy == RoutingStrategy.WEIGHTED:
            agent_id = self._route_weighted(available_agents)
        elif strategy == RoutingStrategy.AVAILABILITY:
            agent_id = self._route_by_availability(available_agents)
        elif strategy == RoutingStrategy.PERFORMANCE:
            agent_id = self._route_by_performance(available_agents)
        elif strategy == RoutingStrategy.GEOGRAPHIC:
            agent_id = self._route_by_geography(available_agents, lead_data)
        elif strategy == RoutingStrategy.SPECIALTY:
            agent_id = self._route_by_specialty(available_agents, lead_data)
        elif strategy == RoutingStrategy.HYBRID:
            agent_id = self._route_hybrid(available_agents, lead_data)
        else:
            agent_id = self._route_round_robin(available_agents, team_id)
        
        if agent_id:
            self._record_assignment(lead_data.get('id', ''), agent_id, '', strategy)
        
        return agent_id
    
    def _match_rules(self, lead_data: Dict) -> Optional[RoutingRule]:
        """Find matching rule for lead."""
        active_rules = sorted(
            [r for r in self.rules.values() if r.is_active],
            key=lambda r: r.priority,
            reverse=True
        )
        
        for rule in active_rules:
            lead_value = self._get_lead_value(lead_data, rule.criteria)
            if self._matches_rule(lead_value, rule.value, rule.operator):
                return rule
        
        return None
    
    def _get_lead_value(self, lead_data: Dict, criteria: RoutingCriteria) -> str:
        """Get lead value for a criteria."""
        mapping = {
            RoutingCriteria.LEAD_SOURCE: 'source',
            RoutingCriteria.LEAD_TYPE: 'lead_type',
            RoutingCriteria.PRICE_RANGE: 'budget',
            RoutingCriteria.LOCATION: 'city',
            RoutingCriteria.LANGUAGE: 'language',
            RoutingCriteria.PROPERTY_TYPE: 'property_type'
        }
        key = mapping.get(criteria, criteria.value)
        return str(lead_data.get(key, ''))
    
    def _matches_rule(self, lead_value: str, rule_value: str, operator: str) -> bool:
        """Check if lead value matches rule."""
        if operator == 'equals':
            return lead_value.lower() == rule_value.lower()
        elif operator == 'contains':
            return rule_value.lower() in lead_value.lower()
        elif operator == 'greater_than':
            try:
                return float(lead_value) > float(rule_value)
            except ValueError:
                return False
        elif operator == 'less_than':
            try:
                return float(lead_value) < float(rule_value)
            except ValueError:
                return False
        return False
    
    def _route_by_rule(self, rule: RoutingRule, strategy: RoutingStrategy) -> Optional[str]:
        """Route using a matched rule."""
        if rule.agent_ids:
            # Filter to available agents
            available = [
                aid for aid in rule.agent_ids
                if self.agent_manager.get_agent(aid) and self.agent_manager.get_agent(aid).can_receive_leads
            ]
            if available:
                if strategy == RoutingStrategy.ROUND_ROBIN:
                    return self._route_round_robin(available, rule.id)
                return random.choice(available)
        
        if rule.team_id:
            team_members = self.agent_manager.get_team_members(rule.team_id)
            available = [a.id for a in team_members if a.can_receive_leads]
            if available:
                return self._route_round_robin(available, rule.team_id)
        
        return None
    
    def _get_candidate_agents(self, lead_data: Dict, team_id: str = "") -> List[str]:
        """Get candidate agents for routing."""
        if team_id:
            members = self.agent_manager.get_team_members(team_id)
            return [a.id for a in members if a.can_receive_leads]
        return [a.id for a in self.agent_manager.get_available_agents()]
    
    def _route_round_robin(self, agent_ids: List[str], group_id: str = "default") -> Optional[str]:
        """Route using round robin."""
        if not agent_ids:
            return None
        
        index = self.round_robin_index.get(group_id, 0)
        agent_id = agent_ids[index % len(agent_ids)]
        
        self.round_robin_index[group_id] = (index + 1) % len(agent_ids)
        self._save_data()
        
        return agent_id
    
    def _route_weighted(self, agent_ids: List[str]) -> Optional[str]:
        """Route using weighted distribution."""
        if not agent_ids:
            return None
        
        weights = [self.agent_weights.get(aid, 1) for aid in agent_ids]
        total = sum(weights)
        
        if total == 0:
            return random.choice(agent_ids)
        
        r = random.uniform(0, total)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return agent_ids[i]
        
        return agent_ids[-1]
    
    def _route_by_availability(self, agent_ids: List[str]) -> Optional[str]:
        """Route to agent who is available now."""
        available_now = [
            aid for aid in agent_ids
            if self.agent_manager.is_available_now(aid)
        ]
        
        if available_now:
            return random.choice(available_now)
        
        return random.choice(agent_ids) if agent_ids else None
    
    def _route_by_performance(self, agent_ids: List[str]) -> Optional[str]:
        """Route to highest performing agent with capacity."""
        agents = [(aid, self.agent_manager.get_agent(aid)) for aid in agent_ids]
        agents = [(aid, a) for aid, a in agents if a]
        
        if not agents:
            return None
        
        # Sort by conversion rate (ytd_closings relative to lead count)
        def score(agent_tuple):
            aid, a = agent_tuple
            if a.current_lead_count == 0:
                return a.ytd_closings  # High performers with no current leads get priority
            return a.ytd_closings / (a.current_lead_count + a.ytd_closings)
        
        agents.sort(key=score, reverse=True)
        return agents[0][0]
    
    def _route_by_geography(self, agent_ids: List[str], lead_data: Dict) -> Optional[str]:
        """Route based on geographic area."""
        lead_area = lead_data.get('city', '') or lead_data.get('zip_code', '')
        
        if lead_area:
            area_agents = [
                aid for aid in agent_ids
                if lead_area.lower() in [a.lower() for a in (self.agent_manager.get_agent(aid).areas_served or [])]
            ]
            if area_agents:
                return random.choice(area_agents)
        
        return random.choice(agent_ids) if agent_ids else None
    
    def _route_by_specialty(self, agent_ids: List[str], lead_data: Dict) -> Optional[str]:
        """Route based on specialty match."""
        lead_type = lead_data.get('lead_type', '')
        property_type = lead_data.get('property_type', '')
        
        for specialty in [lead_type, property_type]:
            if specialty:
                specialist_agents = [
                    aid for aid in agent_ids
                    if specialty.lower() in [s.lower() for s in (self.agent_manager.get_agent(aid).specialties or [])]
                ]
                if specialist_agents:
                    return random.choice(specialist_agents)
        
        return random.choice(agent_ids) if agent_ids else None
    
    def _route_hybrid(self, agent_ids: List[str], lead_data: Dict) -> Optional[str]:
        """Hybrid routing considering multiple factors."""
        scored_agents = []
        
        for aid in agent_ids:
            agent = self.agent_manager.get_agent(aid)
            if not agent:
                continue
            
            score = 0
            
            # Availability bonus
            if self.agent_manager.is_available_now(aid):
                score += 30
            
            # Geographic match
            lead_area = lead_data.get('city', '')
            if lead_area and lead_area.lower() in [a.lower() for a in agent.areas_served]:
                score += 25
            
            # Specialty match
            lead_type = lead_data.get('lead_type', '')
            if lead_type and lead_type.lower() in [s.lower() for s in agent.specialties]:
                score += 20
            
            # Language match
            lead_lang = lead_data.get('language', 'English')
            if lead_lang in agent.languages:
                score += 15
            
            # Capacity (fewer current leads = higher score)
            if agent.max_leads > 0:
                capacity_ratio = 1 - (agent.current_lead_count / agent.max_leads)
                score += capacity_ratio * 10
            else:
                score += 10
            
            scored_agents.append((aid, score))
        
        if not scored_agents:
            return None
        
        # Sort by score and pick from top candidates with some randomization
        scored_agents.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_agents[:3]
        
        return random.choice([a[0] for a in top_candidates])
    
    def _record_assignment(
        self,
        lead_id: str,
        agent_id: str,
        rule_id: str,
        strategy: RoutingStrategy
    ):
        """Record a lead assignment."""
        import uuid
        assignment = RoutingAssignment(
            id=str(uuid.uuid4())[:12],
            lead_id=lead_id,
            agent_id=agent_id,
            rule_id=rule_id,
            strategy_used=strategy
        )
        self.assignments[assignment.id] = assignment
        
        # Update agent lead count
        self.agent_manager.increment_lead_count(agent_id)
        
        self._save_data()
    
    def accept_lead(self, assignment_id: str):
        """Mark a lead as accepted."""
        assignment = self.assignments.get(assignment_id)
        if assignment:
            assignment.accepted = True
            assignment.accepted_at = datetime.now()
            self._save_data()
    
    def reject_lead(self, assignment_id: str, reason: str = ""):
        """Reject and reroute a lead."""
        assignment = self.assignments.get(assignment_id)
        if assignment:
            assignment.rejected = True
            assignment.rejection_reason = reason
            self._save_data()
    
    def get_assignment_stats(self) -> Dict:
        """Get routing statistics."""
        total = len(self.assignments)
        accepted = len([a for a in self.assignments.values() if a.accepted])
        rejected = len([a for a in self.assignments.values() if a.rejected])
        
        by_strategy = {}
        for strategy in RoutingStrategy:
            by_strategy[strategy.value] = len([
                a for a in self.assignments.values()
                if a.strategy_used == strategy
            ])
        
        by_agent = {}
        for assignment in self.assignments.values():
            if assignment.agent_id not in by_agent:
                by_agent[assignment.agent_id] = 0
            by_agent[assignment.agent_id] += 1
        
        return {
            'total_assignments': total,
            'accepted': accepted,
            'rejected': rejected,
            'acceptance_rate': round(accepted / total * 100, 1) if total else 0,
            'by_strategy': by_strategy,
            'by_agent': by_agent
        }
