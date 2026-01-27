"""Lead source ROI analysis."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os


@dataclass
class SourceMetrics:
    """Metrics for a lead source."""
    source: str
    leads_count: int = 0
    cost: float = 0
    conversions: int = 0
    revenue: float = 0
    cost_per_lead: float = 0
    cost_per_conversion: float = 0
    conversion_rate: float = 0
    roi: float = 0
    avg_deal_size: float = 0


@dataclass
class LeadSourceData:
    """Data for a lead from a source."""
    id: str
    source: str
    source_detail: str = ""
    cost: float = 0
    converted: bool = False
    revenue: float = 0
    created_at: datetime = field(default_factory=datetime.now)
    converted_at: datetime = None


class LeadSourceROI:
    """Calculate and track ROI by lead source."""
    
    def __init__(self, storage_path: str = "data/reporting"):
        self.storage_path = storage_path
        self.leads: Dict[str, LeadSourceData] = {}
        self.source_costs: Dict[str, Dict] = {}  # Monthly costs by source
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/lead_source_roi.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                for l in data.get('leads', []):
                    lead = LeadSourceData(
                        id=l['id'],
                        source=l['source'],
                        source_detail=l.get('source_detail', ''),
                        cost=l.get('cost', 0),
                        converted=l.get('converted', False),
                        revenue=l.get('revenue', 0),
                        created_at=datetime.fromisoformat(l['created_at']),
                        converted_at=datetime.fromisoformat(l['converted_at']) if l.get('converted_at') else None
                    )
                    self.leads[lead.id] = lead
                
                self.source_costs = data.get('source_costs', {})
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        leads_data = [
            {
                'id': l.id,
                'source': l.source,
                'source_detail': l.source_detail,
                'cost': l.cost,
                'converted': l.converted,
                'revenue': l.revenue,
                'created_at': l.created_at.isoformat(),
                'converted_at': l.converted_at.isoformat() if l.converted_at else None
            }
            for l in self.leads.values()
        ]
        
        with open(f"{self.storage_path}/lead_source_roi.json", 'w') as f:
            json.dump({
                'leads': leads_data,
                'source_costs': self.source_costs
            }, f, indent=2)
    
    def record_lead(
        self,
        lead_id: str,
        source: str,
        source_detail: str = "",
        cost: float = 0
    ):
        """Record a new lead from a source."""
        lead = LeadSourceData(
            id=lead_id,
            source=source,
            source_detail=source_detail,
            cost=cost
        )
        self.leads[lead_id] = lead
        self._save_data()
    
    def record_conversion(self, lead_id: str, revenue: float = 0):
        """Record a lead conversion."""
        lead = self.leads.get(lead_id)
        if lead:
            lead.converted = True
            lead.revenue = revenue
            lead.converted_at = datetime.now()
            self._save_data()
    
    def set_source_monthly_cost(self, source: str, year: int, month: int, cost: float):
        """Set monthly cost for a lead source."""
        key = f"{year}-{month:02d}"
        if source not in self.source_costs:
            self.source_costs[source] = {}
        self.source_costs[source][key] = cost
        self._save_data()
    
    def get_source_metrics(
        self,
        source: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> SourceMetrics:
        """Get metrics for a specific source."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        # Filter leads by source and date
        leads = [
            l for l in self.leads.values()
            if l.source == source and start <= l.created_at <= end
        ]
        
        leads_count = len(leads)
        conversions = len([l for l in leads if l.converted])
        lead_costs = sum(l.cost for l in leads)
        revenue = sum(l.revenue for l in leads if l.converted)
        
        # Add monthly source costs
        source_monthly = self.source_costs.get(source, {})
        monthly_cost = 0
        current = start
        while current <= end:
            key = f"{current.year}-{current.month:02d}"
            monthly_cost += source_monthly.get(key, 0)
            current += timedelta(days=32)
            current = current.replace(day=1)
        
        total_cost = lead_costs + monthly_cost
        
        return SourceMetrics(
            source=source,
            leads_count=leads_count,
            cost=total_cost,
            conversions=conversions,
            revenue=revenue,
            cost_per_lead=round(total_cost / leads_count, 2) if leads_count else 0,
            cost_per_conversion=round(total_cost / conversions, 2) if conversions else 0,
            conversion_rate=round(conversions / leads_count * 100, 1) if leads_count else 0,
            roi=round((revenue - total_cost) / total_cost * 100, 1) if total_cost else 0,
            avg_deal_size=round(revenue / conversions, 2) if conversions else 0
        )
    
    def get_all_source_metrics(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> List[SourceMetrics]:
        """Get metrics for all sources."""
        sources = set(l.source for l in self.leads.values())
        return [self.get_source_metrics(s, start_date, end_date) for s in sources]
    
    def get_roi_comparison(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Get ROI comparison across all sources."""
        metrics = self.get_all_source_metrics(start_date, end_date)
        
        # Sort by ROI
        by_roi = sorted(metrics, key=lambda m: m.roi, reverse=True)
        
        # Sort by conversion rate
        by_conversion = sorted(metrics, key=lambda m: m.conversion_rate, reverse=True)
        
        # Sort by cost per lead
        by_cpl = sorted(metrics, key=lambda m: m.cost_per_lead)
        
        total_cost = sum(m.cost for m in metrics)
        total_revenue = sum(m.revenue for m in metrics)
        total_leads = sum(m.leads_count for m in metrics)
        total_conversions = sum(m.conversions for m in metrics)
        
        return {
            'summary': {
                'total_sources': len(metrics),
                'total_leads': total_leads,
                'total_cost': total_cost,
                'total_revenue': total_revenue,
                'total_conversions': total_conversions,
                'overall_roi': round((total_revenue - total_cost) / total_cost * 100, 1) if total_cost else 0,
                'overall_conversion_rate': round(total_conversions / total_leads * 100, 1) if total_leads else 0,
                'avg_cost_per_lead': round(total_cost / total_leads, 2) if total_leads else 0
            },
            'by_roi': [
                {'source': m.source, 'roi': m.roi, 'revenue': m.revenue, 'cost': m.cost}
                for m in by_roi[:10]
            ],
            'by_conversion_rate': [
                {'source': m.source, 'rate': m.conversion_rate, 'conversions': m.conversions, 'leads': m.leads_count}
                for m in by_conversion[:10]
            ],
            'by_cost_efficiency': [
                {'source': m.source, 'cost_per_lead': m.cost_per_lead, 'cost_per_conversion': m.cost_per_conversion}
                for m in by_cpl[:10]
            ],
            'all_sources': [
                {
                    'source': m.source,
                    'leads': m.leads_count,
                    'conversions': m.conversions,
                    'cost': m.cost,
                    'revenue': m.revenue,
                    'roi': m.roi,
                    'conversion_rate': m.conversion_rate,
                    'cost_per_lead': m.cost_per_lead,
                    'cost_per_conversion': m.cost_per_conversion
                }
                for m in metrics
            ]
        }
    
    def get_trending_sources(
        self,
        current_period_days: int = 30
    ) -> Dict:
        """Compare current period vs previous period."""
        now = datetime.now()
        current_start = now - timedelta(days=current_period_days)
        previous_start = current_start - timedelta(days=current_period_days)
        
        current_metrics = {m.source: m for m in self.get_all_source_metrics(current_start, now)}
        previous_metrics = {m.source: m for m in self.get_all_source_metrics(previous_start, current_start)}
        
        trending = []
        for source in current_metrics:
            current = current_metrics[source]
            previous = previous_metrics.get(source)
            
            if previous and previous.leads_count > 0:
                lead_change = (current.leads_count - previous.leads_count) / previous.leads_count * 100
                conversion_change = current.conversion_rate - previous.conversion_rate
                roi_change = current.roi - previous.roi
            else:
                lead_change = 100 if current.leads_count > 0 else 0
                conversion_change = current.conversion_rate
                roi_change = current.roi
            
            trending.append({
                'source': source,
                'current_leads': current.leads_count,
                'lead_change_pct': round(lead_change, 1),
                'current_conversion_rate': current.conversion_rate,
                'conversion_change': round(conversion_change, 1),
                'current_roi': current.roi,
                'roi_change': round(roi_change, 1)
            })
        
        # Sort by lead growth
        trending.sort(key=lambda x: x['lead_change_pct'], reverse=True)
        
        return {
            'period': f"Last {current_period_days} days vs previous {current_period_days} days",
            'trending_up': [t for t in trending if t['lead_change_pct'] > 0][:5],
            'trending_down': [t for t in trending if t['lead_change_pct'] < 0][:5],
            'all_sources': trending
        }
