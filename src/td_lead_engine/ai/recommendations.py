"""AI-powered lead recommendations engine."""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Any
import random


class RecommendationType(Enum):
    """Types of recommendations."""
    CONTACT_NOW = "contact_now"
    SEND_LISTING = "send_listing"
    SCHEDULE_SHOWING = "schedule_showing"
    FOLLOW_UP_CALL = "follow_up_call"
    SEND_MARKET_UPDATE = "send_market_update"
    RE_ENGAGE = "re_engage"
    REQUEST_REFERRAL = "request_referral"
    NURTURE_CAMPAIGN = "nurture_campaign"
    PRICE_REDUCTION_ALERT = "price_reduction_alert"
    NEW_LISTING_MATCH = "new_listing_match"
    SCHEDULE_CONSULTATION = "schedule_consultation"
    SEND_CMA = "send_cma"


@dataclass
class Recommendation:
    """A recommendation for action on a lead."""
    id: str
    lead_id: str
    recommendation_type: RecommendationType
    priority: int  # 1-10, 10 being highest
    title: str
    description: str
    reasoning: str
    suggested_action: str
    suggested_timing: str
    confidence: float  # 0-1
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    completed: bool = False
    completed_at: Optional[datetime] = None


class LeadRecommendationEngine:
    """AI engine for generating lead recommendations."""

    def __init__(self, data_dir: str = "data/ai"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.recommendation_history: List[Recommendation] = []
        
        # Weights for recommendation scoring
        self.weights = {
            'score': 0.3,
            'recency': 0.2,
            'engagement': 0.2,
            'timing': 0.15,
            'opportunity': 0.15
        }

    def analyze_lead(self, lead: Dict) -> List[Recommendation]:
        """Analyze a lead and generate recommendations."""
        recommendations = []
        
        lead_id = lead.get('id', '')
        score = lead.get('score', 0)
        days_since_contact = self._days_since_last_contact(lead)
        engagement_level = self._calculate_engagement(lead)
        lead_type = lead.get('lead_type', 'buyer')
        stage = lead.get('stage', 'new')
        
        # High score, recent activity - contact immediately
        if score >= 80 and days_since_contact <= 1:
            recommendations.append(self._create_recommendation(
                lead_id=lead_id,
                rec_type=RecommendationType.CONTACT_NOW,
                priority=10,
                title="Hot Lead - Contact Immediately",
                description=f"This lead has a score of {score} and recent activity. High buying intent detected.",
                reasoning="High lead score combined with recent engagement indicates strong buying intent.",
                action="Call within the next hour",
                timing="Immediately",
                confidence=0.95
            ))
        
        # Good score, active but not contacted recently
        elif score >= 60 and days_since_contact >= 3:
            recommendations.append(self._create_recommendation(
                lead_id=lead_id,
                rec_type=RecommendationType.FOLLOW_UP_CALL,
                priority=8,
                title="Follow-up Needed",
                description=f"It's been {days_since_contact} days since last contact with this warm lead.",
                reasoning="Regular contact with warm leads prevents them from going cold.",
                action="Schedule a check-in call",
                timing="Within 24 hours",
                confidence=0.85
            ))
        
        # Lead has been inactive
        if days_since_contact >= 14 and score >= 40:
            recommendations.append(self._create_recommendation(
                lead_id=lead_id,
                rec_type=RecommendationType.RE_ENGAGE,
                priority=6,
                title="Re-engagement Needed",
                description=f"This lead has been inactive for {days_since_contact} days.",
                reasoning="Extended inactivity may indicate waning interest - re-engagement can revive the opportunity.",
                action="Send personalized re-engagement message or call",
                timing="Within 48 hours",
                confidence=0.70
            ))
        
        # Buyer with search criteria but no listings sent recently
        if lead_type == 'buyer' and lead.get('search_criteria'):
            listings_sent = lead.get('listings_sent_count', 0)
            last_listing_sent = lead.get('last_listing_sent')
            
            if not last_listing_sent or self._days_ago(last_listing_sent) >= 7:
                recommendations.append(self._create_recommendation(
                    lead_id=lead_id,
                    rec_type=RecommendationType.SEND_LISTING,
                    priority=7,
                    title="Send New Listings",
                    description="Time to send fresh property recommendations based on their search criteria.",
                    reasoning="Regular listing updates keep buyers engaged and demonstrate value.",
                    action="Curate and send 3-5 matching properties",
                    timing="Today",
                    confidence=0.80
                ))
        
        # Seller lead - offer CMA
        if lead_type == 'seller' and stage in ['new', 'contacted']:
            if not lead.get('cma_sent'):
                recommendations.append(self._create_recommendation(
                    lead_id=lead_id,
                    rec_type=RecommendationType.SEND_CMA,
                    priority=8,
                    title="Send CMA Report",
                    description="This seller hasn't received a CMA yet.",
                    reasoning="CMAs demonstrate expertise and provide value to potential sellers.",
                    action="Generate and send personalized CMA",
                    timing="Within 24 hours",
                    confidence=0.85
                ))
        
        # High engagement buyer - schedule consultation
        if lead_type == 'buyer' and engagement_level >= 0.7 and stage == 'qualified':
            if not lead.get('consultation_scheduled'):
                recommendations.append(self._create_recommendation(
                    lead_id=lead_id,
                    rec_type=RecommendationType.SCHEDULE_CONSULTATION,
                    priority=9,
                    title="Schedule Buyer Consultation",
                    description="This engaged buyer is ready for a formal consultation.",
                    reasoning="High engagement indicates readiness to move forward in the buying process.",
                    action="Reach out to schedule in-person or virtual consultation",
                    timing="Within 24 hours",
                    confidence=0.88
                ))
        
        # Lead has viewed properties multiple times - schedule showing
        property_views = lead.get('property_views', [])
        if property_views:
            repeated_views = self._find_repeated_views(property_views)
            if repeated_views:
                recommendations.append(self._create_recommendation(
                    lead_id=lead_id,
                    rec_type=RecommendationType.SCHEDULE_SHOWING,
                    priority=9,
                    title="Schedule Showing",
                    description=f"Lead has viewed {len(repeated_views)} properties multiple times.",
                    reasoning="Repeated property views indicate strong interest in specific properties.",
                    action=f"Offer to schedule showings for top {min(3, len(repeated_views))} properties",
                    timing="Today",
                    confidence=0.90,
                    context={'properties': repeated_views[:3]}
                ))
        
        # Closed client - request referral
        if stage == 'closed' and lead.get('closed_date'):
            days_since_close = self._days_ago(lead.get('closed_date'))
            if 30 <= days_since_close <= 90 and not lead.get('referral_requested'):
                recommendations.append(self._create_recommendation(
                    lead_id=lead_id,
                    rec_type=RecommendationType.REQUEST_REFERRAL,
                    priority=5,
                    title="Request Referral",
                    description=f"Client closed {days_since_close} days ago - perfect time for referral request.",
                    reasoning="Happy clients are most likely to refer within 30-90 days of closing.",
                    action="Send personalized referral request",
                    timing="This week",
                    confidence=0.75
                ))
        
        # Sort by priority
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        
        return recommendations

    def get_daily_priorities(self, leads: List[Dict], limit: int = 10) -> List[Recommendation]:
        """Get top priority recommendations across all leads."""
        all_recommendations = []
        
        for lead in leads:
            recs = self.analyze_lead(lead)
            all_recommendations.extend(recs)
        
        # Sort by priority and confidence
        all_recommendations.sort(
            key=lambda r: (r.priority * r.confidence),
            reverse=True
        )
        
        return all_recommendations[:limit]

    def get_recommendations_by_type(
        self,
        leads: List[Dict],
        rec_type: RecommendationType
    ) -> List[Recommendation]:
        """Get all recommendations of a specific type."""
        recommendations = []
        for lead in leads:
            for rec in self.analyze_lead(lead):
                if rec.recommendation_type == rec_type:
                    recommendations.append(rec)
        return sorted(recommendations, key=lambda r: r.priority, reverse=True)

    def mark_completed(self, recommendation_id: str):
        """Mark a recommendation as completed."""
        for rec in self.recommendation_history:
            if rec.id == recommendation_id:
                rec.completed = True
                rec.completed_at = datetime.now()
                break

    def _create_recommendation(
        self,
        lead_id: str,
        rec_type: RecommendationType,
        priority: int,
        title: str,
        description: str,
        reasoning: str,
        action: str,
        timing: str,
        confidence: float,
        context: Dict = None
    ) -> Recommendation:
        """Create a recommendation object."""
        import uuid
        rec = Recommendation(
            id=str(uuid.uuid4()),
            lead_id=lead_id,
            recommendation_type=rec_type,
            priority=priority,
            title=title,
            description=description,
            reasoning=reasoning,
            suggested_action=action,
            suggested_timing=timing,
            confidence=confidence,
            context=context or {},
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.recommendation_history.append(rec)
        return rec

    def _days_since_last_contact(self, lead: Dict) -> int:
        """Calculate days since last contact."""
        last_contact = lead.get('last_contact_date') or lead.get('last_activity_date')
        if not last_contact:
            created = lead.get('created_at')
            if created:
                return self._days_ago(created)
            return 30
        return self._days_ago(last_contact)

    def _days_ago(self, date_str: str) -> int:
        """Calculate days ago from a date string."""
        if isinstance(date_str, datetime):
            date = date_str
        else:
            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                return 0
        return (datetime.now() - date.replace(tzinfo=None)).days

    def _calculate_engagement(self, lead: Dict) -> float:
        """Calculate engagement level (0-1)."""
        score = 0.0
        
        # Email opens
        email_opens = lead.get('email_opens', 0)
        score += min(email_opens * 0.1, 0.3)
        
        # Property views
        views = len(lead.get('property_views', []))
        score += min(views * 0.05, 0.3)
        
        # Showing attendance
        showings = lead.get('showings_attended', 0)
        score += min(showings * 0.15, 0.3)
        
        # Direct responses
        responses = lead.get('response_count', 0)
        score += min(responses * 0.1, 0.3)
        
        return min(score, 1.0)

    def _find_repeated_views(self, property_views: List[Dict]) -> List[str]:
        """Find properties viewed multiple times."""
        view_counts = {}
        for view in property_views:
            prop_id = view.get('property_id')
            if prop_id:
                view_counts[prop_id] = view_counts.get(prop_id, 0) + 1
        
        repeated = [pid for pid, count in view_counts.items() if count >= 2]
        return repeated
