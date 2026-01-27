"""Form builder for lead capture forms."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import json
import uuid
import re


class FieldType(Enum):
    """Form field types."""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime"
    RANGE = "range"
    FILE = "file"
    HIDDEN = "hidden"
    ADDRESS = "address"
    PRICE_RANGE = "price_range"
    PROPERTY_TYPE = "property_type"


@dataclass
class FieldValidation:
    """Validation rules for a form field."""
    required: bool = False
    min_length: int = None
    max_length: int = None
    min_value: float = None
    max_value: float = None
    pattern: str = None
    pattern_message: str = None
    custom_validator: str = None


@dataclass
class FormField:
    """A single form field."""
    id: str
    name: str
    field_type: FieldType
    label: str
    placeholder: str = ""
    help_text: str = ""
    default_value: Any = None
    options: List[Dict] = field(default_factory=list)  # For select/radio/checkbox
    validation: FieldValidation = field(default_factory=FieldValidation)
    conditional_display: Dict = None  # Show/hide based on other field values
    css_class: str = ""
    width: str = "full"  # full, half, third
    order: int = 0
    
    def to_html(self) -> str:
        """Generate HTML for this field."""
        required_attr = 'required' if self.validation.required else ''
        required_star = '<span class="text-danger">*</span>' if self.validation.required else ''
        
        width_class = {
            'full': 'col-12',
            'half': 'col-md-6',
            'third': 'col-md-4'
        }.get(self.width, 'col-12')
        
        html = f'<div class="{width_class} mb-3 {self.css_class}">'
        
        if self.field_type != FieldType.HIDDEN:
            html += f'<label for="{self.id}" class="form-label">{self.label} {required_star}</label>'
        
        if self.field_type == FieldType.TEXT:
            html += f'''<input type="text" class="form-control" id="{self.id}" name="{self.name}" 
                placeholder="{self.placeholder}" {required_attr}
                {f'minlength="{self.validation.min_length}"' if self.validation.min_length else ''}
                {f'maxlength="{self.validation.max_length}"' if self.validation.max_length else ''}>'''
                
        elif self.field_type == FieldType.EMAIL:
            html += f'''<input type="email" class="form-control" id="{self.id}" name="{self.name}" 
                placeholder="{self.placeholder or 'your@email.com'}" {required_attr}>'''
                
        elif self.field_type == FieldType.PHONE:
            html += f'''<input type="tel" class="form-control" id="{self.id}" name="{self.name}" 
                placeholder="{self.placeholder or '(614) 555-1234'}" {required_attr}
                pattern="[0-9()\\-\\s]+">'''
                
        elif self.field_type == FieldType.SELECT:
            options_html = '<option value="">Select...</option>'
            for opt in self.options:
                selected = 'selected' if opt.get('value') == self.default_value else ''
                options_html += f'<option value="{opt["value"]}" {selected}>{opt["label"]}</option>'
            html += f'<select class="form-select" id="{self.id}" name="{self.name}" {required_attr}>{options_html}</select>'
            
        elif self.field_type == FieldType.MULTI_SELECT:
            options_html = ''
            for opt in self.options:
                options_html += f'<option value="{opt["value"]}">{opt["label"]}</option>'
            html += f'<select class="form-select" id="{self.id}" name="{self.name}" multiple {required_attr}>{options_html}</select>'
            
        elif self.field_type == FieldType.RADIO:
            for i, opt in enumerate(self.options):
                checked = 'checked' if opt.get('value') == self.default_value else ''
                html += f'''<div class="form-check">
                    <input class="form-check-input" type="radio" name="{self.name}" id="{self.id}_{i}" 
                        value="{opt['value']}" {checked} {required_attr if i == 0 else ''}>
                    <label class="form-check-label" for="{self.id}_{i}">{opt['label']}</label>
                </div>'''
                
        elif self.field_type == FieldType.CHECKBOX:
            if self.options:
                for i, opt in enumerate(self.options):
                    html += f'''<div class="form-check">
                        <input class="form-check-input" type="checkbox" name="{self.name}[]" id="{self.id}_{i}" 
                            value="{opt['value']}">
                        <label class="form-check-label" for="{self.id}_{i}">{opt['label']}</label>
                    </div>'''
            else:
                html += f'''<div class="form-check">
                    <input class="form-check-input" type="checkbox" id="{self.id}" name="{self.name}" value="1">
                    <label class="form-check-label" for="{self.id}">{self.placeholder}</label>
                </div>'''
                
        elif self.field_type == FieldType.TEXTAREA:
            html += f'''<textarea class="form-control" id="{self.id}" name="{self.name}" 
                rows="4" placeholder="{self.placeholder}" {required_attr}></textarea>'''
                
        elif self.field_type == FieldType.NUMBER:
            html += f'''<input type="number" class="form-control" id="{self.id}" name="{self.name}" 
                placeholder="{self.placeholder}" {required_attr}
                {f'min="{self.validation.min_value}"' if self.validation.min_value is not None else ''}
                {f'max="{self.validation.max_value}"' if self.validation.max_value is not None else ''}>'''
                
        elif self.field_type == FieldType.DATE:
            html += f'<input type="date" class="form-control" id="{self.id}" name="{self.name}" {required_attr}>'
            
        elif self.field_type == FieldType.RANGE:
            min_val = self.validation.min_value or 0
            max_val = self.validation.max_value or 100
            html += f'''<input type="range" class="form-range" id="{self.id}" name="{self.name}" 
                min="{min_val}" max="{max_val}">
                <div class="d-flex justify-content-between"><small>{min_val}</small><small>{max_val}</small></div>'''
                
        elif self.field_type == FieldType.HIDDEN:
            html += f'<input type="hidden" id="{self.id}" name="{self.name}" value="{self.default_value or ""}">'
            
        elif self.field_type == FieldType.ADDRESS:
            html += f'''<input type="text" class="form-control mb-2" id="{self.id}_street" name="{self.name}_street" 
                placeholder="Street Address" {required_attr}>
                <div class="row">
                    <div class="col-6">
                        <input type="text" class="form-control" id="{self.id}_city" name="{self.name}_city" 
                            placeholder="City" {required_attr}>
                    </div>
                    <div class="col-3">
                        <input type="text" class="form-control" id="{self.id}_state" name="{self.name}_state" 
                            placeholder="State" {required_attr}>
                    </div>
                    <div class="col-3">
                        <input type="text" class="form-control" id="{self.id}_zip" name="{self.name}_zip" 
                            placeholder="ZIP" {required_attr}>
                    </div>
                </div>'''
                
        elif self.field_type == FieldType.PRICE_RANGE:
            html += f'''<div class="row">
                <div class="col-6">
                    <input type="number" class="form-control" id="{self.id}_min" name="{self.name}_min" 
                        placeholder="Min Price" step="10000">
                </div>
                <div class="col-6">
                    <input type="number" class="form-control" id="{self.id}_max" name="{self.name}_max" 
                        placeholder="Max Price" step="10000">
                </div>
            </div>'''
            
        elif self.field_type == FieldType.PROPERTY_TYPE:
            property_types = [
                {'value': 'single_family', 'label': 'Single Family'},
                {'value': 'condo', 'label': 'Condo/Townhouse'},
                {'value': 'multi_family', 'label': 'Multi-Family'},
                {'value': 'land', 'label': 'Land'},
                {'value': 'commercial', 'label': 'Commercial'}
            ]
            for pt in property_types:
                html += f'''<div class="form-check form-check-inline">
                    <input class="form-check-input" type="checkbox" name="{self.name}[]" id="{self.id}_{pt['value']}" 
                        value="{pt['value']}">
                    <label class="form-check-label" for="{self.id}_{pt['value']}">{pt['label']}</label>
                </div>'''
        
        if self.help_text:
            html += f'<div class="form-text">{self.help_text}</div>'
            
        html += '</div>'
        return html


@dataclass
class LeadCaptureForm:
    """A complete lead capture form."""
    id: str
    name: str
    description: str = ""
    fields: List[FormField] = field(default_factory=list)
    submit_button_text: str = "Submit"
    submit_button_class: str = "btn btn-primary btn-lg w-100"
    success_message: str = "Thank you! We'll be in touch shortly."
    redirect_url: str = None
    webhook_url: str = None
    notification_emails: List[str] = field(default_factory=list)
    lead_source: str = "website"
    lead_tags: List[str] = field(default_factory=list)
    assign_to_agent: str = None
    enable_captcha: bool = True
    double_opt_in: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_html(self, action_url: str = "/api/leads/capture") -> str:
        """Generate complete HTML form."""
        fields_html = '<div class="row">'
        sorted_fields = sorted(self.fields, key=lambda f: f.order)
        for f in sorted_fields:
            fields_html += f.to_html()
        fields_html += '</div>'
        
        # Hidden fields for tracking
        hidden_fields = f'''
            <input type="hidden" name="form_id" value="{self.id}">
            <input type="hidden" name="lead_source" value="{self.lead_source}">
            <input type="hidden" name="landing_page_url" id="landing_page_url" value="">
            <input type="hidden" name="referrer" id="form_referrer" value="">
            <input type="hidden" name="utm_source" id="utm_source" value="">
            <input type="hidden" name="utm_medium" id="utm_medium" value="">
            <input type="hidden" name="utm_campaign" id="utm_campaign" value="">
        '''
        
        captcha_html = ''
        if self.enable_captcha:
            captcha_html = '<div class="g-recaptcha mb-3" data-sitekey="YOUR_RECAPTCHA_SITE_KEY"></div>'
        
        return f'''
        <form id="lead-form-{self.id}" action="{action_url}" method="POST" class="lead-capture-form">
            {hidden_fields}
            {fields_html}
            {captcha_html}
            <button type="submit" class="{self.submit_button_class}">{self.submit_button_text}</button>
        </form>
        <div id="form-success-{self.id}" class="alert alert-success d-none">{self.success_message}</div>
        <script>
            document.getElementById('landing_page_url').value = window.location.href;
            document.getElementById('form_referrer').value = document.referrer;
            const urlParams = new URLSearchParams(window.location.search);
            document.getElementById('utm_source').value = urlParams.get('utm_source') || '';
            document.getElementById('utm_medium').value = urlParams.get('utm_medium') || '';
            document.getElementById('utm_campaign').value = urlParams.get('utm_campaign') || '';
        </script>
        '''

    def validate_submission(self, data: Dict) -> tuple:
        """Validate form submission data."""
        errors = []
        cleaned_data = {}
        
        for field in self.fields:
            value = data.get(field.name)
            
            # Required validation
            if field.validation.required and not value:
                errors.append(f"{field.label} is required")
                continue
            
            if value:
                # Email validation
                if field.field_type == FieldType.EMAIL:
                    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
                        errors.append(f"Please enter a valid email address")
                        continue
                
                # Phone validation
                if field.field_type == FieldType.PHONE:
                    cleaned_phone = re.sub(r'[^\d]', '', value)
                    if len(cleaned_phone) < 10:
                        errors.append(f"Please enter a valid phone number")
                        continue
                    value = cleaned_phone
                
                # Length validation
                if field.validation.min_length and len(str(value)) < field.validation.min_length:
                    errors.append(f"{field.label} must be at least {field.validation.min_length} characters")
                    continue
                    
                if field.validation.max_length and len(str(value)) > field.validation.max_length:
                    errors.append(f"{field.label} must be no more than {field.validation.max_length} characters")
                    continue
                
                # Pattern validation
                if field.validation.pattern:
                    if not re.match(field.validation.pattern, str(value)):
                        errors.append(field.validation.pattern_message or f"Invalid format for {field.label}")
                        continue
            
            cleaned_data[field.name] = value
        
        return (len(errors) == 0, errors, cleaned_data)


class FormBuilder:
    """Builder class for creating lead capture forms."""
    
    def __init__(self, storage_path: str = "data/forms"):
        self.storage_path = storage_path
        self.forms: Dict[str, LeadCaptureForm] = {}
        self._load_forms()
    
    def _load_forms(self):
        """Load forms from storage."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        forms_file = f"{self.storage_path}/forms.json"
        if os.path.exists(forms_file):
            with open(forms_file, 'r') as f:
                data = json.load(f)
                for form_data in data:
                    form = self._dict_to_form(form_data)
                    self.forms[form.id] = form
    
    def _save_forms(self):
        """Save forms to storage."""
        import os
        os.makedirs(self.storage_path, exist_ok=True)
        
        forms_data = [self._form_to_dict(form) for form in self.forms.values()]
        with open(f"{self.storage_path}/forms.json", 'w') as f:
            json.dump(forms_data, f, indent=2, default=str)
    
    def _form_to_dict(self, form: LeadCaptureForm) -> Dict:
        """Convert form to dictionary."""
        return {
            'id': form.id,
            'name': form.name,
            'description': form.description,
            'fields': [
                {
                    'id': f.id,
                    'name': f.name,
                    'field_type': f.field_type.value,
                    'label': f.label,
                    'placeholder': f.placeholder,
                    'help_text': f.help_text,
                    'default_value': f.default_value,
                    'options': f.options,
                    'validation': {
                        'required': f.validation.required,
                        'min_length': f.validation.min_length,
                        'max_length': f.validation.max_length,
                        'min_value': f.validation.min_value,
                        'max_value': f.validation.max_value,
                        'pattern': f.validation.pattern,
                        'pattern_message': f.validation.pattern_message
                    },
                    'css_class': f.css_class,
                    'width': f.width,
                    'order': f.order
                }
                for f in form.fields
            ],
            'submit_button_text': form.submit_button_text,
            'submit_button_class': form.submit_button_class,
            'success_message': form.success_message,
            'redirect_url': form.redirect_url,
            'webhook_url': form.webhook_url,
            'notification_emails': form.notification_emails,
            'lead_source': form.lead_source,
            'lead_tags': form.lead_tags,
            'assign_to_agent': form.assign_to_agent,
            'enable_captcha': form.enable_captcha,
            'double_opt_in': form.double_opt_in,
            'created_at': str(form.created_at)
        }
    
    def _dict_to_form(self, data: Dict) -> LeadCaptureForm:
        """Convert dictionary to form."""
        fields = []
        for fd in data.get('fields', []):
            validation = FieldValidation(
                required=fd['validation'].get('required', False),
                min_length=fd['validation'].get('min_length'),
                max_length=fd['validation'].get('max_length'),
                min_value=fd['validation'].get('min_value'),
                max_value=fd['validation'].get('max_value'),
                pattern=fd['validation'].get('pattern'),
                pattern_message=fd['validation'].get('pattern_message')
            )
            fields.append(FormField(
                id=fd['id'],
                name=fd['name'],
                field_type=FieldType(fd['field_type']),
                label=fd['label'],
                placeholder=fd.get('placeholder', ''),
                help_text=fd.get('help_text', ''),
                default_value=fd.get('default_value'),
                options=fd.get('options', []),
                validation=validation,
                css_class=fd.get('css_class', ''),
                width=fd.get('width', 'full'),
                order=fd.get('order', 0)
            ))
        
        return LeadCaptureForm(
            id=data['id'],
            name=data['name'],
            description=data.get('description', ''),
            fields=fields,
            submit_button_text=data.get('submit_button_text', 'Submit'),
            submit_button_class=data.get('submit_button_class', 'btn btn-primary btn-lg w-100'),
            success_message=data.get('success_message', 'Thank you!'),
            redirect_url=data.get('redirect_url'),
            webhook_url=data.get('webhook_url'),
            notification_emails=data.get('notification_emails', []),
            lead_source=data.get('lead_source', 'website'),
            lead_tags=data.get('lead_tags', []),
            assign_to_agent=data.get('assign_to_agent'),
            enable_captcha=data.get('enable_captcha', True),
            double_opt_in=data.get('double_opt_in', False)
        )
    
    def create_form(self, name: str, description: str = "") -> LeadCaptureForm:
        """Create a new form."""
        form = LeadCaptureForm(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description
        )
        self.forms[form.id] = form
        self._save_forms()
        return form
    
    def add_field(self, form_id: str, field: FormField) -> bool:
        """Add a field to a form."""
        if form_id not in self.forms:
            return False
        
        self.forms[form_id].fields.append(field)
        self._save_forms()
        return True
    
    def get_form(self, form_id: str) -> Optional[LeadCaptureForm]:
        """Get a form by ID."""
        return self.forms.get(form_id)
    
    def list_forms(self) -> List[LeadCaptureForm]:
        """List all forms."""
        return list(self.forms.values())
    
    def delete_form(self, form_id: str) -> bool:
        """Delete a form."""
        if form_id in self.forms:
            del self.forms[form_id]
            self._save_forms()
            return True
        return False
    
    def clone_form(self, form_id: str, new_name: str) -> Optional[LeadCaptureForm]:
        """Clone an existing form."""
        if form_id not in self.forms:
            return None
        
        original = self.forms[form_id]
        new_form = LeadCaptureForm(
            id=str(uuid.uuid4())[:8],
            name=new_name,
            description=original.description,
            fields=[FormField(
                id=str(uuid.uuid4())[:8],
                name=f.name,
                field_type=f.field_type,
                label=f.label,
                placeholder=f.placeholder,
                help_text=f.help_text,
                default_value=f.default_value,
                options=f.options.copy(),
                validation=FieldValidation(
                    required=f.validation.required,
                    min_length=f.validation.min_length,
                    max_length=f.validation.max_length,
                    min_value=f.validation.min_value,
                    max_value=f.validation.max_value,
                    pattern=f.validation.pattern,
                    pattern_message=f.validation.pattern_message
                ),
                css_class=f.css_class,
                width=f.width,
                order=f.order
            ) for f in original.fields],
            submit_button_text=original.submit_button_text,
            submit_button_class=original.submit_button_class,
            success_message=original.success_message,
            enable_captcha=original.enable_captcha
        )
        
        self.forms[new_form.id] = new_form
        self._save_forms()
        return new_form
    
    # Preset form templates
    def create_buyer_inquiry_form(self) -> LeadCaptureForm:
        """Create a standard buyer inquiry form."""
        form = self.create_form("Buyer Inquiry", "Form for potential home buyers")
        
        fields = [
            FormField(
                id=str(uuid.uuid4())[:8], name="first_name", field_type=FieldType.TEXT,
                label="First Name", placeholder="Your first name",
                validation=FieldValidation(required=True, max_length=50),
                width="half", order=1
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="last_name", field_type=FieldType.TEXT,
                label="Last Name", placeholder="Your last name",
                validation=FieldValidation(required=True, max_length=50),
                width="half", order=2
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="email", field_type=FieldType.EMAIL,
                label="Email Address", placeholder="your@email.com",
                validation=FieldValidation(required=True),
                width="half", order=3
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="phone", field_type=FieldType.PHONE,
                label="Phone Number", placeholder="(614) 555-1234",
                validation=FieldValidation(required=True),
                width="half", order=4
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="price_range", field_type=FieldType.SELECT,
                label="Price Range", options=[
                    {'value': '0-200000', 'label': 'Under $200,000'},
                    {'value': '200000-300000', 'label': '$200,000 - $300,000'},
                    {'value': '300000-400000', 'label': '$300,000 - $400,000'},
                    {'value': '400000-500000', 'label': '$400,000 - $500,000'},
                    {'value': '500000-750000', 'label': '$500,000 - $750,000'},
                    {'value': '750000+', 'label': '$750,000+'}
                ],
                validation=FieldValidation(required=True),
                width="half", order=5
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="timeframe", field_type=FieldType.SELECT,
                label="Buying Timeframe", options=[
                    {'value': 'asap', 'label': 'As soon as possible'},
                    {'value': '1-3months', 'label': '1-3 months'},
                    {'value': '3-6months', 'label': '3-6 months'},
                    {'value': '6-12months', 'label': '6-12 months'},
                    {'value': 'justlooking', 'label': 'Just browsing'}
                ],
                validation=FieldValidation(required=True),
                width="half", order=6
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="areas", field_type=FieldType.TEXT,
                label="Preferred Areas/Neighborhoods",
                placeholder="e.g., Dublin, Worthington, German Village",
                width="full", order=7
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="bedrooms", field_type=FieldType.SELECT,
                label="Bedrooms", options=[
                    {'value': '1', 'label': '1+'},
                    {'value': '2', 'label': '2+'},
                    {'value': '3', 'label': '3+'},
                    {'value': '4', 'label': '4+'},
                    {'value': '5', 'label': '5+'}
                ],
                width="half", order=8
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="bathrooms", field_type=FieldType.SELECT,
                label="Bathrooms", options=[
                    {'value': '1', 'label': '1+'},
                    {'value': '2', 'label': '2+'},
                    {'value': '3', 'label': '3+'},
                    {'value': '4', 'label': '4+'}
                ],
                width="half", order=9
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="preapproved", field_type=FieldType.RADIO,
                label="Are you pre-approved for a mortgage?", options=[
                    {'value': 'yes', 'label': 'Yes'},
                    {'value': 'no', 'label': 'No'},
                    {'value': 'cash', 'label': 'Cash buyer'}
                ],
                width="full", order=10
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="message", field_type=FieldType.TEXTAREA,
                label="Additional Information",
                placeholder="Tell us more about what you're looking for...",
                width="full", order=11
            )
        ]
        
        for field in fields:
            self.add_field(form.id, field)
        
        form.submit_button_text = "Start My Home Search"
        form.lead_source = "buyer_inquiry"
        form.lead_tags = ["buyer", "inquiry"]
        self._save_forms()
        
        return form
    
    def create_seller_valuation_form(self) -> LeadCaptureForm:
        """Create a home valuation request form."""
        form = self.create_form("Home Valuation Request", "Get a free home value estimate")
        
        fields = [
            FormField(
                id=str(uuid.uuid4())[:8], name="first_name", field_type=FieldType.TEXT,
                label="First Name", validation=FieldValidation(required=True),
                width="half", order=1
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="last_name", field_type=FieldType.TEXT,
                label="Last Name", validation=FieldValidation(required=True),
                width="half", order=2
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="email", field_type=FieldType.EMAIL,
                label="Email", validation=FieldValidation(required=True),
                width="half", order=3
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="phone", field_type=FieldType.PHONE,
                label="Phone", validation=FieldValidation(required=True),
                width="half", order=4
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="address", field_type=FieldType.ADDRESS,
                label="Property Address", validation=FieldValidation(required=True),
                width="full", order=5
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="property_type", field_type=FieldType.SELECT,
                label="Property Type", options=[
                    {'value': 'single_family', 'label': 'Single Family Home'},
                    {'value': 'condo', 'label': 'Condo/Townhouse'},
                    {'value': 'multi_family', 'label': 'Multi-Family'},
                    {'value': 'land', 'label': 'Land'}
                ],
                width="half", order=6
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="bedrooms", field_type=FieldType.NUMBER,
                label="Bedrooms", validation=FieldValidation(min_value=0, max_value=20),
                width="half", order=7
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="bathrooms", field_type=FieldType.NUMBER,
                label="Bathrooms", validation=FieldValidation(min_value=0, max_value=20),
                width="half", order=8
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="sqft", field_type=FieldType.NUMBER,
                label="Approx. Square Feet",
                width="half", order=9
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="timeframe", field_type=FieldType.SELECT,
                label="When are you thinking of selling?", options=[
                    {'value': 'asap', 'label': 'Immediately'},
                    {'value': '1-3months', 'label': '1-3 months'},
                    {'value': '3-6months', 'label': '3-6 months'},
                    {'value': '6-12months', 'label': '6-12 months'},
                    {'value': 'justcurious', 'label': 'Just curious about value'}
                ],
                width="full", order=10
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="reason", field_type=FieldType.SELECT,
                label="Reason for selling", options=[
                    {'value': 'relocating', 'label': 'Relocating'},
                    {'value': 'upgrading', 'label': 'Upgrading to larger home'},
                    {'value': 'downsizing', 'label': 'Downsizing'},
                    {'value': 'investment', 'label': 'Investment property'},
                    {'value': 'other', 'label': 'Other'}
                ],
                width="full", order=11
            )
        ]
        
        for field in fields:
            self.add_field(form.id, field)
        
        form.submit_button_text = "Get My Free Home Value"
        form.lead_source = "home_valuation"
        form.lead_tags = ["seller", "valuation"]
        self._save_forms()
        
        return form
    
    def create_contact_form(self) -> LeadCaptureForm:
        """Create a simple contact form."""
        form = self.create_form("Contact Form", "General contact form")
        
        fields = [
            FormField(
                id=str(uuid.uuid4())[:8], name="name", field_type=FieldType.TEXT,
                label="Full Name", validation=FieldValidation(required=True),
                width="full", order=1
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="email", field_type=FieldType.EMAIL,
                label="Email", validation=FieldValidation(required=True),
                width="half", order=2
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="phone", field_type=FieldType.PHONE,
                label="Phone", width="half", order=3
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="subject", field_type=FieldType.SELECT,
                label="What can we help you with?", options=[
                    {'value': 'buying', 'label': 'Buying a home'},
                    {'value': 'selling', 'label': 'Selling my home'},
                    {'value': 'renting', 'label': 'Renting'},
                    {'value': 'investing', 'label': 'Real estate investing'},
                    {'value': 'other', 'label': 'Other'}
                ],
                width="full", order=4
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="message", field_type=FieldType.TEXTAREA,
                label="Message", validation=FieldValidation(required=True),
                placeholder="How can we help you?",
                width="full", order=5
            )
        ]
        
        for field in fields:
            self.add_field(form.id, field)
        
        form.submit_button_text = "Send Message"
        form.lead_source = "contact_form"
        self._save_forms()
        
        return form
    
    def create_open_house_registration(self) -> LeadCaptureForm:
        """Create an open house registration form."""
        form = self.create_form("Open House Registration", "Register for an open house")
        
        fields = [
            FormField(
                id=str(uuid.uuid4())[:8], name="first_name", field_type=FieldType.TEXT,
                label="First Name", validation=FieldValidation(required=True),
                width="half", order=1
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="last_name", field_type=FieldType.TEXT,
                label="Last Name", validation=FieldValidation(required=True),
                width="half", order=2
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="email", field_type=FieldType.EMAIL,
                label="Email", validation=FieldValidation(required=True),
                width="half", order=3
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="phone", field_type=FieldType.PHONE,
                label="Phone", validation=FieldValidation(required=True),
                width="half", order=4
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="working_with_agent", field_type=FieldType.RADIO,
                label="Are you currently working with a real estate agent?", options=[
                    {'value': 'yes', 'label': 'Yes'},
                    {'value': 'no', 'label': 'No'}
                ],
                width="full", order=5
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="preapproved", field_type=FieldType.RADIO,
                label="Are you pre-approved for a mortgage?", options=[
                    {'value': 'yes', 'label': 'Yes'},
                    {'value': 'no', 'label': 'No'},
                    {'value': 'cash', 'label': 'Cash buyer'}
                ],
                width="full", order=6
            ),
            FormField(
                id=str(uuid.uuid4())[:8], name="property_id", field_type=FieldType.HIDDEN,
                label="Property ID", width="full", order=7
            )
        ]
        
        for field in fields:
            self.add_field(form.id, field)
        
        form.submit_button_text = "Register for Open House"
        form.lead_source = "open_house"
        form.lead_tags = ["open_house", "buyer"]
        self._save_forms()
        
        return form
