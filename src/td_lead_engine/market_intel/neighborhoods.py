"""Neighborhood analysis and statistics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import statistics


@dataclass
class NeighborhoodStats:
    """Statistics for a neighborhood."""
    name: str
    city: str
    zip_code: str = ""
    median_price: float = 0
    avg_price: float = 0
    price_per_sqft: float = 0
    avg_days_on_market: int = 0
    active_listings: int = 0
    sold_last_30: int = 0
    sold_last_90: int = 0
    avg_home_size: int = 0
    avg_lot_size: int = 0
    year_built_median: int = 0
    school_rating: float = 0
    crime_score: float = 0
    walkability_score: int = 0
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class NeighborhoodComparison:
    """Comparison between neighborhoods."""
    neighborhoods: List[str]
    metric: str
    values: Dict[str, float]
    winner: str
    analysis: str


class NeighborhoodAnalyzer:
    """Analyze neighborhoods and provide insights."""
    
    def __init__(self, storage_path: str = "data/market_intel"):
        self.storage_path = storage_path
        self.neighborhoods: Dict[str, NeighborhoodStats] = {}
        self.sales_data: List[Dict] = []
        
        self._load_data()
    
    def _load_data(self):
        """Load neighborhood data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/neighborhoods.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for n in data.get('neighborhoods', []):
                    stats = NeighborhoodStats(
                        name=n['name'],
                        city=n.get('city', ''),
                        zip_code=n.get('zip_code', ''),
                        median_price=n.get('median_price', 0),
                        avg_price=n.get('avg_price', 0),
                        price_per_sqft=n.get('price_per_sqft', 0),
                        avg_days_on_market=n.get('avg_days_on_market', 0),
                        active_listings=n.get('active_listings', 0),
                        sold_last_30=n.get('sold_last_30', 0),
                        sold_last_90=n.get('sold_last_90', 0),
                        avg_home_size=n.get('avg_home_size', 0),
                        avg_lot_size=n.get('avg_lot_size', 0),
                        year_built_median=n.get('year_built_median', 0),
                        school_rating=n.get('school_rating', 0),
                        crime_score=n.get('crime_score', 0),
                        walkability_score=n.get('walkability_score', 0),
                        updated_at=datetime.fromisoformat(n['updated_at']) if n.get('updated_at') else datetime.now()
                    )
                    self.neighborhoods[stats.name] = stats
                
                self.sales_data = data.get('sales_data', [])
    
    def _save_data(self):
        """Save neighborhood data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        neighborhoods_data = [
            {
                'name': n.name,
                'city': n.city,
                'zip_code': n.zip_code,
                'median_price': n.median_price,
                'avg_price': n.avg_price,
                'price_per_sqft': n.price_per_sqft,
                'avg_days_on_market': n.avg_days_on_market,
                'active_listings': n.active_listings,
                'sold_last_30': n.sold_last_30,
                'sold_last_90': n.sold_last_90,
                'avg_home_size': n.avg_home_size,
                'avg_lot_size': n.avg_lot_size,
                'year_built_median': n.year_built_median,
                'school_rating': n.school_rating,
                'crime_score': n.crime_score,
                'walkability_score': n.walkability_score,
                'updated_at': n.updated_at.isoformat()
            }
            for n in self.neighborhoods.values()
        ]
        
        with open(f"{self.storage_path}/neighborhoods.json", 'w') as f:
            json.dump({
                'neighborhoods': neighborhoods_data,
                'sales_data': self.sales_data[-10000:]
            }, f, indent=2)
    
    def update_neighborhood(
        self,
        name: str,
        **kwargs
    ) -> NeighborhoodStats:
        """Update or create neighborhood stats."""
        if name in self.neighborhoods:
            stats = self.neighborhoods[name]
            for key, value in kwargs.items():
                if hasattr(stats, key):
                    setattr(stats, key, value)
            stats.updated_at = datetime.now()
        else:
            stats = NeighborhoodStats(
                name=name,
                city=kwargs.get('city', ''),
                zip_code=kwargs.get('zip_code', ''),
                median_price=kwargs.get('median_price', 0),
                avg_price=kwargs.get('avg_price', 0),
                price_per_sqft=kwargs.get('price_per_sqft', 0),
                avg_days_on_market=kwargs.get('avg_days_on_market', 0),
                active_listings=kwargs.get('active_listings', 0),
                sold_last_30=kwargs.get('sold_last_30', 0),
                sold_last_90=kwargs.get('sold_last_90', 0),
                avg_home_size=kwargs.get('avg_home_size', 0),
                avg_lot_size=kwargs.get('avg_lot_size', 0),
                year_built_median=kwargs.get('year_built_median', 0),
                school_rating=kwargs.get('school_rating', 0),
                crime_score=kwargs.get('crime_score', 0),
                walkability_score=kwargs.get('walkability_score', 0)
            )
            self.neighborhoods[name] = stats
        
        self._save_data()
        return stats
    
    def get_neighborhood(self, name: str) -> Optional[NeighborhoodStats]:
        """Get neighborhood stats."""
        return self.neighborhoods.get(name)
    
    def compare_neighborhoods(
        self,
        names: List[str],
        metrics: List[str] = None
    ) -> Dict:
        """Compare multiple neighborhoods."""
        if not metrics:
            metrics = ['median_price', 'price_per_sqft', 'avg_days_on_market', 'school_rating']
        
        comparison = {metric: {} for metric in metrics}
        
        for name in names:
            stats = self.neighborhoods.get(name)
            if stats:
                for metric in metrics:
                    value = getattr(stats, metric, 0)
                    comparison[metric][name] = value
        
        # Determine winners
        winners = {}
        for metric, values in comparison.items():
            if values:
                # For days on market, lower is better
                if metric == 'avg_days_on_market':
                    winners[metric] = min(values, key=values.get)
                else:
                    winners[metric] = max(values, key=values.get)
        
        return {
            'neighborhoods': names,
            'metrics': comparison,
            'winners': winners
        }
    
    def find_similar_neighborhoods(
        self,
        name: str,
        limit: int = 5
    ) -> List[Dict]:
        """Find neighborhoods similar to given one."""
        target = self.neighborhoods.get(name)
        if not target:
            return []
        
        similarities = []
        
        for n_name, stats in self.neighborhoods.items():
            if n_name == name:
                continue
            
            # Calculate similarity score
            score = 0
            
            # Price similarity (within 20%)
            if target.median_price > 0 and stats.median_price > 0:
                price_diff = abs(target.median_price - stats.median_price) / target.median_price
                if price_diff < 0.2:
                    score += 30 * (1 - price_diff)
            
            # Price per sqft similarity
            if target.price_per_sqft > 0 and stats.price_per_sqft > 0:
                ppsf_diff = abs(target.price_per_sqft - stats.price_per_sqft) / target.price_per_sqft
                if ppsf_diff < 0.2:
                    score += 20 * (1 - ppsf_diff)
            
            # School rating similarity
            if target.school_rating > 0 and stats.school_rating > 0:
                school_diff = abs(target.school_rating - stats.school_rating) / 10
                score += 25 * (1 - school_diff)
            
            # Same city bonus
            if target.city == stats.city:
                score += 25
            
            similarities.append({
                'name': n_name,
                'city': stats.city,
                'similarity_score': round(score, 1),
                'median_price': stats.median_price,
                'price_per_sqft': stats.price_per_sqft
            })
        
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarities[:limit]
    
    def get_neighborhood_report(self, name: str) -> Dict:
        """Generate comprehensive neighborhood report."""
        stats = self.neighborhoods.get(name)
        if not stats:
            return {}
        
        # Calculate market activity score
        activity_score = 0
        if stats.sold_last_30 > 10:
            activity_score = 90
        elif stats.sold_last_30 > 5:
            activity_score = 70
        elif stats.sold_last_30 > 2:
            activity_score = 50
        else:
            activity_score = 30
        
        # Calculate affordability relative to city average
        city_neighborhoods = [n for n in self.neighborhoods.values() if n.city == stats.city]
        if city_neighborhoods:
            city_avg_price = statistics.mean([n.median_price for n in city_neighborhoods if n.median_price > 0])
            affordability = 'Average'
            if stats.median_price < city_avg_price * 0.8:
                affordability = 'Below Average (More Affordable)'
            elif stats.median_price > city_avg_price * 1.2:
                affordability = 'Above Average (Premium)'
        else:
            city_avg_price = 0
            affordability = 'Unknown'
        
        return {
            'neighborhood': name,
            'city': stats.city,
            'zip_code': stats.zip_code,
            'pricing': {
                'median_price': stats.median_price,
                'avg_price': stats.avg_price,
                'price_per_sqft': stats.price_per_sqft,
                'city_avg_price': round(city_avg_price, 0),
                'affordability': affordability
            },
            'market_activity': {
                'active_listings': stats.active_listings,
                'sold_last_30': stats.sold_last_30,
                'sold_last_90': stats.sold_last_90,
                'avg_days_on_market': stats.avg_days_on_market,
                'activity_score': activity_score
            },
            'property_characteristics': {
                'avg_home_size': stats.avg_home_size,
                'avg_lot_size': stats.avg_lot_size,
                'year_built_median': stats.year_built_median
            },
            'livability': {
                'school_rating': stats.school_rating,
                'crime_score': stats.crime_score,
                'walkability_score': stats.walkability_score
            },
            'similar_neighborhoods': self.find_similar_neighborhoods(name, 3),
            'updated_at': stats.updated_at.isoformat()
        }
    
    def get_top_neighborhoods(
        self,
        city: str = "",
        metric: str = "median_price",
        limit: int = 10,
        ascending: bool = False
    ) -> List[Dict]:
        """Get top neighborhoods by metric."""
        neighborhoods = list(self.neighborhoods.values())
        
        if city:
            neighborhoods = [n for n in neighborhoods if n.city == city]
        
        neighborhoods.sort(key=lambda n: getattr(n, metric, 0), reverse=not ascending)
        
        return [
            {
                'name': n.name,
                'city': n.city,
                metric: getattr(n, metric, 0)
            }
            for n in neighborhoods[:limit]
        ]
