"""Data source manager for pulling lead data from multiple public sources."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import hashlib
import threading
import time


class DataSourceType(Enum):
    """Types of data sources."""
    COUNTY_AUDITOR = "county_auditor"
    COUNTY_RECORDER = "county_recorder"
    COURT_RECORDS = "court_records"
    MLS_EXPIRED = "mls_expired"
    FSBO_ZILLOW = "fsbo_zillow"
    FSBO_CRAIGSLIST = "fsbo_craigslist"
    FSBO_FACEBOOK = "fsbo_facebook"
    RENTAL_LISTINGS = "rental_listings"
    BUILDING_PERMITS = "building_permits"
    TAX_DELINQUENT = "tax_delinquent"
    FORECLOSURE = "foreclosure"
    PROBATE = "probate"
    DIVORCE = "divorce"
    PROPERTY_TRANSFERS = "property_transfers"
    PRICE_REDUCTIONS = "price_reductions"


@dataclass
class DataSource:
    """A data source configuration."""
    id: str
    name: str
    source_type: DataSourceType
    url: str = ""
    enabled: bool = True
    refresh_hours: int = 24
    last_refresh: datetime = None
    credentials: Dict = field(default_factory=dict)
    config: Dict = field(default_factory=dict)


@dataclass
class RawRecord:
    """A raw record pulled from a data source."""
    id: str
    source_id: str
    source_type: DataSourceType
    data: Dict
    address: str = ""
    owner_name: str = ""
    collected_at: datetime = field(default_factory=datetime.now)
    processed: bool = False


class DataSourceManager:
    """Manage multiple data sources and coordinate data collection."""
    
    # Central Ohio data source URLs (public records)
    OHIO_SOURCES = {
        'franklin_auditor': {
            'name': 'Franklin County Auditor',
            'type': DataSourceType.COUNTY_AUDITOR,
            'url': 'https://apps.franklincountyauditor.com/api',
            'refresh_hours': 24
        },
        'franklin_recorder': {
            'name': 'Franklin County Recorder',
            'type': DataSourceType.COUNTY_RECORDER,
            'url': 'https://recorder.franklincountyohio.gov',
            'refresh_hours': 24
        },
        'franklin_courts': {
            'name': 'Franklin County Courts',
            'type': DataSourceType.COURT_RECORDS,
            'url': 'https://fcdcfcjs.co.franklin.oh.us',
            'refresh_hours': 24
        },
        'delaware_auditor': {
            'name': 'Delaware County Auditor',
            'type': DataSourceType.COUNTY_AUDITOR,
            'url': 'https://www.co.delaware.oh.us/auditor/',
            'refresh_hours': 24
        },
        'columbus_permits': {
            'name': 'Columbus Building Permits',
            'type': DataSourceType.BUILDING_PERMITS,
            'url': 'https://columbus.gov/permits',
            'refresh_hours': 48
        },
        'ohio_foreclosures': {
            'name': 'Ohio Foreclosure Filings',
            'type': DataSourceType.FORECLOSURE,
            'url': 'https://www.ohioforeclosures.com',
            'refresh_hours': 24
        }
    }
    
    def __init__(self, storage_path: str = "data/prospecting"):
        self.storage_path = storage_path
        self.sources: Dict[str, DataSource] = {}
        self.records: Dict[str, RawRecord] = {}
        self.collectors: Dict[DataSourceType, Callable] = {}
        self._running = False
        self._thread = None
        
        os.makedirs(storage_path, exist_ok=True)
        self._load_data()
        self._init_default_sources()
    
    def _load_data(self):
        """Load sources and records from storage."""
        sources_file = f"{self.storage_path}/sources.json"
        if os.path.exists(sources_file):
            with open(sources_file, 'r') as f:
                data = json.load(f)
                for s in data:
                    source = DataSource(
                        id=s['id'],
                        name=s['name'],
                        source_type=DataSourceType(s['source_type']),
                        url=s.get('url', ''),
                        enabled=s.get('enabled', True),
                        refresh_hours=s.get('refresh_hours', 24),
                        last_refresh=datetime.fromisoformat(s['last_refresh']) if s.get('last_refresh') else None,
                        config=s.get('config', {})
                    )
                    self.sources[source.id] = source
        
        records_file = f"{self.storage_path}/raw_records.json"
        if os.path.exists(records_file):
            with open(records_file, 'r') as f:
                data = json.load(f)
                for r in data[-50000:]:  # Keep last 50k
                    record = RawRecord(
                        id=r['id'],
                        source_id=r['source_id'],
                        source_type=DataSourceType(r['source_type']),
                        data=r['data'],
                        address=r.get('address', ''),
                        owner_name=r.get('owner_name', ''),
                        collected_at=datetime.fromisoformat(r['collected_at']),
                        processed=r.get('processed', False)
                    )
                    self.records[record.id] = record
    
    def _save_data(self):
        """Save sources and records to storage."""
        sources_data = [
            {
                'id': s.id,
                'name': s.name,
                'source_type': s.source_type.value,
                'url': s.url,
                'enabled': s.enabled,
                'refresh_hours': s.refresh_hours,
                'last_refresh': s.last_refresh.isoformat() if s.last_refresh else None,
                'config': s.config
            }
            for s in self.sources.values()
        ]
        
        with open(f"{self.storage_path}/sources.json", 'w') as f:
            json.dump(sources_data, f, indent=2)
        
        records_data = [
            {
                'id': r.id,
                'source_id': r.source_id,
                'source_type': r.source_type.value,
                'data': r.data,
                'address': r.address,
                'owner_name': r.owner_name,
                'collected_at': r.collected_at.isoformat(),
                'processed': r.processed
            }
            for r in list(self.records.values())[-50000:]
        ]
        
        with open(f"{self.storage_path}/raw_records.json", 'w') as f:
            json.dump(records_data, f, indent=2)
    
    def _init_default_sources(self):
        """Initialize default Ohio data sources."""
        for source_id, config in self.OHIO_SOURCES.items():
            if source_id not in self.sources:
                self.sources[source_id] = DataSource(
                    id=source_id,
                    name=config['name'],
                    source_type=config['type'],
                    url=config['url'],
                    refresh_hours=config['refresh_hours']
                )
        self._save_data()
    
    def register_collector(self, source_type: DataSourceType, collector: Callable):
        """Register a collector function for a source type."""
        self.collectors[source_type] = collector
    
    def add_source(self, source: DataSource):
        """Add a new data source."""
        self.sources[source.id] = source
        self._save_data()
    
    def add_record(self, record: RawRecord) -> bool:
        """Add a raw record, checking for duplicates."""
        # Generate unique ID based on content
        content_hash = hashlib.md5(
            json.dumps(record.data, sort_keys=True).encode()
        ).hexdigest()[:12]
        
        record.id = f"{record.source_type.value}_{content_hash}"
        
        # Check for duplicate
        if record.id in self.records:
            return False
        
        self.records[record.id] = record
        return True
    
    def collect_from_source(self, source_id: str) -> List[RawRecord]:
        """Collect data from a specific source."""
        source = self.sources.get(source_id)
        if not source or not source.enabled:
            return []
        
        collector = self.collectors.get(source.source_type)
        if not collector:
            return []
        
        try:
            records = collector(source)
            added = []
            for record in records:
                if self.add_record(record):
                    added.append(record)
            
            source.last_refresh = datetime.now()
            self._save_data()
            
            return added
        except Exception as e:
            print(f"Error collecting from {source_id}: {e}")
            return []
    
    def collect_all(self) -> Dict[str, int]:
        """Collect from all enabled sources that need refresh."""
        results = {}
        now = datetime.now()
        
        for source_id, source in self.sources.items():
            if not source.enabled:
                continue
            
            # Check if refresh needed
            if source.last_refresh:
                hours_since = (now - source.last_refresh).total_seconds() / 3600
                if hours_since < source.refresh_hours:
                    continue
            
            records = self.collect_from_source(source_id)
            results[source_id] = len(records)
        
        return results
    
    def get_unprocessed_records(self, source_type: DataSourceType = None, limit: int = 100) -> List[RawRecord]:
        """Get unprocessed records for processing."""
        records = [r for r in self.records.values() if not r.processed]
        
        if source_type:
            records = [r for r in records if r.source_type == source_type]
        
        records.sort(key=lambda r: r.collected_at, reverse=True)
        return records[:limit]
    
    def mark_processed(self, record_ids: List[str]):
        """Mark records as processed."""
        for rid in record_ids:
            if rid in self.records:
                self.records[rid].processed = True
        self._save_data()
    
    def get_records_by_address(self, address: str) -> List[RawRecord]:
        """Get all records for an address."""
        address_lower = address.lower()
        return [r for r in self.records.values() if address_lower in r.address.lower()]
    
    def get_records_by_owner(self, owner_name: str) -> List[RawRecord]:
        """Get all records for an owner."""
        name_lower = owner_name.lower()
        return [r for r in self.records.values() if name_lower in r.owner_name.lower()]
    
    def start_background_collection(self, interval_minutes: int = 60):
        """Start background data collection."""
        if self._running:
            return
        
        self._running = True
        
        def collection_loop():
            while self._running:
                self.collect_all()
                time.sleep(interval_minutes * 60)
        
        self._thread = threading.Thread(target=collection_loop, daemon=True)
        self._thread.start()
    
    def stop_background_collection(self):
        """Stop background collection."""
        self._running = False
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about collected data."""
        by_type = {}
        for source_type in DataSourceType:
            records = [r for r in self.records.values() if r.source_type == source_type]
            by_type[source_type.value] = {
                'total': len(records),
                'unprocessed': len([r for r in records if not r.processed])
            }
        
        return {
            'total_records': len(self.records),
            'unprocessed': len([r for r in self.records.values() if not r.processed]),
            'sources': len(self.sources),
            'enabled_sources': len([s for s in self.sources.values() if s.enabled]),
            'by_type': by_type
        }
