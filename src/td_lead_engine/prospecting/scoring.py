"""Prospect scoring based on signals and data quality."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os

from .signals import LeadSignal, SignalType


class ProspectTier(Enum):
    """Prospect quality tiers."""
    PLATINUM = "platinum"   # 90+ score, multiple signals, contact info
    GOLD = "gold"           # 70-89 score, strong signals
    SILVER = "silver"       # 50-69 score, decent signals
    BRONZE = "bronze"       # 30-49 score, weak signals
    COLD = "cold"           # <30 score, minimal signals


class ProspectType(Enum):
    """Type of prospect."""
    SELLER = "seller"
    BUYER = "buyer"
    INVESTOR = "investor"
    LANDLORD = "landlord"


@dataclass
class ScoredProspect:
    """A scored prospect ready for outreach."""
    id: str
    address: str
    owner_name: str
    owner_phone: str = ""
    owner_email: str = ""
    mailing_address: str = ""
    prospect_type: ProspectType = ProspectType.SELLER
    tier: ProspectTier = ProspectTier.COLD
    score: int = 0
    signals: List[str] = field(default_factory=list)  # Signal IDs
    signal_summary: List[str] = field(default_factory=list)  # Human readable
    property_value: float = 0
    equity_estimate: float = 0
    recommended_approach: str = ""
    data_quality: int = 0  # 0-100
    contact_attempts: int = 0
    last_contact: datetime = None
    status: str = "new"
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class ProspectScorer:
    """Score prospects based on signals and determine outreach priority."""
    
    # Signal type to prospect type mapping
    SIGNAL_TO_PROSPECT_TYPE = {
        SignalType.LONG_TERM_OWNER: ProspectType.SELLER,
        SignalType.HIGH_EQUITY: ProspectType.SELLER,
        SignalType.ABSENTEE_OWNER: ProspectType.SELLER,
        SignalType.PRE_FORECLOSURE: ProspectType.SELLER,
        SignalType.PROBATE: ProspectType.SELLER,
        SignalType.DIVORCE: ProspectType.SELLER,
        SignalType.EXPIRED_LISTING: ProspectType.SELLER,
        SignalType.FSBO: ProspectType.SELLER,
        SignalType.TAX_DELINQUENT: ProspectType.SELLER,
        SignalType.TIRED_LANDLORD: ProspectType.LANDLORD,
        SignalType.BUILDING_PERMIT: ProspectType.SELLER,
        SignalType.PRICE_REDUCTION: ProspectType.SELLER,
    }
    
    # Recommended approaches by signal type
    APPROACHES = {
        SignalType.PRE_FORECLOSURE: "Sensitive outreach - offer foreclosure prevention consultation",
        SignalType.PROBATE: "Respectful timing - offer estate sale expertise and market analysis",
        SignalType.DIVORCE: "Neutral positioning - offer quick sale options and equity split help",
        SignalType.EXPIRED_LISTING: "Direct approach - highlight what went wrong and your strategy",
        SignalType.FSBO: "Value proposition - show marketing reach and negotiation expertise",
        SignalType.ABSENTEE_OWNER: "Convenience pitch - offer hassle-free sale management",
        SignalType.HIGH_EQUITY: "Upgrade pitch - show what their equity could buy them",
        SignalType.LONG_TERM_OWNER: "Life change inquiry - ask about downsizing/upgrading plans",
        SignalType.TAX_DELINQUENT: "Solution-focused - quick sale to resolve tax issues",
        SignalType.TIRED_LANDLORD: "Exit strategy - 1031 exchange or cash out options",
        SignalType.PRICE_REDUCTION: "Fresh perspective - new marketing strategy proposal",
    }
    
    def __init__(self, storage_path: str = "data/prospecting"):
        self.storage_path = storage_path
        self.prospects: Dict[str, ScoredProspect] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_prospects()
    
    def _load_prospects(self):
        """Load scored prospects."""
        prospects_file = f"{self.storage_path}/prospects.json"
        if os.path.exists(prospects_file):
            with open(prospects_file, 'r') as f:
                data = json.load(f)
                for p in data:
                    prospect = ScoredProspect(
                        id=p['id'],
                        address=p['address'],
                        owner_name=p['owner_name'],
                        owner_phone=p.get('owner_phone', ''),
                        owner_email=p.get('owner_email', ''),
                        mailing_address=p.get('mailing_address', ''),
                        prospect_type=ProspectType(p.get('prospect_type', 'seller')),
                        tier=ProspectTier(p.get('tier', 'cold')),
                        score=p.get('score', 0),
                        signals=p.get('signals', []),
                        signal_summary=p.get('signal_summary', []),
                        property_value=p.get('property_value', 0),
                        equity_estimate=p.get('equity_estimate', 0),
                        recommended_approach=p.get('recommended_approach', ''),
                        data_quality=p.get('data_quality', 0),
                        contact_attempts=p.get('contact_attempts', 0),
                        last_contact=datetime.fromisoformat(p['last_contact']) if p.get('last_contact') else None,
                        status=p.get('status', 'new'),
                        notes=p.get('notes', ''),
                        created_at=datetime.fromisoformat(p['created_at']),
                        updated_at=datetime.fromisoformat(p['updated_at'])
                    )
                    self.prospects[prospect.id] = prospect
    
    def _save_prospects(self):
        """Save scored prospects."""
        prospects_data = [
            {
                'id': p.id,
                'address': p.address,
                'owner_name': p.owner_name,
                'owner_phone': p.owner_phone,
                'owner_email': p.owner_email,
                'mailing_address': p.mailing_address,
                'prospect_type': p.prospect_type.value,
                'tier': p.tier.value,
                'score': p.score,
                'signals': p.signals,
                'signal_summary': p.signal_summary,
                'property_value': p.property_value,
                'equity_estimate': p.equity_estimate,
                'recommended_approach': p.recommended_approach,
                'data_quality': p.data_quality,
                'contact_attempts': p.contact_attempts,
                'last_contact': p.last_contact.isoformat() if p.last_contact else None,
                'status': p.status,
                'notes': p.notes,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat()
            }
            for p in self.prospects.values()
        ]
        
        with open(f"{self.storage_path}/prospects.json", 'w') as f:
            json.dump(prospects_data, f, indent=2)
    
    def score_signals(self, signals: List[LeadSignal]) -> ScoredProspect:
        """Score a set of signals for the same property/owner."""
        if not signals:
            return None
        
        import uuid
        
        # Get primary signal (highest strength)
        primary = max(signals, key=lambda s: s.strength)
        
        # Calculate composite score
        base_score = primary.strength
        
        # Bonus for multiple signals
        if len(signals) >= 2:
            base_score += 10
        if len(signals) >= 3:
            base_score += 10
        if len(signals) >= 4:
            base_score += 5
        
        # Bonus for contact info
        data_quality = 0
        if primary.owner_name:
            data_quality += 25
        if primary.owner_phone:
            data_quality += 35
            base_score += 10
        if primary.owner_email:
            data_quality += 25
            base_score += 5
        if primary.mailing_address:
            data_quality += 15
        
        # Bonus for high value properties
        if primary.property_value >= 500000:
            base_score += 10
        elif primary.property_value >= 300000:
            base_score += 5
        
        # Cap at 100
        final_score = min(base_score, 100)
        
        # Determine tier
        if final_score >= 90:
            tier = ProspectTier.PLATINUM
        elif final_score >= 70:
            tier = ProspectTier.GOLD
        elif final_score >= 50:
            tier = ProspectTier.SILVER
        elif final_score >= 30:
            tier = ProspectTier.BRONZE
        else:
            tier = ProspectTier.COLD
        
        # Determine prospect type from primary signal
        prospect_type = self.SIGNAL_TO_PROSPECT_TYPE.get(primary.signal_type, ProspectType.SELLER)
        
        # Build signal summary
        signal_summary = []
        for s in signals:
            if s.signal_type == SignalType.HIGH_EQUITY:
                equity = s.details.get('equity', 0)
                signal_summary.append(f"High equity: ${equity:,.0f}")
            elif s.signal_type == SignalType.LONG_TERM_OWNER:
                years = s.details.get('years_owned', 0)
                signal_summary.append(f"Owner for {years:.0f} years")
            elif s.signal_type == SignalType.ABSENTEE_OWNER:
                signal_summary.append("Absentee owner")
            elif s.signal_type == SignalType.PRE_FORECLOSURE:
                signal_summary.append("Pre-foreclosure filing")
            elif s.signal_type == SignalType.PROBATE:
                signal_summary.append("Probate/estate case")
            elif s.signal_type == SignalType.DIVORCE:
                signal_summary.append("Divorce filing")
            elif s.signal_type == SignalType.EXPIRED_LISTING:
                dom = s.details.get('days_on_market', 0)
                signal_summary.append(f"Expired listing ({dom} DOM)")
            elif s.signal_type == SignalType.FSBO:
                signal_summary.append("For Sale By Owner")
            elif s.signal_type == SignalType.TAX_DELINQUENT:
                owed = s.details.get('amount_owed', 0)
                signal_summary.append(f"Tax delinquent: ${owed:,.0f}")
            elif s.signal_type == SignalType.PRICE_REDUCTION:
                pct = s.details.get('reduction_pct', 0)
                signal_summary.append(f"Price reduced {pct}%")
            else:
                signal_summary.append(s.signal_type.value.replace('_', ' ').title())
        
        # Get recommended approach
        approach = self.APPROACHES.get(primary.signal_type, "Standard outreach")
        
        prospect = ScoredProspect(
            id=str(uuid.uuid4())[:12],
            address=primary.address,
            owner_name=primary.owner_name,
            owner_phone=primary.owner_phone,
            owner_email=primary.owner_email,
            mailing_address=primary.mailing_address,
            prospect_type=prospect_type,
            tier=tier,
            score=final_score,
            signals=[s.id for s in signals],
            signal_summary=signal_summary,
            property_value=primary.property_value,
            equity_estimate=primary.equity_estimate,
            recommended_approach=approach,
            data_quality=data_quality
        )
        
        self.prospects[prospect.id] = prospect
        self._save_prospects()
        
        return prospect
    
    def get_prospects_by_tier(self, tier: ProspectTier) -> List[ScoredProspect]:
        """Get prospects by tier."""
        return [p for p in self.prospects.values() if p.tier == tier]
    
    def get_hot_prospects(self, limit: int = 50) -> List[ScoredProspect]:
        """Get top prospects for immediate outreach."""
        prospects = [p for p in self.prospects.values() if p.status == 'new']
        prospects.sort(key=lambda p: (p.score, p.data_quality), reverse=True)
        return prospects[:limit]
    
    def get_prospects_by_type(self, prospect_type: ProspectType) -> List[ScoredProspect]:
        """Get prospects by type."""
        return [p for p in self.prospects.values() if p.prospect_type == prospect_type]
    
    def update_prospect_status(self, prospect_id: str, status: str, notes: str = ""):
        """Update prospect status after contact."""
        prospect = self.prospects.get(prospect_id)
        if prospect:
            prospect.status = status
            prospect.contact_attempts += 1
            prospect.last_contact = datetime.now()
            prospect.updated_at = datetime.now()
            if notes:
                prospect.notes = notes
            self._save_prospects()
    
    def get_follow_up_list(self) -> List[ScoredProspect]:
        """Get prospects needing follow-up."""
        cutoff = datetime.now() - timedelta(days=7)
        prospects = [
            p for p in self.prospects.values()
            if p.status in ['contacted', 'follow_up'] 
            and p.last_contact and p.last_contact < cutoff
        ]
        prospects.sort(key=lambda p: p.score, reverse=True)
        return prospects
    
    def get_prospect_stats(self) -> Dict:
        """Get prospect statistics."""
        total = len(self.prospects)
        
        by_tier = {}
        for tier in ProspectTier:
            by_tier[tier.value] = len(self.get_prospects_by_tier(tier))
        
        by_type = {}
        for ptype in ProspectType:
            by_type[ptype.value] = len(self.get_prospects_by_type(ptype))
        
        by_status = {}
        for p in self.prospects.values():
            if p.status not in by_status:
                by_status[p.status] = 0
            by_status[p.status] += 1
        
        # Value opportunity
        total_value = sum(p.property_value for p in self.prospects.values())
        hot_value = sum(p.property_value for p in self.get_hot_prospects(100))
        
        return {
            'total_prospects': total,
            'by_tier': by_tier,
            'by_type': by_type,
            'by_status': by_status,
            'total_property_value': total_value,
            'hot_prospect_value': hot_value,
            'avg_score': sum(p.score for p in self.prospects.values()) / total if total else 0
        }
