"""Open house registration management."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import uuid

from .manager import OpenHouseManager, OpenHouseAttendee


@dataclass
class RegistrationForm:
    """Open house registration form configuration."""
    id: str
    open_house_id: str
    fields: List[Dict] = field(default_factory=list)
    confirmation_message: str = "Thank you for registering! We'll see you at the open house."
    send_confirmation_email: bool = True
    send_reminder_email: bool = True
    reminder_hours_before: int = 24


class RegistrationManager:
    """Manage open house registrations."""
    
    def __init__(
        self,
        open_house_manager: OpenHouseManager,
        storage_path: str = "data/oh_registration"
    ):
        self.oh_manager = open_house_manager
        self.storage_path = storage_path
        self.forms: Dict[str, RegistrationForm] = {}
        
        self._load_forms()
    
    def _load_forms(self):
        """Load registration forms from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        forms_file = f"{self.storage_path}/forms.json"
        if os.path.exists(forms_file):
            with open(forms_file, 'r') as f:
                data = json.load(f)
                for form_data in data:
                    form = RegistrationForm(
                        id=form_data['id'],
                        open_house_id=form_data['open_house_id'],
                        fields=form_data.get('fields', []),
                        confirmation_message=form_data.get('confirmation_message', ''),
                        send_confirmation_email=form_data.get('send_confirmation_email', True),
                        send_reminder_email=form_data.get('send_reminder_email', True),
                        reminder_hours_before=form_data.get('reminder_hours_before', 24)
                    )
                    self.forms[form.id] = form
    
    def _save_forms(self):
        """Save registration forms to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'id': f.id,
                'open_house_id': f.open_house_id,
                'fields': f.fields,
                'confirmation_message': f.confirmation_message,
                'send_confirmation_email': f.send_confirmation_email,
                'send_reminder_email': f.send_reminder_email,
                'reminder_hours_before': f.reminder_hours_before
            }
            for f in self.forms.values()
        ]
        
        with open(f"{self.storage_path}/forms.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_form(
        self,
        open_house_id: str,
        custom_fields: List[Dict] = None
    ) -> RegistrationForm:
        """Create a registration form for an open house."""
        default_fields = [
            {'name': 'first_name', 'label': 'First Name', 'type': 'text', 'required': True},
            {'name': 'last_name', 'label': 'Last Name', 'type': 'text', 'required': True},
            {'name': 'email', 'label': 'Email', 'type': 'email', 'required': True},
            {'name': 'phone', 'label': 'Phone', 'type': 'phone', 'required': True},
            {
                'name': 'working_with_agent',
                'label': 'Are you working with a real estate agent?',
                'type': 'radio',
                'options': ['Yes', 'No'],
                'required': True
            },
            {
                'name': 'preapproved',
                'label': 'Are you pre-approved for a mortgage?',
                'type': 'radio',
                'options': ['Yes', 'No', 'Cash buyer'],
                'required': False
            },
            {
                'name': 'timeframe',
                'label': 'When are you looking to buy?',
                'type': 'select',
                'options': ['Immediately', '1-3 months', '3-6 months', '6+ months', 'Just browsing'],
                'required': False
            }
        ]
        
        fields = custom_fields if custom_fields else default_fields
        
        form = RegistrationForm(
            id=str(uuid.uuid4())[:8],
            open_house_id=open_house_id,
            fields=fields
        )
        
        self.forms[form.id] = form
        self._save_forms()
        return form
    
    def get_form(self, form_id: str) -> Optional[RegistrationForm]:
        """Get a registration form."""
        return self.forms.get(form_id)
    
    def get_form_for_open_house(self, open_house_id: str) -> Optional[RegistrationForm]:
        """Get the registration form for an open house."""
        for form in self.forms.values():
            if form.open_house_id == open_house_id:
                return form
        return None
    
    def process_registration(
        self,
        form_id: str,
        form_data: Dict
    ) -> Optional[OpenHouseAttendee]:
        """Process a registration submission."""
        form = self.forms.get(form_id)
        if not form:
            return None
        
        # Validate required fields
        for field in form.fields:
            if field.get('required') and not form_data.get(field['name']):
                return None
        
        # Register attendee
        attendee = self.oh_manager.register_attendee(
            oh_id=form.open_house_id,
            first_name=form_data.get('first_name', ''),
            last_name=form_data.get('last_name', ''),
            email=form_data.get('email', ''),
            phone=form_data.get('phone', ''),
            working_with_agent=form_data.get('working_with_agent') == 'Yes',
            preapproved=form_data.get('preapproved') in ['Yes', 'Cash buyer'],
            timeframe=form_data.get('timeframe', '')
        )
        
        if attendee and form.send_confirmation_email:
            self._send_confirmation_email(attendee, form)
        
        return attendee
    
    def _send_confirmation_email(self, attendee: OpenHouseAttendee, form: RegistrationForm):
        """Send confirmation email to attendee."""
        oh = self.oh_manager.get_open_house(attendee.open_house_id)
        if not oh:
            return
        
        # Would integrate with email module
        pass
    
    def generate_form_html(self, form_id: str, action_url: str = "/api/open-house/register") -> str:
        """Generate HTML for registration form."""
        form = self.forms.get(form_id)
        if not form:
            return ""
        
        html = f'<form action="{action_url}" method="POST" class="oh-registration-form">'
        html += f'<input type="hidden" name="form_id" value="{form_id}">'
        
        for field in form.fields:
            required = 'required' if field.get('required') else ''
            req_star = '<span class="text-danger">*</span>' if field.get('required') else ''
            
            html += f'<div class="mb-3">'
            html += f'<label class="form-label">{field["label"]} {req_star}</label>'
            
            if field['type'] == 'text':
                html += f'<input type="text" class="form-control" name="{field["name"]}" {required}>'
            elif field['type'] == 'email':
                html += f'<input type="email" class="form-control" name="{field["name"]}" {required}>'
            elif field['type'] == 'phone':
                html += f'<input type="tel" class="form-control" name="{field["name"]}" {required}>'
            elif field['type'] == 'select':
                html += f'<select class="form-select" name="{field["name"]}" {required}>'
                html += '<option value="">Select...</option>'
                for opt in field.get('options', []):
                    html += f'<option value="{opt}">{opt}</option>'
                html += '</select>'
            elif field['type'] == 'radio':
                for opt in field.get('options', []):
                    html += f'''<div class="form-check">
                        <input class="form-check-input" type="radio" name="{field["name"]}" value="{opt}" {required}>
                        <label class="form-check-label">{opt}</label>
                    </div>'''
            
            html += '</div>'
        
        html += '<button type="submit" class="btn btn-primary w-100">Register</button>'
        html += '</form>'
        
        return html
