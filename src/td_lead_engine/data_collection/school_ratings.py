"""Ohio school ratings data collector."""

from dataclasses import dataclass
from typing import Dict, List
import json
import os


@dataclass
class SchoolDistrict:
    """An Ohio school district."""
    name: str
    city: str
    county: str
    rating: float  # Out of 10
    performance_index: float
    graduation_rate: float
    enrollment: int
    schools: int
    zip_codes: List[str]


class OhioSchoolRatings:
    """Ohio school district ratings from public data."""
    
    # Central Ohio school districts with ratings
    # Data from Ohio Department of Education report cards
    DISTRICTS = {
        'columbus_city': SchoolDistrict(
            name='Columbus City Schools',
            city='Columbus',
            county='Franklin',
            rating=5.2,
            performance_index=72.1,
            graduation_rate=82.3,
            enrollment=47000,
            schools=110,
            zip_codes=['43201', '43202', '43203', '43204', '43205', '43206', '43207', 
                      '43210', '43211', '43213', '43219', '43222', '43223', '43224', 
                      '43227', '43229', '43232']
        ),
        'dublin': SchoolDistrict(
            name='Dublin City Schools',
            city='Dublin',
            county='Franklin',
            rating=9.0,
            performance_index=102.4,
            graduation_rate=97.2,
            enrollment=16500,
            schools=22,
            zip_codes=['43016', '43017']
        ),
        'upper_arlington': SchoolDistrict(
            name='Upper Arlington City Schools',
            city='Upper Arlington',
            county='Franklin',
            rating=9.1,
            performance_index=104.2,
            graduation_rate=98.1,
            enrollment=6200,
            schools=8,
            zip_codes=['43220', '43221']
        ),
        'worthington': SchoolDistrict(
            name='Worthington City Schools',
            city='Worthington',
            county='Franklin',
            rating=8.8,
            performance_index=99.8,
            graduation_rate=96.5,
            enrollment=10200,
            schools=14,
            zip_codes=['43085', '43235']
        ),
        'hilliard': SchoolDistrict(
            name='Hilliard City Schools',
            city='Hilliard',
            county='Franklin',
            rating=8.3,
            performance_index=96.1,
            graduation_rate=95.2,
            enrollment=16800,
            schools=23,
            zip_codes=['43026']
        ),
        'westerville': SchoolDistrict(
            name='Westerville City Schools',
            city='Westerville',
            county='Franklin',
            rating=8.5,
            performance_index=97.3,
            graduation_rate=94.8,
            enrollment=15600,
            schools=23,
            zip_codes=['43081', '43082']
        ),
        'new_albany': SchoolDistrict(
            name='New Albany-Plain Local Schools',
            city='New Albany',
            county='Franklin',
            rating=9.4,
            performance_index=107.1,
            graduation_rate=98.7,
            enrollment=5400,
            schools=7,
            zip_codes=['43054']
        ),
        'gahanna': SchoolDistrict(
            name='Gahanna-Jefferson City Schools',
            city='Gahanna',
            county='Franklin',
            rating=8.0,
            performance_index=93.5,
            graduation_rate=93.1,
            enrollment=7400,
            schools=11,
            zip_codes=['43230']
        ),
        'bexley': SchoolDistrict(
            name='Bexley City Schools',
            city='Bexley',
            county='Franklin',
            rating=9.0,
            performance_index=102.8,
            graduation_rate=97.9,
            enrollment=2600,
            schools=5,
            zip_codes=['43209']
        ),
        'grandview': SchoolDistrict(
            name='Grandview Heights City Schools',
            city='Grandview Heights',
            county='Franklin',
            rating=8.2,
            performance_index=95.4,
            graduation_rate=95.6,
            enrollment=1800,
            schools=3,
            zip_codes=['43212']
        ),
        'grove_city': SchoolDistrict(
            name='South-Western City Schools',
            city='Grove City',
            county='Franklin',
            rating=7.6,
            performance_index=88.2,
            graduation_rate=91.3,
            enrollment=21500,
            schools=35,
            zip_codes=['43123', '43119']
        ),
        'reynoldsburg': SchoolDistrict(
            name='Reynoldsburg City Schools',
            city='Reynoldsburg',
            county='Franklin',
            rating=7.2,
            performance_index=84.6,
            graduation_rate=89.4,
            enrollment=8100,
            schools=12,
            zip_codes=['43068']
        ),
        'pickerington': SchoolDistrict(
            name='Pickerington Local Schools',
            city='Pickerington',
            county='Fairfield',
            rating=8.6,
            performance_index=98.2,
            graduation_rate=95.9,
            enrollment=11200,
            schools=15,
            zip_codes=['43147']
        ),
        'canal_winchester': SchoolDistrict(
            name='Canal Winchester Local Schools',
            city='Canal Winchester',
            county='Franklin',
            rating=8.1,
            performance_index=94.1,
            graduation_rate=94.2,
            enrollment=4800,
            schools=6,
            zip_codes=['43110']
        ),
        'olentangy': SchoolDistrict(
            name='Olentangy Local Schools',
            city='Powell',
            county='Delaware',
            rating=9.2,
            performance_index=105.8,
            graduation_rate=98.4,
            enrollment=23500,
            schools=32,
            zip_codes=['43065', '43035', '43082']
        ),
        'delaware': SchoolDistrict(
            name='Delaware City Schools',
            city='Delaware',
            county='Delaware',
            rating=8.0,
            performance_index=92.8,
            graduation_rate=93.7,
            enrollment=5200,
            schools=9,
            zip_codes=['43015']
        )
    }
    
    def __init__(self, storage_path: str = "data/school_data"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def get_district_by_zip(self, zip_code: str) -> SchoolDistrict:
        """Get school district for a ZIP code."""
        for district in self.DISTRICTS.values():
            if zip_code in district.zip_codes:
                return district
        return None
    
    def get_all_districts(self) -> List[SchoolDistrict]:
        """Get all Central Ohio school districts."""
        districts = list(self.DISTRICTS.values())
        districts.sort(key=lambda d: d.rating, reverse=True)
        return districts
    
    def get_top_districts(self, limit: int = 5) -> List[SchoolDistrict]:
        """Get top-rated school districts."""
        districts = self.get_all_districts()
        return districts[:limit]
    
    def compare_districts(self, district_ids: List[str]) -> Dict:
        """Compare multiple school districts."""
        districts = [self.DISTRICTS[d] for d in district_ids if d in self.DISTRICTS]
        
        return {
            'districts': [
                {
                    'name': d.name,
                    'city': d.city,
                    'rating': d.rating,
                    'performance_index': d.performance_index,
                    'graduation_rate': d.graduation_rate,
                    'enrollment': d.enrollment
                }
                for d in districts
            ],
            'best_rating': max(d.rating for d in districts) if districts else 0,
            'avg_rating': sum(d.rating for d in districts) / len(districts) if districts else 0
        }
    
    def get_district_for_address(self, city: str, zip_code: str) -> Dict:
        """Get school district info for an address."""
        district = self.get_district_by_zip(zip_code)
        
        if not district:
            return {'error': 'District not found', 'zip_code': zip_code}
        
        return {
            'district_name': district.name,
            'rating': district.rating,
            'performance_index': district.performance_index,
            'graduation_rate': district.graduation_rate,
            'number_of_schools': district.schools,
            'enrollment': district.enrollment,
            'rating_category': self._get_rating_category(district.rating)
        }
    
    def _get_rating_category(self, rating: float) -> str:
        """Convert numeric rating to category."""
        if rating >= 9.0:
            return 'Excellent'
        elif rating >= 8.0:
            return 'Very Good'
        elif rating >= 7.0:
            return 'Good'
        elif rating >= 6.0:
            return 'Average'
        else:
            return 'Below Average'
    
    def search_by_criteria(
        self,
        min_rating: float = 0,
        min_graduation_rate: float = 0,
        max_enrollment: int = None
    ) -> List[SchoolDistrict]:
        """Search districts by criteria."""
        results = []
        
        for district in self.DISTRICTS.values():
            if district.rating < min_rating:
                continue
            if district.graduation_rate < min_graduation_rate:
                continue
            if max_enrollment and district.enrollment > max_enrollment:
                continue
            results.append(district)
        
        results.sort(key=lambda d: d.rating, reverse=True)
        return results
