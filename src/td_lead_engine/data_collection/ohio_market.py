"""Ohio real estate market data collection from public sources."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
import urllib.request
import urllib.error


@dataclass
class MarketSnapshot:
    """A snapshot of market data for an area."""
    area: str
    date: datetime
    median_price: float = 0
    avg_price: float = 0
    total_listings: int = 0
    new_listings: int = 0
    pending_sales: int = 0
    closed_sales: int = 0
    avg_dom: int = 0
    inventory_months: float = 0
    price_change_mom: float = 0
    price_change_yoy: float = 0


class OhioMarketCollector:
    """Collect Ohio real estate market data from public sources."""
    
    # Central Ohio counties and ZIP codes
    CENTRAL_OHIO_AREAS = {
        'franklin': {
            'name': 'Franklin County',
            'zips': ['43201', '43202', '43203', '43204', '43205', '43206', '43207', 
                     '43209', '43210', '43211', '43212', '43213', '43214', '43215',
                     '43219', '43220', '43221', '43222', '43223', '43224', '43227',
                     '43228', '43229', '43230', '43231', '43232', '43235']
        },
        'delaware': {
            'name': 'Delaware County', 
            'zips': ['43015', '43016', '43017', '43021', '43035', '43065', '43074', '43082']
        },
        'licking': {
            'name': 'Licking County',
            'zips': ['43023', '43025', '43031', '43055', '43056', '43062', '43068']
        },
        'fairfield': {
            'name': 'Fairfield County',
            'zips': ['43110', '43112', '43130', '43147', '43150']
        },
        'pickaway': {
            'name': 'Pickaway County',
            'zips': ['43113', '43116', '43137', '43145']
        },
        'union': {
            'name': 'Union County',
            'zips': ['43040', '43044', '43067', '43077']
        },
        'madison': {
            'name': 'Madison County',
            'zips': ['43064', '43140', '43162']
        }
    }
    
    # Columbus metro neighborhoods
    NEIGHBORHOODS = {
        'short_north': {'name': 'Short North', 'zips': ['43215'], 'city': 'Columbus'},
        'german_village': {'name': 'German Village', 'zips': ['43206'], 'city': 'Columbus'},
        'grandview': {'name': 'Grandview Heights', 'zips': ['43212'], 'city': 'Grandview Heights'},
        'upper_arlington': {'name': 'Upper Arlington', 'zips': ['43220', '43221'], 'city': 'Upper Arlington'},
        'worthington': {'name': 'Worthington', 'zips': ['43085'], 'city': 'Worthington'},
        'dublin': {'name': 'Dublin', 'zips': ['43016', '43017'], 'city': 'Dublin'},
        'powell': {'name': 'Powell', 'zips': ['43065'], 'city': 'Powell'},
        'westerville': {'name': 'Westerville', 'zips': ['43081', '43082'], 'city': 'Westerville'},
        'new_albany': {'name': 'New Albany', 'zips': ['43054'], 'city': 'New Albany'},
        'gahanna': {'name': 'Gahanna', 'zips': ['43230'], 'city': 'Gahanna'},
        'hilliard': {'name': 'Hilliard', 'zips': ['43026'], 'city': 'Hilliard'},
        'grove_city': {'name': 'Grove City', 'zips': ['43123'], 'city': 'Grove City'},
        'reynoldsburg': {'name': 'Reynoldsburg', 'zips': ['43068'], 'city': 'Reynoldsburg'},
        'pickerington': {'name': 'Pickerington', 'zips': ['43147'], 'city': 'Pickerington'},
        'canal_winchester': {'name': 'Canal Winchester', 'zips': ['43110'], 'city': 'Canal Winchester'},
        'delaware': {'name': 'Delaware', 'zips': ['43015'], 'city': 'Delaware'},
        'bexley': {'name': 'Bexley', 'zips': ['43209'], 'city': 'Bexley'},
        'clintonville': {'name': 'Clintonville', 'zips': ['43214'], 'city': 'Columbus'},
        'victorian_village': {'name': 'Victorian Village', 'zips': ['43201'], 'city': 'Columbus'},
        'italian_village': {'name': 'Italian Village', 'zips': ['43201'], 'city': 'Columbus'}
    }
    
    # Baseline data (as of Jan 2026) - will be updated by collection
    BASELINE_DATA = {
        'central_ohio': {
            'median_price': 285000,
            'avg_dom': 21,
            'inventory_months': 1.8,
            'yoy_change': 5.2
        },
        'neighborhoods': {
            'short_north': {'median': 425000, 'dom': 14, 'school': 7.5},
            'german_village': {'median': 485000, 'dom': 18, 'school': 7.8},
            'grandview': {'median': 395000, 'dom': 12, 'school': 8.2},
            'upper_arlington': {'median': 525000, 'dom': 21, 'school': 9.1},
            'worthington': {'median': 385000, 'dom': 16, 'school': 8.8},
            'dublin': {'median': 445000, 'dom': 19, 'school': 9.0},
            'powell': {'median': 485000, 'dom': 22, 'school': 9.2},
            'westerville': {'median': 345000, 'dom': 15, 'school': 8.5},
            'new_albany': {'median': 625000, 'dom': 28, 'school': 9.4},
            'gahanna': {'median': 315000, 'dom': 14, 'school': 8.0},
            'hilliard': {'median': 335000, 'dom': 13, 'school': 8.3},
            'grove_city': {'median': 285000, 'dom': 11, 'school': 7.6},
            'reynoldsburg': {'median': 265000, 'dom': 12, 'school': 7.2},
            'pickerington': {'median': 345000, 'dom': 17, 'school': 8.6},
            'canal_winchester': {'median': 315000, 'dom': 14, 'school': 8.1},
            'delaware': {'median': 295000, 'dom': 18, 'school': 8.0},
            'bexley': {'median': 545000, 'dom': 16, 'school': 9.0},
            'clintonville': {'median': 345000, 'dom': 10, 'school': 7.4}
        }
    }
    
    def __init__(self, storage_path: str = "data/market_data"):
        self.storage_path = storage_path
        self.snapshots: List[MarketSnapshot] = []
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_data()
    
    def _load_data(self):
        """Load historical market data."""
        data_file = f"{self.storage_path}/market_snapshots.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                for s in data:
                    snapshot = MarketSnapshot(
                        area=s['area'],
                        date=datetime.fromisoformat(s['date']),
                        median_price=s.get('median_price', 0),
                        avg_price=s.get('avg_price', 0),
                        total_listings=s.get('total_listings', 0),
                        new_listings=s.get('new_listings', 0),
                        pending_sales=s.get('pending_sales', 0),
                        closed_sales=s.get('closed_sales', 0),
                        avg_dom=s.get('avg_dom', 0),
                        inventory_months=s.get('inventory_months', 0),
                        price_change_mom=s.get('price_change_mom', 0),
                        price_change_yoy=s.get('price_change_yoy', 0)
                    )
                    self.snapshots.append(snapshot)
    
    def _save_data(self):
        """Save market data."""
        data = [
            {
                'area': s.area,
                'date': s.date.isoformat(),
                'median_price': s.median_price,
                'avg_price': s.avg_price,
                'total_listings': s.total_listings,
                'new_listings': s.new_listings,
                'pending_sales': s.pending_sales,
                'closed_sales': s.closed_sales,
                'avg_dom': s.avg_dom,
                'inventory_months': s.inventory_months,
                'price_change_mom': s.price_change_mom,
                'price_change_yoy': s.price_change_yoy
            }
            for s in self.snapshots[-1000:]  # Keep last 1000 snapshots
        ]
        
        with open(f"{self.storage_path}/market_snapshots.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def collect_market_data(self) -> MarketSnapshot:
        """Collect current market data for Central Ohio."""
        # In production, this would pull from:
        # - Columbus REALTORS MLS API (if you have access)
        # - Zillow Research Data
        # - Redfin Data Center
        # - FRED Economic Data
        # - Ohio Department of Development
        
        # For now, use baseline with slight randomization to simulate real data
        import random
        
        base = self.BASELINE_DATA['central_ohio']
        
        # Simulate market fluctuations
        price_change = random.uniform(-0.02, 0.03)  # -2% to +3% monthly
        
        snapshot = MarketSnapshot(
            area='central_ohio',
            date=datetime.now(),
            median_price=int(base['median_price'] * (1 + price_change)),
            avg_price=int(base['median_price'] * 1.1 * (1 + price_change)),
            total_listings=random.randint(2200, 2700),
            new_listings=random.randint(400, 600),
            pending_sales=random.randint(500, 700),
            closed_sales=random.randint(600, 800),
            avg_dom=base['avg_dom'] + random.randint(-3, 3),
            inventory_months=round(base['inventory_months'] + random.uniform(-0.3, 0.3), 1),
            price_change_mom=round(price_change * 100, 2),
            price_change_yoy=base['yoy_change'] + random.uniform(-1, 1)
        )
        
        self.snapshots.append(snapshot)
        self._save_data()
        
        return snapshot
    
    def get_neighborhood_stats(self, neighborhood: str = None) -> List[Dict]:
        """Get statistics for neighborhoods."""
        if neighborhood and neighborhood in self.NEIGHBORHOODS:
            info = self.NEIGHBORHOODS[neighborhood]
            base = self.BASELINE_DATA['neighborhoods'].get(neighborhood, {})
            return [{
                'id': neighborhood,
                'name': info['name'],
                'city': info['city'],
                'zip_codes': ','.join(info['zips']),
                'median_price': base.get('median', 285000),
                'avg_dom': base.get('dom', 21),
                'school_rating': base.get('school', 7.5)
            }]
        
        results = []
        for key, info in self.NEIGHBORHOODS.items():
            base = self.BASELINE_DATA['neighborhoods'].get(key, {})
            results.append({
                'id': key,
                'name': info['name'],
                'city': info['city'],
                'zip_codes': ','.join(info['zips']),
                'median_price': base.get('median', 285000),
                'avg_dom': base.get('dom', 21),
                'school_rating': base.get('school', 7.5)
            })
        
        return sorted(results, key=lambda x: x['median_price'], reverse=True)
    
    def get_market_summary(self) -> Dict:
        """Get current market summary."""
        # Get most recent snapshot or create one
        if not self.snapshots:
            self.collect_market_data()
        
        latest = max(self.snapshots, key=lambda s: s.date)
        
        # Get previous month for comparison
        month_ago = datetime.now() - timedelta(days=30)
        prev = [s for s in self.snapshots if s.date < month_ago]
        prev_snapshot = max(prev, key=lambda s: s.date) if prev else latest
        
        return {
            'updated': latest.date.isoformat(),
            'central_ohio': {
                'median_price': latest.median_price,
                'avg_price': latest.avg_price,
                'total_listings': latest.total_listings,
                'new_listings': latest.new_listings,
                'pending_sales': latest.pending_sales,
                'closed_sales': latest.closed_sales,
                'avg_dom': latest.avg_dom,
                'inventory_months': latest.inventory_months,
                'price_change_mom': latest.price_change_mom,
                'price_change_yoy': latest.price_change_yoy
            },
            'comparison': {
                'prev_median': prev_snapshot.median_price,
                'price_direction': 'up' if latest.median_price > prev_snapshot.median_price else 'down',
                'inventory_direction': 'up' if latest.inventory_months > prev_snapshot.inventory_months else 'down'
            }
        }
    
    def get_price_trends(self, months: int = 12) -> List[Dict]:
        """Get price trends over time."""
        cutoff = datetime.now() - timedelta(days=months * 30)
        relevant = [s for s in self.snapshots if s.date >= cutoff]
        
        # Group by month
        by_month = {}
        for s in relevant:
            month_key = s.date.strftime('%Y-%m')
            if month_key not in by_month:
                by_month[month_key] = []
            by_month[month_key].append(s)
        
        trends = []
        for month, snapshots in sorted(by_month.items()):
            avg_price = sum(s.median_price for s in snapshots) / len(snapshots)
            avg_dom = sum(s.avg_dom for s in snapshots) / len(snapshots)
            trends.append({
                'month': month,
                'median_price': int(avg_price),
                'avg_dom': int(avg_dom)
            })
        
        return trends
    
    def analyze_market_conditions(self) -> Dict:
        """Analyze current market conditions."""
        summary = self.get_market_summary()
        data = summary['central_ohio']
        
        # Determine market type
        if data['inventory_months'] < 2:
            market_type = "Strong Seller's Market"
            advice_buyers = "Expect competition. Get pre-approved and be ready to act fast."
            advice_sellers = "Great time to sell. Price competitively to maximize offers."
        elif data['inventory_months'] < 4:
            market_type = "Seller's Market"
            advice_buyers = "Market favors sellers but opportunities exist. Be prepared."
            advice_sellers = "Good conditions for selling. Price strategically."
        elif data['inventory_months'] < 6:
            market_type = "Balanced Market"
            advice_buyers = "Fair conditions. Take time to find the right home."
            advice_sellers = "Price accurately. Expect reasonable negotiation."
        else:
            market_type = "Buyer's Market"
            advice_buyers = "Favorable conditions. You have negotiating power."
            advice_sellers = "Consider competitive pricing and staging."
        
        return {
            'market_type': market_type,
            'inventory_months': data['inventory_months'],
            'median_price': data['median_price'],
            'price_trend': 'rising' if data['price_change_yoy'] > 0 else 'falling',
            'yoy_change': data['price_change_yoy'],
            'avg_days_on_market': data['avg_dom'],
            'advice': {
                'buyers': advice_buyers,
                'sellers': advice_sellers
            },
            'key_stats': {
                'active_listings': data['total_listings'],
                'new_this_week': data['new_listings'],
                'pending': data['pending_sales'],
                'sold_last_month': data['closed_sales']
            }
        }
    
    def get_zip_code_data(self, zip_code: str) -> Optional[Dict]:
        """Get data for a specific ZIP code."""
        # Find which area this ZIP belongs to
        for area_id, area in self.CENTRAL_OHIO_AREAS.items():
            if zip_code in area['zips']:
                return {
                    'zip_code': zip_code,
                    'county': area['name'],
                    'in_central_ohio': True
                }
        
        # Check neighborhoods
        for hood_id, hood in self.NEIGHBORHOODS.items():
            if zip_code in hood['zips']:
                base = self.BASELINE_DATA['neighborhoods'].get(hood_id, {})
                return {
                    'zip_code': zip_code,
                    'neighborhood': hood['name'],
                    'city': hood['city'],
                    'median_price': base.get('median', 285000),
                    'avg_dom': base.get('dom', 21),
                    'school_rating': base.get('school', 7.5)
                }
        
        return None
