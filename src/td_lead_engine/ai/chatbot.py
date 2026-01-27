"""AI chatbot for website visitor engagement."""

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class ChatIntent(Enum):
    """Detected intents from user messages."""
    GREETING = "greeting"
    BUYING = "buying"
    SELLING = "selling"
    PRICING = "pricing"
    SCHEDULING = "scheduling"
    PROPERTY_INFO = "property_info"
    MORTGAGE = "mortgage"
    MARKET_INFO = "market_info"
    AGENT_CONNECT = "agent_connect"
    FAQ = "faq"
    UNKNOWN = "unknown"


@dataclass
class ChatResponse:
    """Response from the chatbot."""
    message: str
    intent: ChatIntent
    suggested_replies: List[str] = field(default_factory=list)
    action: Optional[str] = None
    data_collected: Dict[str, Any] = field(default_factory=dict)
    should_notify_agent: bool = False
    lead_score_impact: int = 0


@dataclass
class ChatSession:
    """A chat session with a visitor."""
    id: str
    visitor_id: str
    messages: List[Dict] = field(default_factory=list)
    collected_data: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    converted_to_lead: bool = False
    lead_id: Optional[str] = None


class LeadChatbot:
    """AI chatbot for capturing and qualifying leads from website."""

    def __init__(self, data_dir: str = "data/chatbot"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.sessions: Dict[str, ChatSession] = {}
        
        # Intent keywords
        self.intent_keywords = {
            ChatIntent.GREETING: ['hello', 'hi', 'hey', 'good morning', 'good afternoon'],
            ChatIntent.BUYING: ['buy', 'buying', 'purchase', 'looking for', 'search', 'find home', 'find house'],
            ChatIntent.SELLING: ['sell', 'selling', 'list', 'listing', 'my home', 'my house', 'what\'s my home worth'],
            ChatIntent.PRICING: ['price', 'cost', 'afford', 'budget', 'how much', 'worth'],
            ChatIntent.SCHEDULING: ['schedule', 'tour', 'showing', 'visit', 'see', 'appointment', 'meet'],
            ChatIntent.PROPERTY_INFO: ['bedroom', 'bathroom', 'sqft', 'square feet', 'garage', 'yard', 'pool'],
            ChatIntent.MORTGAGE: ['mortgage', 'loan', 'finance', 'pre-approval', 'preapproval', 'down payment'],
            ChatIntent.MARKET_INFO: ['market', 'neighborhood', 'area', 'school', 'commute'],
            ChatIntent.AGENT_CONNECT: ['agent', 'realtor', 'speak', 'call', 'contact', 'human', 'person'],
            ChatIntent.FAQ: ['how', 'what', 'when', 'why', 'process', 'steps']
        }
        
        # Response templates
        self.responses = {
            ChatIntent.GREETING: [
                "Hello! 👋 Welcome to TD Realty! I'm here to help you with your real estate needs in Central Ohio. Are you looking to buy or sell?",
                "Hi there! Thanks for visiting TD Realty. How can I help you today? Are you interested in buying, selling, or just exploring the market?"
            ],
            ChatIntent.BUYING: [
                "Great! I'd love to help you find your perfect home in Central Ohio. To get started, could you tell me:\n\n• What areas are you interested in?\n• How many bedrooms do you need?\n• What's your price range?",
                "Exciting! Let's find your dream home. What's most important to you - location, size, or price? I can help narrow down the options."
            ],
            ChatIntent.SELLING: [
                "I'd be happy to help you sell your home! Would you like a free home valuation to see what your property might be worth in today's market?",
                "Great choice! The Central Ohio market is strong right now. To give you the best guidance, can you tell me:\n\n• What's your property address?\n• How soon are you looking to sell?\n• Have you sold a home before?"
            ],
            ChatIntent.PRICING: [
                "I can help with that! Home prices in Central Ohio vary by area. For buyers, are you looking in a specific price range? For sellers, I can provide a free home valuation.",
                "Good question! Prices depend on location, size, and condition. Would you like me to send you a market report for a specific area, or get a valuation for your home?"
            ],
            ChatIntent.SCHEDULING: [
                "I'd be happy to schedule a showing for you! Which property are you interested in, and what times work best for you?",
                "Let's set that up! I can schedule a showing for any available time. Would you prefer weekday or weekend viewings?"
            ],
            ChatIntent.MORTGAGE: [
                "Great question! Getting pre-approved is one of the best first steps. It helps you know exactly what you can afford and makes your offers stronger. Would you like me to connect you with a trusted lender?",
                "Financing is important! A typical down payment is 3-20% depending on the loan type. Are you curious about specific mortgage options?"
            ],
            ChatIntent.MARKET_INFO: [
                "Central Ohio has several great neighborhoods! Dublin, Powell, and New Albany are known for excellent schools. German Village and Grandview are popular for their walkability. What matters most to you in a location?",
                "The Columbus market is quite active right now. Homes are selling quickly in popular areas. What neighborhood or features are you most interested in learning about?"
            ],
            ChatIntent.AGENT_CONNECT: [
                "I'd be happy to connect you with one of our experienced agents! They can provide personalized guidance for your situation. Can I get your name and phone number so they can reach out?",
                "Our agents are the best in Central Ohio! To have someone call you, I just need your contact information. What's the best number to reach you?"
            ],
            ChatIntent.FAQ: [
                "I'm here to answer any questions! Some common ones:\n\n• Buying process takes 30-60 days typically\n• Closing costs are usually 2-5% of purchase price\n• You don't pay agent fees as a buyer\n\nWhat specific question can I help with?",
                "Happy to explain! What would you like to know more about - the buying process, selling process, or something specific about the Columbus market?"
            ],
            ChatIntent.UNKNOWN: [
                "I want to make sure I help you correctly. Are you looking to:\n\n1. Buy a home\n2. Sell your home\n3. Learn about the market\n4. Speak with an agent",
                "I'm here to help! Could you tell me a bit more about what you're looking for? I can assist with buying, selling, or general real estate questions."
            ]
        }

    def start_session(self, visitor_id: str) -> ChatSession:
        """Start a new chat session."""
        session = ChatSession(
            id=str(uuid.uuid4()),
            visitor_id=visitor_id
        )
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get an existing session."""
        return self.sessions.get(session_id)

    def process_message(
        self,
        session_id: str,
        message: str
    ) -> ChatResponse:
        """Process an incoming message and generate response."""
        session = self.get_session(session_id)
        if not session:
            session = self.start_session(session_id)
        
        # Detect intent
        intent = self._detect_intent(message)
        
        # Extract any data from message
        extracted_data = self._extract_data(message, intent)
        session.collected_data.update(extracted_data)
        
        # Generate response
        response = self._generate_response(session, message, intent)
        
        # Log message
        session.messages.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat(),
            'intent': intent.value
        })
        session.messages.append({
            'role': 'assistant',
            'content': response.message,
            'timestamp': datetime.now().isoformat()
        })
        session.last_activity = datetime.now()
        
        return response

    def _detect_intent(self, message: str) -> ChatIntent:
        """Detect the intent of a message."""
        message_lower = message.lower()
        
        # Check for each intent's keywords
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                intent_scores[intent] = score
        
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return ChatIntent.UNKNOWN

    def _extract_data(self, message: str, intent: ChatIntent) -> Dict[str, Any]:
        """Extract structured data from message."""
        data = {}
        message_lower = message.lower()
        
        # Extract price range
        import re
        price_pattern = r'\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+)k?'
        prices = re.findall(price_pattern, message)
        if prices:
            # Convert to numbers
            price_values = []
            for p in prices:
                p = p.replace(',', '')
                if message_lower.find(p) != -1 and 'k' in message_lower[message_lower.find(p):message_lower.find(p)+len(p)+2].lower():
                    price_values.append(float(p) * 1000)
                else:
                    price_values.append(float(p))
            
            if len(price_values) >= 2:
                data['min_price'] = min(price_values)
                data['max_price'] = max(price_values)
            elif price_values:
                data['budget'] = price_values[0]
        
        # Extract bedrooms
        bed_pattern = r'(\d+)\s*(?:bed|br|bedroom)'
        beds = re.findall(bed_pattern, message_lower)
        if beds:
            data['bedrooms'] = int(beds[0])
        
        # Extract bathrooms
        bath_pattern = r'(\d+(?:\.\d+)?)\s*(?:bath|ba|bathroom)'
        baths = re.findall(bath_pattern, message_lower)
        if baths:
            data['bathrooms'] = float(baths[0])
        
        # Extract email
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, message)
        if emails:
            data['email'] = emails[0]
        
        # Extract phone
        phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        phones = re.findall(phone_pattern, message)
        if phones:
            data['phone'] = phones[0]
        
        # Extract areas (Central Ohio)
        areas = ['dublin', 'powell', 'westerville', 'worthington', 'hilliard', 
                 'grove city', 'gahanna', 'reynoldsburg', 'pickerington', 
                 'new albany', 'upper arlington', 'grandview', 'german village',
                 'short north', 'clintonville', 'bexley']
        found_areas = [area for area in areas if area in message_lower]
        if found_areas:
            data['areas'] = found_areas
        
        # Extract timeline
        timeline_keywords = {
            'immediately': 'immediate',
            'asap': 'immediate',
            'right away': 'immediate',
            'this month': '1_month',
            'next month': '1_month',
            '1-3 months': '1_3_months',
            'few months': '1_3_months',
            '3-6 months': '3_6_months',
            'within a year': '6_12_months',
            'just looking': 'just_looking',
            'browsing': 'just_looking'
        }
        for kw, timeline in timeline_keywords.items():
            if kw in message_lower:
                data['timeline'] = timeline
                break
        
        return data

    def _generate_response(
        self,
        session: ChatSession,
        message: str,
        intent: ChatIntent
    ) -> ChatResponse:
        """Generate appropriate response based on context."""
        import random
        
        # Get base response for intent
        responses = self.responses.get(intent, self.responses[ChatIntent.UNKNOWN])
        base_response = random.choice(responses)
        
        # Customize based on collected data
        suggested_replies = []
        action = None
        should_notify = False
        score_impact = 0
        
        # Check what data we already have
        has_contact = bool(session.collected_data.get('email') or session.collected_data.get('phone'))
        has_criteria = bool(session.collected_data.get('bedrooms') or session.collected_data.get('budget'))
        
        # Modify response based on context
        if intent == ChatIntent.BUYING and has_criteria:
            base_response += f"\n\nI see you're interested in "
            if session.collected_data.get('bedrooms'):
                base_response += f"{session.collected_data['bedrooms']} bedroom homes"
            if session.collected_data.get('budget'):
                base_response += f" around ${session.collected_data['budget']:,.0f}"
            if session.collected_data.get('areas'):
                base_response += f" in {', '.join(session.collected_data['areas'])}"
            base_response += ". I can send you matching listings!"
            suggested_replies = ["Send me listings", "I want to see homes", "Schedule a showing"]
            score_impact = 10
        
        elif intent == ChatIntent.SELLING:
            suggested_replies = ["Get home valuation", "What's my home worth?", "Schedule consultation"]
            score_impact = 15
        
        elif intent == ChatIntent.SCHEDULING:
            if not has_contact:
                base_response += "\n\nTo schedule, I'll need your contact information. What's the best way to reach you?"
                suggested_replies = ["Call me", "Email me", "Text me"]
            else:
                action = "schedule_showing"
                should_notify = True
            score_impact = 20
        
        elif intent == ChatIntent.AGENT_CONNECT:
            if not has_contact:
                base_response += "\n\nJust share your phone number or email, and I'll have an agent reach out shortly."
            else:
                base_response = f"Great! I've notified our team. An agent will call you at {session.collected_data.get('phone', session.collected_data.get('email'))} shortly!"
                action = "agent_callback"
                should_notify = True
            score_impact = 25
        
        # Check if we should convert to lead
        if has_contact and (has_criteria or intent in [ChatIntent.BUYING, ChatIntent.SELLING]):
            should_notify = True
            score_impact += 10
        
        # Default suggested replies
        if not suggested_replies:
            if intent == ChatIntent.GREETING:
                suggested_replies = ["I want to buy", "I want to sell", "Just browsing"]
            elif intent == ChatIntent.UNKNOWN:
                suggested_replies = ["Buy a home", "Sell my home", "Speak with agent"]
            else:
                suggested_replies = ["Tell me more", "Contact an agent", "Send me listings"]
        
        return ChatResponse(
            message=base_response,
            intent=intent,
            suggested_replies=suggested_replies,
            action=action,
            data_collected=session.collected_data,
            should_notify_agent=should_notify,
            lead_score_impact=score_impact
        )

    def convert_to_lead(self, session_id: str) -> Optional[Dict]:
        """Convert a chat session to a lead."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        if session.converted_to_lead:
            return {'lead_id': session.lead_id}
        
        # Create lead data from collected info
        lead_data = {
            'source': 'website_chat',
            'chat_session_id': session_id,
            **session.collected_data,
            'chat_transcript': session.messages,
            'created_at': datetime.now().isoformat()
        }
        
        # Determine lead type
        intents = [m.get('intent') for m in session.messages if m.get('role') == 'user']
        if 'selling' in intents:
            lead_data['lead_type'] = 'seller'
        elif 'buying' in intents:
            lead_data['lead_type'] = 'buyer'
        else:
            lead_data['lead_type'] = 'buyer'  # Default
        
        session.converted_to_lead = True
        session.lead_id = str(uuid.uuid4())
        lead_data['id'] = session.lead_id
        
        return lead_data

    def get_active_sessions(self, minutes: int = 30) -> List[ChatSession]:
        """Get sessions active in the last N minutes."""
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(minutes=minutes)
        
        return [
            s for s in self.sessions.values()
            if s.last_activity >= cutoff
        ]

    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get summary of a chat session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            'session_id': session.id,
            'visitor_id': session.visitor_id,
            'message_count': len(session.messages),
            'collected_data': session.collected_data,
            'started_at': session.started_at.isoformat(),
            'duration_minutes': (session.last_activity - session.started_at).seconds // 60,
            'converted': session.converted_to_lead,
            'lead_id': session.lead_id
        }
