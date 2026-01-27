"""Prospect pipeline - automated processing of raw data to scored prospects."""

from dataclasses import dataclass, field
from typing import Dict, List, Callable
from datetime import datetime, timedelta
import threading
import time
import json
import os

from .sources import DataSourceManager, DataSourceType, RawRecord
from .signals import SignalDetector, LeadSignal, SignalType
from .scoring import ProspectScorer, ScoredProspect, ProspectTier


@dataclass
class PipelineStats:
    """Statistics for pipeline run."""
    run_id: str
    started_at: datetime
    completed_at: datetime = None
    records_processed: int = 0
    signals_detected: int = 0
    prospects_created: int = 0
    prospects_updated: int = 0
    errors: int = 0


class ProspectPipeline:
    """Automated pipeline: Data Sources -> Signals -> Scored Prospects."""
    
    def __init__(
        self,
        source_manager: DataSourceManager = None,
        signal_detector: SignalDetector = None,
        prospect_scorer: ProspectScorer = None,
        storage_path: str = "data/prospecting"
    ):
        self.storage_path = storage_path
        self.source_manager = source_manager or DataSourceManager(storage_path)
        self.signal_detector = signal_detector or SignalDetector(storage_path)
        self.prospect_scorer = prospect_scorer or ProspectScorer(storage_path)
        
        self.stats_history: List[PipelineStats] = []
        self._running = False
        self._thread = None
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_stats()
        self._register_default_collectors()
    
    def _load_stats(self):
        """Load pipeline statistics."""
        stats_file = f"{self.storage_path}/pipeline_stats.json"
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                data = json.load(f)
                for s in data[-100:]:  # Keep last 100 runs
                    stats = PipelineStats(
                        run_id=s['run_id'],
                        started_at=datetime.fromisoformat(s['started_at']),
                        completed_at=datetime.fromisoformat(s['completed_at']) if s.get('completed_at') else None,
                        records_processed=s.get('records_processed', 0),
                        signals_detected=s.get('signals_detected', 0),
                        prospects_created=s.get('prospects_created', 0),
                        prospects_updated=s.get('prospects_updated', 0),
                        errors=s.get('errors', 0)
                    )
                    self.stats_history.append(stats)
    
    def _save_stats(self):
        """Save pipeline statistics."""
        stats_data = [
            {
                'run_id': s.run_id,
                'started_at': s.started_at.isoformat(),
                'completed_at': s.completed_at.isoformat() if s.completed_at else None,
                'records_processed': s.records_processed,
                'signals_detected': s.signals_detected,
                'prospects_created': s.prospects_created,
                'prospects_updated': s.prospects_updated,
                'errors': s.errors
            }
            for s in self.stats_history[-100:]
        ]
        
        with open(f"{self.storage_path}/pipeline_stats.json", 'w') as f:
            json.dump(stats_data, f, indent=2)
    
    def _register_default_collectors(self):
        """Register default data collectors."""
        # These would connect to actual APIs/scrapers in production
        # For now, they're placeholders that can be extended
        
        def collect_auditor_data(source):
            """Collect from county auditor API."""
            # Would make actual API calls here
            return []
        
        def collect_court_records(source):
            """Collect from court records."""
            return []
        
        def collect_fsbo(source):
            """Collect FSBO listings."""
            return []
        
        self.source_manager.register_collector(DataSourceType.COUNTY_AUDITOR, collect_auditor_data)
        self.source_manager.register_collector(DataSourceType.COURT_RECORDS, collect_court_records)
        self.source_manager.register_collector(DataSourceType.FSBO_ZILLOW, collect_fsbo)
    
    def run_pipeline(self) -> PipelineStats:
        """Run the full pipeline: collect -> detect -> score."""
        import uuid
        
        stats = PipelineStats(
            run_id=str(uuid.uuid4())[:8],
            started_at=datetime.now()
        )
        
        try:
            # Step 1: Collect new data from sources
            collection_results = self.source_manager.collect_all()
            
            # Step 2: Process unprocessed records into signals
            unprocessed = self.source_manager.get_unprocessed_records(limit=500)
            
            all_signals = []
            processed_ids = []
            
            for record in unprocessed:
                try:
                    signals = self._process_record(record)
                    all_signals.extend(signals)
                    processed_ids.append(record.id)
                    stats.records_processed += 1
                except Exception as e:
                    stats.errors += 1
            
            self.source_manager.mark_processed(processed_ids)
            stats.signals_detected = len(all_signals)
            
            # Step 3: Group signals by address and score
            signals_by_address = {}
            for signal in all_signals:
                addr_key = signal.address.lower().strip()
                if addr_key not in signals_by_address:
                    signals_by_address[addr_key] = []
                signals_by_address[addr_key].append(signal)
            
            # Step 4: Create/update prospects
            for address, signals in signals_by_address.items():
                # Check if prospect already exists
                existing = None
                for p in self.prospect_scorer.prospects.values():
                    if p.address.lower().strip() == address:
                        existing = p
                        break
                
                if existing:
                    # Update existing prospect with new signals
                    existing.signals.extend([s.id for s in signals])
                    existing.updated_at = datetime.now()
                    # Re-score
                    all_signal_objs = [
                        self.signal_detector.signals[sid] 
                        for sid in existing.signals 
                        if sid in self.signal_detector.signals
                    ]
                    if all_signal_objs:
                        new_score = self.prospect_scorer.score_signals(all_signal_objs)
                        if new_score:
                            existing.score = new_score.score
                            existing.tier = new_score.tier
                    stats.prospects_updated += 1
                else:
                    # Create new prospect
                    prospect = self.prospect_scorer.score_signals(signals)
                    if prospect:
                        stats.prospects_created += 1
            
            stats.completed_at = datetime.now()
            
        except Exception as e:
            stats.errors += 1
            stats.completed_at = datetime.now()
        
        self.stats_history.append(stats)
        self._save_stats()
        
        return stats
    
    def _process_record(self, record: RawRecord) -> List[LeadSignal]:
        """Process a raw record into signals based on source type."""
        if record.source_type == DataSourceType.COUNTY_AUDITOR:
            return self.signal_detector.detect_from_auditor_record(record.data)
        elif record.source_type == DataSourceType.COURT_RECORDS:
            return self.signal_detector.detect_from_court_record(record.data)
        elif record.source_type in [DataSourceType.FSBO_ZILLOW, DataSourceType.FSBO_CRAIGSLIST, DataSourceType.FSBO_FACEBOOK]:
            return self.signal_detector.detect_from_fsbo(record.data)
        elif record.source_type == DataSourceType.MLS_EXPIRED:
            return self.signal_detector.detect_from_listing(record.data)
        elif record.source_type == DataSourceType.BUILDING_PERMITS:
            return self.signal_detector.detect_from_permit(record.data)
        elif record.source_type == DataSourceType.TAX_DELINQUENT:
            return self.signal_detector.detect_from_tax_record(record.data)
        elif record.source_type == DataSourceType.FORECLOSURE:
            return self.signal_detector.detect_from_court_record(record.data)
        elif record.source_type == DataSourceType.PROBATE:
            return self.signal_detector.detect_from_court_record(record.data)
        elif record.source_type == DataSourceType.DIVORCE:
            return self.signal_detector.detect_from_court_record(record.data)
        
        return []
    
    def start_automated_pipeline(self, interval_hours: int = 6):
        """Start automated pipeline runs."""
        if self._running:
            return
        
        self._running = True
        
        def pipeline_loop():
            while self._running:
                self.run_pipeline()
                time.sleep(interval_hours * 3600)
        
        self._thread = threading.Thread(target=pipeline_loop, daemon=True)
        self._thread.start()
    
    def stop_automated_pipeline(self):
        """Stop automated pipeline."""
        self._running = False
    
    def get_pipeline_summary(self) -> Dict:
        """Get pipeline summary."""
        source_stats = self.source_manager.get_collection_stats()
        prospect_stats = self.prospect_scorer.get_prospect_stats()
        
        # Recent runs
        recent_runs = self.stats_history[-10:]
        
        return {
            'sources': source_stats,
            'prospects': prospect_stats,
            'signals': {
                'total': len(self.signal_detector.signals),
                'active': len(self.signal_detector.get_active_signals()),
                'high_priority': len(self.signal_detector.get_high_priority_signals())
            },
            'recent_runs': [
                {
                    'run_id': s.run_id,
                    'started': s.started_at.isoformat(),
                    'records': s.records_processed,
                    'signals': s.signals_detected,
                    'prospects': s.prospects_created
                }
                for s in recent_runs
            ],
            'pipeline_status': 'running' if self._running else 'stopped'
        }
    
    def get_actionable_prospects(self, limit: int = 25) -> List[Dict]:
        """Get prospects ready for outreach with full context."""
        hot = self.prospect_scorer.get_hot_prospects(limit)
        
        results = []
        for prospect in hot:
            # Get full signal details
            signals = []
            for sid in prospect.signals:
                if sid in self.signal_detector.signals:
                    s = self.signal_detector.signals[sid]
                    signals.append({
                        'type': s.signal_type.value,
                        'strength': s.strength,
                        'details': s.details,
                        'detected': s.detected_at.isoformat()
                    })
            
            results.append({
                'id': prospect.id,
                'address': prospect.address,
                'owner': prospect.owner_name,
                'phone': prospect.owner_phone,
                'email': prospect.owner_email,
                'mailing_address': prospect.mailing_address,
                'tier': prospect.tier.value,
                'score': prospect.score,
                'type': prospect.prospect_type.value,
                'property_value': prospect.property_value,
                'equity': prospect.equity_estimate,
                'signals': signals,
                'summary': prospect.signal_summary,
                'approach': prospect.recommended_approach,
                'data_quality': prospect.data_quality,
                'status': prospect.status
            })
        
        return results
    
    def add_manual_record(
        self,
        source_type: DataSourceType,
        data: Dict,
        address: str = "",
        owner_name: str = ""
    ) -> bool:
        """Manually add a record to the pipeline."""
        import uuid
        
        record = RawRecord(
            id=str(uuid.uuid4())[:12],
            source_id="manual",
            source_type=source_type,
            data=data,
            address=address,
            owner_name=owner_name
        )
        
        return self.source_manager.add_record(record)
