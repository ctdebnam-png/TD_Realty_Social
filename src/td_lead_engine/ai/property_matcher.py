"""AI-powered property matching for buyers."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
import math


@dataclass
class MatchScore:
    """Score for how well a property matches buyer criteria."""
    property_id: str
    buyer_id: str
    overall_score: float  # 0-100
    price_score: float
    location_score: float
    size_score: float
    features_score: float
    lifestyle_score: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    match_reasons: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    calculated_at: datetime = field(default_factory=datetime.now)


class PropertyMatcher:
    """Matches properties to buyer preferences using AI scoring."""

    def __init__(self):
        # Scoring weights
        self.weights = {
            'price': 0.25,
            'location': 0.25,
            'size': 0.20,
            'features': 0.15,
            'lifestyle': 0.15
        }
        
        # Central Ohio area data
        self.area_rankings = {
            'dublin': {'schools': 9, 'safety': 9, 'commute': 7, 'amenities': 8},
            'powell': {'schools': 9, 'safety': 9, 'commute': 6, 'amenities': 7},
            'new albany': {'schools': 10, 'safety': 9, 'commute': 6, 'amenities': 7},
            'westerville': {'schools': 8, 'safety': 8, 'commute': 7, 'amenities': 8},
            'upper arlington': {'schools': 9, 'safety': 9, 'commute': 8, 'amenities': 8},
            'grandview heights': {'schools': 8, 'safety': 8, 'commute': 9, 'amenities': 9},
            'worthington': {'schools': 8, 'safety': 8, 'commute': 8, 'amenities': 7},
            'hilliard': {'schools': 7, 'safety': 8, 'commute': 7, 'amenities': 7},
            'grove city': {'schools': 6, 'safety': 7, 'commute': 6, 'amenities': 6},
            'reynoldsburg': {'schools': 6, 'safety': 7, 'commute': 7, 'amenities': 6},
            'gahanna': {'schools': 7, 'safety': 8, 'commute': 7, 'amenities': 7},
            'pickerington': {'schools': 7, 'safety': 8, 'commute': 5, 'amenities': 6},
            'columbus': {'schools': 5, 'safety': 6, 'commute': 9, 'amenities': 9},
            'default': {'schools': 5, 'safety': 6, 'commute': 5, 'amenities': 5}
        }

    def match_property(
        self,
        property_data: Dict,
        buyer_preferences: Dict
    ) -> MatchScore:
        """Calculate match score between property and buyer preferences."""
        property_id = property_data.get('id', '')
        buyer_id = buyer_preferences.get('buyer_id', '')
        
        # Calculate individual scores
        price_score = self._calculate_price_score(property_data, buyer_preferences)
        location_score = self._calculate_location_score(property_data, buyer_preferences)
        size_score = self._calculate_size_score(property_data, buyer_preferences)
        features_score = self._calculate_features_score(property_data, buyer_preferences)
        lifestyle_score = self._calculate_lifestyle_score(property_data, buyer_preferences)
        
        # Calculate weighted overall score
        overall_score = (
            price_score * self.weights['price'] +
            location_score * self.weights['location'] +
            size_score * self.weights['size'] +
            features_score * self.weights['features'] +
            lifestyle_score * self.weights['lifestyle']
        )
        
        # Generate match reasons and concerns
        match_reasons, concerns = self._generate_insights(
            property_data, buyer_preferences,
            price_score, location_score, size_score, features_score, lifestyle_score
        )
        
        return MatchScore(
            property_id=property_id,
            buyer_id=buyer_id,
            overall_score=overall_score,
            price_score=price_score,
            location_score=location_score,
            size_score=size_score,
            features_score=features_score,
            lifestyle_score=lifestyle_score,
            breakdown={
                'price': price_score,
                'location': location_score,
                'size': size_score,
                'features': features_score,
                'lifestyle': lifestyle_score
            },
            match_reasons=match_reasons,
            concerns=concerns
        )

    def find_best_matches(
        self,
        properties: List[Dict],
        buyer_preferences: Dict,
        limit: int = 10,
        min_score: float = 60.0
    ) -> List[MatchScore]:
        """Find best matching properties for a buyer."""
        matches = []
        
        for prop in properties:
            match = self.match_property(prop, buyer_preferences)
            if match.overall_score >= min_score:
                matches.append(match)
        
        # Sort by overall score
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        
        return matches[:limit]

    def find_buyers_for_property(
        self,
        property_data: Dict,
        buyers: List[Dict],
        limit: int = 20,
        min_score: float = 50.0
    ) -> List[MatchScore]:
        """Find best matching buyers for a property."""
        matches = []
        
        for buyer in buyers:
            preferences = buyer.get('preferences', buyer)
            preferences['buyer_id'] = buyer.get('id', '')
            match = self.match_property(property_data, preferences)
            if match.overall_score >= min_score:
                matches.append(match)
        
        matches.sort(key=lambda m: m.overall_score, reverse=True)
        return matches[:limit]

    def _calculate_price_score(self, prop: Dict, prefs: Dict) -> float:
        """Calculate price match score."""
        prop_price = prop.get('price', 0)
        min_price = prefs.get('min_price', 0)
        max_price = prefs.get('max_price', float('inf'))
        ideal_price = prefs.get('ideal_price', (min_price + max_price) / 2 if max_price != float('inf') else min_price)
        
        if prop_price == 0:
            return 50.0
        
        # Perfect match if within range
        if min_price <= prop_price <= max_price:
            # Higher score if closer to ideal
            if ideal_price > 0:
                deviation = abs(prop_price - ideal_price) / ideal_price
                return max(70.0, 100.0 - (deviation * 50))
            return 90.0
        
        # Below minimum (might be too low quality)
        if prop_price < min_price:
            below_pct = (min_price - prop_price) / min_price
            return max(40.0, 80.0 - (below_pct * 100))
        
        # Above maximum
        if max_price > 0 and prop_price > max_price:
            over_pct = (prop_price - max_price) / max_price
            if over_pct <= 0.05:  # 5% over - still consider
                return 70.0
            elif over_pct <= 0.10:  # 10% over
                return 50.0
            elif over_pct <= 0.20:  # 20% over
                return 30.0
            return 10.0
        
        return 50.0

    def _calculate_location_score(self, prop: Dict, prefs: Dict) -> float:
        """Calculate location match score."""
        prop_city = prop.get('city', '').lower()
        prop_zip = prop.get('zip', '')
        
        preferred_areas = [a.lower() for a in prefs.get('preferred_areas', [])]
        preferred_zips = prefs.get('preferred_zips', [])
        must_have_areas = [a.lower() for a in prefs.get('must_have_areas', [])]
        excluded_areas = [a.lower() for a in prefs.get('excluded_areas', [])]
        
        # Excluded area - automatic low score
        if prop_city in excluded_areas:
            return 10.0
        
        # Must have area and not in it
        if must_have_areas and prop_city not in must_have_areas:
            return 20.0
        
        score = 50.0  # Base score
        
        # In preferred area
        if prop_city in preferred_areas:
            score = 90.0
        elif prop_zip in preferred_zips:
            score = 85.0
        
        # Adjust based on buyer priorities
        priorities = prefs.get('location_priorities', {})
        area_data = self.area_rankings.get(prop_city, self.area_rankings['default'])
        
        if priorities.get('schools', False):
            score += (area_data['schools'] - 5) * 2
        if priorities.get('safety', False):
            score += (area_data['safety'] - 5) * 2
        if priorities.get('commute', False):
            score += (area_data['commute'] - 5) * 2
        if priorities.get('amenities', False):
            score += (area_data['amenities'] - 5) * 2
        
        return min(100.0, max(0.0, score))

    def _calculate_size_score(self, prop: Dict, prefs: Dict) -> float:
        """Calculate size/bedroom/bathroom match score."""
        score = 100.0
        
        # Bedrooms
        prop_beds = prop.get('beds', 0)
        min_beds = prefs.get('min_beds', 0)
        max_beds = prefs.get('max_beds', 10)
        ideal_beds = prefs.get('ideal_beds')
        
        if prop_beds < min_beds:
            score -= (min_beds - prop_beds) * 20
        elif prop_beds > max_beds:
            score -= (prop_beds - max_beds) * 10  # Less penalty for extra beds
        elif ideal_beds and prop_beds != ideal_beds:
            score -= abs(prop_beds - ideal_beds) * 5
        
        # Bathrooms
        prop_baths = prop.get('baths', 0)
        min_baths = prefs.get('min_baths', 0)
        
        if prop_baths < min_baths:
            score -= (min_baths - prop_baths) * 15
        
        # Square footage
        prop_sqft = prop.get('sqft', 0)
        min_sqft = prefs.get('min_sqft', 0)
        max_sqft = prefs.get('max_sqft', float('inf'))
        
        if prop_sqft > 0:
            if prop_sqft < min_sqft:
                pct_under = (min_sqft - prop_sqft) / min_sqft
                score -= pct_under * 30
            elif max_sqft != float('inf') and prop_sqft > max_sqft:
                pct_over = (prop_sqft - max_sqft) / max_sqft
                score -= pct_over * 15  # Less penalty for extra space
        
        return max(0.0, score)

    def _calculate_features_score(self, prop: Dict, prefs: Dict) -> float:
        """Calculate features match score."""
        score = 70.0  # Base score
        
        prop_features = set(f.lower() for f in prop.get('features', []))
        must_have = set(f.lower() for f in prefs.get('must_have_features', []))
        nice_to_have = set(f.lower() for f in prefs.get('nice_to_have_features', []))
        dealbreakers = set(f.lower() for f in prefs.get('dealbreaker_features', []))
        
        # Check for dealbreakers (features they DON'T want)
        for db in dealbreakers:
            if db in prop_features:
                score -= 30
        
        # Must have features
        if must_have:
            matched_must = len(must_have & prop_features)
            must_have_pct = matched_must / len(must_have)
            if must_have_pct < 1.0:
                score -= (1.0 - must_have_pct) * 40
            else:
                score += 15
        
        # Nice to have features
        if nice_to_have:
            matched_nice = len(nice_to_have & prop_features)
            nice_pct = matched_nice / len(nice_to_have)
            score += nice_pct * 15
        
        # Property type match
        prop_type = prop.get('property_type', '').lower()
        preferred_types = [t.lower() for t in prefs.get('property_types', [])]
        
        if preferred_types and prop_type:
            if prop_type in preferred_types:
                score += 10
            else:
                score -= 15
        
        return min(100.0, max(0.0, score))

    def _calculate_lifestyle_score(self, prop: Dict, prefs: Dict) -> float:
        """Calculate lifestyle fit score."""
        score = 70.0
        
        # Commute considerations
        work_location = prefs.get('work_location')
        max_commute = prefs.get('max_commute_minutes', 60)
        
        if work_location and prop.get('estimated_commute_minutes'):
            commute = prop['estimated_commute_minutes']
            if commute <= max_commute:
                score += 15 * (1 - commute / max_commute)
            else:
                score -= 20
        
        # Lot size for outdoor enthusiasts
        if prefs.get('wants_large_yard', False):
            lot_size = prop.get('lot_sqft', 0)
            if lot_size >= 20000:  # Half acre+
                score += 15
            elif lot_size >= 10000:  # Quarter acre+
                score += 10
            elif lot_size < 5000:
                score -= 10
        
        # Garage requirements
        min_garage = prefs.get('min_garage_spaces', 0)
        prop_garage = prop.get('garage_spaces', 0)
        if prop_garage < min_garage:
            score -= (min_garage - prop_garage) * 10
        
        # Age preference
        preferred_age = prefs.get('preferred_home_age')  # 'new', 'modern', 'character', 'any'
        year_built = prop.get('year_built', 0)
        current_year = datetime.now().year
        
        if preferred_age and year_built:
            age = current_year - year_built
            if preferred_age == 'new' and age > 10:
                score -= 15
            elif preferred_age == 'modern' and age > 30:
                score -= 10
            elif preferred_age == 'character' and age < 50:
                score -= 5
        
        # HOA preference
        has_hoa = prop.get('has_hoa', False)
        hoa_preference = prefs.get('hoa_preference', 'any')  # 'yes', 'no', 'any'
        
        if hoa_preference == 'no' and has_hoa:
            score -= 20
        elif hoa_preference == 'yes' and not has_hoa:
            score -= 10
        
        return min(100.0, max(0.0, score))

    def _generate_insights(
        self,
        prop: Dict,
        prefs: Dict,
        price_score: float,
        location_score: float,
        size_score: float,
        features_score: float,
        lifestyle_score: float
    ) -> tuple:
        """Generate human-readable match reasons and concerns."""
        reasons = []
        concerns = []
        
        # Price insights
        if price_score >= 80:
            reasons.append(f"Well within budget at ${prop.get('price', 0):,}")
        elif price_score >= 60:
            reasons.append("Price is workable within budget")
        elif price_score < 50:
            concerns.append(f"Price (${prop.get('price', 0):,}) may stretch budget")
        
        # Location insights
        if location_score >= 85:
            reasons.append(f"Excellent location in {prop.get('city', 'preferred area')}")
        elif location_score >= 70:
            reasons.append("Good location match")
        elif location_score < 50:
            concerns.append("Location may not be ideal")
        
        # Size insights
        if size_score >= 90:
            beds = prop.get('beds', 0)
            baths = prop.get('baths', 0)
            reasons.append(f"Perfect size: {beds} beds, {baths} baths")
        elif size_score < 60:
            if prop.get('beds', 0) < prefs.get('min_beds', 0):
                concerns.append(f"Only {prop.get('beds')} bedrooms (wanted {prefs.get('min_beds')}+)")
            if prop.get('sqft', 0) < prefs.get('min_sqft', 0):
                concerns.append("Square footage below preference")
        
        # Feature insights
        must_have = set(f.lower() for f in prefs.get('must_have_features', []))
        prop_features = set(f.lower() for f in prop.get('features', []))
        
        matched_must = must_have & prop_features
        if matched_must:
            reasons.append(f"Has desired features: {', '.join(list(matched_must)[:3])}")
        
        missing_must = must_have - prop_features
        if missing_must:
            concerns.append(f"Missing: {', '.join(list(missing_must)[:3])}")
        
        return reasons[:5], concerns[:5]
