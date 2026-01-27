"""SMS template management."""

import json
import os
import uuid
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum


class SMSTemplateCategory(Enum):
    """Categories for SMS templates."""
    WELCOME = "welcome"
    SHOWING = "showing"
    FOLLOW_UP = "follow_up"
    ALERT = "alert"
    REMINDER = "reminder"
    OFFER = "offer"
    TRANSACTION = "transaction"
    CUSTOM = "custom"


@dataclass
class SMSTemplate:
    """An SMS template with variable substitution."""
    id: str
    name: str
    body: str
    category: SMSTemplateCategory
    variables: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    usage_count: int = 0

    def render(self, context: Dict[str, Any]) -> str:
        """Render the template with context."""
        result = self.body
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value) if value else "")
        return result

    def extract_variables(self) -> List[str]:
        """Extract variable placeholders from template."""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, self.body)))

    @property
    def character_count(self) -> int:
        """Get approximate character count (before variable substitution)."""
        return len(self.body)


class SMSTemplateManager:
    """Manages SMS templates."""

    def __init__(self, data_dir: str = "data/sms_templates"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.templates: Dict[str, SMSTemplate] = {}
        self._load_data()
        self._ensure_default_templates()

    def _load_data(self):
        """Load templates from file."""
        templates_file = os.path.join(self.data_dir, "templates.json")
        if os.path.exists(templates_file):
            with open(templates_file) as f:
                data = json.load(f)
                for item in data:
                    item['category'] = SMSTemplateCategory(item['category'])
                    item['created_at'] = datetime.fromisoformat(item['created_at'])
                    self.templates[item['id']] = SMSTemplate(**item)

    def _save_data(self):
        """Save templates to file."""
        templates_file = os.path.join(self.data_dir, "templates.json")
        with open(templates_file, 'w') as f:
            data = []
            for template in self.templates.values():
                item = asdict(template)
                item['category'] = template.category.value
                item['created_at'] = template.created_at.isoformat()
                data.append(item)
            json.dump(data, f, indent=2)

    def create_template(
        self,
        name: str,
        body: str,
        category: SMSTemplateCategory,
        template_id: str = None
    ) -> SMSTemplate:
        """Create a new SMS template."""
        template = SMSTemplate(
            id=template_id or str(uuid.uuid4()),
            name=name,
            body=body,
            category=category
        )
        template.variables = template.extract_variables()
        self.templates[template.id] = template
        self._save_data()
        return template

    def get_template(self, template_id: str) -> Optional[SMSTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def update_template(self, template_id: str, **updates) -> Optional[SMSTemplate]:
        """Update a template."""
        if template_id not in self.templates:
            return None
        template = self.templates[template_id]
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.variables = template.extract_variables()
        self._save_data()
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            self._save_data()
            return True
        return False

    def get_templates_by_category(self, category: SMSTemplateCategory) -> List[SMSTemplate]:
        """Get all templates in a category."""
        return [t for t in self.templates.values()
                if t.category == category and t.is_active]

    def render_template(self, template_id: str, context: Dict[str, Any]) -> Optional[str]:
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
        """Create default SMS templates."""

        # Welcome messages
        self.create_template(
            template_id="sms_welcome_buyer",
            name="Welcome - Buyer",
            category=SMSTemplateCategory.WELCOME,
            body="Hi {{first_name}}! Welcome to TD Realty. I'm excited to help you find your dream home in Central Ohio. Feel free to text me anytime with questions! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_welcome_seller",
            name="Welcome - Seller",
            category=SMSTemplateCategory.WELCOME,
            body="Hi {{first_name}}! Thanks for connecting with TD Realty. I look forward to helping you sell your home for top dollar. Let's chat soon! -{{agent_name}}"
        )

        # Showing templates
        self.create_template(
            template_id="sms_showing_scheduled",
            name="Showing Scheduled",
            category=SMSTemplateCategory.SHOWING,
            body="Hi {{first_name}}! Your showing is confirmed: {{property_address}} on {{date}} at {{time}}. I'll meet you there! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_showing_reminder_24h",
            name="Showing Reminder - 24hr",
            category=SMSTemplateCategory.REMINDER,
            body="Reminder: Tomorrow's showing at {{property_address}} at {{time}}. Reply YES to confirm or call to reschedule. -TD Realty"
        )

        self.create_template(
            template_id="sms_showing_reminder_1h",
            name="Showing Reminder - 1hr",
            category=SMSTemplateCategory.REMINDER,
            body="Hi {{first_name}}! Just a reminder, we're meeting at {{property_address}} in 1 hour. See you soon! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_showing_followup",
            name="Showing Follow-up",
            category=SMSTemplateCategory.FOLLOW_UP,
            body="Hi {{first_name}}! What did you think of {{property_address}}? I'd love to hear your feedback. Scale of 1-5, how interested are you? -{{agent_name}}"
        )

        # Alert templates
        self.create_template(
            template_id="sms_new_listing",
            name="New Listing Alert",
            category=SMSTemplateCategory.ALERT,
            body="New listing alert! {{property_address}} - ${{price}}. {{beds}}bd/{{baths}}ba. View: {{link}} -TD Realty"
        )

        self.create_template(
            template_id="sms_price_drop",
            name="Price Drop Alert",
            category=SMSTemplateCategory.ALERT,
            body="Price drop! {{property_address}} now ${{new_price}} (was ${{old_price}}). Interested? Reply YES to schedule a showing. -TD Realty"
        )

        # Offer templates
        self.create_template(
            template_id="sms_offer_submitted",
            name="Offer Submitted",
            category=SMSTemplateCategory.OFFER,
            body="Hi {{first_name}}! Your offer on {{property_address}} has been submitted. I'll keep you posted on any updates. -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_offer_received",
            name="Offer Received (Seller)",
            category=SMSTemplateCategory.OFFER,
            body="Great news! You've received an offer on {{property_address}} for ${{amount}}. I'm reviewing it now and will call you shortly. -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_offer_accepted",
            name="Offer Accepted",
            category=SMSTemplateCategory.OFFER,
            body="Congratulations {{first_name}}! Your offer on {{property_address}} was ACCEPTED! I'll call you to discuss next steps. -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_offer_countered",
            name="Counter Offer",
            category=SMSTemplateCategory.OFFER,
            body="Hi {{first_name}}, we received a counter offer on {{property_address}} for ${{counter_amount}}. Can we talk? -{{agent_name}}"
        )

        # Transaction templates
        self.create_template(
            template_id="sms_inspection_scheduled",
            name="Inspection Scheduled",
            category=SMSTemplateCategory.TRANSACTION,
            body="Hi {{first_name}}! Home inspection for {{property_address}} is scheduled for {{date}} at {{time}}. I'll be there! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_clear_to_close",
            name="Clear to Close",
            category=SMSTemplateCategory.TRANSACTION,
            body="{{first_name}}, we're CLEAR TO CLOSE on {{property_address}}! Closing is {{closing_date}}. Almost there! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_closing_reminder",
            name="Closing Reminder",
            category=SMSTemplateCategory.TRANSACTION,
            body="Hi {{first_name}}! Reminder: Closing on {{property_address}} is tomorrow at {{time}} at {{location}}. Bring your ID! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_closing_congrats",
            name="Closing Congratulations",
            category=SMSTemplateCategory.TRANSACTION,
            body="CONGRATULATIONS {{first_name}}! You did it! Welcome to your new home at {{property_address}}! It was a pleasure working with you. -{{agent_name}}"
        )

        # Follow-up templates
        self.create_template(
            template_id="sms_check_in",
            name="General Check-in",
            category=SMSTemplateCategory.FOLLOW_UP,
            body="Hi {{first_name}}! Just checking in - how's your home search going? Let me know if you have any questions or want to see more properties! -{{agent_name}}"
        )

        self.create_template(
            template_id="sms_review_request",
            name="Review Request",
            category=SMSTemplateCategory.FOLLOW_UP,
            body="Hi {{first_name}}! I hope you're loving your new home! If you have a moment, a review would mean the world to me: {{review_link}} -{{agent_name}}"
        )

        self._save_data()
