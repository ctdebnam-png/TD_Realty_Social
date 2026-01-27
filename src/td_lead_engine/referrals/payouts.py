"""Referral commission payout management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid


class PayoutStatus(Enum):
    """Payout status."""
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    PAID = "paid"
    CANCELLED = "cancelled"


class PayoutMethod(Enum):
    """Payment method."""
    CHECK = "check"
    ACH = "ach"
    WIRE = "wire"
    VENMO = "venmo"
    ZELLE = "zelle"


@dataclass
class CommissionPayout:
    """A commission payout record."""
    id: str
    referral_id: str
    partner_id: str
    amount: float
    status: PayoutStatus = PayoutStatus.PENDING
    method: PayoutMethod = PayoutMethod.CHECK
    check_number: str = ""
    transaction_id: str = ""
    notes: str = ""
    approved_by: str = ""
    approved_at: datetime = None
    paid_at: datetime = None
    created_at: datetime = field(default_factory=datetime.now)


class PayoutManager:
    """Manage referral commission payouts."""
    
    def __init__(
        self,
        referral_tracker,
        storage_path: str = "data/referrals"
    ):
        self.referral_tracker = referral_tracker
        self.storage_path = storage_path
        self.payouts: Dict[str, CommissionPayout] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load payouts from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/payouts.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for p in data:
                    payout = CommissionPayout(
                        id=p['id'],
                        referral_id=p['referral_id'],
                        partner_id=p['partner_id'],
                        amount=p['amount'],
                        status=PayoutStatus(p.get('status', 'pending')),
                        method=PayoutMethod(p.get('method', 'check')),
                        check_number=p.get('check_number', ''),
                        transaction_id=p.get('transaction_id', ''),
                        notes=p.get('notes', ''),
                        approved_by=p.get('approved_by', ''),
                        approved_at=datetime.fromisoformat(p['approved_at']) if p.get('approved_at') else None,
                        paid_at=datetime.fromisoformat(p['paid_at']) if p.get('paid_at') else None,
                        created_at=datetime.fromisoformat(p['created_at'])
                    )
                    self.payouts[payout.id] = payout
    
    def _save_data(self):
        """Save payouts to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        payouts_data = [
            {
                'id': p.id,
                'referral_id': p.referral_id,
                'partner_id': p.partner_id,
                'amount': p.amount,
                'status': p.status.value,
                'method': p.method.value,
                'check_number': p.check_number,
                'transaction_id': p.transaction_id,
                'notes': p.notes,
                'approved_by': p.approved_by,
                'approved_at': p.approved_at.isoformat() if p.approved_at else None,
                'paid_at': p.paid_at.isoformat() if p.paid_at else None,
                'created_at': p.created_at.isoformat()
            }
            for p in self.payouts.values()
        ]
        
        with open(f"{self.storage_path}/payouts.json", 'w') as f:
            json.dump(payouts_data, f, indent=2)
    
    def create_payout(
        self,
        referral_id: str,
        method: PayoutMethod = PayoutMethod.CHECK
    ) -> Optional[CommissionPayout]:
        """Create a payout for a referral."""
        referral = self.referral_tracker.get_referral(referral_id)
        if not referral or referral.referral_fee <= 0:
            return None
        
        # Check if payout already exists
        for payout in self.payouts.values():
            if payout.referral_id == referral_id and payout.status != PayoutStatus.CANCELLED:
                return None
        
        payout = CommissionPayout(
            id=str(uuid.uuid4())[:12],
            referral_id=referral_id,
            partner_id=referral.partner_id,
            amount=referral.referral_fee,
            method=method
        )
        
        self.payouts[payout.id] = payout
        self._save_data()
        return payout
    
    def approve_payout(self, payout_id: str, approved_by: str) -> bool:
        """Approve a payout."""
        payout = self.payouts.get(payout_id)
        if not payout or payout.status != PayoutStatus.PENDING:
            return False
        
        payout.status = PayoutStatus.APPROVED
        payout.approved_by = approved_by
        payout.approved_at = datetime.now()
        self._save_data()
        return True
    
    def process_payout(
        self,
        payout_id: str,
        check_number: str = "",
        transaction_id: str = ""
    ) -> bool:
        """Process a payout."""
        payout = self.payouts.get(payout_id)
        if not payout or payout.status != PayoutStatus.APPROVED:
            return False
        
        payout.status = PayoutStatus.PAID
        payout.check_number = check_number
        payout.transaction_id = transaction_id
        payout.paid_at = datetime.now()
        
        # Mark referral fee as paid
        self.referral_tracker.mark_fee_paid(payout.referral_id)
        
        self._save_data()
        return True
    
    def cancel_payout(self, payout_id: str, reason: str = "") -> bool:
        """Cancel a payout."""
        payout = self.payouts.get(payout_id)
        if not payout or payout.status == PayoutStatus.PAID:
            return False
        
        payout.status = PayoutStatus.CANCELLED
        payout.notes = reason
        self._save_data()
        return True
    
    def get_payout(self, payout_id: str) -> Optional[CommissionPayout]:
        """Get a payout by ID."""
        return self.payouts.get(payout_id)
    
    def get_partner_payouts(self, partner_id: str) -> List[CommissionPayout]:
        """Get payouts for a partner."""
        payouts = [p for p in self.payouts.values() if p.partner_id == partner_id]
        payouts.sort(key=lambda p: p.created_at, reverse=True)
        return payouts
    
    def get_pending_payouts(self) -> List[CommissionPayout]:
        """Get all pending payouts."""
        return [p for p in self.payouts.values() if p.status == PayoutStatus.PENDING]
    
    def get_approved_payouts(self) -> List[CommissionPayout]:
        """Get approved payouts ready for processing."""
        return [p for p in self.payouts.values() if p.status == PayoutStatus.APPROVED]
    
    def generate_payout_report(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Generate payout report."""
        from datetime import timedelta
        
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        payouts = [
            p for p in self.payouts.values()
            if start <= p.created_at <= end
        ]
        
        paid = [p for p in payouts if p.status == PayoutStatus.PAID]
        pending = [p for p in payouts if p.status == PayoutStatus.PENDING]
        approved = [p for p in payouts if p.status == PayoutStatus.APPROVED]
        
        # By method
        by_method = {}
        for method in PayoutMethod:
            method_payouts = [p for p in paid if p.method == method]
            by_method[method.value] = {
                'count': len(method_payouts),
                'amount': sum(p.amount for p in method_payouts)
            }
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'summary': {
                'total_payouts': len(payouts),
                'total_amount': sum(p.amount for p in payouts),
                'paid_count': len(paid),
                'paid_amount': sum(p.amount for p in paid),
                'pending_count': len(pending),
                'pending_amount': sum(p.amount for p in pending),
                'approved_count': len(approved),
                'approved_amount': sum(p.amount for p in approved)
            },
            'by_method': by_method
        }
    
    def get_outstanding_balance(self) -> Dict:
        """Get outstanding payout balance."""
        pending = self.get_pending_payouts()
        approved = self.get_approved_payouts()
        
        # Group by partner
        by_partner = {}
        for payout in pending + approved:
            if payout.partner_id not in by_partner:
                by_partner[payout.partner_id] = 0
            by_partner[payout.partner_id] += payout.amount
        
        return {
            'total_outstanding': sum(p.amount for p in pending + approved),
            'pending_count': len(pending),
            'pending_amount': sum(p.amount for p in pending),
            'approved_count': len(approved),
            'approved_amount': sum(p.amount for p in approved),
            'by_partner': by_partner
        }
