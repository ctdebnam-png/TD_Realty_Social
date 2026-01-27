"""Email and SMS templates for drip campaigns."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import json
import os
import uuid
import re


class TemplateCategory(Enum):
    """Template categories."""
    WELCOME = "welcome"
    NURTURE = "nurture"
    FOLLOW_UP = "follow_up"
    EDUCATIONAL = "educational"
    PROMOTIONAL = "promotional"
    TRANSACTIONAL = "transactional"
    RE_ENGAGEMENT = "re_engagement"


@dataclass
class EmailTemplate:
    """An email template."""
    id: str
    name: str
    subject: str
    body_html: str
    body_text: str = ""
    category: TemplateCategory = TemplateCategory.NURTURE
    preview_text: str = ""
    from_name: str = ""
    tags: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class SMSTemplate:
    """An SMS template."""
    id: str
    name: str
    content: str
    category: TemplateCategory = TemplateCategory.NURTURE
    character_count: int = 0
    tags: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class TemplateLibrary:
    """Library of email and SMS templates."""
    
    # Common merge fields
    MERGE_FIELDS = [
        'first_name', 'last_name', 'full_name', 'email', 'phone',
        'property_address', 'property_price', 'property_beds', 'property_baths',
        'agent_name', 'agent_phone', 'agent_email', 'agent_photo',
        'office_name', 'office_address', 'office_phone',
        'current_date', 'current_year'
    ]
    
    def __init__(self, storage_path: str = "data/drip_campaigns"):
        self.storage_path = storage_path
        self.email_templates: Dict[str, EmailTemplate] = {}
        self.sms_templates: Dict[str, SMSTemplate] = {}
        
        self._load_data()
        self._create_default_templates()
    
    def _load_data(self):
        """Load templates from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load email templates
        email_file = f"{self.storage_path}/email_templates.json"
        if os.path.exists(email_file):
            with open(email_file, 'r') as f:
                data = json.load(f)
                for t in data:
                    template = EmailTemplate(
                        id=t['id'],
                        name=t['name'],
                        subject=t['subject'],
                        body_html=t['body_html'],
                        body_text=t.get('body_text', ''),
                        category=TemplateCategory(t.get('category', 'nurture')),
                        preview_text=t.get('preview_text', ''),
                        from_name=t.get('from_name', ''),
                        tags=t.get('tags', []),
                        variables=t.get('variables', []),
                        is_active=t.get('is_active', True),
                        created_at=datetime.fromisoformat(t['created_at']),
                        updated_at=datetime.fromisoformat(t.get('updated_at', t['created_at']))
                    )
                    self.email_templates[template.id] = template
        
        # Load SMS templates
        sms_file = f"{self.storage_path}/sms_templates.json"
        if os.path.exists(sms_file):
            with open(sms_file, 'r') as f:
                data = json.load(f)
                for t in data:
                    template = SMSTemplate(
                        id=t['id'],
                        name=t['name'],
                        content=t['content'],
                        category=TemplateCategory(t.get('category', 'nurture')),
                        character_count=t.get('character_count', len(t['content'])),
                        tags=t.get('tags', []),
                        variables=t.get('variables', []),
                        is_active=t.get('is_active', True),
                        created_at=datetime.fromisoformat(t['created_at'])
                    )
                    self.sms_templates[template.id] = template
    
    def _save_data(self):
        """Save templates to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save email templates
        email_data = [
            {
                'id': t.id,
                'name': t.name,
                'subject': t.subject,
                'body_html': t.body_html,
                'body_text': t.body_text,
                'category': t.category.value,
                'preview_text': t.preview_text,
                'from_name': t.from_name,
                'tags': t.tags,
                'variables': t.variables,
                'is_active': t.is_active,
                'created_at': t.created_at.isoformat(),
                'updated_at': t.updated_at.isoformat()
            }
            for t in self.email_templates.values()
        ]
        
        with open(f"{self.storage_path}/email_templates.json", 'w') as f:
            json.dump(email_data, f, indent=2)
        
        # Save SMS templates
        sms_data = [
            {
                'id': t.id,
                'name': t.name,
                'content': t.content,
                'category': t.category.value,
                'character_count': t.character_count,
                'tags': t.tags,
                'variables': t.variables,
                'is_active': t.is_active,
                'created_at': t.created_at.isoformat()
            }
            for t in self.sms_templates.values()
        ]
        
        with open(f"{self.storage_path}/sms_templates.json", 'w') as f:
            json.dump(sms_data, f, indent=2)
    
    def _create_default_templates(self):
        """Create default templates."""
        if self.email_templates or self.sms_templates:
            return
        
        # Welcome email
        self.create_email_template(
            name="Buyer Welcome",
            subject="Welcome to Your Home Search, {first_name}!",
            body_html="""
