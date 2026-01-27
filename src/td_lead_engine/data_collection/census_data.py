"""Census and demographic data collector for Central Ohio."""

from dataclasses import dataclass
from typing import Dict, List
import json
import os


@dataclass
class ZipCodeDemographics:
    """Demographics for a ZIP code."""
    zip_code: str
    city: str
    population: int
    households: int
    median_income: int
    median_age: float
    owner_occupied_pct: float
    renter_occupied_pct: float
    median_home_value: int
    college_educated_pct: float
    family_households_pct: float


class CensusDataCollector:
    """Collect and serve Census data for Central Ohio."""
    
    # Central Ohio ZIP code demographics (2020 Census / ACS estimates)
    DEMOGRAPHICS = {
        # Columbus proper
        '43201': ZipCodeDemographics('43201', 'Columbus', 18500, 9200, 52000, 31.2, 35.4, 64.6, 285000, 48.2, 28.5),
        '43202': ZipCodeDemographics('43202', 'Columbus', 21800, 10100, 68000, 34.5, 52.3, 47.7, 325000, 55.1, 35.2),
        '43203': ZipCodeDemographics('43203', 'Columbus', 12400, 4800, 32000, 32.8, 28.5, 71.5, 125000, 18.5, 42.1),
        '43204': ZipCodeDemographics('43204', 'Columbus', 35200, 13500, 42000, 34.2, 45.2, 54.8, 145000, 22.4, 48.5),
        '43205': ZipCodeDemographics('43205', 'Columbus', 18900, 7200, 38000, 33.5, 38.6, 61.4, 165000, 24.8, 38.2),
        '43206': ZipCodeDemographics('43206', 'Columbus', 24500, 11200, 78000, 35.8, 58.2, 41.8, 385000, 62.5, 32.4),
        '43209': ZipCodeDemographics('43209', 'Bexley', 13800, 5200, 125000, 38.2, 72.5, 27.5, 485000, 78.4, 52.8),
        '43212': ZipCodeDemographics('43212', 'Grandview Heights', 18200, 8500, 85000, 34.5, 55.8, 44.2, 395000, 68.2, 35.6),
        '43214': ZipCodeDemographics('43214', 'Columbus', 28500, 12800, 72000, 36.2, 58.5, 41.5, 345000, 58.5, 38.5),
        '43215': ZipCodeDemographics('43215', 'Columbus', 15200, 8200, 65000, 32.5, 42.5, 57.5, 425000, 52.8, 22.5),
        
        # Suburbs
        '43016': ZipCodeDemographics('43016', 'Dublin', 38500, 14200, 142000, 38.5, 78.5, 21.5, 445000, 72.4, 68.5),
        '43017': ZipCodeDemographics('43017', 'Dublin', 42800, 15800, 155000, 40.2, 82.5, 17.5, 485000, 75.8, 72.4),
        '43026': ZipCodeDemographics('43026', 'Hilliard', 52500, 19200, 98000, 36.8, 72.5, 27.5, 335000, 58.5, 65.2),
        '43054': ZipCodeDemographics('43054', 'New Albany', 12500, 4200, 185000, 42.5, 92.5, 7.5, 625000, 82.5, 78.5),
        '43065': ZipCodeDemographics('43065', 'Powell', 45200, 15800, 165000, 40.8, 88.5, 11.5, 485000, 78.2, 75.8),
        '43081': ZipCodeDemographics('43081', 'Westerville', 38500, 14500, 92000, 37.2, 68.5, 31.5, 325000, 55.8, 62.5),
        '43082': ZipCodeDemographics('43082', 'Westerville', 28500, 10200, 115000, 39.5, 78.5, 21.5, 385000, 65.2, 68.5),
        '43085': ZipCodeDemographics('43085', 'Worthington', 32500, 13200, 105000, 38.5, 65.8, 34.2, 385000, 68.5, 58.2),
        '43110': ZipCodeDemographics('43110', 'Canal Winchester', 18500, 6800, 88000, 35.8, 75.2, 24.8, 315000, 48.5, 68.5),
        '43119': ZipCodeDemographics('43119', 'Galloway', 22500, 8500, 68000, 34.5, 65.5, 34.5, 245000, 35.8, 58.5),
        '43123': ZipCodeDemographics('43123', 'Grove City', 48500, 18200, 72000, 35.2, 68.5, 31.5, 285000, 42.5, 62.5),
        '43147': ZipCodeDemographics('43147', 'Pickerington', 42500, 15500, 105000, 37.8, 82.5, 17.5, 345000, 55.2, 72.5),
        '43220': ZipCodeDemographics('43220', 'Upper Arlington', 18500, 7200, 145000, 42.5, 85.2, 14.8, 525000, 78.5, 68.5),
        '43221': ZipCodeDemographics('43221', 'Upper Arlington', 22500, 8500, 135000, 40.8, 82.5, 17.5, 495000, 75.8, 72.5),
        '43230': ZipCodeDemographics('43230', 'Gahanna', 35500, 13500, 85000, 36.5, 72.5, 27.5, 315000, 52.5, 65.8),
        '43068': ZipCodeDemographics('43068', 'Reynoldsburg', 38500, 14800, 62000, 34.2, 58.5, 41.5, 265000, 38.5, 55.2),
        '43015': ZipCodeDemographics('43015', 'Delaware', 32500, 12500, 75000, 35.8, 68.5, 31.5, 295000, 48.5, 62.5),
    }
    
    def __init__(self, storage_path: str = "data/census"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def get_zip_demographics(self, zip_code: str) -> ZipCodeDemographics:
        """Get demographics for a ZIP code."""
        return self.DEMOGRAPHICS.get(zip_code)
    
    def get_all_demographics(self) -> List[ZipCodeDemographics]:
        """Get all ZIP code demographics."""
        return list(self.DEMOGRAPHICS.values())
    
    def compare_zip_codes(self, zip_codes: List[str]) -> Dict:
        """Compare demographics across ZIP codes."""
        data = [self.DEMOGRAPHICS[z] for z in zip_codes if z in self.DEMOGRAPHICS]
        
        if not data:
            return {'error': 'No valid ZIP codes'}
        
        return {
            'zip_codes': [
                {
                    'zip': d.zip_code,
                    'city': d.city,
                    'population': d.population,
                    'median_income': d.median_income,
                    'median_home_value': d.median_home_value,
                    'owner_occupied_pct': d.owner_occupied_pct,
                    'college_educated_pct': d.college_educated_pct
                }
                for d in data
            ],
            'averages': {
                'population': int(sum(d.population for d in data) / len(data)),
                'median_income': int(sum(d.median_income for d in data) / len(data)),
                'median_home_value': int(sum(d.median_home_value for d in data) / len(data)),
                'owner_occupied_pct': round(sum(d.owner_occupied_pct for d in data) / len(data), 1)
            }
        }
    
    def find_neighborhoods_by_criteria(
        self,
        min_income: int = 0,
        max_income: int = 999999,
        min_home_value: int = 0,
        max_home_value: int = 9999999,
        min_owner_pct: float = 0,
        min_college_pct: float = 0
    ) -> List[ZipCodeDemographics]:
        """Find neighborhoods matching criteria."""
        results = []
        
        for demo in self.DEMOGRAPHICS.values():
            if demo.median_income < min_income or demo.median_income > max_income:
                continue
            if demo.median_home_value < min_home_value or demo.median_home_value > max_home_value:
                continue
            if demo.owner_occupied_pct < min_owner_pct:
                continue
            if demo.college_educated_pct < min_college_pct:
                continue
            results.append(demo)
        
        return sorted(results, key=lambda d: d.median_home_value, reverse=True)
    
    def get_buyer_profile_match(self, buyer_criteria: Dict) -> List[Dict]:
        """Find ZIP codes matching a buyer's profile."""
        results = []
        
        budget_min = buyer_criteria.get('budget_min', 0)
        budget_max = buyer_criteria.get('budget_max', 9999999)
        wants_families = buyer_criteria.get('family_friendly', False)
        wants_young = buyer_criteria.get('young_professionals', False)
        
        for demo in self.DEMOGRAPHICS.values():
            # Price match
            if demo.median_home_value < budget_min * 0.7 or demo.median_home_value > budget_max * 1.3:
                continue
            
            score = 0
            reasons = []
            
            # Budget alignment
            if budget_min <= demo.median_home_value <= budget_max:
                score += 30
                reasons.append('Within budget')
            
            # Family friendly
            if wants_families and demo.family_households_pct > 60:
                score += 20
                reasons.append('Family-friendly area')
            
            # Young professionals
            if wants_young and demo.median_age < 35 and demo.college_educated_pct > 50:
                score += 20
                reasons.append('Young professional area')
            
            # Ownership stability
            if demo.owner_occupied_pct > 70:
                score += 10
                reasons.append('High homeownership')
            
            if score > 0:
                results.append({
                    'zip_code': demo.zip_code,
                    'city': demo.city,
                    'match_score': score,
                    'reasons': reasons,
                    'median_home_value': demo.median_home_value,
                    'median_income': demo.median_income
                })
        
        results.sort(key=lambda r: r['match_score'], reverse=True)
        return results[:10]
    
    def get_area_report(self, zip_code: str) -> Dict:
        """Generate a comprehensive area report."""
        demo = self.DEMOGRAPHICS.get(zip_code)
        if not demo:
            return {'error': 'ZIP code not found'}
        
        # Compare to averages
        all_demos = list(self.DEMOGRAPHICS.values())
        avg_income = sum(d.median_income for d in all_demos) / len(all_demos)
        avg_home_value = sum(d.median_home_value for d in all_demos) / len(all_demos)
        avg_owner_pct = sum(d.owner_occupied_pct for d in all_demos) / len(all_demos)
        
        return {
            'zip_code': zip_code,
            'city': demo.city,
            'demographics': {
                'population': demo.population,
                'households': demo.households,
                'median_age': demo.median_age
            },
            'economics': {
                'median_income': demo.median_income,
                'vs_area_avg': round((demo.median_income / avg_income - 1) * 100, 1),
                'college_educated_pct': demo.college_educated_pct
            },
            'housing': {
                'median_home_value': demo.median_home_value,
                'vs_area_avg': round((demo.median_home_value / avg_home_value - 1) * 100, 1),
                'owner_occupied_pct': demo.owner_occupied_pct,
                'renter_occupied_pct': demo.renter_occupied_pct
            },
            'lifestyle': {
                'family_households_pct': demo.family_households_pct,
                'area_type': self._get_area_type(demo)
            }
        }
    
    def _get_area_type(self, demo: ZipCodeDemographics) -> str:
        """Categorize the area type based on demographics."""
        if demo.family_households_pct > 70 and demo.owner_occupied_pct > 80:
            return 'Established Family Suburb'
        elif demo.median_age < 32 and demo.renter_occupied_pct > 50:
            return 'Young Urban'
        elif demo.college_educated_pct > 70 and demo.median_income > 120000:
            return 'Affluent Professional'
        elif demo.family_households_pct > 60 and demo.median_home_value < 300000:
            return 'Affordable Family'
        elif demo.median_age > 40 and demo.owner_occupied_pct > 75:
            return 'Established Community'
        else:
            return 'Mixed/Transitional'
