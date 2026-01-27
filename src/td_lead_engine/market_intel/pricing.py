"""Property pricing analysis and predictions."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import statistics


@dataclass
class Comparable:
    """A comparable property for analysis."""
    address: str
    sale_price: float
    sale_date: datetime
    sqft: int
    beds: int
    baths: float
    year_built: int
    lot_size: int = 0
    distance_miles: float = 0
    days_on_market: int = 0
    adjustments: Dict[str, float] = field(default_factory=dict)
    adjusted_price: float = 0


@dataclass
class ComparableAnalysis:
    """Result of comparable analysis."""
    subject_address: str
    comps: List[Comparable]
    suggested_price: float
    price_range_low: float
    price_range_high: float
    confidence: float
    price_per_sqft: float
    analysis_date: datetime = field(default_factory=datetime.now)


class PricePredictor:
    """Predict property prices using comparables and market data."""
    
    # Adjustment factors per unit
    ADJUSTMENTS = {
        'sqft': 100,  # $ per sqft difference
        'beds': 5000,  # $ per bedroom
        'baths': 7500,  # $ per bathroom
        'garage': 10000,  # $ per garage space
        'pool': 15000,  # $ for pool
        'year_built': 500,  # $ per year newer
        'lot_size': 2,  # $ per sqft of lot
        'condition': {  # Multipliers
            'excellent': 1.05,
            'good': 1.00,
            'average': 0.95,
            'fair': 0.90,
            'poor': 0.80
        }
    }
    
    def __init__(self, storage_path: str = "data/market_intel"):
        self.storage_path = storage_path
        self.sales_history: List[Dict] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load sales history from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/sales_history.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                self.sales_history = json.load(f)
    
    def _save_data(self):
        """Save sales history to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        with open(f"{self.storage_path}/sales_history.json", 'w') as f:
            json.dump(self.sales_history[-50000:], f, indent=2)
    
    def add_sale(
        self,
        address: str,
        sale_price: float,
        sale_date: datetime,
        sqft: int,
        beds: int,
        baths: float,
        year_built: int,
        **kwargs
    ):
        """Add a sale to history."""
        sale = {
            'address': address,
            'sale_price': sale_price,
            'sale_date': sale_date.isoformat(),
            'sqft': sqft,
            'beds': beds,
            'baths': baths,
            'year_built': year_built,
            'lot_size': kwargs.get('lot_size', 0),
            'city': kwargs.get('city', ''),
            'zip_code': kwargs.get('zip_code', ''),
            'neighborhood': kwargs.get('neighborhood', ''),
            'property_type': kwargs.get('property_type', 'single_family'),
            'days_on_market': kwargs.get('days_on_market', 0),
            'lat': kwargs.get('lat', 0),
            'lng': kwargs.get('lng', 0)
        }
        self.sales_history.append(sale)
        self._save_data()
    
    def find_comparables(
        self,
        subject: Dict,
        max_comps: int = 6,
        max_age_months: int = 6,
        price_range_pct: float = 0.25
    ) -> List[Comparable]:
        """Find comparable properties for a subject."""
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_months * 30)
        
        # Filter potential comps
        candidates = []
        for sale in self.sales_history:
            sale_date = datetime.fromisoformat(sale['sale_date'])
            
            # Must be recent
            if sale_date < cutoff_date:
                continue
            
            # Must be same area (zip or neighborhood)
            if subject.get('zip_code') and sale.get('zip_code') != subject.get('zip_code'):
                if subject.get('neighborhood') and sale.get('neighborhood') != subject.get('neighborhood'):
                    continue
            
            # Must be similar size (within 30%)
            if subject.get('sqft'):
                size_diff = abs(sale['sqft'] - subject['sqft']) / subject['sqft']
                if size_diff > 0.3:
                    continue
            
            # Must be similar beds (within 1)
            if subject.get('beds'):
                if abs(sale['beds'] - subject['beds']) > 1:
                    continue
            
            candidates.append(sale)
        
        # Score and sort candidates
        scored = []
        for sale in candidates:
            score = self._score_comp(subject, sale)
            scored.append((sale, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to Comparable objects
        comps = []
        for sale, score in scored[:max_comps]:
            comp = Comparable(
                address=sale['address'],
                sale_price=sale['sale_price'],
                sale_date=datetime.fromisoformat(sale['sale_date']),
                sqft=sale['sqft'],
                beds=sale['beds'],
                baths=sale['baths'],
                year_built=sale['year_built'],
                lot_size=sale.get('lot_size', 0),
                days_on_market=sale.get('days_on_market', 0)
            )
            
            # Calculate adjustments
            comp.adjustments = self._calculate_adjustments(subject, sale)
            comp.adjusted_price = sale['sale_price'] + sum(comp.adjustments.values())
            
            comps.append(comp)
        
        return comps
    
    def _score_comp(self, subject: Dict, comp: Dict) -> float:
        """Score how good a comparable is."""
        score = 100
        
        # Size similarity
        if subject.get('sqft') and comp.get('sqft'):
            size_diff = abs(comp['sqft'] - subject['sqft']) / subject['sqft']
            score -= size_diff * 30
        
        # Bed/bath similarity
        if subject.get('beds'):
            score -= abs(comp['beds'] - subject['beds']) * 5
        if subject.get('baths'):
            score -= abs(comp['baths'] - subject['baths']) * 3
        
        # Age similarity
        if subject.get('year_built') and comp.get('year_built'):
            age_diff = abs(comp['year_built'] - subject['year_built'])
            score -= min(age_diff, 20)
        
        # Recency bonus
        sale_date = datetime.fromisoformat(comp['sale_date'])
        days_ago = (datetime.now() - sale_date).days
        if days_ago < 30:
            score += 10
        elif days_ago < 60:
            score += 5
        
        return max(0, score)
    
    def _calculate_adjustments(self, subject: Dict, comp: Dict) -> Dict[str, float]:
        """Calculate price adjustments."""
        adjustments = {}
        
        # Square footage adjustment
        if subject.get('sqft') and comp.get('sqft'):
            sqft_diff = subject['sqft'] - comp['sqft']
            adjustments['sqft'] = sqft_diff * self.ADJUSTMENTS['sqft']
        
        # Bedroom adjustment
        if subject.get('beds') and comp.get('beds'):
            bed_diff = subject['beds'] - comp['beds']
            adjustments['beds'] = bed_diff * self.ADJUSTMENTS['beds']
        
        # Bathroom adjustment
        if subject.get('baths') and comp.get('baths'):
            bath_diff = subject['baths'] - comp['baths']
            adjustments['baths'] = bath_diff * self.ADJUSTMENTS['baths']
        
        # Year built adjustment
        if subject.get('year_built') and comp.get('year_built'):
            year_diff = subject['year_built'] - comp['year_built']
            adjustments['year_built'] = year_diff * self.ADJUSTMENTS['year_built']
        
        # Lot size adjustment
        if subject.get('lot_size') and comp.get('lot_size'):
            lot_diff = subject['lot_size'] - comp['lot_size']
            adjustments['lot_size'] = lot_diff * self.ADJUSTMENTS['lot_size']
        
        return adjustments
    
    def analyze_comparables(
        self,
        subject_address: str,
        subject: Dict,
        max_comps: int = 6
    ) -> ComparableAnalysis:
        """Perform comparable analysis."""
        comps = self.find_comparables(subject, max_comps)
        
        if not comps:
            return ComparableAnalysis(
                subject_address=subject_address,
                comps=[],
                suggested_price=0,
                price_range_low=0,
                price_range_high=0,
                confidence=0,
                price_per_sqft=0
            )
        
        adjusted_prices = [c.adjusted_price for c in comps]
        
        # Calculate suggested price (weighted by recency)
        weights = []
        for comp in comps:
            days_ago = (datetime.now() - comp.sale_date).days
            weight = max(1, 180 - days_ago) / 180
            weights.append(weight)
        
        weighted_sum = sum(p * w for p, w in zip(adjusted_prices, weights))
        total_weight = sum(weights)
        suggested_price = weighted_sum / total_weight if total_weight else 0
        
        # Calculate price range
        std_dev = statistics.stdev(adjusted_prices) if len(adjusted_prices) > 1 else suggested_price * 0.05
        price_range_low = suggested_price - std_dev
        price_range_high = suggested_price + std_dev
        
        # Calculate confidence (based on number and quality of comps)
        confidence = min(100, len(comps) * 15 + 10)
        if std_dev / suggested_price > 0.1:  # High variance
            confidence -= 20
        
        # Price per sqft
        if subject.get('sqft'):
            price_per_sqft = suggested_price / subject['sqft']
        else:
            price_per_sqft = 0
        
        return ComparableAnalysis(
            subject_address=subject_address,
            comps=comps,
            suggested_price=round(suggested_price, 0),
            price_range_low=round(price_range_low, 0),
            price_range_high=round(price_range_high, 0),
            confidence=round(confidence, 0),
            price_per_sqft=round(price_per_sqft, 2)
        )
    
    def get_price_history(
        self,
        zip_code: str = "",
        neighborhood: str = "",
        months: int = 12
    ) -> List[Dict]:
        """Get price history for an area."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=months * 30)
        
        sales = [
            s for s in self.sales_history
            if datetime.fromisoformat(s['sale_date']) >= cutoff
        ]
        
        if zip_code:
            sales = [s for s in sales if s.get('zip_code') == zip_code]
        elif neighborhood:
            sales = [s for s in sales if s.get('neighborhood') == neighborhood]
        
        # Group by month
        monthly = {}
        for sale in sales:
            month = datetime.fromisoformat(sale['sale_date']).strftime('%Y-%m')
            if month not in monthly:
                monthly[month] = []
            monthly[month].append(sale['sale_price'])
        
        history = []
        for month, prices in sorted(monthly.items()):
            history.append({
                'month': month,
                'median_price': statistics.median(prices),
                'avg_price': round(statistics.mean(prices), 0),
                'sales_count': len(prices)
            })
        
        return history
