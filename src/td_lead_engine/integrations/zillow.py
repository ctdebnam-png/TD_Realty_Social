"""Zillow lead integration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
import os
import uuid
import hashlib
import hmac


class ZillowLeadType(Enum):
    """Types of Zillow leads."""
    BUYER = "buyer"
    SELLER = "seller"
    RENTER = "renter"
    BRAND = "brand"


class ZillowLeadStatus(Enum):
    """Status of imported leads."""
    NEW = "new"
    IMPORTED = "imported"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    PROCESSED = "processed"


@dataclass
class ZillowLead:
    """A lead from Zillow."""
    id: str
    zillow_id: str
    lead_type: ZillowLeadType
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    message: str = ""
    property_address: str = ""
    property_zpid: str = ""
    property_price: float = 0
    property_beds: int = 0
    property_baths: float = 0
    prequalified: bool = False
    prequalified_amount: float = 0
    search_criteria: Dict = field(default_factory=dict)
    timeline: str = ""
    status: ZillowLeadStatus = ZillowLeadStatus.NEW
    raw_data: Dict = field(default_factory=dict)
    imported_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime = None


class ZillowIntegration:
    """Integration with Zillow Premier Agent and Flex."""
    
    def __init__(
        self,
        api_key: str = None,
        webhook_secret: str = None,
        storage_path: str = "data/integrations/zillow"
    ):
        self.api_key = api_key or os.getenv("ZILLOW_API_KEY", "")
        self.webhook_secret = webhook_secret or os.getenv("ZILLOW_WEBHOOK_SECRET", "")
        self.storage_path = storage_path
        self.leads: Dict[str, ZillowLead] = {}
        self.callbacks: List[Callable] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load Zillow leads from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        leads_file = f"{self.storage_path}/leads.json"
        
        if os.path.exists(leads_file):
            with open(leads_file, 'r') as f:
                data = json.load(f)
                for lead_data in data:
                    lead = ZillowLead(
                        id=lead_data['id'],
                        zillow_id=lead_data['zillow_id'],
                        lead_type=ZillowLeadType(lead_data['lead_type']),
                        first_name=lead_data['first_name'],
                        last_name=lead_data['last_name'],
                        email=lead_data['email'],
                        phone=lead_data.get('phone', ''),
                        message=lead_data.get('message', ''),
                        property_address=lead_data.get('property_address', ''),
                        property_zpid=lead_data.get('property_zpid', ''),
                        property_price=lead_data.get('property_price', 0),
                        property_beds=lead_data.get('property_beds', 0),
                        property_baths=lead_data.get('property_baths', 0),
                        prequalified=lead_data.get('prequalified', False),
                        prequalified_amount=lead_data.get('prequalified_amount', 0),
                        search_criteria=lead_data.get('search_criteria', {}),
                        timeline=lead_data.get('timeline', ''),
                        status=ZillowLeadStatus(lead_data['status']),
                        raw_data=lead_data.get('raw_data', {}),
                        imported_at=datetime.fromisoformat(lead_data['imported_at']),
                        processed_at=datetime.fromisoformat(lead_data['processed_at']) if lead_data.get('processed_at') else None
                    )
                    self.leads[lead.id] = lead
    
    def _save_data(self):
        """Save Zillow leads to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        leads_data = [
            {
                'id': l.id,
                'zillow_id': l.zillow_id,
                'lead_type': l.lead_type.value,
                'first_name': l.first_name,
                'last_name': l.last_name,
                'email': l.email,
                'phone': l.phone,
                'message': l.message,
                'property_address': l.property_address,
                'property_zpid': l.property_zpid,
                'property_price': l.property_price,
                'property_beds': l.property_beds,
                'property_baths': l.property_baths,
                'prequalified': l.prequalified,
                'prequalified_amount': l.prequalified_amount,
                'search_criteria': l.search_criteria,
                'timeline': l.timeline,
                'status': l.status.value,
                'raw_data': l.raw_data,
                'imported_at': l.imported_at.isoformat(),
                'processed_at': l.processed_at.isoformat() if l.processed_at else None
            }
            for l in self.leads.values()
        ]
        
        with open(f"{self.storage_path}/leads.json", 'w') as f:
            json.dump(leads_data, f, indent=2)
    
    def verify_webhook(self, payload: str, signature: str) -> bool:
        """Verify Zillow webhook signature."""
        if not self.webhook_secret:
            return False
        
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    
    def process_webhook(self, payload: Dict) -> Optional[ZillowLead]:
        """Process incoming Zillow webhook payload."""
        # Check for duplicate
        zillow_id = payload.get('leadId', payload.get('id', ''))
        for lead in self.leads.values():
            if lead.zillow_id == zillow_id:
                lead.status = ZillowLeadStatus.DUPLICATE
                self._save_data()
                return None
        
        # Determine lead type
        lead_type_str = payload.get('leadType', 'buyer').lower()
        try:
            lead_type = ZillowLeadType(lead_type_str)
        except ValueError:
            lead_type = ZillowLeadType.BUYER
        
        # Extract contact info
        contact = payload.get('contact', {})
        property_info = payload.get('property', {})
        
        lead = ZillowLead(
            id=str(uuid.uuid4())[:12],
            zillow_id=zillow_id,
            lead_type=lead_type,
            first_name=contact.get('firstName', payload.get('firstName', '')),
            last_name=contact.get('lastName', payload.get('lastName', '')),
            email=contact.get('email', payload.get('email', '')),
            phone=contact.get('phone', payload.get('phone', '')),
            message=payload.get('message', ''),
            property_address=property_info.get('address', payload.get('propertyAddress', '')),
            property_zpid=property_info.get('zpid', payload.get('zpid', '')),
            property_price=float(property_info.get('price', payload.get('price', 0)) or 0),
            property_beds=int(property_info.get('beds', 0) or 0),
            property_baths=float(property_info.get('baths', 0) or 0),
            prequalified=payload.get('prequalified', False),
            prequalified_amount=float(payload.get('prequalifiedAmount', 0) or 0),
            search_criteria=payload.get('searchCriteria', {}),
            timeline=payload.get('timeline', payload.get('buyingTimeline', '')),
            status=ZillowLeadStatus.IMPORTED,
            raw_data=payload
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
    
    def on_lead_received(self, callback: Callable[[ZillowLead], None]):
        """Register callback for new leads."""
        self.callbacks.append(callback)
    
    def convert_to_crm_lead(self, zillow_lead: ZillowLead) -> Dict:
        """Convert Zillow lead to CRM lead format."""
        return {
            'first_name': zillow_lead.first_name,
            'last_name': zillow_lead.last_name,
            'email': zillow_lead.email,
            'phone': zillow_lead.phone,
            'source': 'zillow',
            'source_detail': f"Zillow {zillow_lead.lead_type.value.title()}",
            'lead_type': 'buyer' if zillow_lead.lead_type in [ZillowLeadType.BUYER, ZillowLeadType.RENTER] else 'seller',
            'notes': zillow_lead.message,
            'property_interest': zillow_lead.property_address,
            'budget': zillow_lead.prequalified_amount or zillow_lead.property_price,
            'timeline': zillow_lead.timeline,
            'preapproved': zillow_lead.prequalified,
            'custom_fields': {
                'zillow_id': zillow_lead.zillow_id,
                'zillow_zpid': zillow_lead.property_zpid,
                'zillow_lead_type': zillow_lead.lead_type.value,
                'search_criteria': zillow_lead.search_criteria
            }
        }
    
    def mark_processed(self, lead_id: str):
        """Mark a lead as processed."""
        lead = self.leads.get(lead_id)
        if lead:
            lead.status = ZillowLeadStatus.PROCESSED
            lead.processed_at = datetime.now()
            self._save_data()
    
    def get_unprocessed_leads(self) -> List[ZillowLead]:
        """Get all unprocessed leads."""
        return [
            l for l in self.leads.values()
            if l.status == ZillowLeadStatus.IMPORTED
        ]
    
    def get_leads_by_type(self, lead_type: ZillowLeadType) -> List[ZillowLead]:
        """Get leads by type."""
        return [l for l in self.leads.values() if l.lead_type == lead_type]
    
    def get_stats(self) -> Dict:
        """Get Zillow integration statistics."""
        total = len(self.leads)
        by_type = {}
        by_status = {}
        
        for lead_type in ZillowLeadType:
            by_type[lead_type.value] = len([l for l in self.leads.values() if l.lead_type == lead_type])
        
        for status in ZillowLeadStatus:
            by_status[status.value] = len([l for l in self.leads.values() if l.status == status])
        
        return {
            'total_leads': total,
            'by_type': by_type,
            'by_status': by_status,
            'processed_rate': (by_status.get('processed', 0) / total * 100) if total else 0
        }
