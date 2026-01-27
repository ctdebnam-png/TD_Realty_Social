"""Email template management system."""

import json
import os
import uuid
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class TemplateCategory(Enum):
    """Categories for email templates."""
    WELCOME = "welcome"
    NURTURE = "nurture"
    FOLLOW_UP = "follow_up"
    SHOWING = "showing"
    TRANSACTION = "transaction"
    MARKET_UPDATE = "market_update"
    PROMOTIONAL = "promotional"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


@dataclass
class EmailTemplate:
    """An email template with variable substitution."""
    id: str
    name: str
    subject: str
    body_html: str
    body_text: str
    category: TemplateCategory
    variables: List[str] = field(default_factory=list)
    preview_text: str = ""
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def render(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Render the template with given context."""
        rendered_subject = self._substitute(self.subject, context)
        rendered_html = self._substitute(self.body_html, context)
        rendered_text = self._substitute(self.body_text, context)
        rendered_preview = self._substitute(self.preview_text, context)

        return {
            'subject': rendered_subject,
            'body_html': rendered_html,
            'body_text': rendered_text,
            'preview_text': rendered_preview
        }

    def _substitute(self, text: str, context: Dict[str, Any]) -> str:
        """Substitute variables in text."""
        result = text
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    def extract_variables(self) -> List[str]:
        """Extract all variable placeholders from the template."""
        pattern = r'\{\{(\w+)\}\}'
        all_text = f"{self.subject} {self.body_html} {self.body_text}"
        variables = re.findall(pattern, all_text)
        return list(set(variables))


class EmailTemplateManager:
    """Manages email templates."""

    def __init__(self, data_dir: str = "data/email_templates"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.templates: Dict[str, EmailTemplate] = {}
        self._load_data()
        self._ensure_default_templates()

    def _load_data(self):
        """Load templates from file."""
        templates_file = os.path.join(self.data_dir, "templates.json")
        if os.path.exists(templates_file):
            with open(templates_file) as f:
                data = json.load(f)
                for item in data:
                    item['category'] = TemplateCategory(item['category'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    item['updated_at'] = datetime.fromisoformat(item['updated_at'])
                    self.templates[item['id']] = EmailTemplate(**item)

    def _save_data(self):
        """Save templates to file."""
        templates_file = os.path.join(self.data_dir, "templates.json")
        with open(templates_file, 'w') as f:
            data = []
            for template in self.templates.values():
                item = asdict(template)
                item['category'] = template.category.value
                item['created_at'] = template.created_at.isoformat()
                item['updated_at'] = template.updated_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    def create_template(
        self,
        name: str,
        subject: str,
        body_html: str,
        body_text: str,
        category: TemplateCategory,
        preview_text: str = "",
        template_id: Optional[str] = None
    ) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(
            id=template_id or str(uuid.uuid4()),
            name=name,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            category=category,
            preview_text=preview_text
        )
        template.variables = template.extract_variables()
        self.templates[template.id] = template
        self._save_data()
        return template

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def update_template(self, template_id: str, **updates) -> Optional[EmailTemplate]:
        """Update a template."""
        if template_id not in self.templates:
            return None
        template = self.templates[template_id]
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.variables = template.extract_variables()
        template.updated_at = datetime.now()
        self._save_data()
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            self._save_data()
            return True
        return False

    def get_templates_by_category(self, category: TemplateCategory) -> List[EmailTemplate]:
        """Get all templates in a category."""
        return [t for t in self.templates.values()
                if t.category == category and t.is_active]

    def render_template(self, template_id: str, context: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Render a template with context."""
        template = self.get_template(template_id)
        if not template:
            return None
        template.usage_count += 1
        self._save_data()
        return template.render(context)

    def _ensure_default_templates(self):
        """Create default templates if they don't exist."""
        if not self.templates:
            self._create_default_templates()

    def _create_default_templates(self):
        """Create a set of default real estate email templates."""

        # Welcome email for buyers
        self.create_template(
            template_id="buyer_welcome",
            name="Buyer Welcome Email",
            category=TemplateCategory.WELCOME,
            subject="Welcome to TD Realty, {{first_name}}!",
            preview_text="Let's find your perfect home in Central Ohio",
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; background: #f8fafc; }
        .button { display: inline-block; background: #2563eb; color: white; padding: 12px 30px;
                  text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to TD Realty!</h1>
        </div>
        <div class="content">
            <p>Hi {{first_name}},</p>

            <p>Thank you for reaching out! I'm excited to help you find your perfect home in Central Ohio.</p>

            <p>As your dedicated real estate agent, I'll be with you every step of the way, from searching for
            properties to handing you the keys to your new home.</p>

            <p><strong>Here's what happens next:</strong></p>
            <ul>
                <li>I'll send you listings that match your criteria</li>
                <li>You can save your favorites and schedule tours</li>
                <li>I'm always just a call or text away</li>
            </ul>

            <p>Ready to start your home search?</p>

            <a href="{{portal_url}}" class="button">View Your Portal</a>

            <p>If you have any questions, feel free to reply to this email or call me at {{agent_phone}}.</p>

            <p>Looking forward to working with you!</p>

            <p>Best regards,<br>
            {{agent_name}}<br>
            TD Realty</p>
        </div>
        <div class="footer">
            <p>TD Realty | Central Ohio's Trusted Real Estate Partner</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
            """,
            body_text="""
Hi {{first_name}},

Thank you for reaching out! I'm excited to help you find your perfect home in Central Ohio.

As your dedicated real estate agent, I'll be with you every step of the way, from searching for
properties to handing you the keys to your new home.

Here's what happens next:
- I'll send you listings that match your criteria
- You can save your favorites and schedule tours
- I'm always just a call or text away

Ready to start your home search? Visit your portal: {{portal_url}}

If you have any questions, feel free to reply to this email or call me at {{agent_phone}}.

Looking forward to working with you!

Best regards,
{{agent_name}}
TD Realty
            """
        )

        # Welcome email for sellers
        self.create_template(
            template_id="seller_welcome",
            name="Seller Welcome Email",
            category=TemplateCategory.WELCOME,
            subject="Let's Get Your Home Sold, {{first_name}}!",
            preview_text="Your partner in selling your Central Ohio home",
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #059669; color: white; padding: 30px; text-align: center; }
        .content { padding: 30px; background: #f8fafc; }
        .button { display: inline-block; background: #059669; color: white; padding: 12px 30px;
                  text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Let's Sell Your Home!</h1>
        </div>
        <div class="content">
            <p>Hi {{first_name}},</p>

            <p>Thank you for considering TD Realty to help sell your home. I understand this is a big decision,
            and I'm here to make the process as smooth and profitable as possible.</p>

            <p><strong>What I offer:</strong></p>
            <ul>
                <li>Free comprehensive market analysis (CMA)</li>
                <li>Professional photography and marketing</li>
                <li>Expert pricing strategy</li>
                <li>Skilled negotiation to get you top dollar</li>
            </ul>

            <p>Would you like to know what your home is worth in today's market?</p>

            <a href="{{cma_request_url}}" class="button">Request Free Home Valuation</a>

            <p>I'd love to schedule a time to meet and discuss your goals. Reply to this email or call me
            at {{agent_phone}} to get started.</p>

            <p>Looking forward to helping you!</p>

            <p>Best regards,<br>
            {{agent_name}}<br>
            TD Realty</p>
        </div>
        <div class="footer">
            <p>TD Realty | Central Ohio's Trusted Real Estate Partner</p>
            <p><a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
            """,
            body_text="""
Hi {{first_name}},

Thank you for considering TD Realty to help sell your home. I understand this is a big decision,
and I'm here to make the process as smooth and profitable as possible.

What I offer:
- Free comprehensive market analysis (CMA)
- Professional photography and marketing
- Expert pricing strategy
- Skilled negotiation to get you top dollar

Would you like to know what your home is worth in today's market?
Request your free home valuation: {{cma_request_url}}

I'd love to schedule a time to meet and discuss your goals. Reply to this email or call me
at {{agent_phone}} to get started.

Looking forward to helping you!

Best regards,
{{agent_name}}
TD Realty
            """
        )

        # Showing reminder
        self.create_template(
            template_id="showing_reminder",
            name="Showing Reminder",
            category=TemplateCategory.SHOWING,
            subject="Reminder: Home Tour Tomorrow at {{property_address}}",
            preview_text="Don't forget your showing tomorrow!",
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2563eb; color: white; padding: 20px; text-align: center; }
        .property-card { background: white; border: 1px solid #e2e8f0; border-radius: 8px;
                         padding: 20px; margin: 20px 0; }
        .details { background: #f8fafc; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .button { display: inline-block; background: #2563eb; color: white; padding: 12px 30px;
                  text-decoration: none; border-radius: 5px; margin: 10px 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Your Showing is Tomorrow!</h2>
        </div>
        <div class="property-card">
            <h3>{{property_address}}</h3>
            <p>{{property_city}}, {{property_state}} {{property_zip}}</p>

            <div class="details">
                <p><strong>Date:</strong> {{showing_date}}</p>
                <p><strong>Time:</strong> {{showing_time}}</p>
                <p><strong>Price:</strong> ${{property_price}}</p>
                <p><strong>Details:</strong> {{property_beds}} beds | {{property_baths}} baths | {{property_sqft}} sqft</p>
            </div>

            <p>I'll meet you at the property. Please let me know if you need to reschedule.</p>

            <a href="{{confirm_url}}" class="button">Confirm Attendance</a>
            <a href="{{reschedule_url}}" class="button" style="background: #64748b;">Reschedule</a>
        </div>
        <div class="footer">
            <p>See you tomorrow!<br>{{agent_name}} | {{agent_phone}}</p>
        </div>
    </div>
</body>
</html>
            """,
            body_text="""
Your Showing is Tomorrow!

Property: {{property_address}}
{{property_city}}, {{property_state}} {{property_zip}}

Date: {{showing_date}}
Time: {{showing_time}}
Price: ${{property_price}}
Details: {{property_beds}} beds | {{property_baths}} baths | {{property_sqft}} sqft

I'll meet you at the property. Please let me know if you need to reschedule.

Confirm your attendance: {{confirm_url}}
Need to reschedule? {{reschedule_url}}

See you tomorrow!
{{agent_name}} | {{agent_phone}}
            """
        )

        # New listing alert
        self.create_template(
            template_id="new_listing_alert",
            name="New Listing Alert",
            category=TemplateCategory.NOTIFICATION,
            subject="New Listing: {{property_address}} - Matches Your Search!",
            preview_text="A new property matching your criteria just hit the market",
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .badge { display: inline-block; background: #059669; color: white; padding: 5px 15px;
                 border-radius: 20px; font-size: 12px; margin-bottom: 15px; }
        .property-card { background: white; border: 1px solid #e2e8f0; border-radius: 8px;
                         overflow: hidden; margin: 20px 0; }
        .property-image { width: 100%; height: 250px; object-fit: cover; }
        .property-details { padding: 20px; }
        .price { font-size: 28px; font-weight: bold; color: #2563eb; }
        .button { display: inline-block; background: #2563eb; color: white; padding: 12px 30px;
                  text-decoration: none; border-radius: 5px; margin: 10px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <span class="badge">New Listing!</span>

        <div class="property-card">
            <img src="{{property_image}}" alt="Property" class="property-image">
            <div class="property-details">
                <div class="price">${{property_price}}</div>
                <h3>{{property_address}}</h3>
                <p>{{property_city}}, {{property_state}} {{property_zip}}</p>
                <p>{{property_beds}} beds | {{property_baths}} baths | {{property_sqft}} sqft</p>

                <p>{{property_description}}</p>

                <a href="{{property_url}}" class="button">View Full Details</a>
                <a href="{{schedule_url}}" class="button" style="background: #059669;">Schedule Tour</a>
            </div>
        </div>

        <p>This property matches your saved search: "{{search_name}}"</p>

        <div class="footer">
            <p>{{agent_name}} | TD Realty | {{agent_phone}}</p>
            <p><a href="{{manage_alerts_url}}">Manage Alert Settings</a> |
               <a href="{{unsubscribe_url}}">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
            """,
            body_text="""
New Listing Alert!

${{property_price}}
{{property_address}}
{{property_city}}, {{property_state}} {{property_zip}}

{{property_beds}} beds | {{property_baths}} baths | {{property_sqft}} sqft

{{property_description}}

View full details: {{property_url}}
Schedule a tour: {{schedule_url}}

This property matches your saved search: "{{search_name}}"

{{agent_name}} | TD Realty | {{agent_phone}}

Manage alerts: {{manage_alerts_url}}
Unsubscribe: {{unsubscribe_url}}
            """
        )

        # Review request
        self.create_template(
            template_id="review_request",
            name="Review Request",
            category=TemplateCategory.FOLLOW_UP,
            subject="{{first_name}}, would you share your experience?",
            preview_text="Your feedback helps other home buyers and sellers",
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .content { padding: 30px; background: #f8fafc; text-align: center; }
        .stars { font-size: 40px; color: #fbbf24; margin: 20px 0; }
        .button { display: inline-block; background: #2563eb; color: white; padding: 15px 40px;
                  text-decoration: none; border-radius: 5px; margin: 20px 0; font-size: 18px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <h2>How was your experience?</h2>

            <p>Hi {{first_name}},</p>

            <p>Congratulations again on {{transaction_type == 'buyer' ? 'your new home' : 'selling your home'}}!
            I truly enjoyed working with you.</p>

            <p>If you have a moment, I'd be incredibly grateful if you could share your experience.
            Your review helps other families make informed decisions about their real estate needs.</p>

            <div class="stars">&#9733; &#9733; &#9733; &#9733; &#9733;</div>

            <a href="{{review_url}}" class="button">Leave a Review</a>

            <p>Thank you so much for your trust in TD Realty!</p>

            <p>Warmly,<br>{{agent_name}}</p>
        </div>
        <div class="footer">
            <p>TD Realty | Central Ohio's Trusted Real Estate Partner</p>
        </div>
    </div>
</body>
</html>
            """,
            body_text="""
How was your experience?

Hi {{first_name}},

Congratulations again on your real estate journey! I truly enjoyed working with you.

If you have a moment, I'd be incredibly grateful if you could share your experience.
Your review helps other families make informed decisions about their real estate needs.

Leave a review: {{review_url}}

Thank you so much for your trust in TD Realty!

Warmly,
{{agent_name}}
TD Realty
            """
        )

        self._save_data()
