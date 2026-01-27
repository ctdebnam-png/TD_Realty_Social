"""Team management module for brokerages."""

from .agents import AgentManager, Agent, AgentStatus
from .lead_routing import LeadRouter, RoutingRule, RoutingStrategy
from .goals import GoalTracker, Goal, GoalType
from .commissions import CommissionCalculator, CommissionSplit, CommissionPlan
from .leaderboard import Leaderboard, LeaderboardMetric

__all__ = [
    'AgentManager',
    'Agent',
    'AgentStatus',
    'LeadRouter',
    'RoutingRule',
    'RoutingStrategy',
    'GoalTracker',
    'Goal',
    'GoalType',
    'CommissionCalculator',
    'CommissionSplit',
    'CommissionPlan',
    'Leaderboard',
    'LeaderboardMetric'
]
