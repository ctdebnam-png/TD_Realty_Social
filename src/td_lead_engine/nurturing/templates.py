"""Email and SMS templates for lead nurturing."""

import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path
from string import Template


@dataclass
class EmailTemplate:
    """An email template for nurturing."""

    name: str
    subject: str
    body_html: str
    body_text: str
    category: str  # "buyer", "seller", "nurture", "follow_up"
    tags: List[str] = field(default_factory=list)

    def render(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Render the template with context variables."""
        # Use safe substitution to handle missing variables
        subject = Template(self.subject).safe_substitute(context)
        body_html = Template(self.body_html).safe_substitute(context)
        body_text = Template(self.body_text).safe_substitute(context)

        return {
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text
        }


@dataclass
class SMSTemplate:
    """An SMS template for nurturing."""

    name: str
    body: str
    category: str
    max_length: int = 160

    def render(self, context: Dict[str, Any]) -> str:
        """Render the template with context variables."""
        rendered = Template(self.body).safe_substitute(context)

        # Truncate if too long
        if len(rendered) > self.max_length:
            rendered = rendered[:self.max_length - 3] + "..."

        return rendered


class TemplateEngine:
    """Manage and render nurturing templates."""

    def __init__(self):
        """Initialize the template engine with built-in templates."""
        self.email_templates: Dict[str, EmailTemplate] = {}
        self.sms_templates: Dict[str, SMSTemplate] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self):
        """Load built-in email and SMS templates."""
        # =====================
        # BUYER EMAIL TEMPLATES
        # =====================

        self.email_templates["buyer_welcome"] = EmailTemplate(
            name="buyer_welcome",
            subject="Welcome! Let's Find Your Perfect Columbus Home",
            category="buyer",
            tags=["welcome", "first_contact"],
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1e3a5f; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9fafb; }
        .cta { background: #22c55e; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
        .footer { padding: 20px; font-size: 12px; color: #666; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to TD Realty!</h1>
        </div>
        <div class="content">
            <p>Hi $first_name,</p>

            <p>Thank you for reaching out about finding your next home in Columbus! I'm excited to help you on this journey.</p>

            <p>Based on what you shared, it sounds like you're looking for:</p>
            <ul>
                <li>Location: $target_area</li>
                <li>Price Range: $price_range</li>
                <li>Timeline: $timeline</li>
            </ul>

            <p>I specialize in the Columbus market and would love to be your guide. Here's what I can help with:</p>
            <ul>
                <li>Personalized property recommendations</li>
                <li>Market insights for your target neighborhoods</li>
                <li>Expert negotiation to get you the best deal</li>
                <li>Smooth transaction coordination</li>
            </ul>

            <p>Would you be open to a quick 15-minute call this week to discuss your search?</p>

            <a href="$calendar_link" class="cta">Schedule a Call</a>

            <p>Looking forward to connecting!</p>

            <p>Best,<br>
            $agent_name<br>
            $agent_phone<br>
            TD Realty Ohio</p>
        </div>
        <div class="footer">
            <p>TD Realty Ohio | Columbus, OH</p>
            <p><a href="$unsubscribe_link">Unsubscribe</a></p>
        </div>
    </div>
</body>
</html>
""",
            body_text="""
Hi $first_name,

Thank you for reaching out about finding your next home in Columbus! I'm excited to help you on this journey.

Based on what you shared, it sounds like you're looking for:
- Location: $target_area
- Price Range: $price_range
- Timeline: $timeline

I specialize in the Columbus market and would love to be your guide. Here's what I can help with:
- Personalized property recommendations
- Market insights for your target neighborhoods
- Expert negotiation to get you the best deal
- Smooth transaction coordination

Would you be open to a quick 15-minute call this week to discuss your search?

Schedule a call: $calendar_link

Looking forward to connecting!

Best,
$agent_name
$agent_phone
TD Realty Ohio
"""
        )

        self.email_templates["buyer_listings"] = EmailTemplate(
            name="buyer_listings",
            subject="New Listings in $target_area You'll Love",
            category="buyer",
            tags=["listings", "value_add"],
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .listing { border: 1px solid #e5e7eb; border-radius: 8px; margin: 15px 0; overflow: hidden; }
        .listing-img { width: 100%; height: 200px; background: #ddd; }
        .listing-info { padding: 15px; }
        .listing-price { font-size: 24px; font-weight: bold; color: #1e3a5f; }
        .cta { background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <p>Hi $first_name,</p>

        <p>I found some new listings in $target_area that match what you're looking for:</p>

        $listings_html

        <p>Want to schedule showings for any of these? Just reply to this email or give me a call!</p>

        <a href="$search_link" class="cta">See All Matches</a>

        <p>Best,<br>$agent_name</p>
    </div>
</body>
</html>
""",
            body_text="""
Hi $first_name,

I found some new listings in $target_area that match what you're looking for:

$listings_text

Want to schedule showings for any of these? Just reply to this email or give me a call!

See all matches: $search_link

Best,
$agent_name
$agent_phone
"""
        )

        self.email_templates["buyer_market_update"] = EmailTemplate(
            name="buyer_market_update",
            subject="Columbus Market Update: What Buyers Need to Know",
            category="buyer",
            tags=["market_update", "value_add"],
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .stat-box { background: #f0f9ff; padding: 15px; border-radius: 8px; margin: 10px 0; }
        .stat-number { font-size: 28px; font-weight: bold; color: #1e3a5f; }
    </style>
</head>
<body>
    <div class="container">
        <p>Hi $first_name,</p>

        <p>Here's what's happening in the Columbus real estate market this month:</p>

        <div class="stat-box">
            <div class="stat-number">$median_price</div>
            <div>Median Home Price (${price_change}% from last month)</div>
        </div>

        <div class="stat-box">
            <div class="stat-number">$days_on_market days</div>
            <div>Average Days on Market</div>
        </div>

        <div class="stat-box">
            <div class="stat-number">$inventory_level</div>
            <div>Current Inventory Level</div>
        </div>

        <h3>What This Means for You:</h3>
        <p>$market_analysis</p>

        <p>Questions about timing your purchase? I'm always happy to chat strategy.</p>

        <p>Best,<br>$agent_name</p>
    </div>
</body>
</html>
""",
            body_text="""
Hi $first_name,

Here's what's happening in the Columbus real estate market this month:

- Median Home Price: $median_price (${price_change}% from last month)
- Average Days on Market: $days_on_market days
- Current Inventory: $inventory_level

What This Means for You:
$market_analysis

Questions about timing your purchase? I'm always happy to chat strategy.

Best,
$agent_name
$agent_phone
"""
        )

        # ======================
        # SELLER EMAIL TEMPLATES
        # ======================

        self.email_templates["seller_cma"] = EmailTemplate(
            name="seller_cma",
            subject="Your Free Home Value Report for $property_address",
            category="seller",
            tags=["cma", "first_contact"],
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .value-box { background: #22c55e; color: white; padding: 30px; text-align: center; border-radius: 12px; margin: 20px 0; }
        .value-number { font-size: 36px; font-weight: bold; }
        .cta { background: #1e3a5f; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <p>Hi $first_name,</p>

        <p>Thank you for requesting a home value report for your property at $property_address. Based on recent sales and current market conditions, here's what I found:</p>

        <div class="value-box">
            <div>Estimated Market Value</div>
            <div class="value-number">$estimated_value</div>
            <div>Range: $value_range</div>
        </div>

        <h3>How I Calculated This:</h3>
        <ul>
            <li>Analyzed $comp_count comparable sales in your area</li>
            <li>Considered current market conditions</li>
            <li>Factored in your property's unique features</li>
        </ul>

        <p>This is an initial estimate. For a more precise valuation, I'd love to see your home in person and discuss any updates or improvements you've made.</p>

        <a href="$calendar_link" class="cta">Schedule a Free Consultation</a>

        <p>No pressure, no obligation - just helpful information to guide your decision.</p>

        <p>Best,<br>$agent_name<br>$agent_phone</p>
    </div>
</body>
</html>
""",
            body_text="""
Hi $first_name,

Thank you for requesting a home value report for your property at $property_address.

ESTIMATED MARKET VALUE: $estimated_value
Range: $value_range

How I Calculated This:
- Analyzed $comp_count comparable sales in your area
- Considered current market conditions
- Factored in your property's unique features

This is an initial estimate. For a more precise valuation, I'd love to see your home in person and discuss any updates or improvements you've made.

Schedule a free consultation: $calendar_link

No pressure, no obligation - just helpful information to guide your decision.

Best,
$agent_name
$agent_phone
"""
        )

        self.email_templates["seller_tips"] = EmailTemplate(
            name="seller_tips",
            subject="5 Things to Do Before Listing Your Columbus Home",
            category="seller",
            tags=["value_add", "nurture"],
            body_html="""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .tip { background: #f9fafb; padding: 15px; margin: 10px 0; border-left: 4px solid #22c55e; }
        .tip-number { font-weight: bold; color: #22c55e; }
    </style>
</head>
<body>
    <div class="container">
        <p>Hi $first_name,</p>

        <p>Thinking about selling your home? Here are 5 things that can make a big difference in your sale price:</p>

        <div class="tip">
            <span class="tip-number">1.</span> <strong>Declutter ruthlessly</strong> - Buyers need to envision themselves living there. Less is more.
        </div>

        <div class="tip">
            <span class="tip-number">2.</span> <strong>Fix the small stuff</strong> - Leaky faucets, squeaky doors, and scuffed walls signal deferred maintenance.
        </div>

        <div class="tip">
            <span class="tip-number">3.</span> <strong>Boost curb appeal</strong> - First impressions matter. Fresh mulch and a clean entry go a long way.
        </div>

        <div class="tip">
            <span class="tip-number">4.</span> <strong>Deep clean everything</strong> - Especially kitchens, bathrooms, and windows.
        </div>

        <div class="tip">
            <span class="tip-number">5.</span> <strong>Get a pre-listing inspection</strong> - Know what buyers will find before they do.
        </div>

        <p>Want a personalized checklist for your home? I'm happy to do a quick walkthrough and give you my recommendations.</p>

        <p>Best,<br>$agent_name</p>
    </div>
</body>
</html>
""",
            body_text="""
Hi $first_name,

Thinking about selling your home? Here are 5 things that can make a big difference in your sale price:

1. DECLUTTER RUTHLESSLY - Buyers need to envision themselves living there. Less is more.

2. FIX THE SMALL STUFF - Leaky faucets, squeaky doors, and scuffed walls signal deferred maintenance.

3. BOOST CURB APPEAL - First impressions matter. Fresh mulch and a clean entry go a long way.

4. DEEP CLEAN EVERYTHING - Especially kitchens, bathrooms, and windows.

5. GET A PRE-LISTING INSPECTION - Know what buyers will find before they do.

Want a personalized checklist for your home? I'm happy to do a quick walkthrough and give you my recommendations.

Best,
$agent_name
$agent_phone
"""
        )

        # =======================
        # NURTURE EMAIL TEMPLATES
        # =======================

        self.email_templates["check_in"] = EmailTemplate(
            name="check_in",
            subject="Quick check-in: How's your home search going?",
            category="nurture",
            tags=["follow_up", "check_in"],
            body_html="""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <p>Hi $first_name,</p>

    <p>Just wanted to check in and see how things are going with your real estate plans.</p>

    <p>Has anything changed since we last spoke? Whether you're ready to move forward, have questions, or just want to chat about the market, I'm here to help.</p>

    <p>No pressure at all - just want you to know I'm thinking of you!</p>

    <p>Best,<br>$agent_name<br>$agent_phone</p>
</body>
</html>
""",
            body_text="""
Hi $first_name,

Just wanted to check in and see how things are going with your real estate plans.

Has anything changed since we last spoke? Whether you're ready to move forward, have questions, or just want to chat about the market, I'm here to help.

No pressure at all - just want you to know I'm thinking of you!

Best,
$agent_name
$agent_phone
"""
        )

        # ================
        # SMS TEMPLATES
        # ================

        self.sms_templates["initial_followup"] = SMSTemplate(
            name="initial_followup",
            body="Hi $first_name! This is $agent_name with TD Realty. Got your inquiry - would love to help! When's a good time to chat?",
            category="follow_up"
        )

        self.sms_templates["showing_reminder"] = SMSTemplate(
            name="showing_reminder",
            body="Hi $first_name! Reminder: We're seeing $property_address tomorrow at $showing_time. Let me know if anything changes!",
            category="showing"
        )

        self.sms_templates["hot_lead"] = SMSTemplate(
            name="hot_lead",
            body="Hi $first_name! Just saw a great listing hit the market in $target_area. Want me to send details? -$agent_name",
            category="buyer"
        )

        self.sms_templates["check_in"] = SMSTemplate(
            name="check_in",
            body="Hi $first_name! Quick check-in - how's your home search going? Here if you need anything! -$agent_name",
            category="nurture"
        )

        self.sms_templates["listing_update"] = SMSTemplate(
            name="listing_update",
            body="Hi $first_name! Update on your listing: $update_message. Call me if you have questions! -$agent_name",
            category="seller"
        )

        self.sms_templates["price_drop"] = SMSTemplate(
            name="price_drop",
            body="$first_name - a home you liked just dropped to $new_price! Want to schedule a showing? -$agent_name",
            category="buyer"
        )

        self.sms_templates["thank_you"] = SMSTemplate(
            name="thank_you",
            body="$first_name - thanks for meeting today! Let me know if you have any questions. Talk soon! -$agent_name",
            category="follow_up"
        )

    def get_email_template(self, name: str) -> Optional[EmailTemplate]:
        """Get an email template by name."""
        return self.email_templates.get(name)

    def get_sms_template(self, name: str) -> Optional[SMSTemplate]:
        """Get an SMS template by name."""
        return self.sms_templates.get(name)

    def get_templates_by_category(self, category: str) -> Dict[str, Any]:
        """Get all templates in a category."""
        return {
            "email": [t for t in self.email_templates.values() if t.category == category],
            "sms": [t for t in self.sms_templates.values() if t.category == category]
        }

    def list_templates(self) -> Dict[str, List[str]]:
        """List all available template names."""
        return {
            "email": list(self.email_templates.keys()),
            "sms": list(self.sms_templates.keys())
        }

    def add_custom_template(
        self,
        template_type: str,
        name: str,
        **kwargs
    ) -> bool:
        """Add a custom template."""
        if template_type == "email":
            self.email_templates[name] = EmailTemplate(name=name, **kwargs)
            return True
        elif template_type == "sms":
            self.sms_templates[name] = SMSTemplate(name=name, **kwargs)
            return True
        return False
