"""Lead attribution and marketing analytics."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os


class AttributionModel(Enum):
    """Attribution models."""
    FIRST_TOUCH = "first_touch"
    LAST_TOUCH = "last_touch"
    LINEAR = "linear"
    TIME_DECAY = "time_decay"
    POSITION_BASED = "position_based"  # 40% first, 40% last, 20% middle


@dataclass
class TouchPoint:
    """A marketing touch point."""
    timestamp: datetime
    channel: str
    source: str
    medium: str
    campaign: str = ""
    content: str = ""
    landing_page: str = ""
    referrer: str = ""


@dataclass
class LeadAttribution:
    """Attribution data for a lead."""
    lead_id: str
    touch_points: List[TouchPoint] = field(default_factory=list)
    conversion_date: datetime = None
    conversion_value: float = 0
    
    # First/last touch
    first_touch_channel: str = ""
    first_touch_source: str = ""
    first_touch_campaign: str = ""
    last_touch_channel: str = ""
    last_touch_source: str = ""
    last_touch_campaign: str = ""
    
    # Attribution credits
    channel_credits: Dict[str, float] = field(default_factory=dict)
    source_credits: Dict[str, float] = field(default_factory=dict)
    campaign_credits: Dict[str, float] = field(default_factory=dict)


class AttributionManager:
    """Manage lead attribution and marketing analytics."""
    
    def __init__(self, storage_path: str = "data/attribution"):
        self.storage_path = storage_path
        self.attributions: Dict[str, LeadAttribution] = {}
        self.default_model = AttributionModel.POSITION_BASED
        
        self._load_data()
    
    def _load_data(self):
        """Load attribution data."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        file_path = f"{self.storage_path}/attributions.json"
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                for attr_data in data:
                    touch_points = [
                        TouchPoint(
                            timestamp=datetime.fromisoformat(tp['timestamp']),
                            channel=tp['channel'],
                            source=tp['source'],
                            medium=tp['medium'],
                            campaign=tp.get('campaign', ''),
                            content=tp.get('content', ''),
                            landing_page=tp.get('landing_page', ''),
                            referrer=tp.get('referrer', '')
                        )
                        for tp in attr_data.get('touch_points', [])
                    ]
                    
                    attribution = LeadAttribution(
                        lead_id=attr_data['lead_id'],
                        touch_points=touch_points,
                        conversion_date=datetime.fromisoformat(attr_data['conversion_date']) if attr_data.get('conversion_date') else None,
                        conversion_value=attr_data.get('conversion_value', 0),
                        first_touch_channel=attr_data.get('first_touch_channel', ''),
                        first_touch_source=attr_data.get('first_touch_source', ''),
                        first_touch_campaign=attr_data.get('first_touch_campaign', ''),
                        last_touch_channel=attr_data.get('last_touch_channel', ''),
                        last_touch_source=attr_data.get('last_touch_source', ''),
                        last_touch_campaign=attr_data.get('last_touch_campaign', ''),
                        channel_credits=attr_data.get('channel_credits', {}),
                        source_credits=attr_data.get('source_credits', {}),
                        campaign_credits=attr_data.get('campaign_credits', {})
                    )
                    self.attributions[attribution.lead_id] = attribution
    
    def _save_data(self):
        """Save attribution data."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data = [
            {
                'lead_id': a.lead_id,
                'touch_points': [
                    {
                        'timestamp': tp.timestamp.isoformat(),
                        'channel': tp.channel,
                        'source': tp.source,
                        'medium': tp.medium,
                        'campaign': tp.campaign,
                        'content': tp.content,
                        'landing_page': tp.landing_page,
                        'referrer': tp.referrer
                    }
                    for tp in a.touch_points
                ],
                'conversion_date': a.conversion_date.isoformat() if a.conversion_date else None,
                'conversion_value': a.conversion_value,
                'first_touch_channel': a.first_touch_channel,
                'first_touch_source': a.first_touch_source,
                'first_touch_campaign': a.first_touch_campaign,
                'last_touch_channel': a.last_touch_channel,
                'last_touch_source': a.last_touch_source,
                'last_touch_campaign': a.last_touch_campaign,
                'channel_credits': a.channel_credits,
                'source_credits': a.source_credits,
                'campaign_credits': a.campaign_credits
            }
            for a in self.attributions.values()
        ]
        
        with open(f"{self.storage_path}/attributions.json", 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_touch_point(
        self,
        lead_id: str,
        channel: str,
        source: str,
        medium: str,
        campaign: str = "",
        content: str = "",
        landing_page: str = "",
        referrer: str = ""
    ):
        """Add a touch point for a lead."""
        if lead_id not in self.attributions:
            self.attributions[lead_id] = LeadAttribution(lead_id=lead_id)
        
        touch_point = TouchPoint(
            timestamp=datetime.now(),
            channel=channel,
            source=source,
            medium=medium,
            campaign=campaign,
            content=content,
            landing_page=landing_page,
            referrer=referrer
        )
        
        attribution = self.attributions[lead_id]
        attribution.touch_points.append(touch_point)
        
        # Update first/last touch
        if len(attribution.touch_points) == 1:
            attribution.first_touch_channel = channel
            attribution.first_touch_source = source
            attribution.first_touch_campaign = campaign
        
        attribution.last_touch_channel = channel
        attribution.last_touch_source = source
        attribution.last_touch_campaign = campaign
        
        self._save_data()
    
    def record_conversion(
        self,
        lead_id: str,
        value: float = 0,
        model: AttributionModel = None
    ):
        """Record a conversion and calculate attribution."""
        if lead_id not in self.attributions:
            return
        
        attribution = self.attributions[lead_id]
        attribution.conversion_date = datetime.now()
        attribution.conversion_value = value
        
        # Calculate credits based on model
        model = model or self.default_model
        self._calculate_credits(attribution, model)
        
        self._save_data()
    
    def _calculate_credits(self, attribution: LeadAttribution, model: AttributionModel):
        """Calculate attribution credits."""
        touch_points = attribution.touch_points
        if not touch_points:
            return
        
        # Initialize credit dictionaries
        channel_credits = {}
        source_credits = {}
        campaign_credits = {}
        
        n = len(touch_points)
        
        if model == AttributionModel.FIRST_TOUCH:
            tp = touch_points[0]
            channel_credits[tp.channel] = 1.0
            source_credits[tp.source] = 1.0
            if tp.campaign:
                campaign_credits[tp.campaign] = 1.0
                
        elif model == AttributionModel.LAST_TOUCH:
            tp = touch_points[-1]
            channel_credits[tp.channel] = 1.0
            source_credits[tp.source] = 1.0
            if tp.campaign:
                campaign_credits[tp.campaign] = 1.0
                
        elif model == AttributionModel.LINEAR:
            credit = 1.0 / n
            for tp in touch_points:
                channel_credits[tp.channel] = channel_credits.get(tp.channel, 0) + credit
                source_credits[tp.source] = source_credits.get(tp.source, 0) + credit
                if tp.campaign:
                    campaign_credits[tp.campaign] = campaign_credits.get(tp.campaign, 0) + credit
                    
        elif model == AttributionModel.TIME_DECAY:
            # More recent touch points get more credit
            total_weight = sum(2 ** i for i in range(n))
            for i, tp in enumerate(touch_points):
                weight = (2 ** i) / total_weight
                channel_credits[tp.channel] = channel_credits.get(tp.channel, 0) + weight
                source_credits[tp.source] = source_credits.get(tp.source, 0) + weight
                if tp.campaign:
                    campaign_credits[tp.campaign] = campaign_credits.get(tp.campaign, 0) + weight
                    
        elif model == AttributionModel.POSITION_BASED:
            if n == 1:
                tp = touch_points[0]
                channel_credits[tp.channel] = 1.0
                source_credits[tp.source] = 1.0
                if tp.campaign:
                    campaign_credits[tp.campaign] = 1.0
            else:
                # 40% first, 40% last, 20% middle
                first_last_credit = 0.4
                middle_credit = 0.2 / max(1, n - 2)
                
                for i, tp in enumerate(touch_points):
                    if i == 0:
                        credit = first_last_credit
                    elif i == n - 1:
                        credit = first_last_credit
                    else:
                        credit = middle_credit
                    
                    channel_credits[tp.channel] = channel_credits.get(tp.channel, 0) + credit
                    source_credits[tp.source] = source_credits.get(tp.source, 0) + credit
                    if tp.campaign:
                        campaign_credits[tp.campaign] = campaign_credits.get(tp.campaign, 0) + credit
        
        attribution.channel_credits = channel_credits
        attribution.source_credits = source_credits
        attribution.campaign_credits = campaign_credits
    
    def get_attribution(self, lead_id: str) -> Optional[LeadAttribution]:
        """Get attribution for a lead."""
        return self.attributions.get(lead_id)
    
    def get_channel_performance(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        model: AttributionModel = None
    ) -> Dict:
        """Get performance by channel."""
        model = model or self.default_model
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()
        
        # Recalculate credits if needed
        for attribution in self.attributions.values():
            if attribution.conversion_date and start_date <= attribution.conversion_date <= end_date:
                if not attribution.channel_credits:
                    self._calculate_credits(attribution, model)
        
        # Aggregate by channel
        channel_stats = {}
        
        for attribution in self.attributions.values():
            if not attribution.conversion_date:
                continue
            if not (start_date <= attribution.conversion_date <= end_date):
                continue
            
            for channel, credit in attribution.channel_credits.items():
                if channel not in channel_stats:
                    channel_stats[channel] = {
                        'conversions': 0,
                        'credit': 0,
                        'value': 0,
                        'first_touch_conversions': 0,
                        'last_touch_conversions': 0
                    }
                
                channel_stats[channel]['conversions'] += 1
                channel_stats[channel]['credit'] += credit
                channel_stats[channel]['value'] += attribution.conversion_value * credit
                
                if attribution.first_touch_channel == channel:
                    channel_stats[channel]['first_touch_conversions'] += 1
                if attribution.last_touch_channel == channel:
                    channel_stats[channel]['last_touch_conversions'] += 1
        
        return channel_stats
    
    def get_campaign_performance(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        model: AttributionModel = None
    ) -> Dict:
        """Get performance by campaign."""
        model = model or self.default_model
        start_date = start_date or (datetime.now() - timedelta(days=30))
        end_date = end_date or datetime.now()
        
        campaign_stats = {}
        
        for attribution in self.attributions.values():
            if not attribution.conversion_date:
                continue
            if not (start_date <= attribution.conversion_date <= end_date):
                continue
            
            if not attribution.campaign_credits:
                self._calculate_credits(attribution, model)
            
            for campaign, credit in attribution.campaign_credits.items():
                if campaign not in campaign_stats:
                    campaign_stats[campaign] = {
                        'conversions': 0,
                        'credit': 0,
                        'value': 0
                    }
                
                campaign_stats[campaign]['conversions'] += 1
                campaign_stats[campaign]['credit'] += credit
                campaign_stats[campaign]['value'] += attribution.conversion_value * credit
        
        return campaign_stats
    
    def get_conversion_path_analysis(self, limit: int = 20) -> Dict:
        """Analyze common conversion paths."""
        paths = {}
        
        for attribution in self.attributions.values():
            if not attribution.conversion_date:
                continue
            
            # Create path string
            path = ' > '.join([tp.channel for tp in attribution.touch_points])
            
            if path not in paths:
                paths[path] = {
                    'count': 0,
                    'total_value': 0,
                    'avg_touch_points': 0
                }
            
            paths[path]['count'] += 1
            paths[path]['total_value'] += attribution.conversion_value
            paths[path]['avg_touch_points'] = len(attribution.touch_points)
        
        # Sort by count
        sorted_paths = sorted(paths.items(), key=lambda x: x[1]['count'], reverse=True)
        return dict(sorted_paths[:limit])
    
    def get_time_to_conversion(self) -> Dict:
        """Analyze time from first touch to conversion."""
        times = []
        
        for attribution in self.attributions.values():
            if not attribution.conversion_date or not attribution.touch_points:
                continue
            
            first_touch = attribution.touch_points[0].timestamp
            time_to_convert = (attribution.conversion_date - first_touch).days
            times.append(time_to_convert)
        
        if not times:
            return {}
        
        times.sort()
        
        return {
            'average_days': sum(times) / len(times),
            'median_days': times[len(times) // 2],
            'min_days': min(times),
            'max_days': max(times),
            'same_day': len([t for t in times if t == 0]),
            'within_7_days': len([t for t in times if t <= 7]),
            'within_30_days': len([t for t in times if t <= 30]),
            'over_30_days': len([t for t in times if t > 30])
        }
    
    def get_roi_by_channel(
        self,
        channel_costs: Dict[str, float],
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Calculate ROI by channel."""
        performance = self.get_channel_performance(start_date, end_date)
        
        roi_data = {}
        for channel, stats in performance.items():
            cost = channel_costs.get(channel, 0)
            revenue = stats['value']
            
            roi_data[channel] = {
                'cost': cost,
                'revenue': revenue,
                'profit': revenue - cost,
                'roi': ((revenue - cost) / cost * 100) if cost > 0 else 0,
                'cost_per_conversion': cost / stats['conversions'] if stats['conversions'] > 0 else 0,
                'conversions': stats['conversions']
            }
        
        return roi_data
