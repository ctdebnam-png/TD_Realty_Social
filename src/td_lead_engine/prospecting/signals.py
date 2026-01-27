"""Signal detection from raw property and owner data."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class SignalType(Enum):
    """Types of lead signals."""
    # Seller signals
    LONG_TERM_OWNER = "long_term_owner"           # 10+ years ownership
    HIGH_EQUITY = "high_equity"                    # Significant equity built up
    ABSENTEE_OWNER = "absentee_owner"             # Owner lives elsewhere
    VACANT_PROPERTY = "vacant_property"            # Property appears vacant
    TAX_DELINQUENT = "tax_delinquent"             # Behind on taxes
    PRE_FORECLOSURE = "pre_foreclosure"           # NOD filed
    PROBATE = "probate"                           # Estate/inheritance
    DIVORCE = "divorce"                           # Divorce filing
    CODE_VIOLATION = "code_violation"             # City code issues
    EXPIRED_LISTING = "expired_listing"           # Failed to sell
    WITHDRAWN_LISTING = "withdrawn_listing"       # Pulled from market
    FSBO = "fsbo"                                 # For sale by owner
    PRICE_REDUCTION = "price_reduction"           # Motivated seller
    TIRED_LANDLORD = "tired_landlord"             # Rental property issues
    DOWNSIZING = "downsizing"                     # Large home, older owner
    UPSIZING = "upsizing"                         # Growing family signals
    RELOCATION = "relocation"                     # Job transfer signals
    
    # Buyer signals
    RENTER_LONG_TERM = "renter_long_term"         # Been renting 2+ years
    RENTAL_INCREASE = "rental_increase"           # Rent going up
    PREAPPROVAL = "preapproval"                   # Got preapproved
    SAVED_SEARCH = "saved_search"                 # Active property search
    OPEN_HOUSE_VISIT = "open_house_visit"         # Attended open house
    MULTIPLE_SHOWINGS = "multiple_showings"       # Viewing properties
    
    # Life event signals
    MARRIAGE = "marriage"                         # Recent marriage
    BIRTH = "birth"                               # New baby
    DEATH = "death"                               # Death in family
    JOB_CHANGE = "job_change"                     # New job
    RETIREMENT = "retirement"                     # Retiring
    EMPTY_NEST = "empty_nest"                     # Kids moved out
    
    # Property signals
    BUILDING_PERMIT = "building_permit"           # Major renovation
    SOLAR_PERMIT = "solar_permit"                 # Solar installation
    POOL_PERMIT = "pool_permit"                   # Pool installation
    NEW_LISTING = "new_listing"                   # Just listed


@dataclass
class LeadSignal:
    """A detected signal for a potential lead."""
    id: str
    signal_type: SignalType
    strength: int  # 1-100
    address: str
    owner_name: str = ""
    owner_phone: str = ""
    owner_email: str = ""
    mailing_address: str = ""
    property_value: float = 0
    equity_estimate: float = 0
    details: Dict = field(default_factory=dict)
    source_records: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = None


class SignalDetector:
    """Detect lead signals from raw data records."""
    
    # Signal strength weights
    SIGNAL_WEIGHTS = {
        SignalType.PRE_FORECLOSURE: 95,
        SignalType.PROBATE: 90,
        SignalType.DIVORCE: 85,
        SignalType.EXPIRED_LISTING: 85,
        SignalType.FSBO: 80,
        SignalType.TAX_DELINQUENT: 75,
        SignalType.ABSENTEE_OWNER: 70,
        SignalType.HIGH_EQUITY: 70,
        SignalType.LONG_TERM_OWNER: 65,
        SignalType.PRICE_REDUCTION: 65,
        SignalType.TIRED_LANDLORD: 60,
        SignalType.VACANT_PROPERTY: 60,
        SignalType.CODE_VIOLATION: 55,
        SignalType.BUILDING_PERMIT: 50,
        SignalType.DOWNSIZING: 50,
        SignalType.RELOCATION: 45,
        SignalType.WITHDRAWN_LISTING: 40,
    }
    
    def __init__(self, storage_path: str = "data/prospecting"):
        self.storage_path = storage_path
        self.signals: Dict[str, LeadSignal] = {}
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_signals()
    
    def _load_signals(self):
        """Load detected signals."""
        signals_file = f"{self.storage_path}/signals.json"
        if os.path.exists(signals_file):
            with open(signals_file, 'r') as f:
                data = json.load(f)
                for s in data:
                    signal = LeadSignal(
                        id=s['id'],
                        signal_type=SignalType(s['signal_type']),
                        strength=s['strength'],
                        address=s['address'],
                        owner_name=s.get('owner_name', ''),
                        owner_phone=s.get('owner_phone', ''),
                        owner_email=s.get('owner_email', ''),
                        mailing_address=s.get('mailing_address', ''),
                        property_value=s.get('property_value', 0),
                        equity_estimate=s.get('equity_estimate', 0),
                        details=s.get('details', {}),
                        source_records=s.get('source_records', []),
                        detected_at=datetime.fromisoformat(s['detected_at']),
                        expires_at=datetime.fromisoformat(s['expires_at']) if s.get('expires_at') else None
                    )
                    self.signals[signal.id] = signal
    
    def _save_signals(self):
        """Save detected signals."""
        signals_data = [
            {
                'id': s.id,
                'signal_type': s.signal_type.value,
                'strength': s.strength,
                'address': s.address,
                'owner_name': s.owner_name,
                'owner_phone': s.owner_phone,
                'owner_email': s.owner_email,
                'mailing_address': s.mailing_address,
                'property_value': s.property_value,
                'equity_estimate': s.equity_estimate,
                'details': s.details,
                'source_records': s.source_records,
                'detected_at': s.detected_at.isoformat(),
                'expires_at': s.expires_at.isoformat() if s.expires_at else None
            }
            for s in self.signals.values()
        ]
        
        with open(f"{self.storage_path}/signals.json", 'w') as f:
            json.dump(signals_data, f, indent=2)
    
    def detect_from_auditor_record(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from county auditor data."""
        signals = []
        address = record.get('address', '')
        owner = record.get('owner_name', '')
        
        # Long-term owner (10+ years)
        sale_date = record.get('last_sale_date')
        if sale_date:
            try:
                years_owned = (datetime.now() - datetime.fromisoformat(sale_date)).days / 365
                if years_owned >= 10:
                    signals.append(self._create_signal(
                        SignalType.LONG_TERM_OWNER,
                        address, owner,
                        details={'years_owned': round(years_owned, 1)},
                        property_value=record.get('market_value', 0)
                    ))
            except:
                pass
        
        # High equity
        market_value = record.get('market_value', 0)
        last_sale_price = record.get('last_sale_price', 0)
        if market_value > 0 and last_sale_price > 0:
            equity = market_value - last_sale_price
            equity_pct = equity / market_value * 100
            if equity_pct > 40:
                signals.append(self._create_signal(
                    SignalType.HIGH_EQUITY,
                    address, owner,
                    details={'equity': equity, 'equity_pct': round(equity_pct, 1)},
                    property_value=market_value,
                    equity_estimate=equity
                ))
        
        # Absentee owner
        mailing_address = record.get('mailing_address', '')
        if mailing_address and address:
            if not self._addresses_match(address, mailing_address):
                signals.append(self._create_signal(
                    SignalType.ABSENTEE_OWNER,
                    address, owner,
                    details={'mailing_address': mailing_address},
                    property_value=market_value,
                    mailing_address=mailing_address
                ))
        
        return signals
    
    def detect_from_court_record(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from court records."""
        signals = []
        case_type = record.get('case_type', '').lower()
        address = record.get('property_address', record.get('address', ''))
        parties = record.get('parties', [])
        
        owner = parties[0] if parties else ''
        
        if 'foreclosure' in case_type or 'mortgage' in case_type:
            signals.append(self._create_signal(
                SignalType.PRE_FORECLOSURE,
                address, owner,
                details={
                    'case_number': record.get('case_number', ''),
                    'filing_date': record.get('filing_date', ''),
                    'lender': record.get('plaintiff', '')
                }
            ))
        
        if 'probate' in case_type or 'estate' in case_type:
            signals.append(self._create_signal(
                SignalType.PROBATE,
                address, owner,
                details={
                    'case_number': record.get('case_number', ''),
                    'decedent': record.get('decedent', owner)
                }
            ))
        
        if 'divorce' in case_type or 'dissolution' in case_type:
            signals.append(self._create_signal(
                SignalType.DIVORCE,
                address, owner,
                details={
                    'case_number': record.get('case_number', ''),
                    'parties': parties
                }
            ))
        
        return signals
    
    def detect_from_listing(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from listing data."""
        signals = []
        status = record.get('status', '').lower()
        address = record.get('address', '')
        
        if status in ['expired', 'cancelled']:
            signals.append(self._create_signal(
                SignalType.EXPIRED_LISTING,
                address, record.get('owner', ''),
                details={
                    'list_price': record.get('list_price', 0),
                    'days_on_market': record.get('days_on_market', 0),
                    'expired_date': record.get('status_date', ''),
                    'listing_agent': record.get('listing_agent', '')
                },
                property_value=record.get('list_price', 0)
            ))
        
        if status == 'withdrawn':
            signals.append(self._create_signal(
                SignalType.WITHDRAWN_LISTING,
                address, record.get('owner', ''),
                details={
                    'list_price': record.get('list_price', 0),
                    'withdrawn_date': record.get('status_date', '')
                },
                property_value=record.get('list_price', 0)
            ))
        
        # Price reduction
        original_price = record.get('original_price', 0)
        current_price = record.get('current_price', record.get('list_price', 0))
        if original_price > 0 and current_price < original_price:
            reduction = original_price - current_price
            reduction_pct = reduction / original_price * 100
            if reduction_pct >= 5:
                signals.append(self._create_signal(
                    SignalType.PRICE_REDUCTION,
                    address, record.get('owner', ''),
                    details={
                        'original_price': original_price,
                        'current_price': current_price,
                        'reduction': reduction,
                        'reduction_pct': round(reduction_pct, 1)
                    },
                    property_value=current_price
                ))
        
        return signals
    
    def detect_from_fsbo(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from FSBO listings."""
        signals = []
        address = record.get('address', '')
        
        signals.append(self._create_signal(
            SignalType.FSBO,
            address, record.get('seller_name', ''),
            details={
                'asking_price': record.get('price', 0),
                'source': record.get('source', 'unknown'),
                'listing_url': record.get('url', ''),
                'phone': record.get('phone', ''),
                'days_listed': record.get('days_listed', 0)
            },
            property_value=record.get('price', 0),
            owner_phone=record.get('phone', '')
        ))
        
        return signals
    
    def detect_from_permit(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from building permits."""
        signals = []
        permit_type = record.get('permit_type', '').lower()
        address = record.get('address', '')
        owner = record.get('owner', record.get('applicant', ''))
        
        signal_type = None
        if any(t in permit_type for t in ['remodel', 'renovation', 'addition', 'roof']):
            signal_type = SignalType.BUILDING_PERMIT
        elif 'solar' in permit_type:
            signal_type = SignalType.SOLAR_PERMIT
        elif 'pool' in permit_type:
            signal_type = SignalType.POOL_PERMIT
        
        if signal_type:
            signals.append(self._create_signal(
                signal_type,
                address, owner,
                details={
                    'permit_number': record.get('permit_number', ''),
                    'permit_type': permit_type,
                    'value': record.get('value', 0),
                    'issue_date': record.get('issue_date', '')
                }
            ))
        
        return signals
    
    def detect_from_tax_record(self, record: Dict) -> List[LeadSignal]:
        """Detect signals from tax delinquency records."""
        signals = []
        address = record.get('address', '')
        owner = record.get('owner', '')
        
        amount_owed = record.get('amount_owed', 0)
        if amount_owed > 0:
            signals.append(self._create_signal(
                SignalType.TAX_DELINQUENT,
                address, owner,
                details={
                    'amount_owed': amount_owed,
                    'years_delinquent': record.get('years', 1),
                    'parcel_id': record.get('parcel_id', '')
                },
                property_value=record.get('market_value', 0)
            ))
        
        return signals
    
    def _create_signal(
        self,
        signal_type: SignalType,
        address: str,
        owner_name: str,
        details: Dict = None,
        property_value: float = 0,
        equity_estimate: float = 0,
        mailing_address: str = "",
        owner_phone: str = ""
    ) -> LeadSignal:
        """Create a new signal."""
        import uuid
        
        strength = self.SIGNAL_WEIGHTS.get(signal_type, 50)
        
        # Set expiration based on signal type
        expires_days = 90  # Default 90 days
        if signal_type in [SignalType.EXPIRED_LISTING, SignalType.FSBO]:
            expires_days = 30
        elif signal_type in [SignalType.PRE_FORECLOSURE, SignalType.PROBATE]:
            expires_days = 180
        
        signal = LeadSignal(
            id=str(uuid.uuid4())[:12],
            signal_type=signal_type,
            strength=strength,
            address=address,
            owner_name=owner_name,
            owner_phone=owner_phone,
            mailing_address=mailing_address,
            property_value=property_value,
            equity_estimate=equity_estimate,
            details=details or {},
            expires_at=datetime.now() + timedelta(days=expires_days)
        )
        
        self.signals[signal.id] = signal
        self._save_signals()
        
        return signal
    
    def _addresses_match(self, addr1: str, addr2: str) -> bool:
        """Check if two addresses are the same property."""
        # Normalize addresses
        addr1_norm = addr1.lower().replace('.', '').replace(',', '').strip()
        addr2_norm = addr2.lower().replace('.', '').replace(',', '').strip()
        
        # Simple check - could be enhanced with address parsing
        return addr1_norm[:30] == addr2_norm[:30]
    
    def get_signals_by_type(self, signal_type: SignalType) -> List[LeadSignal]:
        """Get all signals of a specific type."""
        return [s for s in self.signals.values() if s.signal_type == signal_type]
    
    def get_signals_for_address(self, address: str) -> List[LeadSignal]:
        """Get all signals for an address."""
        address_lower = address.lower()
        return [s for s in self.signals.values() if address_lower in s.address.lower()]
    
    def get_active_signals(self) -> List[LeadSignal]:
        """Get non-expired signals."""
        now = datetime.now()
        return [s for s in self.signals.values() if not s.expires_at or s.expires_at > now]
    
    def get_high_priority_signals(self, min_strength: int = 70) -> List[LeadSignal]:
        """Get high-priority signals."""
        signals = self.get_active_signals()
        signals = [s for s in signals if s.strength >= min_strength]
        signals.sort(key=lambda s: s.strength, reverse=True)
        return signals
