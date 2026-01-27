"""Realtor.com lead integration."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class RealtorLeadType(Enum):
    """Types of Realtor.com leads."""
    PROPERTY_INQUIRY = "property_inquiry"
    AGENT_INQUIRY = "agent_inquiry"
    MORTGAGE_INQUIRY = "mortgage_inquiry"
    VALUATION_REQUEST = "valuation_request"


@dataclass
class RealtorLead:
    """A lead from Realtor.com."""
    id: str
    realtor_id: str
    lead_type: RealtorLeadType
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    message: str = ""
    property_id: str = ""
    property_address: str = ""
    property_mls_id: str = ""
    property_price: float = 0
    is_preapproved: bool = False
    preapproval_amount: float = 0
    move_timeline: str = ""
    raw_data: Dict = field(default_factory=dict)
    status: str = "new"
    imported_at: datetime = field(default_factory=datetime.now)
    processed_at: datetime = None


class RealtorIntegration:
    """Integration with Realtor.com connections."""
    
    def __init__(
        self,
        api_key: str = None,
        storage_path: str = "data/integrations/realtor"
    ):
        self.api_key = api_key or os.getenv("REALTOR_API_KEY", "")
        self.storage_path = storage_path
        self.leads: Dict[str, RealtorLead] = {}
        self.callbacks: List[Callable] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load leads from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        leads_file = f"{self.storage_path}/leads.json"
        
        if os.path.exists(leads_file):
            with open(leads_file, 'r') as f:
                data = json.load(f)
                for lead_data in data:
                    lead = RealtorLead(
                        id=lead_data['id'],
                        realtor_id=lead_data['realtor_id'],
                        lead_type=RealtorLeadType(lead_data['lead_type']),
                        first_name=lead_data['first_name'],
                        last_name=lead_data['last_name'],
                        email=lead_data['email'],
                        phone=lead_data.get('phone', ''),
                        message=lead_data.get('message', ''),
                        property_id=lead_data.get('property_id', ''),
                        property_address=lead_data.get('property_address', ''),
                        property_mls_id=lead_data.get('property_mls_id', ''),
                        property_price=lead_data.get('property_price', 0),
                        is_preapproved=lead_data.get('is_preapproved', False),
                        preapproval_amount=lead_data.get('preapproval_amount', 0),
                        move_timeline=lead_data.get('move_timeline', ''),
                        raw_data=lead_data.get('raw_data', {}),
                        status=lead_data.get('status', 'new'),
                        imported_at=datetime.fromisoformat(lead_data['imported_at']),
                        processed_at=datetime.fromisoformat(lead_data['processed_at']) if lead_data.get('processed_at') else None
                    )
                    self.leads[lead.id] = lead
    
    def _save_data(self):
        """Save leads to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        leads_data = [
            {
                'id': l.id,
                'realtor_id': l.realtor_id,
                'lead_type': l.lead_type.value,
                'first_name': l.first_name,
                'last_name': l.last_name,
                'email': l.email,
                'phone': l.phone,
                'message': l.message,
                'property_id': l.property_id,
                'property_address': l.property_address,
                'property_mls_id': l.property_mls_id,
                'property_price': l.property_price,
                'is_preapproved': l.is_preapproved,
                'preapproval_amount': l.preapproval_amount,
                'move_timeline': l.move_timeline,
                'raw_data': l.raw_data,
                'status': l.status,
                'imported_at': l.imported_at.isoformat(),
                'processed_at': l.processed_at.isoformat() if l.processed_at else None
            }
            for l in self.leads.values()
        ]
        
        with open(f"{self.storage_path}/leads.json", 'w') as f:
            json.dump(leads_data, f, indent=2)
    
    def process_webhook(self, payload: Dict) -> Optional[RealtorLead]:
        """Process incoming Realtor.com webhook."""
        realtor_id = payload.get('leadId', payload.get('id', str(uuid.uuid4())[:12]))
        
        # Check for duplicate
        for lead in self.leads.values():
            if lead.realtor_id == realtor_id:
                return None
        
        # Determine lead type
        lead_type_str = payload.get('type', 'property_inquiry')
        try:
            lead_type = RealtorLeadType(lead_type_str)
        except ValueError:
            lead_type = RealtorLeadType.PROPERTY_INQUIRY
        
        lead = RealtorLead(
            id=str(uuid.uuid4())[:12],
            realtor_id=realtor_id,
            lead_type=lead_type,
            first_name=payload.get('firstName', ''),
            last_name=payload.get('lastName', ''),
            email=payload.get('email', ''),
            phone=payload.get('phone', ''),
            message=payload.get('message', ''),
            property_id=payload.get('propertyId', ''),
            property_address=payload.get('propertyAddress', ''),
            property_mls_id=payload.get('mlsId', ''),
            property_price=float(payload.get('price', 0) or 0),
            is_preapproved=payload.get('isPreapproved', False),
            preapproval_amount=float(payload.get('preapprovalAmount', 0) or 0),
            move_timeline=payload.get('moveTimeline', ''),
            raw_data=payload,
            status='imported'
        )
        
        self.leads[lead.id] = lead
        self._save_data()
        
        for callback in self.callbacks:
            try:
                callback(lead)
            except Exception:
                pass
        
        return lead
    
    def on_lead_received(self, callback: Callable[[RealtorLead], None]):
        """Register callback for new leads."""
        self.callbacks.append(callback)
    
    def convert_to_crm_lead(self, realtor_lead: RealtorLead) -> Dict:
        """Convert to CRM lead format."""
        return {
            'first_name': realtor_lead.first_name,
            'last_name': realtor_lead.last_name,
            'email': realtor_lead.email,
            'phone': realtor_lead.phone,
            'source': 'realtor.com',
            'source_detail': f"Realtor.com {realtor_lead.lead_type.value.replace('_', ' ').title()}",
            'lead_type': 'seller' if realtor_lead.lead_type == RealtorLeadType.VALUATION_REQUEST else 'buyer',
            'notes': realtor_lead.message,
            'property_interest': realtor_lead.property_address,
            'budget': realtor_lead.preapproval_amount or realtor_lead.property_price,
            'timeline': realtor_lead.move_timeline,
            'preapproved': realtor_lead.is_preapproved,
            'custom_fields': {
                'realtor_id': realtor_lead.realtor_id,
                'realtor_property_id': realtor_lead.property_id,
                'realtor_mls_id': realtor_lead.property_mls_id
            }
        }
    
    def mark_processed(self, lead_id: str):
        """Mark lead as processed."""
        lead = self.leads.get(lead_id)
        if lead:
            lead.status = 'processed'
            lead.processed_at = datetime.now()
            self._save_data()
    
    def get_unprocessed_leads(self) -> List[RealtorLead]:
        """Get unprocessed leads."""
        return [l for l in self.leads.values() if l.status == 'imported']
    
    def get_stats(self) -> Dict:
        """Get integration statistics."""
        total = len(self.leads)
        by_type = {}
        
        for lead_type in RealtorLeadType:
            by_type[lead_type.value] = len([l for l in self.leads.values() if l.lead_type == lead_type])
        
        processed = len([l for l in self.leads.values() if l.status == 'processed'])
        
        return {
            'total_leads': total,
            'by_type': by_type,
            'processed': processed,
            'processed_rate': (processed / total * 100) if total else 0
        }
