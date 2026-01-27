"""AI-powered lead predictions."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import random
import math


@dataclass
class PredictionResult:
    """Result of a prediction analysis."""
    lead_id: str
    prediction_type: str
    probability: float  # 0-1
    confidence: float   # 0-1
    predicted_value: Any
    factors: List[Dict[str, Any]]
    recommendations: List[str]
    calculated_at: datetime = field(default_factory=datetime.now)


class LeadPredictionEngine:
    """Predicts lead outcomes and behaviors."""

    def __init__(self):
        # Historical conversion rates by source
        self.source_conversion_rates = {
            'zillow': 0.08,
            'realtor.com': 0.07,
            'facebook': 0.05,
            'google_ads': 0.06,
            'referral': 0.25,
            'open_house': 0.12,
            'website': 0.04,
            'sign_call': 0.15,
            'sphere': 0.30,
            'default': 0.05
        }
        
        # Score to conversion multipliers
        self.score_multipliers = {
            (90, 100): 2.5,
            (80, 89): 2.0,
            (70, 79): 1.5,
            (60, 69): 1.2,
            (50, 59): 1.0,
            (40, 49): 0.7,
            (30, 39): 0.4,
            (0, 29): 0.2
        }
        
        # Average days to close by lead type
        self.avg_days_to_close = {
            'buyer': 90,
            'seller': 120,
            'investor': 60
        }

    def predict_conversion(self, lead: Dict) -> PredictionResult:
        """Predict likelihood of lead converting to client."""
        lead_id = lead.get('id', '')
        source = lead.get('source', 'default').lower()
        score = lead.get('score', 50)
        lead_type = lead.get('lead_type', 'buyer')
        
        # Base probability from source
        base_prob = self.source_conversion_rates.get(source, self.source_conversion_rates['default'])
        
        # Apply score multiplier
        multiplier = 1.0
        for (low, high), mult in self.score_multipliers.items():
            if low <= score <= high:
                multiplier = mult
                break
        
        adjusted_prob = base_prob * multiplier
        
        # Adjust for engagement signals
        factors = []
        
        # Email engagement
        email_opens = lead.get('email_opens', 0)
        if email_opens > 5:
            adjusted_prob *= 1.2
            factors.append({'factor': 'High email engagement', 'impact': '+20%'})
        
        # Property views
        views = len(lead.get('property_views', []))
        if views > 10:
            adjusted_prob *= 1.3
            factors.append({'factor': 'High property interest', 'impact': '+30%'})
        elif views > 5:
            adjusted_prob *= 1.15
            factors.append({'factor': 'Moderate property interest', 'impact': '+15%'})
        
        # Showings attended
        showings = lead.get('showings_attended', 0)
        if showings > 0:
            adjusted_prob *= (1 + showings * 0.1)
            factors.append({'factor': f'{showings} showings attended', 'impact': f'+{showings * 10}%'})
        
        # Pre-approval status
        if lead_type == 'buyer' and lead.get('preapproved'):
            adjusted_prob *= 1.5
            factors.append({'factor': 'Pre-approved', 'impact': '+50%'})
        
        # Timeline urgency
        timeline = lead.get('timeline', '').lower()
        if 'immediate' in timeline or 'asap' in timeline or '< 1 month' in timeline:
            adjusted_prob *= 1.4
            factors.append({'factor': 'Urgent timeline', 'impact': '+40%'})
        elif '1-3 month' in timeline:
            adjusted_prob *= 1.2
            factors.append({'factor': 'Active timeline', 'impact': '+20%'})
        
        # Response rate
        if lead.get('response_count', 0) > 0:
            adjusted_prob *= 1.15
            factors.append({'factor': 'Responsive to outreach', 'impact': '+15%'})
        
        # Days since first contact (recency decay)
        days_active = self._days_since_created(lead)
        if days_active > 90:
            adjusted_prob *= 0.7
            factors.append({'factor': 'Lead aging (90+ days)', 'impact': '-30%'})
        elif days_active > 60:
            adjusted_prob *= 0.85
            factors.append({'factor': 'Lead aging (60+ days)', 'impact': '-15%'})
        
        # Cap probability
        final_prob = min(0.95, adjusted_prob)
        
        # Calculate confidence based on data completeness
        confidence = self._calculate_confidence(lead)
        
        # Generate recommendations
        recommendations = self._generate_conversion_recommendations(lead, final_prob, factors)
        
        return PredictionResult(
            lead_id=lead_id,
            prediction_type='conversion',
            probability=final_prob,
            confidence=confidence,
            predicted_value={'will_convert': final_prob >= 0.3},
            factors=factors,
            recommendations=recommendations
        )

    def predict_close_date(self, lead: Dict) -> PredictionResult:
        """Predict when a lead might close."""
        lead_id = lead.get('id', '')
        lead_type = lead.get('lead_type', 'buyer')
        stage = lead.get('stage', 'new')
        score = lead.get('score', 50)
        
        # Base days from lead type
        base_days = self.avg_days_to_close.get(lead_type, 90)
        
        factors = []
        
        # Adjust by stage
        stage_adjustments = {
            'new': 1.0,
            'contacted': 0.9,
            'qualified': 0.8,
            'showing': 0.6,
            'offer': 0.3,
            'under_contract': 0.15
        }
        stage_mult = stage_adjustments.get(stage, 1.0)
        adjusted_days = base_days * stage_mult
        factors.append({'factor': f'Current stage: {stage}', 'impact': f'{stage_mult:.0%} of base'})
        
        # Adjust by score
        if score >= 80:
            adjusted_days *= 0.8
            factors.append({'factor': 'High lead score', 'impact': '-20% time'})
        elif score >= 60:
            adjusted_days *= 0.9
            factors.append({'factor': 'Good lead score', 'impact': '-10% time'})
        
        # Urgency
        timeline = lead.get('timeline', '').lower()
        if 'immediate' in timeline:
            adjusted_days *= 0.5
            factors.append({'factor': 'Immediate timeline', 'impact': '-50% time'})
        elif '1-3 month' in timeline:
            adjusted_days *= 0.7
            factors.append({'factor': '1-3 month timeline', 'impact': '-30% time'})
        
        # Pre-approval (buyers)
        if lead_type == 'buyer' and lead.get('preapproved'):
            adjusted_days *= 0.85
            factors.append({'factor': 'Pre-approved buyer', 'impact': '-15% time'})
        
        predicted_date = datetime.now() + timedelta(days=int(adjusted_days))
        
        # Confidence decreases with time
        confidence = max(0.3, 0.9 - (adjusted_days / 365))
        
        return PredictionResult(
            lead_id=lead_id,
            prediction_type='close_date',
            probability=0.0,  # Not applicable
            confidence=confidence,
            predicted_value={
                'estimated_date': predicted_date.strftime('%Y-%m-%d'),
                'days_from_now': int(adjusted_days),
                'date_range': {
                    'earliest': (datetime.now() + timedelta(days=int(adjusted_days * 0.7))).strftime('%Y-%m-%d'),
                    'latest': (datetime.now() + timedelta(days=int(adjusted_days * 1.3))).strftime('%Y-%m-%d')
                }
            },
            factors=factors,
            recommendations=self._generate_timeline_recommendations(lead, adjusted_days)
        )

    def predict_deal_value(self, lead: Dict) -> PredictionResult:
        """Predict potential deal value/commission."""
        lead_id = lead.get('id', '')
        lead_type = lead.get('lead_type', 'buyer')
        
        factors = []
        
        # Get price range
        if lead_type == 'buyer':
            min_price = lead.get('min_price', 200000)
            max_price = lead.get('max_price', 500000)
            estimated_price = (min_price + max_price) / 2
            
            # Adjust based on preferences
            if lead.get('preapproved'):
                preapproval_amount = lead.get('preapproval_amount', estimated_price)
                estimated_price = min(preapproval_amount, max_price)
                factors.append({'factor': 'Pre-approval amount', 'impact': f'${preapproval_amount:,.0f}'})
        else:
            # Seller - use property value
            estimated_price = lead.get('property_value', lead.get('estimated_home_value', 350000))
            factors.append({'factor': 'Property value estimate', 'impact': f'${estimated_price:,.0f}'})
        
        # Calculate commission (assuming 3% average)
        commission_rate = 0.03
        gross_commission = estimated_price * commission_rate
        
        # Adjust for market conditions
        market_factor = lead.get('market_factor', 1.0)
        adjusted_commission = gross_commission * market_factor
        
        factors.append({'factor': 'Estimated sale price', 'impact': f'${estimated_price:,.0f}'})
        factors.append({'factor': 'Commission rate', 'impact': f'{commission_rate:.1%}'})
        
        # Factor in conversion probability
        conversion_pred = self.predict_conversion(lead)
        expected_value = adjusted_commission * conversion_pred.probability
        
        factors.append({'factor': 'Conversion probability', 'impact': f'{conversion_pred.probability:.0%}'})
        
        return PredictionResult(
            lead_id=lead_id,
            prediction_type='deal_value',
            probability=conversion_pred.probability,
            confidence=conversion_pred.confidence * 0.9,
            predicted_value={
                'estimated_sale_price': estimated_price,
                'gross_commission': adjusted_commission,
                'expected_value': expected_value,
                'commission_range': {
                    'low': adjusted_commission * 0.8,
                    'high': adjusted_commission * 1.2
                }
            },
            factors=factors,
            recommendations=self._generate_value_recommendations(lead, estimated_price)
        )

    def predict_best_contact_time(self, lead: Dict) -> PredictionResult:
        """Predict optimal contact time based on behavior patterns."""
        lead_id = lead.get('id', '')
        
        # Analyze activity patterns
        activities = lead.get('activity_log', [])
        hour_counts = {}
        day_counts = {}
        
        for activity in activities:
            timestamp = activity.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        continue
                else:
                    dt = timestamp
                
                hour = dt.hour
                day = dt.strftime('%A').lower()
                
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
                day_counts[day] = day_counts.get(day, 0) + 1
        
        # Find peak times
        if hour_counts:
            best_hour = max(hour_counts, key=hour_counts.get)
        else:
            best_hour = 10  # Default
        
        if day_counts:
            best_day = max(day_counts, key=day_counts.get)
        else:
            best_day = 'tuesday'  # Default
        
        factors = [
            {'factor': 'Most active hour', 'impact': f'{best_hour}:00'},
            {'factor': 'Most active day', 'impact': best_day.title()},
            {'factor': 'Activity data points', 'impact': str(len(activities))}
        ]
        
        confidence = min(0.9, 0.4 + len(activities) * 0.05)
        
        return PredictionResult(
            lead_id=lead_id,
            prediction_type='best_contact_time',
            probability=0.0,
            confidence=confidence,
            predicted_value={
                'best_hour': best_hour,
                'best_day': best_day,
                'recommended_window': f'{best_day.title()} at {best_hour}:00',
                'alternative_times': [
                    f'{best_day.title()} at {best_hour + 1}:00',
                    f'{best_day.title()} at {best_hour - 1}:00'
                ]
            },
            factors=factors,
            recommendations=[
                f"Best time to reach out: {best_day.title()} around {best_hour}:00",
                "Consider their timezone and work schedule",
                "Text first to confirm availability for a call"
            ]
        )

    def _days_since_created(self, lead: Dict) -> int:
        """Calculate days since lead was created."""
        created = lead.get('created_at')
        if not created:
            return 0
        
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace('Z', '+00:00'))
            except:
                return 0
        
        return (datetime.now() - created.replace(tzinfo=None)).days

    def _calculate_confidence(self, lead: Dict) -> float:
        """Calculate confidence based on data completeness."""
        completeness = 0.0
        
        # Essential fields
        if lead.get('name'):
            completeness += 0.1
        if lead.get('email'):
            completeness += 0.1
        if lead.get('phone'):
            completeness += 0.1
        if lead.get('source'):
            completeness += 0.1
        
        # Behavioral data
        if lead.get('property_views'):
            completeness += 0.15
        if lead.get('email_opens'):
            completeness += 0.1
        if lead.get('showings_attended'):
            completeness += 0.15
        
        # Qualification data
        if lead.get('preapproved') is not None:
            completeness += 0.1
        if lead.get('timeline'):
            completeness += 0.1
        
        return min(0.95, completeness)

    def _generate_conversion_recommendations(
        self,
        lead: Dict,
        probability: float,
        factors: List[Dict]
    ) -> List[str]:
        """Generate recommendations to improve conversion."""
        recommendations = []
        
        if probability < 0.3:
            recommendations.append("Focus on re-engagement - lead may be going cold")
            recommendations.append("Consider adding to long-term nurture campaign")
        elif probability < 0.5:
            recommendations.append("Increase touchpoint frequency")
            recommendations.append("Send personalized property recommendations")
        else:
            recommendations.append("Strike while hot - schedule call today")
            recommendations.append("Prepare for next steps in transaction")
        
        # Specific recommendations based on missing factors
        if not lead.get('preapproved') and lead.get('lead_type') == 'buyer':
            recommendations.append("Encourage mortgage pre-approval to strengthen position")
        
        if lead.get('showings_attended', 0) == 0 and lead.get('stage') not in ['new']:
            recommendations.append("Schedule first property showing")
        
        if not lead.get('property_views'):
            recommendations.append("Send curated property list to gauge interest")
        
        return recommendations[:5]

    def _generate_timeline_recommendations(self, lead: Dict, days: float) -> List[str]:
        """Generate timeline-based recommendations."""
        recommendations = []
        
        if days < 30:
            recommendations.extend([
                "Fast-track this lead - closing could be imminent",
                "Ensure all financing is in order",
                "Prepare closing documents early"
            ])
        elif days < 60:
            recommendations.extend([
                "Maintain weekly contact",
                "Continue showing relevant properties",
                "Address any concerns promptly"
            ])
        else:
            recommendations.extend([
                "Set up automated nurture sequence",
                "Schedule monthly check-ins",
                "Add to market update distribution"
            ])
        
        return recommendations

    def _generate_value_recommendations(self, lead: Dict, price: float) -> List[str]:
        """Generate value-optimization recommendations."""
        recommendations = []
        
        if price >= 500000:
            recommendations.append("High-value opportunity - prioritize personal attention")
            recommendations.append("Consider premium marketing materials")
        
        if lead.get('lead_type') == 'buyer':
            recommendations.append("Explore move-up potential for future business")
        else:
            recommendations.append("Discuss staging and prep for maximum sale price")
        
        recommendations.append("Request referrals upon successful close")
        
        return recommendations
