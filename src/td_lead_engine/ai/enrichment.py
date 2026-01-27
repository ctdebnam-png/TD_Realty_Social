"""AI-powered lead data enrichment."""

import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class EnrichedData:
    """Enriched data about a lead."""

    # Inferred demographics
    estimated_age_range: Optional[str] = None
    estimated_income_range: Optional[str] = None
    likely_profession: Optional[str] = None
    family_status: Optional[str] = None

    # Real estate specific
    likely_buyer_or_seller: Optional[str] = None
    property_type_interest: Optional[str] = None
    price_range_estimate: Optional[str] = None
    timeline_estimate: Optional[str] = None
    motivation_factors: List[str] = None

    # Location
    likely_current_area: Optional[str] = None
    target_areas: List[str] = None

    # Engagement
    best_contact_method: Optional[str] = None
    best_contact_time: Optional[str] = None
    communication_preferences: List[str] = None

    # Confidence
    enrichment_confidence: float = 0.0


class AIEnrichment:
    """Enrich lead data using AI analysis."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the enrichment engine."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required")
        return self._client

    def enrich_lead(self, lead) -> EnrichedData:
        """Enrich a lead with AI-inferred data."""
        # Start with rule-based enrichment
        enriched = self._rule_based_enrichment(lead)

        # Enhance with AI if available
        if self.api_key:
            ai_enriched = self._ai_enrichment(lead)
            if ai_enriched:
                enriched = self._merge_enrichment(enriched, ai_enriched)

        return enriched

    def _rule_based_enrichment(self, lead) -> EnrichedData:
        """Apply rule-based enrichment from available data."""
        enriched = EnrichedData()

        bio = getattr(lead, 'bio', '') or ''
        name = getattr(lead, 'name', '') or ''
        email = getattr(lead, 'email', '') or ''
        source = getattr(lead, 'source', '') or ''

        bio_lower = bio.lower()

        # Buyer vs Seller signals
        buyer_signals = ['looking for', 'searching', 'want to buy', 'first home', 'relocating', 'moving to', 'preapproved', 'pre-approved']
        seller_signals = ['selling', 'downsizing', 'upgrading', 'relocating from', 'moving from', 'listing']

        buyer_score = sum(1 for s in buyer_signals if s in bio_lower)
        seller_score = sum(1 for s in seller_signals if s in bio_lower)

        if buyer_score > seller_score:
            enriched.likely_buyer_or_seller = "buyer"
        elif seller_score > buyer_score:
            enriched.likely_buyer_or_seller = "seller"
        elif buyer_score > 0 and seller_score > 0:
            enriched.likely_buyer_or_seller = "both"

        # Family status
        family_indicators = {
            'married': ['married', 'husband', 'wife', 'spouse'],
            'parent': ['kids', 'children', 'family', 'mom', 'dad', 'parent'],
            'single': ['single', 'bachelor'],
            'couple': ['couple', 'partner', 'fiancé', 'engaged']
        }

        for status, indicators in family_indicators.items():
            if any(ind in bio_lower for ind in indicators):
                enriched.family_status = status
                break

        # Property type interest
        property_types = {
            'single_family': ['house', 'home', 'single family', 'yard', 'garage'],
            'condo': ['condo', 'condominium', 'low maintenance'],
            'townhouse': ['townhouse', 'townhome'],
            'investment': ['rental', 'investment', 'income property', 'flip']
        }

        for ptype, indicators in property_types.items():
            if any(ind in bio_lower for ind in indicators):
                enriched.property_type_interest = ptype
                break

        # Target areas (Central Ohio specific)
        areas = ['dublin', 'powell', 'westerville', 'new albany', 'upper arlington',
                 'grandview', 'german village', 'short north', 'clintonville',
                 'worthington', 'hilliard', 'grove city', 'gahanna', 'bexley',
                 'pickerington', 'reynoldsburg', 'delaware', 'lewis center']

        target_areas = [area.title() for area in areas if area in bio_lower]
        if target_areas:
            enriched.target_areas = target_areas

        # Timeline
        timeline_signals = {
            'immediate': ['asap', 'immediately', 'urgent', 'this month', 'now'],
            '1-3 months': ['soon', 'few months', '1-3 months', 'this spring', 'this summer'],
            '3-6 months': ['later this year', '3-6 months', 'by end of year'],
            '6+ months': ['next year', 'eventually', 'someday', 'not sure when']
        }

        for timeline, indicators in timeline_signals.items():
            if any(ind in bio_lower for ind in indicators):
                enriched.timeline_estimate = timeline
                break

        # Price range from mentions
        price_patterns = [
            r'\$(\d{3})k', r'\$(\d{3}),?000', r'(\d{3})k budget',
            r'budget.{0,20}\$?(\d{3})', r'afford.{0,20}\$?(\d{3})'
        ]

        for pattern in price_patterns:
            match = re.search(pattern, bio_lower)
            if match:
                try:
                    price = int(match.group(1)) * 1000
                    enriched.price_range_estimate = f"${price:,} range"
                    break
                except ValueError:
                    pass

        # Best contact method from source
        contact_methods = {
            'instagram': 'social_dm',
            'facebook': 'social_dm',
            'linkedin': 'email',
            'zillow': 'phone',
            'realtor.com': 'phone',
            'google': 'email',
            'csv': 'email',
            'manual': 'phone'
        }

        enriched.best_contact_method = contact_methods.get(source.lower(), 'email')

        # Email-based inferences
        if email:
            if any(corp in email.lower() for corp in ['@google', '@amazon', '@microsoft', '@apple', '@meta', '@salesforce']):
                enriched.likely_profession = "tech professional"
                enriched.estimated_income_range = "$100k-200k"
            elif any(edu in email.lower() for edu in ['.edu', '@osu', '@ohio']):
                enriched.likely_profession = "education/student"

        # Set confidence based on available data
        confidence_factors = [
            enriched.likely_buyer_or_seller is not None,
            enriched.target_areas is not None and len(enriched.target_areas) > 0,
            enriched.timeline_estimate is not None,
            enriched.property_type_interest is not None,
            bool(bio)
        ]
        enriched.enrichment_confidence = sum(confidence_factors) / len(confidence_factors)

        return enriched

    def _ai_enrichment(self, lead) -> Optional[EnrichedData]:
        """Use AI to enrich lead data."""
        context = self._build_context(lead)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a lead data analyst for a Columbus, Ohio real estate agent.
Analyze the provided lead information and infer additional details.
Be conservative - only include inferences you're reasonably confident about.

Return JSON with:
{
    "estimated_age_range": "e.g., 25-35, 35-45, etc.",
    "estimated_income_range": "e.g., $75k-100k",
    "likely_profession": "inferred profession if evident",
    "family_status": "single/couple/family",
    "likely_buyer_or_seller": "buyer/seller/both/unknown",
    "property_type_interest": "single_family/condo/townhouse/investment",
    "price_range_estimate": "estimated budget",
    "timeline_estimate": "immediate/1-3 months/3-6 months/6+ months",
    "motivation_factors": ["list of likely motivations"],
    "target_areas": ["list of Columbus areas they might prefer"],
    "best_contact_method": "email/phone/text/social_dm",
    "best_contact_time": "morning/afternoon/evening/weekend",
    "communication_preferences": ["direct", "detailed", etc.],
    "enrichment_confidence": 0.0-1.0
}

Only include fields you have reasonable confidence about. Leave others null."""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this lead:\n\n{context}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.5,
                max_tokens=800
            )

            result = json.loads(response.choices[0].message.content)

            return EnrichedData(
                estimated_age_range=result.get("estimated_age_range"),
                estimated_income_range=result.get("estimated_income_range"),
                likely_profession=result.get("likely_profession"),
                family_status=result.get("family_status"),
                likely_buyer_or_seller=result.get("likely_buyer_or_seller"),
                property_type_interest=result.get("property_type_interest"),
                price_range_estimate=result.get("price_range_estimate"),
                timeline_estimate=result.get("timeline_estimate"),
                motivation_factors=result.get("motivation_factors", []),
                target_areas=result.get("target_areas", []),
                best_contact_method=result.get("best_contact_method"),
                best_contact_time=result.get("best_contact_time"),
                communication_preferences=result.get("communication_preferences", []),
                enrichment_confidence=result.get("enrichment_confidence", 0.5)
            )

        except Exception as e:
            logger.error(f"AI enrichment error: {e}")
            return None

    def _build_context(self, lead) -> str:
        """Build context string for AI analysis."""
        parts = []

        for attr in ['name', 'email', 'phone', 'bio', 'source', 'score', 'tier', 'tags']:
            value = getattr(lead, attr, None)
            if value:
                parts.append(f"{attr.title()}: {value}")

        if hasattr(lead, 'followers') and lead.followers:
            parts.append(f"Social Followers: {lead.followers}")

        if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
            try:
                breakdown = json.loads(lead.score_breakdown)
                if "matches" in breakdown:
                    signals = [m["phrase"] for m in breakdown["matches"]]
                    parts.append(f"Detected Interest Signals: {', '.join(signals)}")
            except Exception:
                pass

        return "\n".join(parts)

    def _merge_enrichment(self, rule_based: EnrichedData, ai_based: EnrichedData) -> EnrichedData:
        """Merge rule-based and AI-based enrichment, preferring AI for conflicts."""
        # Start with rule-based
        merged = EnrichedData()

        # Copy all fields from rule-based first
        for field in vars(rule_based):
            rule_value = getattr(rule_based, field)
            ai_value = getattr(ai_based, field, None)

            # Prefer AI value if it exists and is more specific
            if ai_value is not None:
                setattr(merged, field, ai_value)
            elif rule_value is not None:
                setattr(merged, field, rule_value)

        # Combine lists
        if rule_based.target_areas and ai_based.target_areas:
            merged.target_areas = list(set(rule_based.target_areas + ai_based.target_areas))

        if rule_based.motivation_factors and ai_based.motivation_factors:
            merged.motivation_factors = list(set(
                (rule_based.motivation_factors or []) +
                (ai_based.motivation_factors or [])
            ))

        # Average confidence
        merged.enrichment_confidence = (
            rule_based.enrichment_confidence + ai_based.enrichment_confidence
        ) / 2

        return merged

    def batch_enrich(self, leads: List, max_leads: int = 100) -> Dict[str, EnrichedData]:
        """Enrich multiple leads."""
        results = {}

        for lead in leads[:max_leads]:
            lead_id = str(getattr(lead, 'id', id(lead)))
            results[lead_id] = self.enrich_lead(lead)

        return results
