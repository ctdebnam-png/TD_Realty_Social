"""Market trends analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import statistics


class MarketIndicator(Enum):
    """Market indicators."""
    MEDIAN_PRICE = "median_price"
    AVG_PRICE = "avg_price"
    PRICE_PER_SQFT = "price_per_sqft"
    DAYS_ON_MARKET = "days_on_market"
    INVENTORY = "inventory"
    NEW_LISTINGS = "new_listings"
    PENDING_SALES = "pending_sales"
    CLOSED_SALES = "closed_sales"
    LIST_TO_SALE_RATIO = "list_to_sale_ratio"
    MONTHS_SUPPLY = "months_supply"


@dataclass
class MarketDataPoint:
    """A market data point."""
    date: datetime
    indicator: MarketIndicator
    value: float
    area: str = ""
    property_type: str = ""


@dataclass
class TrendAnalysis:
    """Market trend analysis results."""
    indicator: MarketIndicator
    area: str
    current_value: float
    previous_value: float
    change_amount: float
    change_percent: float
    trend_direction: str  # up, down, stable
    forecast: float = 0
    analysis_date: datetime = field(default_factory=datetime.now)


class MarketTrends:
    """Analyze real estate market trends."""
    
    def __init__(self, storage_path: str = "data/market_intel"):
        self.storage_path = storage_path
        self.data_points: List[MarketDataPoint] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load market data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/market_data.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for d in data:
                    point = MarketDataPoint(
                        date=datetime.fromisoformat(d['date']),
                        indicator=MarketIndicator(d['indicator']),
                        value=d['value'],
                        area=d.get('area', ''),
                        property_type=d.get('property_type', '')
                    )
                    self.data_points.append(point)
    
    def _save_data(self):
        """Save market data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'date': d.date.isoformat(),
                'indicator': d.indicator.value,
                'value': d.value,
                'area': d.area,
                'property_type': d.property_type
            }
            for d in self.data_points[-100000:]  # Keep last 100k points
        ]
        
        with open(f"{self.storage_path}/market_data.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def record_data(
        self,
        indicator: MarketIndicator,
        value: float,
        area: str = "",
        property_type: str = "",
        date: datetime = None
    ):
        """Record a market data point."""
        point = MarketDataPoint(
            date=date or datetime.now(),
            indicator=indicator,
            value=value,
            area=area,
            property_type=property_type
        )
        self.data_points.append(point)
        self._save_data()
    
    def bulk_record(self, data: List[Dict]):
        """Record multiple data points."""
        for d in data:
            point = MarketDataPoint(
                date=datetime.fromisoformat(d['date']) if isinstance(d['date'], str) else d['date'],
                indicator=MarketIndicator(d['indicator']) if isinstance(d['indicator'], str) else d['indicator'],
                value=d['value'],
                area=d.get('area', ''),
                property_type=d.get('property_type', '')
            )
            self.data_points.append(point)
        self._save_data()
    
    def get_trend(
        self,
        indicator: MarketIndicator,
        area: str = "",
        months: int = 12
    ) -> List[Dict]:
        """Get trend data for an indicator."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        points = [
            p for p in self.data_points
            if p.indicator == indicator
            and (not area or p.area == area)
            and start_date <= p.date <= end_date
        ]
        
        # Group by month
        monthly = {}
        for point in points:
            month_key = point.date.strftime('%Y-%m')
            if month_key not in monthly:
                monthly[month_key] = []
            monthly[month_key].append(point.value)
        
        # Calculate monthly averages
        trend = []
        for month, values in sorted(monthly.items()):
            trend.append({
                'month': month,
                'value': round(statistics.mean(values), 2),
                'count': len(values)
            })
        
        return trend
    
    def analyze_trend(
        self,
        indicator: MarketIndicator,
        area: str = "",
        compare_months: int = 3
    ) -> TrendAnalysis:
        """Analyze trend for an indicator."""
        now = datetime.now()
        current_start = now - timedelta(days=compare_months * 30)
        previous_start = current_start - timedelta(days=compare_months * 30)
        
        # Get current period data
        current_points = [
            p.value for p in self.data_points
            if p.indicator == indicator
            and (not area or p.area == area)
            and current_start <= p.date <= now
        ]
        
        # Get previous period data
        previous_points = [
            p.value for p in self.data_points
            if p.indicator == indicator
            and (not area or p.area == area)
            and previous_start <= p.date < current_start
        ]
        
        current_value = statistics.mean(current_points) if current_points else 0
        previous_value = statistics.mean(previous_points) if previous_points else 0
        
        change_amount = current_value - previous_value
        change_percent = (change_amount / previous_value * 100) if previous_value else 0
        
        # Determine trend direction
        if change_percent > 2:
            direction = "up"
        elif change_percent < -2:
            direction = "down"
        else:
            direction = "stable"
        
        # Simple forecast (linear extrapolation)
        forecast = current_value + change_amount
        
        return TrendAnalysis(
            indicator=indicator,
            area=area,
            current_value=round(current_value, 2),
            previous_value=round(previous_value, 2),
            change_amount=round(change_amount, 2),
            change_percent=round(change_percent, 1),
            trend_direction=direction,
            forecast=round(forecast, 2)
        )
    
    def get_market_snapshot(self, area: str = "") -> Dict:
        """Get current market snapshot."""
        snapshot = {}
        
        for indicator in MarketIndicator:
            analysis = self.analyze_trend(indicator, area, compare_months=1)
            snapshot[indicator.value] = {
                'current': analysis.current_value,
                'change_pct': analysis.change_percent,
                'trend': analysis.trend_direction
            }
        
        return {
            'area': area or 'All Areas',
            'date': datetime.now().isoformat(),
            'indicators': snapshot
        }
    
    def compare_areas(self, areas: List[str], indicator: MarketIndicator) -> Dict:
        """Compare indicator across areas."""
        comparison = []
        
        for area in areas:
            analysis = self.analyze_trend(indicator, area)
            comparison.append({
                'area': area,
                'value': analysis.current_value,
                'change_pct': analysis.change_percent,
                'trend': analysis.trend_direction
            })
        
        # Sort by value
        comparison.sort(key=lambda x: x['value'], reverse=True)
        
        return {
            'indicator': indicator.value,
            'areas': comparison
        }
    
    def get_market_health_score(self, area: str = "") -> Dict:
        """Calculate overall market health score."""
        scores = {}
        
        # Days on market (lower is better for sellers, higher for buyers)
        dom_analysis = self.analyze_trend(MarketIndicator.DAYS_ON_MARKET, area)
        if dom_analysis.current_value < 30:
            scores['dom'] = 90  # Hot market
        elif dom_analysis.current_value < 60:
            scores['dom'] = 70
        elif dom_analysis.current_value < 90:
            scores['dom'] = 50
        else:
            scores['dom'] = 30  # Slow market
        
        # Price trend
        price_analysis = self.analyze_trend(MarketIndicator.MEDIAN_PRICE, area)
        if price_analysis.change_percent > 5:
            scores['price'] = 90
        elif price_analysis.change_percent > 0:
            scores['price'] = 70
        elif price_analysis.change_percent > -5:
            scores['price'] = 50
        else:
            scores['price'] = 30
        
        # Inventory/Months supply
        supply_analysis = self.analyze_trend(MarketIndicator.MONTHS_SUPPLY, area)
        if supply_analysis.current_value < 3:
            scores['supply'] = 90  # Seller's market
        elif supply_analysis.current_value < 6:
            scores['supply'] = 70  # Balanced
        else:
            scores['supply'] = 40  # Buyer's market
        
        # List to sale ratio
        ratio_analysis = self.analyze_trend(MarketIndicator.LIST_TO_SALE_RATIO, area)
        if ratio_analysis.current_value > 100:
            scores['ratio'] = 90  # Above asking
        elif ratio_analysis.current_value > 98:
            scores['ratio'] = 80
        elif ratio_analysis.current_value > 95:
            scores['ratio'] = 60
        else:
            scores['ratio'] = 40
        
        overall = statistics.mean(scores.values()) if scores else 50
        
        # Determine market type
        if overall >= 75:
            market_type = "Strong Seller's Market"
        elif overall >= 60:
            market_type = "Seller's Market"
        elif overall >= 45:
            market_type = "Balanced Market"
        elif overall >= 30:
            market_type = "Buyer's Market"
        else:
            market_type = "Strong Buyer's Market"
        
        return {
            'area': area or 'All Areas',
            'overall_score': round(overall, 1),
            'market_type': market_type,
            'component_scores': scores,
            'analysis_date': datetime.now().isoformat()
        }
