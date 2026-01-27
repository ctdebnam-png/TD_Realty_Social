"""Email automation and drip campaign module."""

from .automation import EmailAutomation, EmailTrigger, TriggerType
from .campaigns import DripCampaign, CampaignEmail, CampaignStatus
from .templates import EmailTemplate, EmailTemplateManager

__all__ = [
    'EmailAutomation',
    'EmailTrigger',
    'TriggerType',
    'DripCampaign',
    'CampaignEmail',
    'CampaignStatus',
    'EmailTemplate',
    'EmailTemplateManager',
]
