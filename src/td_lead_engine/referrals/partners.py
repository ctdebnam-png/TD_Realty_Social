"""Referral partner management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class PartnerType(Enum):
    """Types of referral partners."""
    AGENT = "agent"  # Another agent
    LENDER = "lender"
    TITLE = "title"
    INSPECTOR = "inspector"
    CONTRACTOR = "contractor"
    ATTORNEY = "attorney"
    PAST_CLIENT = "past_client"
    SPHERE = "sphere"  # Sphere of influence
    RELOCATION = "relocation"
    CORPORATE = "corporate"
    OTHER = "other"


class PartnerStatus(Enum):
    """Partner status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


@dataclass
class ReferralPartner:
    """A referral partner."""
    id: str
    name: str
    company: str = ""
    partner_type: PartnerType = PartnerType.OTHER
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    referral_fee_percentage: float = 25  # Default 25% referral fee
    referral_fee_flat: float = 0  # Or flat fee
    notes: str = ""
    status: PartnerStatus = PartnerStatus.ACTIVE
    total_referrals: int = 0
    total_closings: int = 0
    total_volume: float = 0
    total_paid: float = 0
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_referral_at: datetime = None


class PartnerManager:
    """Manage referral partners."""
    
    def __init__(self, storage_path: str = "data/referrals"):
        self.storage_path = storage_path
        self.partners: Dict[str, ReferralPartner] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load partners from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/partners.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for p in data:
                    partner = ReferralPartner(
                        id=p['id'],
                        name=p['name'],
                        company=p.get('company', ''),
                        partner_type=PartnerType(p.get('partner_type', 'other')),
                        email=p.get('email', ''),
                        phone=p.get('phone', ''),
                        address=p.get('address', ''),
                        city=p.get('city', ''),
                        state=p.get('state', ''),
                        zip_code=p.get('zip_code', ''),
                        referral_fee_percentage=p.get('referral_fee_percentage', 25),
                        referral_fee_flat=p.get('referral_fee_flat', 0),
                        notes=p.get('notes', ''),
                        status=PartnerStatus(p.get('status', 'active')),
                        total_referrals=p.get('total_referrals', 0),
                        total_closings=p.get('total_closings', 0),
                        total_volume=p.get('total_volume', 0),
                        total_paid=p.get('total_paid', 0),
                        tags=p.get('tags', []),
                        created_at=datetime.fromisoformat(p['created_at']),
                        last_referral_at=datetime.fromisoformat(p['last_referral_at']) if p.get('last_referral_at') else None
                    )
                    self.partners[partner.id] = partner
    
    def _save_data(self):
        """Save partners to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        partners_data = [
            {
                'id': p.id,
                'name': p.name,
                'company': p.company,
                'partner_type': p.partner_type.value,
                'email': p.email,
                'phone': p.phone,
                'address': p.address,
                'city': p.city,
                'state': p.state,
                'zip_code': p.zip_code,
                'referral_fee_percentage': p.referral_fee_percentage,
                'referral_fee_flat': p.referral_fee_flat,
                'notes': p.notes,
                'status': p.status.value,
                'total_referrals': p.total_referrals,
                'total_closings': p.total_closings,
                'total_volume': p.total_volume,
                'total_paid': p.total_paid,
                'tags': p.tags,
                'created_at': p.created_at.isoformat(),
                'last_referral_at': p.last_referral_at.isoformat() if p.last_referral_at else None
            }
            for p in self.partners.values()
        ]
        
        with open(f"{self.storage_path}/partners.json", 'w') as f:
            json.dump(partners_data, f, indent=2)
    
    def add_partner(
        self,
        name: str,
        partner_type: PartnerType = PartnerType.OTHER,
        **kwargs
    ) -> ReferralPartner:
        """Add a new referral partner."""
        partner = ReferralPartner(
            id=str(uuid.uuid4())[:12],
            name=name,
            partner_type=partner_type,
            company=kwargs.get('company', ''),
            email=kwargs.get('email', ''),
            phone=kwargs.get('phone', ''),
            address=kwargs.get('address', ''),
            city=kwargs.get('city', ''),
            state=kwargs.get('state', ''),
            zip_code=kwargs.get('zip_code', ''),
            referral_fee_percentage=kwargs.get('referral_fee_percentage', 25),
            referral_fee_flat=kwargs.get('referral_fee_flat', 0),
            notes=kwargs.get('notes', ''),
            tags=kwargs.get('tags', [])
        )
        self.partners[partner.id] = partner
        self._save_data()
        return partner
    
    def get_partner(self, partner_id: str) -> Optional[ReferralPartner]:
        """Get a partner by ID."""
        return self.partners.get(partner_id)
    
    def update_partner(self, partner_id: str, **kwargs) -> Optional[ReferralPartner]:
        """Update a partner."""
        partner = self.partners.get(partner_id)
        if not partner:
            return None
        
        for key, value in kwargs.items():
            if hasattr(partner, key):
                setattr(partner, key, value)
        
        self._save_data()
        return partner
    
    def get_partners_by_type(self, partner_type: PartnerType) -> List[ReferralPartner]:
        """Get partners by type."""
        return [
            p for p in self.partners.values()
            if p.partner_type == partner_type and p.status == PartnerStatus.ACTIVE
        ]
    
    def get_active_partners(self) -> List[ReferralPartner]:
        """Get all active partners."""
        return [p for p in self.partners.values() if p.status == PartnerStatus.ACTIVE]
    
    def search_partners(self, query: str) -> List[ReferralPartner]:
        """Search partners by name or company."""
        query = query.lower()
        return [
            p for p in self.partners.values()
            if query in p.name.lower() or query in p.company.lower()
        ]
    
    def record_referral(self, partner_id: str):
        """Record a referral from a partner."""
        partner = self.partners.get(partner_id)
        if partner:
            partner.total_referrals += 1
            partner.last_referral_at = datetime.now()
            self._save_data()
    
    def record_closing(self, partner_id: str, volume: float, commission_paid: float):
        """Record a closing from a referral."""
        partner = self.partners.get(partner_id)
        if partner:
            partner.total_closings += 1
            partner.total_volume += volume
            partner.total_paid += commission_paid
            self._save_data()
    
    def get_partner_stats(self, partner_id: str) -> Dict:
        """Get statistics for a partner."""
        partner = self.partners.get(partner_id)
        if not partner:
            return {}
        
        return {
            'partner_id': partner.id,
            'name': partner.name,
            'type': partner.partner_type.value,
            'total_referrals': partner.total_referrals,
            'total_closings': partner.total_closings,
            'total_volume': partner.total_volume,
            'total_paid': partner.total_paid,
            'conversion_rate': round(partner.total_closings / partner.total_referrals * 100, 1) if partner.total_referrals else 0,
            'avg_deal_size': round(partner.total_volume / partner.total_closings, 2) if partner.total_closings else 0,
            'last_referral': partner.last_referral_at.isoformat() if partner.last_referral_at else None
        }
    
    def get_top_partners(self, limit: int = 10, by: str = 'referrals') -> List[ReferralPartner]:
        """Get top performing partners."""
        partners = list(self.partners.values())
        
        if by == 'referrals':
            partners.sort(key=lambda p: p.total_referrals, reverse=True)
        elif by == 'closings':
            partners.sort(key=lambda p: p.total_closings, reverse=True)
        elif by == 'volume':
            partners.sort(key=lambda p: p.total_volume, reverse=True)
        elif by == 'conversion':
            partners.sort(key=lambda p: p.total_closings / p.total_referrals if p.total_referrals else 0, reverse=True)
        
        return partners[:limit]
    
    def get_partner_summary(self) -> Dict:
        """Get overall partner summary."""
        partners = list(self.partners.values())
        active = [p for p in partners if p.status == PartnerStatus.ACTIVE]
        
        by_type = {}
        for ptype in PartnerType:
            type_partners = [p for p in active if p.partner_type == ptype]
            by_type[ptype.value] = {
                'count': len(type_partners),
                'referrals': sum(p.total_referrals for p in type_partners),
                'closings': sum(p.total_closings for p in type_partners)
            }
        
        return {
            'total_partners': len(partners),
            'active_partners': len(active),
            'total_referrals': sum(p.total_referrals for p in partners),
            'total_closings': sum(p.total_closings for p in partners),
            'total_volume': sum(p.total_volume for p in partners),
            'total_paid': sum(p.total_paid for p in partners),
            'by_type': by_type
        }
