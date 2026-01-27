"""Email integration for lead notifications and outreach."""

import json
import logging
import smtplib
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SMTPConfig:
    """SMTP email configuration."""

    host: str
    port: int
    username: str
    password: str
    from_email: str
    from_name: str = "TD Lead Engine"
    use_tls: bool = True


@dataclass
class SendGridConfig:
    """SendGrid email configuration."""

    api_key: str
    from_email: str
    from_name: str = "TD Lead Engine"


@dataclass
class EmailConfig:
    """Combined email configuration."""

    provider: str = "smtp"  # "smtp" or "sendgrid"
    smtp: Optional[SMTPConfig] = None
    sendgrid: Optional[SendGridConfig] = None
    enabled: bool = True

    # Notification recipients
    notify_emails: List[str] = field(default_factory=list)

    # Email templates
    templates: Dict[str, Dict[str, str]] = None

    def __post_init__(self):
        if self.templates is None:
            self.templates = {
                "hot_lead_alert": {
                    "subject": "🔥 Hot Lead Alert: {name}",
                    "body": """
<h2>Hot Lead Detected!</h2>

<table style="border-collapse: collapse; width: 100%; max-width: 500px;">
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Name</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{name}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Score</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{score} ({tier})</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Email</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{email}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Phone</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{phone}</td>
    </tr>
    <tr>
        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Source</strong></td>
        <td style="padding: 8px; border: 1px solid #ddd;">{source}</td>
    </tr>
</table>

<p><strong>Notes:</strong><br>{notes}</p>

<p style="color: #666; font-size: 12px;">
    Lead ID: {lead_id}<br>
    Detected: {timestamp}
</p>
"""
                },
                "daily_digest": {
                    "subject": "📊 Daily Lead Report - {date}",
                    "body": """
<h2>Daily Lead Summary</h2>

<h3>Overview</h3>
<ul>
    <li><strong>Total Leads:</strong> {total}</li>
    <li><strong>Hot:</strong> {hot}</li>
    <li><strong>Warm:</strong> {warm}</li>
    <li><strong>Lukewarm:</strong> {lukewarm}</li>
    <li><strong>Cold:</strong> {cold}</li>
</ul>

<h3>Top Hot Leads</h3>
{hot_leads_html}

<p style="color: #666; font-size: 12px;">
    Generated: {timestamp}
</p>
"""
                },
            }


