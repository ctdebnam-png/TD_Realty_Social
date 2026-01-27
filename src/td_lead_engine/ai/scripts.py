"""AI-powered script generation for lead outreach."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ScriptType(Enum):
    """Types of outreach scripts."""
    INITIAL_CALL = "initial_call"
    FOLLOW_UP_CALL = "follow_up_call"
    VOICEMAIL = "voicemail"
    EMAIL_INTRO = "email_intro"
    EMAIL_FOLLOW_UP = "email_follow_up"
    TEXT_MESSAGE = "text_message"
    SOCIAL_DM = "social_dm"
    OBJECTION_RESPONSE = "objection_response"


@dataclass
class GeneratedScript:
    """A generated outreach script."""
    script_type: ScriptType
    lead_name: str
    content: str
    subject_line: Optional[str] = None  # For emails
    talking_points: Optional[List[str]] = None
    variations: Optional[List[str]] = None


class ScriptGenerator:
    """Generate personalized outreach scripts using AI."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the script generator."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None

        # Agent info for personalization
        self.agent_name = "TD Realty"
        self.agent_phone = "(614) 555-0123"
        self.agent_email = "info@tdrealtyohio.com"
        self.market_area = "Columbus, Ohio"

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

    def configure_agent(
        self,
        name: str,
        phone: str = None,
        email: str = None,
        market_area: str = None
    ):
        """Configure agent details for script personalization."""
        self.agent_name = name
        if phone:
            self.agent_phone = phone
        if email:
            self.agent_email = email
        if market_area:
            self.market_area = market_area

    def generate_script(
        self,
        lead,
        script_type: ScriptType,
        context: str = None
    ) -> Optional[GeneratedScript]:
        """Generate a personalized script for a lead."""
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return self._get_template_script(lead, script_type)

        lead_context = self._build_lead_context(lead)
        if context:
            lead_context += f"\n\nAdditional Context: {context}"

        prompt = self._get_script_prompt(script_type, lead_context)

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,
                max_tokens=1000
            )

            result = json.loads(response.choices[0].message.content)

            return GeneratedScript(
                script_type=script_type,
                lead_name=getattr(lead, 'name', 'there'),
                content=result.get("script", ""),
                subject_line=result.get("subject_line"),
                talking_points=result.get("talking_points"),
                variations=result.get("variations")
            )

        except Exception as e:
            logger.error(f"Error generating script: {e}")
            return self._get_template_script(lead, script_type)

    def _build_lead_context(self, lead) -> str:
        """Build context string from lead data."""
        parts = [f"Lead Name: {getattr(lead, 'name', 'Unknown')}"]

        if hasattr(lead, 'source'):
            parts.append(f"Source: {lead.source}")
        if hasattr(lead, 'tier'):
            parts.append(f"Tier: {lead.tier} (Score: {getattr(lead, 'score', 0)})")
        if hasattr(lead, 'bio') and lead.bio:
            parts.append(f"Bio/Notes: {lead.bio}")
        if hasattr(lead, 'tags') and lead.tags:
            parts.append(f"Tags: {lead.tags}")

        # Extract signals
        if hasattr(lead, 'score_breakdown') and lead.score_breakdown:
            try:
                breakdown = json.loads(lead.score_breakdown)
                if "matches" in breakdown:
                    signals = [m["phrase"] for m in breakdown["matches"][:5]]
                    parts.append(f"Interest Signals: {', '.join(signals)}")
            except Exception:
                pass

        return "\n".join(parts)

    def _get_system_prompt(self) -> str:
        """Get system prompt for script generation."""
        return f"""You are an expert real estate sales copywriter creating outreach scripts for {self.agent_name} in {self.market_area}.

Guidelines:
- Be conversational and genuine, never pushy or salesy
- Reference specific details from the lead's profile when possible
- Keep messages concise - respect people's time
- Include a clear but soft call-to-action
- For Columbus, OH: mention local areas like Dublin, Powell, Westerville, German Village when relevant
- Sound like a helpful neighbor, not a pushy salesperson

Agent Contact Info:
- Name: {self.agent_name}
- Phone: {self.agent_phone}
- Email: {self.agent_email}"""

    def _get_script_prompt(self, script_type: ScriptType, lead_context: str) -> str:
        """Get the specific prompt for each script type."""
        prompts = {
            ScriptType.INITIAL_CALL: f"""Create an initial phone call script for this lead.

{lead_context}

Return JSON:
{{
    "script": "Full phone script with natural conversation flow, including greeting, hook, questions to ask, and soft close",
    "talking_points": ["Key points to cover"],
    "variations": ["Alternative opening lines"]
}}""",

            ScriptType.VOICEMAIL: f"""Create a voicemail script for this lead (under 30 seconds when spoken).

{lead_context}

Return JSON:
{{
    "script": "Voicemail script - friendly, brief, with clear callback reason",
    "variations": ["2-3 alternative versions"]
}}""",

            ScriptType.EMAIL_INTRO: f"""Create an initial email for this lead.

{lead_context}

Return JSON:
{{
    "subject_line": "Compelling but not clickbaity subject",
    "script": "Email body - personalized, valuable, with soft CTA",
    "variations": ["Alternative subject lines"]
}}""",

            ScriptType.EMAIL_FOLLOW_UP: f"""Create a follow-up email for this lead (assume no response to initial outreach).

{lead_context}

Return JSON:
{{
    "subject_line": "Follow-up subject line",
    "script": "Follow-up email - add value, don't be pushy",
    "talking_points": ["Value-adds to mention"]
}}""",

            ScriptType.TEXT_MESSAGE: f"""Create a text message for this lead (under 160 characters if possible).

{lead_context}

Return JSON:
{{
    "script": "Text message - casual, brief, conversational",
    "variations": ["2-3 alternative messages"]
}}""",

            ScriptType.SOCIAL_DM: f"""Create a social media direct message for this lead.

{lead_context}

Return JSON:
{{
    "script": "DM - casual, reference their content if relevant, not salesy",
    "variations": ["Alternative approaches"]
}}""",

            ScriptType.FOLLOW_UP_CALL: f"""Create a follow-up call script for this lead.

{lead_context}

Return JSON:
{{
    "script": "Follow-up phone script with value-add approach",
    "talking_points": ["Topics to discuss"],
    "variations": ["Alternative hooks"]
}}""",

            ScriptType.OBJECTION_RESPONSE: f"""Create responses to common objections for this lead.

{lead_context}

Return JSON:
{{
    "script": "General approach to objections for this lead type",
    "talking_points": [
        {{"objection": "I'm just looking", "response": "..."}},
        {{"objection": "I'm working with another agent", "response": "..."}},
        {{"objection": "Now isn't a good time", "response": "..."}},
        {{"objection": "I need to think about it", "response": "..."}}
    ]
}}"""
        }

        return prompts.get(script_type, prompts[ScriptType.EMAIL_INTRO])

    def _get_template_script(self, lead, script_type: ScriptType) -> GeneratedScript:
        """Get a template script when AI is not available."""
        name = getattr(lead, 'name', 'there')
        first_name = name.split()[0] if name and name != 'there' else 'there'

        templates = {
            ScriptType.INITIAL_CALL: f"""Hi {first_name}, this is {self.agent_name} with TD Realty.

I noticed you've been exploring real estate options in the Columbus area, and I wanted to reach out personally.

Are you currently looking to buy, sell, or just keeping an eye on the market?

[Listen and respond]

I'd love to be a resource for you - even if you're not ready to make a move yet. Would you be open to a quick chat about what you're seeing in the market?""",

            ScriptType.VOICEMAIL: f"""Hi {first_name}, this is {self.agent_name} with TD Realty.

I'm reaching out because I help people in the Columbus area with their real estate goals, and I'd love to be a resource for you.

Give me a call back at {self.agent_phone} when you have a moment. Talk soon!""",

            ScriptType.EMAIL_INTRO: f"""Hi {first_name},

I noticed your interest in Columbus real estate and wanted to personally reach out.

Whether you're thinking about buying, selling, or just curious about the market, I'd be happy to help answer any questions.

Would you be open to a quick call this week?

Best,
{self.agent_name}
{self.agent_phone}""",

            ScriptType.TEXT_MESSAGE: f"""Hi {first_name}! This is {self.agent_name} with TD Realty. Saw you're interested in Columbus real estate - happy to help if you have any questions!""",

            ScriptType.SOCIAL_DM: f"""Hey {first_name}! Noticed we're both in the Columbus area. I help people with real estate here - let me know if you ever have questions about the market!"""
        }

        return GeneratedScript(
            script_type=script_type,
            lead_name=name,
            content=templates.get(script_type, templates[ScriptType.EMAIL_INTRO]),
            subject_line="Quick question about Columbus real estate" if "EMAIL" in script_type.name else None
        )

    def generate_all_scripts(self, lead) -> Dict[str, GeneratedScript]:
        """Generate all script types for a lead."""
        scripts = {}

        for script_type in ScriptType:
            script = self.generate_script(lead, script_type)
            if script:
                scripts[script_type.value] = script

        return scripts

    def generate_objection_handlers(self, objections: List[str] = None) -> Dict[str, str]:
        """Generate responses to common or specific objections."""
        if not self.api_key:
            return self._get_template_objections()

        default_objections = [
            "I'm not ready to buy/sell yet",
            "I'm already working with an agent",
            "I'm just looking online, not serious",
            "The market is too crazy right now",
            "I can't afford anything in this market",
            "I want to wait for prices to drop"
        ]

        objections = objections or default_objections

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are a real estate sales expert helping agents handle objections professionally.
Create empathetic, value-focused responses that address concerns without being pushy.
Market: Columbus, Ohio
Agent: {self.agent_name}"""
                    },
                    {
                        "role": "user",
                        "content": f"Create responses to these objections:\n\n" + "\n".join(f"- {o}" for o in objections)
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=1500
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("responses", {})

        except Exception as e:
            logger.error(f"Error generating objection handlers: {e}")
            return self._get_template_objections()

    def _get_template_objections(self) -> Dict[str, str]:
        """Get template objection responses."""
        return {
            "I'm not ready yet": "That's totally fine! Most of my best clients started by just exploring. Would it help if I sent you a monthly market update so you can keep an eye on things?",
            "Working with another agent": "No problem at all - loyalty is important in this business. If anything changes or you'd like a second opinion, I'm always here.",
            "Just looking": "That's a great place to start! Are there specific neighborhoods you're curious about? I can send you some insights.",
            "Market is crazy": "You're not wrong - it's definitely competitive. That said, I've helped clients find great deals even in this market. Want me to show you how?",
            "Can't afford it": "I hear that a lot, and there are actually more options than most people realize. Have you looked into the programs for first-time buyers or down payment assistance?",
            "Waiting for prices to drop": "That's a common strategy. The tricky part is that rates and prices don't always move together. Want me to run some numbers to show you the real cost of waiting?"
        }
