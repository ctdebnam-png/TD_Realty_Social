"""Pipeline forecasting and projections."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import statistics


class PipelineStage(Enum):
    """Pipeline stages."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    SHOWING = "showing"
    OFFER = "offer"
    UNDER_CONTRACT = "under_contract"
    CLOSED = "closed"
    LOST = "lost"


@dataclass
class PipelineLead:
    """A lead in the pipeline."""
    id: str
    stage: PipelineStage
    lead_type: str  # buyer/seller
    estimated_value: float = 0
    probability: float = 0
    expected_close_date: datetime = None
    days_in_stage: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    stage_changed_at: datetime = field(default_factory=datetime.now)


@dataclass
class StageProbability:
    """Historical probability of closing from each stage."""
    stage: PipelineStage
    total_leads: int = 0
    closed_leads: int = 0
    probability: float = 0
    avg_days_to_close: float = 0


class PipelineForecast:
    """Pipeline forecasting and analysis."""
    
    # Default stage probabilities (can be overridden by historical data)
    DEFAULT_PROBABILITIES = {
        PipelineStage.NEW: 0.05,
        PipelineStage.CONTACTED: 0.10,
        PipelineStage.QUALIFIED: 0.25,
        PipelineStage.SHOWING: 0.40,
        PipelineStage.OFFER: 0.60,
        PipelineStage.UNDER_CONTRACT: 0.90,
        PipelineStage.CLOSED: 1.0,
        PipelineStage.LOST: 0.0
    }
    
    def __init__(self, storage_path: str = "data/reporting"):
        self.storage_path = storage_path
        self.leads: Dict[str, PipelineLead] = {}
        self.historical_conversions: List[Dict] = []
        self.stage_probabilities: Dict[PipelineStage, StageProbability] = {}
        
        self._load_data()
        self._calculate_probabilities()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/pipeline_forecast.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for l in data.get('leads', []):
                    lead = PipelineLead(
                        id=l['id'],
                        stage=PipelineStage(l['stage']),
                        lead_type=l.get('lead_type', 'buyer'),
                        estimated_value=l.get('estimated_value', 0),
                        probability=l.get('probability', 0),
                        expected_close_date=datetime.fromisoformat(l['expected_close_date']) if l.get('expected_close_date') else None,
                        days_in_stage=l.get('days_in_stage', 0),
                        created_at=datetime.fromisoformat(l['created_at']),
                        stage_changed_at=datetime.fromisoformat(l['stage_changed_at']) if l.get('stage_changed_at') else datetime.now()
                    )
                    self.leads[lead.id] = lead
                
                self.historical_conversions = data.get('historical_conversions', [])
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        leads_data = [
            {
                'id': l.id,
                'stage': l.stage.value,
                'lead_type': l.lead_type,
                'estimated_value': l.estimated_value,
                'probability': l.probability,
                'expected_close_date': l.expected_close_date.isoformat() if l.expected_close_date else None,
                'days_in_stage': l.days_in_stage,
                'created_at': l.created_at.isoformat(),
                'stage_changed_at': l.stage_changed_at.isoformat()
            }
            for l in self.leads.values()
        ]
        
        with open(f"{self.storage_path}/pipeline_forecast.json", 'w') as f:
            json.dump({
                'leads': leads_data,
                'historical_conversions': self.historical_conversions[-5000:]
            }, f, indent=2)
    
    def _calculate_probabilities(self):
        """Calculate stage probabilities from historical data."""
        for stage in PipelineStage:
            if stage in [PipelineStage.CLOSED, PipelineStage.LOST]:
                continue
            
            # Filter historical conversions that went through this stage
            through_stage = [
                c for c in self.historical_conversions
                if stage.value in c.get('stages_visited', [])
            ]
            
            closed_from_stage = [
                c for c in through_stage
                if c.get('final_stage') == 'closed'
            ]
            
            total = len(through_stage)
            closed = len(closed_from_stage)
            
            # Calculate average days to close from this stage
            days_to_close = [
                c.get('days_to_close_from_stage', {}).get(stage.value, 0)
                for c in closed_from_stage
                if c.get('days_to_close_from_stage', {}).get(stage.value)
            ]
            avg_days = statistics.mean(days_to_close) if days_to_close else 30
            
            prob = closed / total if total >= 10 else self.DEFAULT_PROBABILITIES.get(stage, 0.1)
            
            self.stage_probabilities[stage] = StageProbability(
                stage=stage,
                total_leads=total,
                closed_leads=closed,
                probability=round(prob, 3),
                avg_days_to_close=round(avg_days, 1)
            )
    
    def add_lead(
        self,
        lead_id: str,
        stage: PipelineStage,
        lead_type: str = "buyer",
        estimated_value: float = 0,
        expected_close_date: datetime = None
    ):
        """Add a lead to the pipeline."""
        prob_data = self.stage_probabilities.get(stage)
        probability = prob_data.probability if prob_data else self.DEFAULT_PROBABILITIES.get(stage, 0.1)
        
        lead = PipelineLead(
            id=lead_id,
            stage=stage,
            lead_type=lead_type,
            estimated_value=estimated_value,
            probability=probability,
            expected_close_date=expected_close_date
        )
        self.leads[lead_id] = lead
        self._save_data()
    
    def update_stage(self, lead_id: str, new_stage: PipelineStage):
        """Update lead stage."""
        lead = self.leads.get(lead_id)
        if not lead:
            return
        
        # Record historical data
        old_stage = lead.stage
        lead.days_in_stage = (datetime.now() - lead.stage_changed_at).days
        
        # Update stage
        lead.stage = new_stage
        lead.stage_changed_at = datetime.now()
        
        # Update probability
        prob_data = self.stage_probabilities.get(new_stage)
        lead.probability = prob_data.probability if prob_data else self.DEFAULT_PROBABILITIES.get(new_stage, 0.1)
        
        self._save_data()
    
    def record_conversion(
        self,
        lead_id: str,
        final_stage: str,
        stages_visited: List[str],
        days_in_each_stage: Dict[str, int],
        total_days: int
    ):
        """Record a conversion for historical analysis."""
        # Calculate days to close from each stage
        days_to_close = {}
        remaining = total_days
        for stage in reversed(stages_visited):
            days_to_close[stage] = remaining
            remaining -= days_in_each_stage.get(stage, 0)
        
        self.historical_conversions.append({
            'lead_id': lead_id,
            'final_stage': final_stage,
            'stages_visited': stages_visited,
            'days_in_each_stage': days_in_each_stage,
            'days_to_close_from_stage': days_to_close,
            'total_days': total_days,
            'recorded_at': datetime.now().isoformat()
        })
        
        self._save_data()
        self._calculate_probabilities()
    
    def get_pipeline_summary(self) -> Dict:
        """Get current pipeline summary."""
        active_leads = [l for l in self.leads.values() if l.stage not in [PipelineStage.CLOSED, PipelineStage.LOST]]
        
        by_stage = {}
        for stage in PipelineStage:
            stage_leads = [l for l in active_leads if l.stage == stage]
            by_stage[stage.value] = {
                'count': len(stage_leads),
                'value': sum(l.estimated_value for l in stage_leads),
                'weighted_value': sum(l.estimated_value * l.probability for l in stage_leads)
            }
        
        total_value = sum(l.estimated_value for l in active_leads)
        weighted_value = sum(l.estimated_value * l.probability for l in active_leads)
        
        return {
            'total_leads': len(active_leads),
            'total_value': total_value,
            'weighted_value': round(weighted_value, 2),
            'by_stage': by_stage,
            'by_type': {
                'buyer': len([l for l in active_leads if l.lead_type == 'buyer']),
                'seller': len([l for l in active_leads if l.lead_type == 'seller'])
            }
        }
    
    def forecast_closings(
        self,
        months: int = 3
    ) -> Dict:
        """Forecast closings for the next N months."""
        active_leads = [l for l in self.leads.values() if l.stage not in [PipelineStage.CLOSED, PipelineStage.LOST]]
        
        forecasts = []
        now = datetime.now()
        
        for i in range(months):
            month_start = (now + timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            month_leads = []
            month_value = 0
            month_weighted = 0
            
            for lead in active_leads:
                # Estimate close date based on stage
                prob_data = self.stage_probabilities.get(lead.stage)
                avg_days = prob_data.avg_days_to_close if prob_data else 30
                estimated_close = lead.stage_changed_at + timedelta(days=avg_days)
                
                # Use expected_close_date if provided
                if lead.expected_close_date:
                    estimated_close = lead.expected_close_date
                
                if month_start <= estimated_close <= month_end:
                    month_leads.append(lead)
                    month_value += lead.estimated_value
                    month_weighted += lead.estimated_value * lead.probability
            
            forecasts.append({
                'month': month_start.strftime('%Y-%m'),
                'month_name': month_start.strftime('%B %Y'),
                'expected_closings': len(month_leads),
                'expected_value': month_value,
                'weighted_value': round(month_weighted, 2),
                'leads': [
                    {
                        'id': l.id,
                        'stage': l.stage.value,
                        'value': l.estimated_value,
                        'probability': l.probability
                    }
                    for l in month_leads
                ]
            })
        
        return {
            'forecast_period': f"Next {months} months",
            'total_expected_closings': sum(f['expected_closings'] for f in forecasts),
            'total_expected_value': sum(f['expected_value'] for f in forecasts),
            'total_weighted_value': sum(f['weighted_value'] for f in forecasts),
            'monthly_forecasts': forecasts
        }
    
    def get_stage_conversion_rates(self) -> Dict:
        """Get conversion rates between stages."""
        rates = {}
        
        for stage, prob_data in self.stage_probabilities.items():
            rates[stage.value] = {
                'probability_to_close': prob_data.probability,
                'sample_size': prob_data.total_leads,
                'avg_days_to_close': prob_data.avg_days_to_close
            }
        
        return rates
    
    def get_velocity_report(self) -> Dict:
        """Get pipeline velocity metrics."""
        active_leads = [l for l in self.leads.values() if l.stage not in [PipelineStage.CLOSED, PipelineStage.LOST]]
        
        # Calculate days in current stage
        now = datetime.now()
        stage_times = {}
        
        for stage in PipelineStage:
            stage_leads = [l for l in active_leads if l.stage == stage]
            if stage_leads:
                days = [(now - l.stage_changed_at).days for l in stage_leads]
                stage_times[stage.value] = {
                    'avg_days': round(statistics.mean(days), 1),
                    'max_days': max(days),
                    'leads_stale_30d': len([d for d in days if d > 30]),
                    'leads_stale_60d': len([d for d in days if d > 60])
                }
        
        return {
            'stage_velocity': stage_times,
            'stale_leads': [
                {
                    'id': l.id,
                    'stage': l.stage.value,
                    'days_in_stage': (now - l.stage_changed_at).days,
                    'value': l.estimated_value
                }
                for l in active_leads
                if (now - l.stage_changed_at).days > 30
            ][:20]
        }
