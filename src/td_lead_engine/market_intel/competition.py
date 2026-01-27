"""Competitive analysis and market share tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os


@dataclass
class AgentMarketShare:
    """Market share data for an agent."""
    agent_name: str
    brokerage: str = ""
    total_transactions: int = 0
    total_volume: float = 0
    buyer_transactions: int = 0
    seller_transactions: int = 0
    avg_sale_price: float = 0
    avg_days_on_market: float = 0
    list_to_sale_ratio: float = 0
    market_share_pct: float = 0


@dataclass
class BrokerageMarketShare:
    """Market share data for a brokerage."""
    name: str
    total_transactions: int = 0
    total_volume: float = 0
    agent_count: int = 0
    market_share_pct: float = 0
    avg_price: float = 0


class CompetitiveAnalysis:
    """Analyze competition in the market."""
    
    def __init__(self, storage_path: str = "data/market_intel"):
        self.storage_path = storage_path
        self.transactions: List[Dict] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load transaction data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/transactions.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                self.transactions = json.load(f)
    
    def _save_data(self):
        """Save transaction data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        with open(f"{self.storage_path}/transactions.json", 'w') as f:
            json.dump(self.transactions[-50000:], f, indent=2)
    
    def add_transaction(
        self,
        address: str,
        sale_price: float,
        sale_date: datetime,
        listing_agent: str,
        listing_brokerage: str,
        buyer_agent: str,
        buyer_brokerage: str,
        **kwargs
    ):
        """Add a transaction."""
        transaction = {
            'address': address,
            'sale_price': sale_price,
            'sale_date': sale_date.isoformat(),
            'listing_agent': listing_agent,
            'listing_brokerage': listing_brokerage,
            'buyer_agent': buyer_agent,
            'buyer_brokerage': buyer_brokerage,
            'list_price': kwargs.get('list_price', sale_price),
            'days_on_market': kwargs.get('days_on_market', 0),
            'city': kwargs.get('city', ''),
            'zip_code': kwargs.get('zip_code', ''),
            'property_type': kwargs.get('property_type', 'single_family')
        }
        self.transactions.append(transaction)
        self._save_data()
    
    def get_agent_market_share(
        self,
        area: str = "",
        months: int = 12,
        limit: int = 25
    ) -> List[AgentMarketShare]:
        """Get market share by agent."""
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        transactions = [
            t for t in self.transactions
            if datetime.fromisoformat(t['sale_date']) >= cutoff
        ]
        
        if area:
            transactions = [
                t for t in transactions
                if t.get('city') == area or t.get('zip_code') == area
            ]
        
        total_volume = sum(t['sale_price'] for t in transactions)
        total_transactions = len(transactions)
        
        # Aggregate by agent
        agent_data = {}
        for t in transactions:
            # Listing agent
            listing_agent = t['listing_agent']
            if listing_agent not in agent_data:
                agent_data[listing_agent] = {
                    'name': listing_agent,
                    'brokerage': t['listing_brokerage'],
                    'transactions': 0,
                    'volume': 0,
                    'buyer_trans': 0,
                    'seller_trans': 0,
                    'days_on_market': [],
                    'list_to_sale': []
                }
            
            agent_data[listing_agent]['transactions'] += 1
            agent_data[listing_agent]['volume'] += t['sale_price']
            agent_data[listing_agent]['seller_trans'] += 1
            if t.get('days_on_market'):
                agent_data[listing_agent]['days_on_market'].append(t['days_on_market'])
            if t.get('list_price') and t['sale_price']:
                ratio = t['sale_price'] / t['list_price'] * 100
                agent_data[listing_agent]['list_to_sale'].append(ratio)
            
            # Buyer agent
            buyer_agent = t['buyer_agent']
            if buyer_agent and buyer_agent != listing_agent:
                if buyer_agent not in agent_data:
                    agent_data[buyer_agent] = {
                        'name': buyer_agent,
                        'brokerage': t['buyer_brokerage'],
                        'transactions': 0,
                        'volume': 0,
                        'buyer_trans': 0,
                        'seller_trans': 0,
                        'days_on_market': [],
                        'list_to_sale': []
                    }
                agent_data[buyer_agent]['transactions'] += 1
                agent_data[buyer_agent]['volume'] += t['sale_price']
                agent_data[buyer_agent]['buyer_trans'] += 1
        
        # Convert to AgentMarketShare objects
        agents = []
        for data in agent_data.values():
            import statistics
            
            agent = AgentMarketShare(
                agent_name=data['name'],
                brokerage=data['brokerage'],
                total_transactions=data['transactions'],
                total_volume=data['volume'],
                buyer_transactions=data['buyer_trans'],
                seller_transactions=data['seller_trans'],
                avg_sale_price=round(data['volume'] / data['transactions'], 0) if data['transactions'] else 0,
                avg_days_on_market=round(statistics.mean(data['days_on_market']), 1) if data['days_on_market'] else 0,
                list_to_sale_ratio=round(statistics.mean(data['list_to_sale']), 1) if data['list_to_sale'] else 0,
                market_share_pct=round(data['volume'] / total_volume * 100, 2) if total_volume else 0
            )
            agents.append(agent)
        
        # Sort by volume
        agents.sort(key=lambda a: a.total_volume, reverse=True)
        return agents[:limit]
    
    def get_brokerage_market_share(
        self,
        area: str = "",
        months: int = 12,
        limit: int = 15
    ) -> List[BrokerageMarketShare]:
        """Get market share by brokerage."""
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        transactions = [
            t for t in self.transactions
            if datetime.fromisoformat(t['sale_date']) >= cutoff
        ]
        
        if area:
            transactions = [
                t for t in transactions
                if t.get('city') == area or t.get('zip_code') == area
            ]
        
        total_volume = sum(t['sale_price'] for t in transactions)
        
        # Aggregate by brokerage
        brokerage_data = {}
        for t in transactions:
            for brokerage in [t['listing_brokerage'], t['buyer_brokerage']]:
                if not brokerage:
                    continue
                
                if brokerage not in brokerage_data:
                    brokerage_data[brokerage] = {
                        'name': brokerage,
                        'transactions': 0,
                        'volume': 0,
                        'agents': set()
                    }
                
                brokerage_data[brokerage]['transactions'] += 1
                brokerage_data[brokerage]['volume'] += t['sale_price'] / 2  # Split between listing and buyer side
                
                if brokerage == t['listing_brokerage']:
                    brokerage_data[brokerage]['agents'].add(t['listing_agent'])
                else:
                    brokerage_data[brokerage]['agents'].add(t['buyer_agent'])
        
        # Convert to BrokerageMarketShare objects
        brokerages = []
        for data in brokerage_data.values():
            brokerage = BrokerageMarketShare(
                name=data['name'],
                total_transactions=data['transactions'],
                total_volume=round(data['volume'], 0),
                agent_count=len(data['agents']),
                market_share_pct=round(data['volume'] / total_volume * 100, 2) if total_volume else 0,
                avg_price=round(data['volume'] / data['transactions'], 0) if data['transactions'] else 0
            )
            brokerages.append(brokerage)
        
        # Sort by volume
        brokerages.sort(key=lambda b: b.total_volume, reverse=True)
        return brokerages[:limit]
    
    def get_market_summary(
        self,
        area: str = "",
        months: int = 12
    ) -> Dict:
        """Get market summary."""
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        transactions = [
            t for t in self.transactions
            if datetime.fromisoformat(t['sale_date']) >= cutoff
        ]
        
        if area:
            transactions = [
                t for t in transactions
                if t.get('city') == area or t.get('zip_code') == area
            ]
        
        if not transactions:
            return {}
        
        import statistics
        
        prices = [t['sale_price'] for t in transactions]
        dom = [t['days_on_market'] for t in transactions if t.get('days_on_market')]
        
        # Top agents and brokerages
        top_agents = self.get_agent_market_share(area, months, 5)
        top_brokerages = self.get_brokerage_market_share(area, months, 5)
        
        return {
            'area': area or 'All Areas',
            'period_months': months,
            'summary': {
                'total_transactions': len(transactions),
                'total_volume': sum(prices),
                'median_price': statistics.median(prices),
                'avg_price': round(statistics.mean(prices), 0),
                'avg_days_on_market': round(statistics.mean(dom), 1) if dom else 0,
                'unique_listing_agents': len(set(t['listing_agent'] for t in transactions)),
                'unique_brokerages': len(set(t['listing_brokerage'] for t in transactions))
            },
            'top_agents': [
                {
                    'name': a.agent_name,
                    'brokerage': a.brokerage,
                    'transactions': a.total_transactions,
                    'volume': a.total_volume,
                    'market_share': a.market_share_pct
                }
                for a in top_agents
            ],
            'top_brokerages': [
                {
                    'name': b.name,
                    'transactions': b.total_transactions,
                    'volume': b.total_volume,
                    'market_share': b.market_share_pct
                }
                for b in top_brokerages
            ]
        }
    
    def compare_to_competition(
        self,
        agent_name: str,
        area: str = "",
        months: int = 12
    ) -> Dict:
        """Compare agent to competition."""
        all_agents = self.get_agent_market_share(area, months, 100)
        
        # Find the agent
        target = None
        rank = 0
        for i, agent in enumerate(all_agents):
            if agent.agent_name.lower() == agent_name.lower():
                target = agent
                rank = i + 1
                break
        
        if not target:
            return {'error': 'Agent not found'}
        
        # Calculate averages
        avg_transactions = statistics.mean([a.total_transactions for a in all_agents]) if all_agents else 0
        avg_volume = statistics.mean([a.total_volume for a in all_agents]) if all_agents else 0
        avg_dom = statistics.mean([a.avg_days_on_market for a in all_agents if a.avg_days_on_market > 0]) if all_agents else 0
        
        return {
            'agent': agent_name,
            'rank': rank,
            'total_agents': len(all_agents),
            'performance': {
                'transactions': target.total_transactions,
                'vs_avg': round((target.total_transactions / avg_transactions - 1) * 100, 1) if avg_transactions else 0,
                'volume': target.total_volume,
                'volume_vs_avg': round((target.total_volume / avg_volume - 1) * 100, 1) if avg_volume else 0,
                'market_share': target.market_share_pct,
                'avg_days_on_market': target.avg_days_on_market,
                'dom_vs_avg': round(avg_dom - target.avg_days_on_market, 1) if avg_dom else 0,
                'list_to_sale_ratio': target.list_to_sale_ratio
            },
            'strengths': self._identify_strengths(target, all_agents),
            'opportunities': self._identify_opportunities(target, all_agents)
        }
    
    def _identify_strengths(self, agent: AgentMarketShare, all_agents: List[AgentMarketShare]) -> List[str]:
        """Identify agent's competitive strengths."""
        import statistics
        strengths = []
        
        avg_trans = statistics.mean([a.total_transactions for a in all_agents]) if all_agents else 0
        if agent.total_transactions > avg_trans * 1.5:
            strengths.append("High transaction volume")
        
        avg_dom = statistics.mean([a.avg_days_on_market for a in all_agents if a.avg_days_on_market > 0]) if all_agents else 0
        if agent.avg_days_on_market > 0 and agent.avg_days_on_market < avg_dom * 0.8:
            strengths.append("Properties sell faster than average")
        
        if agent.list_to_sale_ratio > 99:
            strengths.append("Strong negotiation (high list-to-sale ratio)")
        
        if agent.seller_transactions > agent.buyer_transactions * 2:
            strengths.append("Strong listing agent")
        elif agent.buyer_transactions > agent.seller_transactions * 2:
            strengths.append("Strong buyer's agent")
        
        return strengths
    
    def _identify_opportunities(self, agent: AgentMarketShare, all_agents: List[AgentMarketShare]) -> List[str]:
        """Identify opportunities for improvement."""
        import statistics
        opportunities = []
        
        avg_trans = statistics.mean([a.total_transactions for a in all_agents]) if all_agents else 0
        if agent.total_transactions < avg_trans:
            opportunities.append("Increase transaction volume")
        
        if agent.seller_transactions < agent.buyer_transactions:
            opportunities.append("Focus on gaining more listings")
        
        avg_dom = statistics.mean([a.avg_days_on_market for a in all_agents if a.avg_days_on_market > 0]) if all_agents else 0
        if agent.avg_days_on_market > avg_dom:
            opportunities.append("Reduce days on market through pricing strategy")
        
        if agent.list_to_sale_ratio < 98:
            opportunities.append("Improve list-to-sale ratio")
        
        return opportunities