<h2>Welcome, {first_name}!</h2>
<p>Thank you for reaching out about finding your new home in Central Ohio.</p>
<p>I'm {agent_name}, and I'm excited to help you on this journey.</p>
<p>Here's what you can expect:</p>
<ul>
    <li>Personalized property recommendations</li>
    <li>Market updates for your areas of interest</li>
    <li>Expert guidance through every step</li>
</ul>
<p>Feel free to reach out anytime at {agent_phone}.</p>
<p>Best regards,<br>{agent_name}</p>
            """,
            category=TemplateCategory.WELCOME,
            tags=['buyer', 'welcome']
        )
        
        # Follow-up email
        self.create_email_template(
            name="Property Follow-Up",
            subject="What did you think of {property_address}?",
            body_html="""
<p>Hi {first_name},</p>
<p>I hope you enjoyed viewing {property_address}!</p>
<p>I'd love to hear your thoughts:</p>
<ul>
    <li>What did you like most about the home?</li>
    <li>Any concerns or questions?</li>
    <li>Would you like to see similar properties?</li>
</ul>
<p>Let me know how I can help!</p>
<p>{agent_name}<br>{agent_phone}</p>
            """,
            category=TemplateCategory.FOLLOW_UP,
            tags=['showing', 'follow-up']
        )
        
        # Welcome SMS
        self.create_sms_template(
            name="Quick Welcome",
            content="Hi {first_name}! This is {agent_name}. Thanks for reaching out about your home search. I'm here to help! Text or call me anytime.",
            category=TemplateCategory.WELCOME,
            tags=['buyer', 'welcome']
        )
        
        # Follow-up SMS
        self.create_sms_template(
            name="Check-In",
            content="Hi {first_name}! Just checking in on your home search. Any questions or new properties you'd like to see? - {agent_name}",
            category=TemplateCategory.FOLLOW_UP,
            tags=['nurture', 'check-in']
        )
    
    def _extract_variables(self, content: str) -> List[str]:
        """Extract merge variables from content."""
        pattern = r'\{([a-z_]+)\}'
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    def create_email_template(
        self,
        name: str,
        subject: str,
        body_html: str,
        body_text: str = "",
        category: TemplateCategory = TemplateCategory.NURTURE,
        preview_text: str = "",
        from_name: str = "",
        tags: List[str] = None
    ) -> EmailTemplate:
        """Create an email template."""
        # Auto-generate text version if not provided
        if not body_text:
            body_text = re.sub(r'<[^>]+>', '', body_html).strip()
        
        # Extract variables
        all_content = f"{subject} {body_html}"
        variables = self._extract_variables(all_content)
        
        template = EmailTemplate(
            id=str(uuid.uuid4())[:12],
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            category=category,
            preview_text=preview_text,
            from_name=from_name,
            tags=tags or [],
            variables=variables
        )
        self.email_templates[template.id] = template
        self._save_data()
        return template
    
    def create_sms_template(
        self,
        name: str,
        content: str,
        category: TemplateCategory = TemplateCategory.NURTURE,
        tags: List[str] = None
    ) -> SMSTemplate:
        """Create an SMS template."""
        variables = self._extract_variables(content)
        
        template = SMSTemplate(
            id=str(uuid.uuid4())[:12],
            name=name,
            content=content,
            category=category,
            character_count=len(content),
            tags=tags or [],
            variables=variables
        )
        self.sms_templates[template.id] = template
        self._save_data()
        return template
    
    def render_email(self, template_id: str, data: Dict) -> Optional[Dict]:
        """Render an email template with data."""
        template = self.email_templates.get(template_id)
        if not template:
            return None
        
        subject = template.subject
        body_html = template.body_html
        body_text = template.body_text
        
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            body_html = body_html.replace(placeholder, str(value))
            body_text = body_text.replace(placeholder, str(value))
        
        return {
            'subject': subject,
            'body_html': body_html,
            'body_text': body_text,
            'preview_text': template.preview_text,
            'from_name': template.from_name
        }
    
    def render_sms(self, template_id: str, data: Dict) -> Optional[str]:
        """Render an SMS template with data."""
        template = self.sms_templates.get(template_id)
        if not template:
            return None
        
        content = template.content
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            content = content.replace(placeholder, str(value))
        
        return content
    
    def get_templates_by_category(self, category: TemplateCategory) -> Dict:
        """Get templates by category."""
        return {
            'email': [t for t in self.email_templates.values() if t.category == category and t.is_active],
            'sms': [t for t in self.sms_templates.values() if t.category == category and t.is_active]
        }
    
    def search_templates(self, query: str) -> Dict:
        """Search templates by name or tags."""
        query = query.lower()
        
        email_matches = [
            t for t in self.email_templates.values()
            if query in t.name.lower() or any(query in tag.lower() for tag in t.tags)
        ]
        
        sms_matches = [
            t for t in self.sms_templates.values()
            if query in t.name.lower() or any(query in tag.lower() for tag in t.tags)
        ]
        
        return {
            'email': email_matches,
            'sms': sms_matches
        }
