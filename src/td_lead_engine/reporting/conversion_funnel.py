"""Conversion funnel analysis and reporting."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import os
import statistics


@dataclass
class FunnelStage:
    """A stage in the conversion funnel."""
    name: str
    order: int
    count: int = 0
    conversion_to_next: float = 0
    avg_time_in_stage: float = 0  # hours


@dataclass
class FunnelEntry:
    """A lead's journey through the funnel."""
    lead_id: str
    current_stage: str
    stages_completed: List[str] = field(default_factory=list)
    stage_times: Dict[str, datetime] = field(default_factory=dict)
    converted: bool = False
    dropped_at: str = ""
    entered_at: datetime = field(default_factory=datetime.now)
    converted_at: datetime = None


class ConversionFunnelReport:
    """Conversion funnel analysis."""
    
    # Default funnel stages
    DEFAULT_STAGES = [
        "visitor",
        "lead",
        "contacted",
        "qualified",
        "showing",
        "offer",
        "contract",
        "closed"
    ]
    
    def __init__(
        self,
        stages: List[str] = None,
        storage_path: str = "data/reporting"
    ):
        self.stages = stages or self.DEFAULT_STAGES
        self.storage_path = storage_path
        self.entries: Dict[str, FunnelEntry] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load funnel data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        data_file = f"{self.storage_path}/conversion_funnel.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                self.stages = data.get('stages', self.DEFAULT_STAGES)
                
                for e in data.get('entries', []):
                    stage_times = {
                        k: datetime.fromisoformat(v)
                        for k, v in e.get('stage_times', {}).items()
                    }
                    entry = FunnelEntry(
                        lead_id=e['lead_id'],
                        current_stage=e['current_stage'],
                        stages_completed=e.get('stages_completed', []),
                        stage_times=stage_times,
                        converted=e.get('converted', False),
                        dropped_at=e.get('dropped_at', ''),
                        entered_at=datetime.fromisoformat(e['entered_at']),
                        converted_at=datetime.fromisoformat(e['converted_at']) if e.get('converted_at') else None
                    )
                    self.entries[entry.lead_id] = entry
    
    def _save_data(self):
        """Save funnel data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        entries_data = [
            {
                'lead_id': e.lead_id,
                'current_stage': e.current_stage,
                'stages_completed': e.stages_completed,
                'stage_times': {k: v.isoformat() for k, v in e.stage_times.items()},
                'converted': e.converted,
                'dropped_at': e.dropped_at,
                'entered_at': e.entered_at.isoformat(),
                'converted_at': e.converted_at.isoformat() if e.converted_at else None
            }
            for e in self.entries.values()
        ]
        
        with open(f"{self.storage_path}/conversion_funnel.json", 'w') as f:
            json.dump({
                'stages': self.stages,
                'entries': entries_data
            }, f, indent=2)
    
    def enter_funnel(self, lead_id: str, stage: str = None):
        """Enter a lead into the funnel."""
        initial_stage = stage or self.stages[0]
        
        entry = FunnelEntry(
            lead_id=lead_id,
            current_stage=initial_stage,
            stages_completed=[initial_stage],
            stage_times={initial_stage: datetime.now()}
        )
        self.entries[lead_id] = entry
        self._save_data()
    
    def advance_stage(self, lead_id: str, new_stage: str):
        """Advance a lead to a new stage."""
        entry = self.entries.get(lead_id)
        if not entry:
            return
        
        # Validate stage exists
        if new_stage not in self.stages:
            return
        
        entry.current_stage = new_stage
        if new_stage not in entry.stages_completed:
            entry.stages_completed.append(new_stage)
        entry.stage_times[new_stage] = datetime.now()
        
        # Check if converted (reached final stage)
        if new_stage == self.stages[-1]:
            entry.converted = True
            entry.converted_at = datetime.now()
        
        self._save_data()
    
    def mark_dropped(self, lead_id: str, dropped_stage: str = None):
        """Mark a lead as dropped from the funnel."""
        entry = self.entries.get(lead_id)
        if not entry:
            return
        
        entry.dropped_at = dropped_stage or entry.current_stage
        self._save_data()
    
    def get_funnel_analysis(
        self,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict:
        """Get funnel analysis."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        # Filter entries by date
        entries = [
            e for e in self.entries.values()
            if start <= e.entered_at <= end
        ]
        
        # Build funnel stages
        funnel_stages = []
        previous_count = 0
        
        for i, stage_name in enumerate(self.stages):
            # Count entries that reached this stage
            reached = [e for e in entries if stage_name in e.stages_completed]
            count = len(reached)
            
            # Calculate conversion from previous stage
            if i == 0:
                conversion = 100.0
            else:
                conversion = round(count / previous_count * 100, 1) if previous_count else 0
            
            # Calculate average time in stage
            times = []
            for e in reached:
                if stage_name in e.stage_times:
                    next_stage_idx = i + 1
                    if next_stage_idx < len(self.stages):
                        next_stage = self.stages[next_stage_idx]
                        if next_stage in e.stage_times:
                            time_diff = (e.stage_times[next_stage] - e.stage_times[stage_name]).total_seconds() / 3600
                            times.append(time_diff)
            
            avg_time = round(statistics.mean(times), 1) if times else 0
            
            funnel_stages.append(FunnelStage(
                name=stage_name,
                order=i,
                count=count,
                conversion_to_next=conversion,
                avg_time_in_stage=avg_time
            ))
            
            previous_count = count
        
        # Calculate drop-off points
        drop_offs = {}
        for entry in entries:
            if entry.dropped_at and not entry.converted:
                if entry.dropped_at not in drop_offs:
                    drop_offs[entry.dropped_at] = 0
                drop_offs[entry.dropped_at] += 1
        
        # Overall conversion rate
        total_entered = len([e for e in entries if self.stages[0] in e.stages_completed])
        total_converted = len([e for e in entries if e.converted])
        
        return {
            'period': {
                'start': start.isoformat(),
                'end': end.isoformat()
            },
            'summary': {
                'total_entered': total_entered,
                'total_converted': total_converted,
                'overall_conversion_rate': round(total_converted / total_entered * 100, 1) if total_entered else 0,
                'total_dropped': len([e for e in entries if e.dropped_at and not e.converted])
            },
            'stages': [
                {
                    'name': s.name,
                    'count': s.count,
                    'conversion_to_next': s.conversion_to_next,
                    'avg_time_hours': s.avg_time_in_stage
                }
                for s in funnel_stages
            ],
            'drop_off_points': [
                {'stage': stage, 'count': count, 'percentage': round(count / total_entered * 100, 1) if total_entered else 0}
                for stage, count in sorted(drop_offs.items(), key=lambda x: x[1], reverse=True)
            ]
        }
    
    def get_stage_breakdown(self, stage: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Get detailed breakdown for a specific stage."""
        start = start_date or datetime.now() - timedelta(days=30)
        end = end_date or datetime.now()
        
        entries = [
            e for e in self.entries.values()
            if start <= e.entered_at <= end and stage in e.stages_completed
        ]
        
        # Currently in stage
        current = [e for e in entries if e.current_stage == stage and not e.dropped_at]
        
        # Advanced to next stage
        stage_idx = self.stages.index(stage) if stage in self.stages else -1
        next_stage = self.stages[stage_idx + 1] if stage_idx >= 0 and stage_idx < len(self.stages) - 1 else None
        advanced = [e for e in entries if next_stage and next_stage in e.stages_completed] if next_stage else []
        
        # Dropped at this stage
        dropped = [e for e in entries if e.dropped_at == stage]
        
        # Time in stage distribution
        times = []
        for e in entries:
            if stage in e.stage_times and next_stage and next_stage in e.stage_times:
                hours = (e.stage_times[next_stage] - e.stage_times[stage]).total_seconds() / 3600
                times.append(hours)
        
        return {
            'stage': stage,
            'total_reached': len(entries),
            'currently_in_stage': len(current),
            'advanced_to_next': len(advanced),
            'dropped_here': len(dropped),
            'conversion_rate': round(len(advanced) / len(entries) * 100, 1) if entries else 0,
            'time_in_stage': {
                'avg_hours': round(statistics.mean(times), 1) if times else 0,
                'min_hours': round(min(times), 1) if times else 0,
                'max_hours': round(max(times), 1) if times else 0,
                'median_hours': round(statistics.median(times), 1) if times else 0
            } if times else None
        }
    
    def get_cohort_analysis(
        self,
        cohort_period: str = "week",  # week, month
        num_periods: int = 8
    ) -> Dict:
        """Analyze conversion by cohort."""
        now = datetime.now()
        cohorts = []
        
        for i in range(num_periods):
            if cohort_period == "week":
                period_start = now - timedelta(weeks=num_periods-i)
                period_end = now - timedelta(weeks=num_periods-i-1)
                period_name = period_start.strftime("%Y-W%U")
            else:  # month
                period_start = (now - timedelta(days=30*(num_periods-i))).replace(day=1)
                period_end = (period_start + timedelta(days=32)).replace(day=1)
                period_name = period_start.strftime("%Y-%m")
            
            # Get entries for this cohort
            entries = [
                e for e in self.entries.values()
                if period_start <= e.entered_at < period_end
            ]
            
            total = len(entries)
            converted = len([e for e in entries if e.converted])
            
            # Stage progression
            stage_counts = {}
            for stage in self.stages:
                stage_counts[stage] = len([e for e in entries if stage in e.stages_completed])
            
            cohorts.append({
                'period': period_name,
                'entered': total,
                'converted': converted,
                'conversion_rate': round(converted / total * 100, 1) if total else 0,
                'stage_progression': stage_counts
            })
        
        return {
            'cohort_period': cohort_period,
            'cohorts': cohorts
        }
    
    def get_bottleneck_analysis(self, start_date: datetime = None, end_date: datetime = None) -> Dict:
        """Identify bottlenecks in the funnel."""
        analysis = self.get_funnel_analysis(start_date, end_date)
        stages = analysis['stages']
        
        bottlenecks = []
        
        for i in range(1, len(stages)):
            current = stages[i]
            previous = stages[i-1]
            
            # Low conversion rate indicates bottleneck
            if current['conversion_to_next'] < 50:  # Less than 50% conversion
                bottlenecks.append({
                    'stage': previous['name'],
                    'next_stage': current['name'],
                    'conversion_rate': current['conversion_to_next'],
                    'drop_off': previous['count'] - current['count'],
                    'severity': 'high' if current['conversion_to_next'] < 25 else 'medium'
                })
            
            # Long time in stage indicates bottleneck
            if current['avg_time_hours'] > 72:  # More than 3 days
                existing = next((b for b in bottlenecks if b['stage'] == current['name']), None)
                if existing:
                    existing['long_duration'] = True
                    existing['avg_time_hours'] = current['avg_time_hours']
                else:
                    bottlenecks.append({
                        'stage': current['name'],
                        'avg_time_hours': current['avg_time_hours'],
                        'long_duration': True,
                        'severity': 'medium'
                    })
        
        # Sort by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        bottlenecks.sort(key=lambda x: severity_order.get(x['severity'], 2))
        
        return {
            'bottlenecks': bottlenecks,
            'recommendations': [
                f"Stage '{b['stage']}' has only {b.get('conversion_rate', 'N/A')}% conversion - review qualification criteria"
                for b in bottlenecks if b.get('conversion_rate')
            ] + [
                f"Stage '{b['stage']}' averages {b['avg_time_hours']:.1f} hours - consider automation"
                for b in bottlenecks if b.get('long_duration')
            ]
        }
