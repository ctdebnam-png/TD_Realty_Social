"""Facebook/Meta Ads integration for lead tracking."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import uuid
import hashlib


class FBCampaignObjective(Enum):
    """Facebook campaign objectives."""
    LEAD_GENERATION = "lead_generation"
    TRAFFIC = "traffic"
    CONVERSIONS = "conversions"
    MESSAGES = "messages"
    ENGAGEMENT = "engagement"
    VIDEO_VIEWS = "video_views"
    BRAND_AWARENESS = "brand_awareness"


class FBLeadStatus(Enum):
    """Lead form submission status."""
    NEW = "new"
    IMPORTED = "imported"
    PROCESSED = "processed"
    INVALID = "invalid"


@dataclass
class FacebookCampaign:
    """A Facebook Ads campaign."""
    id: str
    fb_campaign_id: str
    name: str
    objective: FBCampaignObjective
    status: str = "active"
    budget_daily: float = 0
    budget_lifetime: float = 0
    audience_name: str = ""
    audience_size: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FacebookLeadForm:
    """A Facebook Lead Form."""
    id: str
    fb_form_id: str
    campaign_id: str
    name: str
    questions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FacebookLead:
    """A lead from Facebook Lead Ads."""
    id: str
    fb_lead_id: str
    form_id: str
    campaign_id: str
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    field_data: Dict = field(default_factory=dict)
    ad_id: str = ""
    ad_name: str = ""
    adset_id: str = ""
    adset_name: str = ""
    status: FBLeadStatus = FBLeadStatus.NEW
    created_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime = None


class FacebookAdsIntegration:
    """Integration with Facebook/Meta Ads."""
    
    def __init__(
        self,
        access_token: str = None,
        app_secret: str = None,
        page_id: str = None,
        storage_path: str = "data/integrations/facebook_ads"
    ):
        self.access_token = access_token or os.getenv("FB_ACCESS_TOKEN", "")
        self.app_secret = app_secret or os.getenv("FB_APP_SECRET", "")
        self.page_id = page_id or os.getenv("FB_PAGE_ID", "")
        self.storage_path = storage_path
        
        self.campaigns: Dict[str, FacebookCampaign] = {}
        self.forms: Dict[str, FacebookLeadForm] = {}
        self.leads: Dict[str, FacebookLead] = {}
        self.callbacks: List[Callable] = []
        
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
                    campaign = FacebookCampaign(
                        id=c['id'],
                        fb_campaign_id=c['fb_campaign_id'],
                        name=c['name'],
                        objective=FBCampaignObjective(c['objective']),
                        status=c.get('status', 'active'),
                        budget_daily=c.get('budget_daily', 0),
                        budget_lifetime=c.get('budget_lifetime', 0),
                        audience_name=c.get('audience_name', ''),
                        audience_size=c.get('audience_size', 0),
                        created_at=datetime.fromisoformat(c['created_at'])
                    )
                    self.campaigns[campaign.id] = campaign
        
        # Load forms
        forms_file = f"{self.storage_path}/forms.json"
        if os.path.exists(forms_file):
            with open(forms_file, 'r') as f:
                data = json.load(f)
                for form_data in data:
                    form = FacebookLeadForm(
                        id=form_data['id'],
                        fb_form_id=form_data['fb_form_id'],
                        campaign_id=form_data['campaign_id'],
                        name=form_data['name'],
                        questions=form_data.get('questions', []),
                        created_at=datetime.fromisoformat(form_data['created_at'])
                    )
                    self.forms[form.id] = form
        
        # Load leads
        leads_file = f"{self.storage_path}/leads.json"
        if os.path.exists(leads_file):
            with open(leads_file, 'r') as f:
                data = json.load(f)
                for l in data:
                    lead = FacebookLead(
                        id=l['id'],
                        fb_lead_id=l['fb_lead_id'],
                        form_id=l['form_id'],
                        campaign_id=l['campaign_id'],
                        first_name=l['first_name'],
                        last_name=l['last_name'],
                        email=l['email'],
                        phone=l.get('phone', ''),
                        field_data=l.get('field_data', {}),
                        ad_id=l.get('ad_id', ''),
                        ad_name=l.get('ad_name', ''),
                        adset_id=l.get('adset_id', ''),
                        adset_name=l.get('adset_name', ''),
                        status=FBLeadStatus(l['status']),
                        created_at=datetime.fromisoformat(l['created_at']),
                        processed_at=datetime.fromisoformat(l['processed_at']) if l.get('processed_at') else None
                    )
                    self.leads[lead.id] = lead
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save campaigns
        campaigns_data = [
            {
                'id': c.id,
                'fb_campaign_id': c.fb_campaign_id,
                'name': c.name,
                'objective': c.objective.value,
                'status': c.status,
                'budget_daily': c.budget_daily,
                'budget_lifetime': c.budget_lifetime,
                'audience_name': c.audience_name,
                'audience_size': c.audience_size,
                'created_at': c.created_at.isoformat()
            }
            for c in self.campaigns.values()
        ]
        
        with open(f"{self.storage_path}/campaigns.json", 'w') as f:
            json.dump(campaigns_data, f, indent=2)
        
        # Save forms
        forms_data = [
            {
                'id': f.id,
                'fb_form_id': f.fb_form_id,
                'campaign_id': f.campaign_id,
                'name': f.name,
                'questions': f.questions,
                'created_at': f.created_at.isoformat()
            }
            for f in self.forms.values()
        ]
        
        with open(f"{self.storage_path}/forms.json", 'w') as f:
            json.dump(forms_data, f, indent=2)
        
        # Save leads
        leads_data = [
            {
                'id': l.id,
                'fb_lead_id': l.fb_lead_id,
                'form_id': l.form_id,
                'campaign_id': l.campaign_id,
                'first_name': l.first_name,
                'last_name': l.last_name,
                'email': l.email,
                'phone': l.phone,
                'field_data': l.field_data,
                'ad_id': l.ad_id,
                'ad_name': l.ad_name,
                'adset_id': l.adset_id,
                'adset_name': l.adset_name,
                'status': l.status.value,
                'created_at': l.created_at.isoformat(),
                'processed_at': l.processed_at.isoformat() if l.processed_at else None
            }
            for l in self.leads.values()
        ]
        
        with open(f"{self.storage_path}/leads.json", 'w') as f:
            json.dump(leads_data, f, indent=2)
    
    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify Facebook webhook signature."""
        if not self.app_secret:
            return False
        
        expected = 'sha256=' + hashlib.sha256(
            (self.app_secret + payload).encode()
        ).hexdigest()
        
        return expected == signature
    
    def track_campaign(
        self,
        fb_campaign_id: str,
        name: str,
        objective: FBCampaignObjective,
        **kwargs
    ) -> FacebookCampaign:
        """Track a Facebook campaign."""
        campaign = FacebookCampaign(
            id=str(uuid.uuid4())[:12],
            fb_campaign_id=fb_campaign_id,
            name=name,
            objective=objective,
            budget_daily=kwargs.get('budget_daily', 0),
            budget_lifetime=kwargs.get('budget_lifetime', 0),
            audience_name=kwargs.get('audience_name', ''),
            audience_size=kwargs.get('audience_size', 0)
        )
        self.campaigns[campaign.id] = campaign
        self._save_data()
        return campaign
    
    def track_form(self, fb_form_id: str, campaign_id: str, name: str, questions: List[str] = None) -> FacebookLeadForm:
        """Track a lead form."""
        form = FacebookLeadForm(
            id=str(uuid.uuid4())[:12],
            fb_form_id=fb_form_id,
            campaign_id=campaign_id,
            name=name,
            questions=questions or []
        )
        self.forms[form.id] = form
        self._save_data()
        return form
    
    def process_lead_webhook(self, payload: Dict) -> Optional[FacebookLead]:
        """Process incoming lead webhook from Facebook."""
        fb_lead_id = payload.get('leadgen_id', payload.get('id', ''))
        
        # Check for duplicate
        for lead in self.leads.values():
            if lead.fb_lead_id == fb_lead_id:
                return None
        
        # Extract field data
        field_data = {}
        for field_item in payload.get('field_data', []):
            field_name = field_item.get('name', '')
            field_value = field_item.get('values', [''])[0] if field_item.get('values') else ''
            field_data[field_name] = field_value
        
        # Get form and campaign
        form_id = payload.get('form_id', '')
        form = None
        campaign_id = ''
        for f in self.forms.values():
            if f.fb_form_id == form_id:
                form = f
                campaign_id = f.campaign_id
                break
        
        lead = FacebookLead(
            id=str(uuid.uuid4())[:12],
            fb_lead_id=fb_lead_id,
            form_id=form.id if form else '',
            campaign_id=campaign_id,
            first_name=field_data.get('first_name', payload.get('first_name', '')),
            last_name=field_data.get('last_name', payload.get('last_name', '')),
            email=field_data.get('email', payload.get('email', '')),
            phone=field_data.get('phone_number', field_data.get('phone', payload.get('phone', ''))),
            field_data=field_data,
            ad_id=payload.get('ad_id', ''),
            ad_name=payload.get('ad_name', ''),
            adset_id=payload.get('adset_id', ''),
            adset_name=payload.get('adset_name', ''),
            status=FBLeadStatus.IMPORTED
        )
        
        self.leads[lead.id] = lead
        self._save_data()
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(lead)
            except Exception:
                pass
        
        return lead
    
    def on_lead_received(self, callback: Callable[[FacebookLead], None]):
        """Register callback for new leads."""
        self.callbacks.append(callback)
    
    def convert_to_crm_lead(self, fb_lead: FacebookLead) -> Dict:
        """Convert to CRM lead format."""
        campaign = self.campaigns.get(fb_lead.campaign_id)
        form = self.forms.get(fb_lead.form_id)
        
        return {
            'first_name': fb_lead.first_name,
            'last_name': fb_lead.last_name,
            'email': fb_lead.email,
            'phone': fb_lead.phone,
            'source': 'facebook',
            'source_detail': f"Facebook Lead Ad - {campaign.name if campaign else 'Unknown Campaign'}",
            'lead_type': 'buyer',
            'notes': f"Form: {form.name if form else 'Unknown'}\nAd: {fb_lead.ad_name}",
            'custom_fields': {
                'fb_lead_id': fb_lead.fb_lead_id,
                'fb_campaign_id': fb_lead.campaign_id,
                'fb_ad_id': fb_lead.ad_id,
                'fb_adset_id': fb_lead.adset_id,
                'fb_field_data': fb_lead.field_data
            }
        }
    
    def mark_processed(self, lead_id: str):
        """Mark lead as processed."""
        lead = self.leads.get(lead_id)
        if lead:
            lead.status = FBLeadStatus.PROCESSED
            lead.processed_at = datetime.now()
            self._save_data()
    
    def get_unprocessed_leads(self) -> List[FacebookLead]:
        """Get unprocessed leads."""
        return [l for l in self.leads.values() if l.status == FBLeadStatus.IMPORTED]
    
    def get_campaign_leads(self, campaign_id: str) -> List[FacebookLead]:
        """Get leads for a campaign."""
        return [l for l in self.leads.values() if l.campaign_id == campaign_id]
    
    def get_campaign_stats(self, campaign_id: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get campaign statistics."""
        campaign = self.campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        leads = [
            l for l in self.leads.values()
            if l.campaign_id == campaign_id
            and start <= l.created_at <= end
        ]
        
        processed = [l for l in leads if l.status == FBLeadStatus.PROCESSED]
        
        # By ad
        by_ad = {}
        for lead in leads:
            ad_name = lead.ad_name or 'Unknown'
            if ad_name not in by_ad:
                by_ad[ad_name] = 0
            by_ad[ad_name] += 1
        
        return {
            'campaign_id': campaign_id,
            'campaign_name': campaign.name,
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'total_leads': len(leads),
            'processed': len(processed),
            'by_ad': by_ad
        }
    
    def get_all_stats(self) -> Dict:
        """Get overall Facebook Ads stats."""
        total_leads = len(self.leads)
        processed = len([l for l in self.leads.values() if l.status == FBLeadStatus.PROCESSED])
        
        by_campaign = {}
        for campaign in self.campaigns.values():
            leads = self.get_campaign_leads(campaign.id)
            by_campaign[campaign.name] = len(leads)
        
        return {
            'total_campaigns': len(self.campaigns),
            'total_forms': len(self.forms),
            'total_leads': total_leads,
            'processed': processed,
            'process_rate': (processed / total_leads * 100) if total_leads else 0,
            'by_campaign': by_campaign
        }
