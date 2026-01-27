"""AI-powered lead insights using OpenAI GPT."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class LeadInsight:
    """AI-generated insight about a lead."""

    lead_id: str
    summary: str
    personality_type: str
    communication_style: str
    buying_readiness: str  # "hot", "warm", "nurture", "cold"
    recommended_approach: str
    talking_points: List[str]
    potential_objections: List[str]
    follow_up_timing: str
    confidence_score: float


class LeadInsightsEngine:
    """Generate AI-powered insights about leads."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the insights engine."""
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
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def analyze_lead(self, lead) -> Optional[LeadInsight]:
        """Analyze a lead and generate insights."""
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return None

        # Build context from lead data
        context = self._build_lead_context(lead)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this real estate lead and provide insights:\n\n{context}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)

            return LeadInsight(
                lead_id=str(lead.id) if hasattr(lead, 'id') else "unknown",
                summary=result.get("summary", ""),
                personality_type=result.get("personality_type", "unknown"),
                communication_style=result.get("communication_style", "balanced"),
                buying_readiness=result.get("buying_readiness", "warm"),
                recommended_approach=result.get("recommended_approach", ""),
                talking_points=result.get("talking_points", []),
                potential_objections=result.get("potential_objections", []),
                follow_up_timing=result.get("follow_up_timing", ""),
                confidence_score=result.get("confidence_score", 0.5)
            )

        except Exception as e:
            logger.error(f"Error analyzing lead: {e}")
            return None

    def _build_lead_context(self, lead) -> str:
        """Build context string from lead data."""
        parts = []

        if hasattr(lead, 'name') and lead.name:
            parts.append(f"Name: {lead.name}")

        if hasattr(lead, 'source') and lead.source:
            parts.append(f"Source: {lead.source}")

        if hasattr(lead, 'bio') and lead.bio:
            parts.append(f"Bio/Notes: {lead.bio}")

        if hasattr(lead, 'score'):
            parts.append(f"Lead Score: {lead.score}")

        if hasattr(lead, 'tier'):
            parts.append(f"Tier: {lead.tier}")

        if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
            try:
                breakdown = json.loads(lead.score_breakdown)
                if "matches" in breakdown:
                    signals = [m["phrase"] for m in breakdown["matches"][:10]]
                    parts.append(f"Detected Signals: {', '.join(signals)}")
            except Exception:
                pass

        if hasattr(lead, 'tags') and lead.tags:
            parts.append(f"Tags: {lead.tags}")

        if hasattr(lead, 'followers') and lead.followers:
            parts.append(f"Social Followers: {lead.followers}")

        if hasattr(lead, 'engagement_rate') and lead.engagement_rate:
            parts.append(f"Engagement Rate: {lead.engagement_rate:.1%}")

        return "\n".join(parts)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for lead analysis."""
        return """You are an expert real estate sales coach analyzing leads for a real estate agent in Columbus, Ohio.

Analyze the provided lead information and return a JSON object with the following fields:

{
    "summary": "2-3 sentence summary of who this lead is and their likely situation",
    "personality_type": "One of: analytical, driver, expressive, amiable",
    "communication_style": "Preferred communication approach: direct, consultative, relationship-focused, data-driven",
    "buying_readiness": "One of: hot, warm, nurture, cold",
    "recommended_approach": "Specific strategy for engaging this lead (2-3 sentences)",
    "talking_points": ["List of 3-5 specific talking points or topics to discuss"],
    "potential_objections": ["List of 2-3 likely objections or concerns they might have"],
    "follow_up_timing": "Recommended follow-up timing and frequency",
    "confidence_score": 0.0 to 1.0 confidence in this analysis
}

Consider Central Ohio market specifics:
- Popular areas: Dublin, Powell, Westerville, German Village, Short North, New Albany
- Key concerns: School districts, commute times, property taxes
- Common buyer types: Young professionals, growing families, investors, relocators

Be practical and actionable. Focus on insights that will help close deals."""

    def generate_batch_insights(self, leads: List, max_leads: int = 50) -> List[LeadInsight]:
        """Generate insights for multiple leads."""
        insights = []

        for lead in leads[:max_leads]:
            insight = self.analyze_lead(lead)
            if insight:
                insights.append(insight)

        return insights

    def get_daily_priorities(self, leads: List, limit: int = 10) -> Dict[str, Any]:
        """Get AI-powered daily priority recommendations."""
        if not self.api_key:
            return {"error": "OpenAI API key not configured"}

        # Get hot and warm leads
        hot_leads = [l for l in leads if hasattr(l, 'tier') and l.tier == 'hot'][:5]
        warm_leads = [l for l in leads if hasattr(l, 'tier') and l.tier == 'warm'][:10]

        leads_context = []
        for lead in hot_leads + warm_leads:
            leads_context.append({
                "name": getattr(lead, 'name', 'Unknown'),
                "score": getattr(lead, 'score', 0),
                "tier": getattr(lead, 'tier', 'unknown'),
                "source": getattr(lead, 'source', 'unknown'),
                "bio_preview": (getattr(lead, 'bio', '') or '')[:200]
            })

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a real estate sales coach. Given a list of leads, create a prioritized daily action plan.
Return JSON with:
{
    "priority_contacts": [{"name": "...", "reason": "...", "suggested_action": "..."}],
    "daily_focus": "One sentence describing today's focus",
    "quick_wins": ["List of 2-3 quick actions that could move deals forward"],
    "avoid": "One thing to avoid today based on the lead mix"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Here are today's leads to prioritize:\n\n{json.dumps(leads_context, indent=2)}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=800
            )

            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.error(f"Error generating priorities: {e}")
            return {"error": str(e)}

    def analyze_lead_pool(self, leads: List) -> Dict[str, Any]:
        """Analyze the entire lead pool for patterns and recommendations."""
        if not self.api_key or not leads:
            return {"error": "No API key or no leads to analyze"}

        # Gather statistics
        total = len(leads)
        by_tier = {}
        by_source = {}
        signals = []

        for lead in leads:
            tier = getattr(lead, 'tier', 'unknown')
            source = getattr(lead, 'source', 'unknown')

            by_tier[tier] = by_tier.get(tier, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1

            if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
                try:
                    breakdown = json.loads(lead.score_breakdown)
                    for match in breakdown.get("matches", []):
                        signals.append(match["phrase"])
                except Exception:
                    pass

        # Count top signals
        signal_counts = {}
        for s in signals:
            signal_counts[s] = signal_counts.get(s, 0) + 1
        top_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        stats = {
            "total_leads": total,
            "by_tier": by_tier,
            "by_source": by_source,
            "top_signals": top_signals
        }

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a real estate analytics expert. Analyze the lead pool statistics and provide strategic recommendations.
Return JSON with:
{
    "health_score": 0-100 score for lead pool health,
    "summary": "2-3 sentence summary of lead pool status",
    "strengths": ["List of 2-3 strengths"],
    "gaps": ["List of 2-3 gaps or concerns"],
    "recommendations": ["List of 3-5 specific recommendations"],
    "source_analysis": "Which sources are performing best and worst",
    "market_signals": "What the signal data tells us about current buyer/seller interest"
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this lead pool for a Columbus, Ohio real estate agent:\n\n{json.dumps(stats, indent=2)}"
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)
            result["raw_stats"] = stats
            return result

        except Exception as e:
            logger.error(f"Error analyzing lead pool: {e}")
            return {"error": str(e), "raw_stats": stats}
