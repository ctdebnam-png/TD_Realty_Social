"""Drip campaign module for automated email/SMS sequences."""

from .campaigns import CampaignManager, DripCampaign, CampaignStatus
from .templates import EmailTemplate, SMSTemplate, TemplateLibrary
from .scheduler import CampaignScheduler, ScheduledMessage
from .analytics import CampaignAnalytics

__all__ = [
    'CampaignManager',
    'DripCampaign',
    'CampaignStatus',
    'EmailTemplate',
    'SMSTemplate',
    'TemplateLibrary',
    'CampaignScheduler',
    'ScheduledMessage',
    'CampaignAnalytics'
]
