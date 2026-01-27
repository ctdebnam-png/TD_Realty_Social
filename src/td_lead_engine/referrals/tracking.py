"""Referral tracking and management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class ReferralStatus(Enum):
    """Referral status."""
    NEW = "new"
    CONTACTED = "contacted"
    WORKING = "working"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    LOST = "lost"


class ReferralDirection(Enum):
    """Direction of referral."""
    INCOMING = "incoming"  # Received from partner
    OUTGOING = "outgoing"  # Sent to partner


@dataclass
class Referral:
    """A referral."""
    id: str
    partner_id: str
    direction: ReferralDirection
    lead_id: str = ""
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    lead_type: str = "buyer"  # buyer, seller
    notes: str = ""
    status: ReferralStatus = ReferralStatus.NEW
    estimated_value: float = 0
    actual_value: float = 0
    referral_fee: float = 0
    fee_paid: bool = False
    fee_paid_date: datetime = None
    property_address: str = ""
    close_date: datetime = None
    assigned_agent_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ReferralTracker:
    """Track referrals."""
    
    def __init__(
        self,
        partner_manager,
        storage_path: str = "data/referrals"
    ):
        self.partner_manager = partner_manager
        self.storage_path = storage_path
        self.referrals: Dict[str, Referral] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load referrals from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/referrals.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for r in data:
                    referral = Referral(
                        id=r['id'],
                        partner_id=r['partner_id'],
                        direction=ReferralDirection(r.get('direction', 'incoming')),
                        lead_id=r.get('lead_id', ''),
                        first_name=r.get('first_name', ''),
                        last_name=r.get('last_name', ''),
                        email=r.get('email', ''),
                        phone=r.get('phone', ''),
                        lead_type=r.get('lead_type', 'buyer'),
                        notes=r.get('notes', ''),
                        status=ReferralStatus(r.get('status', 'new')),
                        estimated_value=r.get('estimated_value', 0),
                        actual_value=r.get('actual_value', 0),
                        referral_fee=r.get('referral_fee', 0),
                        fee_paid=r.get('fee_paid', False),
                        fee_paid_date=datetime.fromisoformat(r['fee_paid_date']) if r.get('fee_paid_date') else None,
                        property_address=r.get('property_address', ''),
                        close_date=datetime.fromisoformat(r['close_date']) if r.get('close_date') else None,
                        assigned_agent_id=r.get('assigned_agent_id', ''),
                        created_at=datetime.fromisoformat(r['created_at']),
                        updated_at=datetime.fromisoformat(r.get('updated_at', r['created_at']))
                    )
                    self.referrals[referral.id] = referral
    
    def _save_data(self):
        """Save referrals to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        referrals_data = [
            {
                'id': r.id,
                'partner_id': r.partner_id,
                'direction': r.direction.value,
                'lead_id': r.lead_id,
                'first_name': r.first_name,
                'last_name': r.last_name,
                'email': r.email,
                'phone': r.phone,
                'lead_type': r.lead_type,
                'notes': r.notes,
                'status': r.status.value,
                'estimated_value': r.estimated_value,
                'actual_value': r.actual_value,
                'referral_fee': r.referral_fee,
                'fee_paid': r.fee_paid,
                'fee_paid_date': r.fee_paid_date.isoformat() if r.fee_paid_date else None,
                'property_address': r.property_address,
                'close_date': r.close_date.isoformat() if r.close_date else None,
                'assigned_agent_id': r.assigned_agent_id,
                'created_at': r.created_at.isoformat(),
                'updated_at': r.updated_at.isoformat()
            }
            for r in self.referrals.values()
        ]
        
        with open(f"{self.storage_path}/referrals.json", 'w') as f:
            json.dump(referrals_data, f, indent=2)
    
    def create_referral(
        self,
        partner_id: str,
        direction: ReferralDirection = ReferralDirection.INCOMING,
        **kwargs
    ) -> Referral:
        """Create a new referral."""
        referral = Referral(
            id=str(uuid.uuid4())[:12],
            partner_id=partner_id,
            direction=direction,
            lead_id=kwargs.get('lead_id', ''),
            first_name=kwargs.get('first_name', ''),
            last_name=kwargs.get('last_name', ''),
            email=kwargs.get('email', ''),
            phone=kwargs.get('phone', ''),
            lead_type=kwargs.get('lead_type', 'buyer'),
            notes=kwargs.get('notes', ''),
            estimated_value=kwargs.get('estimated_value', 0),
            assigned_agent_id=kwargs.get('assigned_agent_id', '')
        )
        
        self.referrals[referral.id] = referral
        
        # Update partner stats
        if direction == ReferralDirection.INCOMING:
            self.partner_manager.record_referral(partner_id)
        
        self._save_data()
        return referral
    
    def update_status(self, referral_id: str, status: ReferralStatus) -> Optional[Referral]:
        """Update referral status."""
        referral = self.referrals.get(referral_id)
        if not referral:
            return None
        
        referral.status = status
        referral.updated_at = datetime.now()
        self._save_data()
        return referral
    
    def record_closing(
        self,
        referral_id: str,
        actual_value: float,
        close_date: datetime = None,
        property_address: str = ""
    ) -> Optional[Referral]:
        """Record a closing for a referral."""
        referral = self.referrals.get(referral_id)
        if not referral:
            return None
        
        referral.status = ReferralStatus.CLOSED
        referral.actual_value = actual_value
        referral.close_date = close_date or datetime.now()
        referral.property_address = property_address
        referral.updated_at = datetime.now()
        
        # Calculate referral fee
        partner = self.partner_manager.get_partner(referral.partner_id)
        if partner:
            if partner.referral_fee_flat > 0:
                referral.referral_fee = partner.referral_fee_flat
            else:
                # Assume 3% commission, then apply referral fee percentage
                commission = actual_value * 0.03
                referral.referral_fee = commission * (partner.referral_fee_percentage / 100)
        
        self._save_data()
        return referral
    
    def mark_fee_paid(self, referral_id: str) -> bool:
        """Mark referral fee as paid."""
        referral = self.referrals.get(referral_id)
        if not referral:
            return False
        
        referral.fee_paid = True
        referral.fee_paid_date = datetime.now()
        referral.updated_at = datetime.now()
        
        # Update partner stats
        if referral.direction == ReferralDirection.INCOMING:
            self.partner_manager.record_closing(
                referral.partner_id,
                referral.actual_value,
                referral.referral_fee
            )
        
        self._save_data()
        return True
    
    def get_referral(self, referral_id: str) -> Optional[Referral]:
        """Get a referral by ID."""
        return self.referrals.get(referral_id)
    
    def get_partner_referrals(self, partner_id: str) -> List[Referral]:
        """Get all referrals for a partner."""
        referrals = [r for r in self.referrals.values() if r.partner_id == partner_id]
        referrals.sort(key=lambda r: r.created_at, reverse=True)
        return referrals
    
    def get_referrals_by_status(self, status: ReferralStatus) -> List[Referral]:
        """Get referrals by status."""
        return [r for r in self.referrals.values() if r.status == status]
    
    def get_unpaid_referrals(self) -> List[Referral]:
        """Get closed referrals with unpaid fees."""
        return [
            r for r in self.referrals.values()
            if r.status == ReferralStatus.CLOSED and not r.fee_paid and r.referral_fee > 0
        ]
    
    def get_referral_pipeline(self) -> Dict:
        """Get referral pipeline summary."""
        active_statuses = [ReferralStatus.NEW, ReferralStatus.CONTACTED, ReferralStatus.WORKING, ReferralStatus.UNDER_CONTRACT]
        
        pipeline = {}
        for status in active_statuses:
            referrals = self.get_referrals_by_status(status)
            pipeline[status.value] = {
                'count': len(referrals),
                'estimated_value': sum(r.estimated_value for r in referrals)
            }
        
        return pipeline
    
    def get_referral_stats(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get referral statistics."""
        from datetime import timedelta
        
        start = start_date or datetime.now() - timedelta(days=365)
        end = end_date or datetime.now()
        
        referrals = [
            r for r in self.referrals.values()
            if start <= r.created_at <= end
        ]
        
        incoming = [r for r in referrals if r.direction == ReferralDirection.INCOMING]
        outgoing = [r for r in referrals if r.direction == ReferralDirection.OUTGOING]
        closed = [r for r in referrals if r.status == ReferralStatus.CLOSED]
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'total_referrals': len(referrals),
            'incoming': {
                'count': len(incoming),
                'closed': len([r for r in incoming if r.status == ReferralStatus.CLOSED]),
                'volume': sum(r.actual_value for r in incoming if r.status == ReferralStatus.CLOSED),
                'fees_owed': sum(r.referral_fee for r in incoming if not r.fee_paid)
            },
            'outgoing': {
                'count': len(outgoing),
                'closed': len([r for r in outgoing if r.status == ReferralStatus.CLOSED]),
                'volume': sum(r.actual_value for r in outgoing if r.status == ReferralStatus.CLOSED),
                'fees_earned': sum(r.referral_fee for r in outgoing if r.status == ReferralStatus.CLOSED)
            },
            'conversion_rate': round(len(closed) / len(referrals) * 100, 1) if referrals else 0
        }
