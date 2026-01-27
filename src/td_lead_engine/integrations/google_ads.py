"""Google Ads integration for lead tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid


class CampaignType(Enum):
    """Google Ads campaign types."""
    SEARCH = "search"
    DISPLAY = "display"
    VIDEO = "video"
    SHOPPING = "shopping"
    PERFORMANCE_MAX = "performance_max"
    LOCAL = "local"


class ConversionType(Enum):
    """Conversion types to track."""
    LEAD_FORM = "lead_form"
    PHONE_CALL = "phone_call"
    WEBSITE_VISIT = "website_visit"
    PROPERTY_VIEW = "property_view"
    SCHEDULE_SHOWING = "schedule_showing"
    CONTACT_AGENT = "contact_agent"


@dataclass
class GoogleAdsCampaign:
    """A Google Ads campaign."""
    id: str
    google_campaign_id: str
    name: str
    campaign_type: CampaignType
    status: str = "active"
    budget_daily: float = 0
    budget_total: float = 0
    start_date: datetime = None
    end_date: datetime = None
    target_locations: List[str] = field(default_factory=list)
    target_keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class GoogleAdsConversion:
    """A conversion from Google Ads."""
    id: str
    campaign_id: str
    conversion_type: ConversionType
    gclid: str  # Google Click ID
    lead_id: str = ""
    value: float = 0
    conversion_time: datetime = field(default_factory=datetime.now)
    device: str = ""
    location: str = ""


@dataclass
class CampaignMetrics:
    """Metrics for a campaign."""
    campaign_id: str
    date: datetime
    impressions: int = 0
    clicks: int = 0
    cost: float = 0
    conversions: int = 0
    conversion_value: float = 0
    ctr: float = 0
    cpc: float = 0
    cpa: float = 0
    roas: float = 0


class GoogleAdsIntegration:
    """Integration with Google Ads."""
    
    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        refresh_token: str = None,
        customer_id: str = None,
        storage_path: str = "data/integrations/google_ads"
    ):
        self.client_id = client_id or os.getenv("GOOGLE_ADS_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
        self.refresh_token = refresh_token or os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
        self.customer_id = customer_id or os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
        self.storage_path = storage_path
        
        self.campaigns: Dict[str, GoogleAdsCampaign] = {}
        self.conversions: Dict[str, GoogleAdsConversion] = {}
        self.metrics: List[CampaignMetrics] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load campaigns
        campaigns_file = f"{self.storage_path}/campaigns.json"
        if os.path.exists(campaigns_file):
            with open(campaigns_file, 'r') as f:
                data = json.load(f)
                for c in data:
                    campaign = GoogleAdsCampaign(
                        id=c['id'],
                        google_campaign_id=c['google_campaign_id'],
                        name=c['name'],
                        campaign_type=CampaignType(c['campaign_type']),
                        status=c.get('status', 'active'),
                        budget_daily=c.get('budget_daily', 0),
                        budget_total=c.get('budget_total', 0),
                        start_date=datetime.fromisoformat(c['start_date']) if c.get('start_date') else None,
                        end_date=datetime.fromisoformat(c['end_date']) if c.get('end_date') else None,
                        target_locations=c.get('target_locations', []),
                        target_keywords=c.get('target_keywords', []),
                        created_at=datetime.fromisoformat(c['created_at'])
                    )
                    self.campaigns[campaign.id] = campaign
        
        # Load conversions
        conversions_file = f"{self.storage_path}/conversions.json"
        if os.path.exists(conversions_file):
            with open(conversions_file, 'r') as f:
                data = json.load(f)
                for c in data:
                    conversion = GoogleAdsConversion(
                        id=c['id'],
                        campaign_id=c['campaign_id'],
                        conversion_type=ConversionType(c['conversion_type']),
                        gclid=c['gclid'],
                        lead_id=c.get('lead_id', ''),
                        value=c.get('value', 0),
                        conversion_time=datetime.fromisoformat(c['conversion_time']),
                        device=c.get('device', ''),
                        location=c.get('location', '')
                    )
                    self.conversions[conversion.id] = conversion
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save campaigns
        campaigns_data = [
            {
                'id': c.id,
                'google_campaign_id': c.google_campaign_id,
                'name': c.name,
                'campaign_type': c.campaign_type.value,
                'status': c.status,
                'budget_daily': c.budget_daily,
                'budget_total': c.budget_total,
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
                'target_locations': c.target_locations,
                'target_keywords': c.target_keywords,
                'created_at': c.created_at.isoformat()
            }
            for c in self.campaigns.values()
        ]
        
        with open(f"{self.storage_path}/campaigns.json", 'w') as f:
            json.dump(campaigns_data, f, indent=2)
        
        # Save conversions
        conversions_data = [
            {
                'id': c.id,
                'campaign_id': c.campaign_id,
                'conversion_type': c.conversion_type.value,
                'gclid': c.gclid,
                'lead_id': c.lead_id,
                'value': c.value,
                'conversion_time': c.conversion_time.isoformat(),
                'device': c.device,
                'location': c.location
            }
            for c in self.conversions.values()
        ]
        
        with open(f"{self.storage_path}/conversions.json", 'w') as f:
            json.dump(conversions_data, f, indent=2)
    
    def track_campaign(self, google_campaign_id: str, name: str, campaign_type: CampaignType, **kwargs) -> GoogleAdsCampaign:
        """Track a Google Ads campaign."""
        campaign = GoogleAdsCampaign(
            id=str(uuid.uuid4())[:12],
            google_campaign_id=google_campaign_id,
            name=name,
            campaign_type=campaign_type,
            budget_daily=kwargs.get('budget_daily', 0),
            budget_total=kwargs.get('budget_total', 0),
            start_date=kwargs.get('start_date'),
            end_date=kwargs.get('end_date'),
            target_locations=kwargs.get('target_locations', []),
            target_keywords=kwargs.get('target_keywords', [])
        )
        self.campaigns[campaign.id] = campaign
        self._save_data()
        return campaign
    
    def record_conversion(
        self,
        campaign_id: str,
        conversion_type: ConversionType,
        gclid: str,
        lead_id: str = "",
        value: float = 0,
        device: str = "",
        location: str = ""
    ) -> GoogleAdsConversion:
        """Record a conversion from Google Ads."""
        conversion = GoogleAdsConversion(
            id=str(uuid.uuid4())[:12],
            campaign_id=campaign_id,
            conversion_type=conversion_type,
            gclid=gclid,
            lead_id=lead_id,
            value=value,
            device=device,
            location=location
        )
        self.conversions[conversion.id] = conversion
        self._save_data()
        return conversion
    
    def link_lead_to_conversion(self, lead_id: str, gclid: str) -> Optional[GoogleAdsConversion]:
        """Link a lead to a conversion by GCLID."""
        for conversion in self.conversions.values():
            if conversion.gclid == gclid:
                conversion.lead_id = lead_id
                self._save_data()
                return conversion
        return None
    
    def get_campaign_conversions(self, campaign_id: str) -> List[GoogleAdsConversion]:
        """Get conversions for a campaign."""
        return [c for c in self.conversions.values() if c.campaign_id == campaign_id]
    
    def calculate_campaign_metrics(
        self,
        campaign_id: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Calculate campaign performance metrics."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        conversions = [
            c for c in self.conversions.values()
            if c.campaign_id == campaign_id
            and start <= c.conversion_time <= end
        ]
        
        total_conversions = len(conversions)
        total_value = sum(c.value for c in conversions)
        
        # By conversion type
        by_type = {}
        for ct in ConversionType:
            type_conversions = [c for c in conversions if c.conversion_type == ct]
            by_type[ct.value] = {
                'count': len(type_conversions),
                'value': sum(c.value for c in type_conversions)
            }
        
        # By device
        by_device = {}
        for conversion in conversions:
            device = conversion.device or 'unknown'
            if device not in by_device:
                by_device[device] = {'count': 0, 'value': 0}
            by_device[device]['count'] += 1
            by_device[device]['value'] += conversion.value
        
        return {
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'summary': {
                'total_conversions': total_conversions,
                'total_value': total_value,
                'avg_value': total_value / total_conversions if total_conversions else 0
            },
            'by_type': by_type,
            'by_device': by_device
        }
    
    def get_lead_attribution(self, lead_id: str) -> Optional[Dict]:
        """Get Google Ads attribution for a lead."""
        for conversion in self.conversions.values():
            if conversion.lead_id == lead_id:
                campaign = self.campaigns.get(conversion.campaign_id)
                return {
                    'campaign_id': conversion.campaign_id,
                    'campaign_name': campaign.name if campaign else 'Unknown',
                    'campaign_type': campaign.campaign_type.value if campaign else 'unknown',
                    'conversion_type': conversion.conversion_type.value,
                    'gclid': conversion.gclid,
                    'conversion_time': conversion.conversion_time.isoformat(),
                    'device': conversion.device,
                    'location': conversion.location
                }
        return None
    
    def get_all_campaign_stats(self) -> List[Dict]:
        """Get stats for all campaigns."""
        stats = []
        for campaign in self.campaigns.values():
            conversions = self.get_campaign_conversions(campaign.id)
            stats.append({
                'campaign_id': campaign.id,
                'google_campaign_id': campaign.google_campaign_id,
                'name': campaign.name,
                'type': campaign.campaign_type.value,
                'status': campaign.status,
                'total_conversions': len(conversions),
                'total_value': sum(c.value for c in conversions),
                'budget_daily': campaign.budget_daily
            })
        return stats
