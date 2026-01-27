"""Marketing campaign analytics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import statistics


class CampaignType(Enum):
    """Marketing campaign types."""
    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    PPC = "ppc"
    DIRECT_MAIL = "direct_mail"
    EVENTS = "events"
    CONTENT = "content"
    REFERRAL = "referral"


class CampaignStatus(Enum):
    """Campaign status."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Campaign:
    """A marketing campaign."""
    id: str
    name: str
    campaign_type: CampaignType
    status: CampaignStatus = CampaignStatus.DRAFT
    budget: float = 0
    spent: float = 0
    start_date: datetime = None
    end_date: datetime = None
    target_audience: str = ""
    goals: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CampaignMetrics:
    """Metrics for a campaign."""
    campaign_id: str
    impressions: int = 0
    clicks: int = 0
    leads: int = 0
    conversions: int = 0
    revenue: float = 0
    ctr: float = 0
    conversion_rate: float = 0
    cost_per_lead: float = 0
    cost_per_conversion: float = 0
    roi: float = 0


class MarketingAnalytics:
    """Marketing campaign analytics and tracking."""
    
    def __init__(self, storage_path: str = "data/reporting"):
        self.storage_path = storage_path
        self.campaigns: Dict[str, Campaign] = {}
        self.events: List[Dict] = []  # Campaign events (impressions, clicks, etc.)
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/marketing_analytics.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for c in data.get('campaigns', []):
                    campaign = Campaign(
                        id=c['id'],
                        name=c['name'],
                        campaign_type=CampaignType(c['campaign_type']),
                        status=CampaignStatus(c['status']),
                        budget=c.get('budget', 0),
                        spent=c.get('spent', 0),
                        start_date=datetime.fromisoformat(c['start_date']) if c.get('start_date') else None,
                        end_date=datetime.fromisoformat(c['end_date']) if c.get('end_date') else None,
                        target_audience=c.get('target_audience', ''),
                        goals=c.get('goals', {}),
                        created_at=datetime.fromisoformat(c['created_at'])
                    )
                    self.campaigns[campaign.id] = campaign
                
                self.events = data.get('events', [])
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        campaigns_data = [
            {
                'id': c.id,
                'name': c.name,
                'campaign_type': c.campaign_type.value,
                'status': c.status.value,
                'budget': c.budget,
                'spent': c.spent,
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
                'target_audience': c.target_audience,
                'goals': c.goals,
                'created_at': c.created_at.isoformat()
            }
            for c in self.campaigns.values()
        ]
        
        with open(f"{self.storage_path}/marketing_analytics.json", 'w') as f:
            json.dump({
                'campaigns': campaigns_data,
                'events': self.events[-50000:]  # Keep last 50k events
            }, f, indent=2)
    
    def create_campaign(
        self,
        campaign_id: str,
        name: str,
        campaign_type: CampaignType,
        budget: float = 0,
        start_date: datetime = None,
        end_date: datetime = None,
        target_audience: str = "",
        goals: Dict = None
    ) -> Campaign:
        """Create a new campaign."""
        campaign = Campaign(
            id=campaign_id,
            name=name,
            campaign_type=campaign_type,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
            target_audience=target_audience,
            goals=goals or {}
        )
        self.campaigns[campaign_id] = campaign
        self._save_data()
        return campaign
    
    def update_campaign_status(self, campaign_id: str, status: CampaignStatus):
        """Update campaign status."""
        campaign = self.campaigns.get(campaign_id)
        if campaign:
            campaign.status = status
            self._save_data()
    
    def record_impression(self, campaign_id: str, count: int = 1, metadata: Dict = None):
        """Record impressions."""
        self.events.append({
            'campaign_id': campaign_id,
            'type': 'impression',
            'count': count,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        self._save_data()
    
    def record_click(self, campaign_id: str, metadata: Dict = None):
        """Record a click."""
        self.events.append({
            'campaign_id': campaign_id,
            'type': 'click',
            'count': 1,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        self._save_data()
    
    def record_lead(self, campaign_id: str, lead_id: str, metadata: Dict = None):
        """Record a lead from a campaign."""
        self.events.append({
            'campaign_id': campaign_id,
            'type': 'lead',
            'lead_id': lead_id,
            'count': 1,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        self._save_data()
    
    def record_conversion(self, campaign_id: str, lead_id: str, revenue: float = 0, metadata: Dict = None):
        """Record a conversion from a campaign."""
        self.events.append({
            'campaign_id': campaign_id,
            'type': 'conversion',
            'lead_id': lead_id,
            'revenue': revenue,
            'count': 1,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        })
        self._save_data()
    
    def record_spend(self, campaign_id: str, amount: float):
        """Record campaign spend."""
        campaign = self.campaigns.get(campaign_id)
        if campaign:
            campaign.spent += amount
            self._save_data()
    
    def get_campaign_metrics(
        self,
        campaign_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Optional[CampaignMetrics]:
        """Get metrics for a campaign."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return None
        
        start = start_date or campaign.start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        # Filter events
        events = [
            e for e in self.events
            if e['campaign_id'] == campaign_id
            and start <= datetime.fromisoformat(e['timestamp']) <= end
        ]
        
        impressions = sum(e['count'] for e in events if e['type'] == 'impression')
        clicks = sum(e['count'] for e in events if e['type'] == 'click')
        leads = sum(e['count'] for e in events if e['type'] == 'lead')
        conversions = sum(e['count'] for e in events if e['type'] == 'conversion')
        revenue = sum(e.get('revenue', 0) for e in events if e['type'] == 'conversion')
        
        spent = campaign.spent
        
        return CampaignMetrics(
            campaign_id=campaign_id,
            impressions=impressions,
            clicks=clicks,
            leads=leads,
            conversions=conversions,
            revenue=revenue,
            ctr=round(clicks / impressions * 100, 2) if impressions else 0,
            conversion_rate=round(conversions / leads * 100, 2) if leads else 0,
            cost_per_lead=round(spent / leads, 2) if leads else 0,
            cost_per_conversion=round(spent / conversions, 2) if conversions else 0,
            roi=round((revenue - spent) / spent * 100, 2) if spent else 0
        )
    
    def get_all_campaign_metrics(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        campaign_type: CampaignType = None
    ) -> List[CampaignMetrics]:
        """Get metrics for all campaigns."""
        campaigns = self.campaigns.values()
        
        if campaign_type:
            campaigns = [c for c in campaigns if c.campaign_type == campaign_type]
        
        return [
            self.get_campaign_metrics(c.id, start_date, end_date)
            for c in campaigns
            if self.get_campaign_metrics(c.id, start_date, end_date)
        ]
    
    def get_marketing_summary(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Get overall marketing summary."""
        metrics = self.get_all_campaign_metrics(start_date, end_date)
        
        total_spent = sum(self.campaigns[m.campaign_id].spent for m in metrics)
        total_impressions = sum(m.impressions for m in metrics)
        total_clicks = sum(m.clicks for m in metrics)
        total_leads = sum(m.leads for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        total_revenue = sum(m.revenue for m in metrics)
        
        # By campaign type
        by_type = {}
        for ctype in CampaignType:
            type_metrics = [m for m in metrics if self.campaigns[m.campaign_id].campaign_type == ctype]
            if type_metrics:
                by_type[ctype.value] = {
                    'campaigns': len(type_metrics),
                    'leads': sum(m.leads for m in type_metrics),
                    'conversions': sum(m.conversions for m in type_metrics),
                    'revenue': sum(m.revenue for m in type_metrics),
                    'spent': sum(self.campaigns[m.campaign_id].spent for m in type_metrics)
                }
        
        return {
            'summary': {
                'total_campaigns': len(metrics),
                'total_spent': total_spent,
                'total_impressions': total_impressions,
                'total_clicks': total_clicks,
                'total_leads': total_leads,
                'total_conversions': total_conversions,
                'total_revenue': total_revenue,
                'overall_ctr': round(total_clicks / total_impressions * 100, 2) if total_impressions else 0,
                'overall_conversion_rate': round(total_conversions / total_leads * 100, 2) if total_leads else 0,
                'overall_cpl': round(total_spent / total_leads, 2) if total_leads else 0,
                'overall_roi': round((total_revenue - total_spent) / total_spent * 100, 2) if total_spent else 0
            },
            'by_type': by_type,
            'top_performers': sorted(
                [
                    {
                        'campaign_id': m.campaign_id,
                        'name': self.campaigns[m.campaign_id].name,
                        'type': self.campaigns[m.campaign_id].campaign_type.value,
                        'leads': m.leads,
                        'conversions': m.conversions,
                        'roi': m.roi
                    }
                    for m in metrics
                ],
                key=lambda x: x['roi'],
                reverse=True
            )[:10]
        }
    
    def get_channel_comparison(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Compare performance across marketing channels."""
        comparison = []
        
        for ctype in CampaignType:
            type_metrics = self.get_all_campaign_metrics(start_date, end_date, ctype)
            
            if type_metrics:
                total_spent = sum(self.campaigns[m.campaign_id].spent for m in type_metrics)
                total_leads = sum(m.leads for m in type_metrics)
                total_conversions = sum(m.conversions for m in type_metrics)
                total_revenue = sum(m.revenue for m in type_metrics)
                
                comparison.append({
                    'channel': ctype.value,
                    'campaigns': len(type_metrics),
                    'spent': total_spent,
                    'leads': total_leads,
                    'conversions': total_conversions,
                    'revenue': total_revenue,
                    'cpl': round(total_spent / total_leads, 2) if total_leads else 0,
                    'cpc': round(total_spent / total_conversions, 2) if total_conversions else 0,
                    'roi': round((total_revenue - total_spent) / total_spent * 100, 2) if total_spent else 0
                })
        
        # Sort by ROI
        comparison.sort(key=lambda x: x['roi'], reverse=True)
        
        return {
            'channels': comparison,
            'best_roi': comparison[0] if comparison else None,
            'best_cpl': min(comparison, key=lambda x: x['cpl']) if comparison else None,
            'most_leads': max(comparison, key=lambda x: x['leads']) if comparison else None
        }