class EmailIntegration:
    """Send email notifications via SMTP or SendGrid."""

    def __init__(self, config: EmailConfig):
        """Initialize email integration."""
        self.config = config

    def _send_smtp(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via SMTP."""
        if not self.config.smtp:
            logger.error("SMTP not configured")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.config.smtp.from_name} <{self.config.smtp.from_email}>"
        msg["To"] = to

        msg.attach(MIMEText(html_body, "html"))

        try:
            if self.config.smtp.use_tls:
                server = smtplib.SMTP(self.config.smtp.host, self.config.smtp.port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.config.smtp.host, self.config.smtp.port)

            server.login(self.config.smtp.username, self.config.smtp.password)
            server.sendmail(self.config.smtp.from_email, to, msg.as_string())
            server.quit()

            logger.info(f"Email sent to {to}")
            return True

        except Exception as e:
            logger.error(f"SMTP email failed: {e}")
            return False

    def _send_sendgrid(self, to: str, subject: str, html_body: str) -> bool:
        """Send email via SendGrid API."""
        if not self.config.sendgrid:
            logger.error("SendGrid not configured")
            return False

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {
                "email": self.config.sendgrid.from_email,
                "name": self.config.sendgrid.from_name,
            },
            "subject": subject,
            "content": [{"type": "text/html", "value": html_body}],
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=data,
                headers={
                    "Authorization": f"Bearer {self.config.sendgrid.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                logger.info(f"SendGrid email sent to {to}")
                return response.status in [200, 202]

        except Exception as e:
            logger.error(f"SendGrid email failed: {e}")
            return False

    def send_email(self, to: str, subject: str, html_body: str) -> bool:
        """Send email using configured provider."""
        if not self.config.enabled:
            return False

        if self.config.provider == "sendgrid":
            return self._send_sendgrid(to, subject, html_body)
        else:
            return self._send_smtp(to, subject, html_body)

    def send_hot_lead_alert(self, lead) -> List[Dict[str, Any]]:
        """Send hot lead alert to all notify emails."""
        if not self.config.enabled:
            return []

        template = self.config.templates.get("hot_lead_alert", {})
        subject = template.get("subject", "Hot Lead: {name}").format(name=lead.display_name)
        body = template.get("body", "").format(
            name=lead.display_name,
            score=lead.score,
            tier=lead.tier.upper(),
            email=lead.email or "N/A",
            phone=lead.phone or "N/A",
            source=lead.source,
            notes=lead.notes or "No notes",
            lead_id=lead.id,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        results = []
        for email in self.config.notify_emails:
            success = self.send_email(email, subject, body)
            results.append({"email": email, "success": success})

        return results

    def send_daily_digest(
        self,
        stats: Dict[str, Any],
        hot_leads: List
    ) -> List[Dict[str, Any]]:
        """Send daily digest to all notify emails."""
        if not self.config.enabled:
            return []

        tier_stats = stats.get("by_tier", {})

        # Build hot leads HTML
        hot_leads_html = "<ul>"
        for lead in hot_leads[:10]:
            hot_leads_html += f"<li><strong>{lead.display_name}</strong> - Score: {lead.score}, Source: {lead.source}</li>"
        hot_leads_html += "</ul>" if hot_leads else "<p>No hot leads today.</p>"

        template = self.config.templates.get("daily_digest", {})
        subject = template.get("subject", "Daily Report - {date}").format(
            date=datetime.now().strftime("%B %d, %Y")
        )
        body = template.get("body", "").format(
            date=datetime.now().strftime("%B %d, %Y"),
            total=stats.get("total_leads", 0),
            hot=tier_stats.get("hot", 0),
            warm=tier_stats.get("warm", 0),
            lukewarm=tier_stats.get("lukewarm", 0),
            cold=tier_stats.get("cold", 0),
            hot_leads_html=hot_leads_html,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        results = []
        for email in self.config.notify_emails:
            success = self.send_email(email, subject, body)
            results.append({"email": email, "success": success})

        return results


def setup_gmail_smtp(
    gmail_address: str,
    app_password: str,
    notify_emails: List[str]
) -> EmailIntegration:
    """Quick setup for Gmail SMTP."""
    config = EmailConfig(
        provider="smtp",
        smtp=SMTPConfig(
            host="smtp.gmail.com",
            port=587,
            username=gmail_address,
            password=app_password,
            from_email=gmail_address,
            from_name="TD Lead Engine",
        ),
        notify_emails=notify_emails,
    )
    return EmailIntegration(config)


def setup_sendgrid(
    api_key: str,
    from_email: str,
    notify_emails: List[str]
) -> EmailIntegration:
    """Quick setup for SendGrid."""
    config = EmailConfig(
        provider="sendgrid",
        sendgrid=SendGridConfig(
            api_key=api_key,
            from_email=from_email,
        ),
        notify_emails=notify_emails,
    )
    return EmailIntegration(config)


def print_email_setup_guide():
    """Print email setup instructions."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              EMAIL INTEGRATION SETUP GUIDE                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Option 1: Gmail SMTP (Free, Easy)                           ║
║  ─────────────────────────────────                           ║
║  1. Enable 2-Factor Authentication on Google Account         ║
║  2. Generate App Password:                                   ║
║     - Go to myaccount.google.com/apppasswords               ║
║     - Create app password for "Mail"                         ║
║  3. Configure TD Lead Engine:                                ║
║     socialops config email --provider gmail                  ║
║                                                               ║
║  Option 2: SendGrid (Scalable, Professional)                 ║
║  ─────────────────────────────────                           ║
║  1. Sign up at sendgrid.com (free tier: 100 emails/day)     ║
║  2. Create API key in Settings > API Keys                    ║
║  3. Verify sender email address                              ║
║  4. Configure TD Lead Engine:                                ║
║     socialops config email --provider sendgrid               ║
║                                                               ║
║  Option 3: Custom SMTP                                       ║
║  ─────────────────────────────────                           ║
║  Configure any SMTP server:                                  ║
║  socialops config email --provider smtp                      ║
║                                                               ║
║  Pricing:                                                    ║
║  ─────────────────────────────                               ║
║  • Gmail: Free (500 emails/day limit)                        ║
║  • SendGrid Free: 100 emails/day                             ║
║  • SendGrid Essentials: $19.95/mo for 50K emails             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
""")
