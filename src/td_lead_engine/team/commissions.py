"""Commission calculation and tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class CommissionType(Enum):
    """Commission structure types."""
    FLAT_PERCENTAGE = "flat_percentage"
    TIERED = "tiered"
    GRADUATED = "graduated"
    SPLIT = "split"


@dataclass
class CommissionTier:
    """A tier in a tiered commission plan."""
    min_volume: float
    max_volume: float
    percentage: float


@dataclass
class CommissionPlan:
    """A commission plan."""
    id: str
    name: str
    commission_type: CommissionType
    base_percentage: float = 0  # For flat percentage
    tiers: List[CommissionTier] = field(default_factory=list)
    brokerage_split: float = 0  # Percentage kept by brokerage
    team_split: float = 0  # Percentage to team lead
    cap_amount: float = 0  # Annual cap (0 = no cap)
    cap_percentage_after: float = 100  # Percentage after cap
    franchise_fee: float = 0
    e_and_o_fee: float = 0
    transaction_fee: float = 0
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CommissionSplit:
    """A commission split calculation."""
    id: str
    transaction_id: str
    agent_id: str
    plan_id: str
    sale_price: float
    gross_commission: float
    gross_commission_rate: float
    brokerage_share: float
    team_share: float
    agent_share: float
    fees_deducted: float
    net_to_agent: float
    cap_applied: bool = False
    calculated_at: datetime = field(default_factory=datetime.now)


class CommissionCalculator:
    """Calculate and track commissions."""
    
    def __init__(self, storage_path: str = "data/team"):
        self.storage_path = storage_path
        self.plans: Dict[str, CommissionPlan] = {}
        self.splits: Dict[str, CommissionSplit] = {}
        self.agent_ytd_paid: Dict[str, float] = {}  # Track YTD for cap
        
        self._load_data()
        self._create_default_plans()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/commissions.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for p in data.get('plans', []):
                    tiers = [
                        CommissionTier(t['min_volume'], t['max_volume'], t['percentage'])
                        for t in p.get('tiers', [])
                    ]
                    plan = CommissionPlan(
                        id=p['id'],
                        name=p['name'],
                        commission_type=CommissionType(p['commission_type']),
                        base_percentage=p.get('base_percentage', 0),
                        tiers=tiers,
                        brokerage_split=p.get('brokerage_split', 0),
                        team_split=p.get('team_split', 0),
                        cap_amount=p.get('cap_amount', 0),
                        cap_percentage_after=p.get('cap_percentage_after', 100),
                        franchise_fee=p.get('franchise_fee', 0),
                        e_and_o_fee=p.get('e_and_o_fee', 0),
                        transaction_fee=p.get('transaction_fee', 0),
                        is_active=p.get('is_active', True),
                        created_at=datetime.fromisoformat(p['created_at'])
                    )
                    self.plans[plan.id] = plan
                
                for s in data.get('splits', []):
                    split = CommissionSplit(
                        id=s['id'],
                        transaction_id=s['transaction_id'],
                        agent_id=s['agent_id'],
                        plan_id=s['plan_id'],
                        sale_price=s['sale_price'],
                        gross_commission=s['gross_commission'],
                        gross_commission_rate=s['gross_commission_rate'],
                        brokerage_share=s['brokerage_share'],
                        team_share=s['team_share'],
                        agent_share=s['agent_share'],
                        fees_deducted=s['fees_deducted'],
                        net_to_agent=s['net_to_agent'],
                        cap_applied=s.get('cap_applied', False),
                        calculated_at=datetime.fromisoformat(s['calculated_at'])
                    )
                    self.splits[split.id] = split
                
                self.agent_ytd_paid = data.get('agent_ytd_paid', {})
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        plans_data = [
            {
                'id': p.id,
                'name': p.name,
                'commission_type': p.commission_type.value,
                'base_percentage': p.base_percentage,
                'tiers': [
                    {'min_volume': t.min_volume, 'max_volume': t.max_volume, 'percentage': t.percentage}
                    for t in p.tiers
                ],
                'brokerage_split': p.brokerage_split,
                'team_split': p.team_split,
                'cap_amount': p.cap_amount,
                'cap_percentage_after': p.cap_percentage_after,
                'franchise_fee': p.franchise_fee,
                'e_and_o_fee': p.e_and_o_fee,
                'transaction_fee': p.transaction_fee,
                'is_active': p.is_active,
                'created_at': p.created_at.isoformat()
            }
            for p in self.plans.values()
        ]
        
        splits_data = [
            {
                'id': s.id,
                'transaction_id': s.transaction_id,
                'agent_id': s.agent_id,
                'plan_id': s.plan_id,
                'sale_price': s.sale_price,
                'gross_commission': s.gross_commission,
                'gross_commission_rate': s.gross_commission_rate,
                'brokerage_share': s.brokerage_share,
                'team_share': s.team_share,
                'agent_share': s.agent_share,
                'fees_deducted': s.fees_deducted,
                'net_to_agent': s.net_to_agent,
                'cap_applied': s.cap_applied,
                'calculated_at': s.calculated_at.isoformat()
            }
            for s in self.splits.values()
        ]
        
        with open(f"{self.storage_path}/commissions.json", 'w') as f:
            json.dump({
                'plans': plans_data,
                'splits': splits_data,
                'agent_ytd_paid': self.agent_ytd_paid
            }, f, indent=2)
    
    def _create_default_plans(self):
        """Create default commission plans if none exist."""
        if self.plans:
            return
        
        # Standard 70/30 split
        standard = CommissionPlan(
            id="plan_standard",
            name="Standard 70/30",
            commission_type=CommissionType.FLAT_PERCENTAGE,
            base_percentage=70,
            brokerage_split=30,
            transaction_fee=395
        )
        self.plans[standard.id] = standard
        
        # Tiered plan
        tiered = CommissionPlan(
            id="plan_tiered",
            name="Tiered Performance",
            commission_type=CommissionType.TIERED,
            tiers=[
                CommissionTier(0, 3000000, 70),
                CommissionTier(3000000, 6000000, 80),
                CommissionTier(6000000, float('inf'), 90)
            ],
            brokerage_split=0,  # Handled by tiers
            transaction_fee=395
        )
        self.plans[tiered.id] = tiered
        
        # Capped plan
        capped = CommissionPlan(
            id="plan_capped",
            name="Capped at $25K",
            commission_type=CommissionType.FLAT_PERCENTAGE,
            base_percentage=70,
            brokerage_split=30,
            cap_amount=25000,
            cap_percentage_after=95,
            transaction_fee=395
        )
        self.plans[capped.id] = capped
        
        self._save_data()
    
    def create_plan(
        self,
        name: str,
        commission_type: CommissionType,
        base_percentage: float = 0,
        **kwargs
    ) -> CommissionPlan:
        """Create a new commission plan."""
        plan = CommissionPlan(
            id=str(uuid.uuid4())[:12],
            name=name,
            commission_type=commission_type,
            base_percentage=base_percentage,
            tiers=kwargs.get('tiers', []),
            brokerage_split=kwargs.get('brokerage_split', 0),
            team_split=kwargs.get('team_split', 0),
            cap_amount=kwargs.get('cap_amount', 0),
            cap_percentage_after=kwargs.get('cap_percentage_after', 100),
            franchise_fee=kwargs.get('franchise_fee', 0),
            e_and_o_fee=kwargs.get('e_and_o_fee', 0),
            transaction_fee=kwargs.get('transaction_fee', 0)
        )
        self.plans[plan.id] = plan
        self._save_data()
        return plan
    
    def calculate_commission(
        self,
        agent_id: str,
        plan_id: str,
        sale_price: float,
        commission_rate: float,  # As decimal, e.g., 0.03 for 3%
        transaction_id: str = ""
    ) -> CommissionSplit:
        """Calculate commission split for a transaction."""
        plan = self.plans.get(plan_id)
        if not plan:
            raise ValueError(f"Commission plan {plan_id} not found")
        
        # Calculate gross commission
        gross_commission = sale_price * commission_rate
        
        # Get agent's YTD for cap calculation
        ytd_paid = self.agent_ytd_paid.get(agent_id, 0)
        
        # Determine agent percentage based on plan type
        if plan.commission_type == CommissionType.FLAT_PERCENTAGE:
            agent_percentage = plan.base_percentage
        elif plan.commission_type == CommissionType.TIERED:
            agent_percentage = self._get_tiered_percentage(plan, ytd_paid + gross_commission)
        else:
            agent_percentage = plan.base_percentage
        
        # Check cap
        cap_applied = False
        if plan.cap_amount > 0:
            brokerage_ytd = ytd_paid * (100 - plan.base_percentage) / 100
            if brokerage_ytd >= plan.cap_amount:
                agent_percentage = plan.cap_percentage_after
                cap_applied = True
        
        # Calculate splits
        brokerage_percentage = 100 - agent_percentage - plan.team_split
        
        agent_share = gross_commission * (agent_percentage / 100)
        team_share = gross_commission * (plan.team_split / 100)
        brokerage_share = gross_commission * (brokerage_percentage / 100)
        
        # Deduct fees
        total_fees = plan.franchise_fee + plan.e_and_o_fee + plan.transaction_fee
        net_to_agent = agent_share - total_fees
        
        split = CommissionSplit(
            id=str(uuid.uuid4())[:12],
            transaction_id=transaction_id or str(uuid.uuid4())[:12],
            agent_id=agent_id,
            plan_id=plan_id,
            sale_price=sale_price,
            gross_commission=round(gross_commission, 2),
            gross_commission_rate=commission_rate,
            brokerage_share=round(brokerage_share, 2),
            team_share=round(team_share, 2),
            agent_share=round(agent_share, 2),
            fees_deducted=round(total_fees, 2),
            net_to_agent=round(net_to_agent, 2),
            cap_applied=cap_applied
        )
        
        self.splits[split.id] = split
        
        # Update YTD
        self.agent_ytd_paid[agent_id] = ytd_paid + brokerage_share
        
        self._save_data()
        return split
    
    def _get_tiered_percentage(self, plan: CommissionPlan, volume: float) -> float:
        """Get percentage for tiered plan based on volume."""
        for tier in plan.tiers:
            if tier.min_volume <= volume <= tier.max_volume:
                return tier.percentage
        return plan.tiers[-1].percentage if plan.tiers else 70
    
    def get_agent_commission_summary(
        self,
        agent_id: str,
        year: int = None
    ) -> Dict:
        """Get commission summary for an agent."""
        year = year or datetime.now().year
        
        agent_splits = [
            s for s in self.splits.values()
            if s.agent_id == agent_id and s.calculated_at.year == year
        ]
        
        total_volume = sum(s.sale_price for s in agent_splits)
        total_gross = sum(s.gross_commission for s in agent_splits)
        total_agent = sum(s.agent_share for s in agent_splits)
        total_fees = sum(s.fees_deducted for s in agent_splits)
        total_net = sum(s.net_to_agent for s in agent_splits)
        
        return {
            'agent_id': agent_id,
            'year': year,
            'transactions': len(agent_splits),
            'total_volume': round(total_volume, 2),
            'total_gross_commission': round(total_gross, 2),
            'total_agent_share': round(total_agent, 2),
            'total_fees': round(total_fees, 2),
            'total_net_to_agent': round(total_net, 2),
            'avg_commission_per_transaction': round(total_net / len(agent_splits), 2) if agent_splits else 0,
            'effective_split': round(total_agent / total_gross * 100, 1) if total_gross else 0
        }
    
    def get_brokerage_commission_summary(self, year: int = None) -> Dict:
        """Get brokerage-wide commission summary."""
        year = year or datetime.now().year
        
        year_splits = [
            s for s in self.splits.values()
            if s.calculated_at.year == year
        ]
        
        total_volume = sum(s.sale_price for s in year_splits)
        total_gross = sum(s.gross_commission for s in year_splits)
        total_brokerage = sum(s.brokerage_share for s in year_splits)
        total_agent = sum(s.agent_share for s in year_splits)
        total_team = sum(s.team_share for s in year_splits)
        
        # By agent
        by_agent = {}
        for split in year_splits:
            if split.agent_id not in by_agent:
                by_agent[split.agent_id] = {
                    'transactions': 0,
                    'volume': 0,
                    'gross': 0,
                    'agent_share': 0
                }
            by_agent[split.agent_id]['transactions'] += 1
            by_agent[split.agent_id]['volume'] += split.sale_price
            by_agent[split.agent_id]['gross'] += split.gross_commission
            by_agent[split.agent_id]['agent_share'] += split.agent_share
        
        return {
            'year': year,
            'total_transactions': len(year_splits),
            'total_volume': round(total_volume, 2),
            'total_gross_commission': round(total_gross, 2),
            'brokerage_share': round(total_brokerage, 2),
            'agent_share': round(total_agent, 2),
            'team_share': round(total_team, 2),
            'by_agent': by_agent
        }
