"""Property synchronization from MLS."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json
import os
import threading
import time

from .client import MLSClient, Property, PropertyStatus


class SyncStatus(Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SyncJob:
    """A sync job record."""
    id: str
    started_at: datetime
    completed_at: datetime = None
    status: SyncStatus = SyncStatus.PENDING
    properties_added: int = 0
    properties_updated: int = 0
    properties_removed: int = 0
    errors: List[str] = field(default_factory=list)


@dataclass
class SyncRule:
    """Rule for automatic syncing."""
    id: str
    name: str
    enabled: bool = True
    criteria: Dict = field(default_factory=dict)
    schedule_minutes: int = 60  # Sync interval
    last_sync: datetime = None
    

class PropertySync:
    """Synchronize properties from MLS."""
    
    def __init__(
        self,
        mls_client: MLSClient,
        storage_path: str = "data/sync"
    ):
        self.mls_client = mls_client
        self.storage_path = storage_path
        self.sync_jobs: List[SyncJob] = []
        self.sync_rules: Dict[str, SyncRule] = {}
        self.listeners: List[Callable] = []
        self._sync_thread: Optional[threading.Thread] = None
        self._running = False
        
        self._load_data()
    
    def _load_data(self):
        """Load sync data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load sync rules
        rules_file = f"{self.storage_path}/sync_rules.json"
        if os.path.exists(rules_file):
            with open(rules_file, 'r') as f:
                data = json.load(f)
                for rule_data in data:
                    rule = SyncRule(
                        id=rule_data['id'],
                        name=rule_data['name'],
                        enabled=rule_data.get('enabled', True),
                        criteria=rule_data.get('criteria', {}),
                        schedule_minutes=rule_data.get('schedule_minutes', 60),
                        last_sync=datetime.fromisoformat(rule_data['last_sync']) if rule_data.get('last_sync') else None
                    )
                    self.sync_rules[rule.id] = rule
        
        # Load recent sync jobs
        jobs_file = f"{self.storage_path}/sync_jobs.json"
        if os.path.exists(jobs_file):
            with open(jobs_file, 'r') as f:
                data = json.load(f)
                for job_data in data[-100:]:  # Keep last 100
                    job = SyncJob(
                        id=job_data['id'],
                        started_at=datetime.fromisoformat(job_data['started_at']),
                        completed_at=datetime.fromisoformat(job_data['completed_at']) if job_data.get('completed_at') else None,
                        status=SyncStatus(job_data.get('status', 'pending')),
                        properties_added=job_data.get('properties_added', 0),
                        properties_updated=job_data.get('properties_updated', 0),
                        properties_removed=job_data.get('properties_removed', 0),
                        errors=job_data.get('errors', [])
                    )
                    self.sync_jobs.append(job)
    
    def _save_data(self):
        """Save sync data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save sync rules
        rules_data = [
            {
                'id': r.id,
                'name': r.name,
                'enabled': r.enabled,
                'criteria': r.criteria,
                'schedule_minutes': r.schedule_minutes,
                'last_sync': r.last_sync.isoformat() if r.last_sync else None
            }
            for r in self.sync_rules.values()
        ]
        with open(f"{self.storage_path}/sync_rules.json", 'w') as f:
            json.dump(rules_data, f, indent=2)
        
        # Save sync jobs (last 100)
        jobs_data = [
            {
                'id': j.id,
                'started_at': j.started_at.isoformat(),
                'completed_at': j.completed_at.isoformat() if j.completed_at else None,
                'status': j.status.value,
                'properties_added': j.properties_added,
                'properties_updated': j.properties_updated,
                'properties_removed': j.properties_removed,
                'errors': j.errors
            }
            for j in self.sync_jobs[-100:]
        ]
        with open(f"{self.storage_path}/sync_jobs.json", 'w') as f:
            json.dump(jobs_data, f, indent=2)
    
    def add_listener(self, callback: Callable):
        """Add a listener for sync events."""
        self.listeners.append(callback)
    
    def _notify_listeners(self, event: str, data: Dict):
        """Notify all listeners of an event."""
        for listener in self.listeners:
            try:
                listener(event, data)
            except Exception:
                pass
    
    def create_sync_rule(
        self,
        name: str,
        criteria: Dict,
        schedule_minutes: int = 60
    ) -> SyncRule:
        """Create a new sync rule."""
        import uuid
        rule = SyncRule(
            id=str(uuid.uuid4())[:8],
            name=name,
            criteria=criteria,
            schedule_minutes=schedule_minutes
        )
        self.sync_rules[rule.id] = rule
        self._save_data()
        return rule
    
    def update_sync_rule(self, rule_id: str, updates: Dict) -> Optional[SyncRule]:
        """Update a sync rule."""
        if rule_id not in self.sync_rules:
            return None
        
        rule = self.sync_rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        self._save_data()
        return rule
    
    def delete_sync_rule(self, rule_id: str) -> bool:
        """Delete a sync rule."""
        if rule_id in self.sync_rules:
            del self.sync_rules[rule_id]
            self._save_data()
            return True
        return False
    
    def sync_now(self, criteria: Dict = None) -> SyncJob:
        """Run immediate sync with optional criteria."""
        import uuid
        
        job = SyncJob(
            id=str(uuid.uuid4())[:8],
            started_at=datetime.now(),
            status=SyncStatus.RUNNING
        )
        self.sync_jobs.append(job)
        
        try:
            # Get current property IDs
            existing_ids = set(self.mls_client.properties.keys())
            
            # Search MLS with criteria
            search_criteria = criteria or {'status': 'active', 'limit': 1000}
            results = self.mls_client.search(**search_criteria)
            
            new_ids = set()
            for prop in results:
                new_ids.add(prop.mls_id)
                
                if prop.mls_id in existing_ids:
                    # Check if property was updated
                    existing = self.mls_client.properties[prop.mls_id]
                    if prop.last_modified and existing.last_modified:
                        if prop.last_modified > existing.last_modified:
                            self.mls_client.properties[prop.mls_id] = prop
                            job.properties_updated += 1
                            self._notify_listeners('property_updated', {'property': prop})
                else:
                    # New property
                    self.mls_client.properties[prop.mls_id] = prop
                    job.properties_added += 1
                    self._notify_listeners('property_added', {'property': prop})
            
            # Check for removed properties (status change)
            for mls_id in existing_ids - new_ids:
                existing = self.mls_client.properties.get(mls_id)
                if existing and existing.status == PropertyStatus.ACTIVE:
                    # Mark as potentially sold/expired
                    job.properties_removed += 1
                    self._notify_listeners('property_removed', {'mls_id': mls_id})
            
            job.status = SyncStatus.COMPLETED
            
        except Exception as e:
            job.status = SyncStatus.FAILED
            job.errors.append(str(e))
        
        job.completed_at = datetime.now()
        self._save_data()
        
        self._notify_listeners('sync_completed', {
            'job_id': job.id,
            'added': job.properties_added,
            'updated': job.properties_updated,
            'removed': job.properties_removed
        })
        
        return job
    
    def sync_rule(self, rule_id: str) -> Optional[SyncJob]:
        """Run sync for a specific rule."""
        if rule_id not in self.sync_rules:
            return None
        
        rule = self.sync_rules[rule_id]
        job = self.sync_now(rule.criteria)
        
        rule.last_sync = datetime.now()
        self._save_data()
        
        return job
    
    def start_background_sync(self):
        """Start background sync thread."""
        if self._running:
            return
        
        self._running = True
        self._sync_thread = threading.Thread(target=self._background_sync_loop, daemon=True)
        self._sync_thread.start()
    
    def stop_background_sync(self):
        """Stop background sync thread."""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
    
    def _background_sync_loop(self):
        """Background sync loop."""
        while self._running:
            try:
                for rule in self.sync_rules.values():
                    if not rule.enabled:
                        continue
                    
                    # Check if sync is due
                    if rule.last_sync is None:
                        self.sync_rule(rule.id)
                    elif (datetime.now() - rule.last_sync).total_seconds() > rule.schedule_minutes * 60:
                        self.sync_rule(rule.id)
                
                # Check every minute
                time.sleep(60)
                
            except Exception:
                time.sleep(60)
    
    def get_sync_history(self, limit: int = 20) -> List[SyncJob]:
        """Get recent sync history."""
        return self.sync_jobs[-limit:]
    
    def get_sync_stats(self) -> Dict:
        """Get sync statistics."""
        if not self.sync_jobs:
            return {}
        
        recent = [j for j in self.sync_jobs if j.completed_at and 
                  (datetime.now() - j.completed_at).days <= 7]
        
        successful = [j for j in recent if j.status == SyncStatus.COMPLETED]
        failed = [j for j in recent if j.status == SyncStatus.FAILED]
        
        return {
            'total_syncs_7_days': len(recent),
            'successful_syncs': len(successful),
            'failed_syncs': len(failed),
            'success_rate': (len(successful) / len(recent) * 100) if recent else 0,
            'total_added': sum(j.properties_added for j in successful),
            'total_updated': sum(j.properties_updated for j in successful),
            'total_removed': sum(j.properties_removed for j in successful),
            'last_sync': self.sync_jobs[-1].completed_at.isoformat() if self.sync_jobs else None
        }
    
    def detect_changes(self, days: int = 1) -> Dict:
        """Detect property changes in the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        new_listings = []
        price_changes = []
        status_changes = []
        
        for prop in self.mls_client.properties.values():
            # New listings
            if prop.list_date and prop.list_date > cutoff:
                new_listings.append(prop)
            
            # Price changes
            if prop.original_price and prop.list_price != prop.original_price:
                if prop.last_modified and prop.last_modified > cutoff:
                    price_changes.append({
                        'property': prop,
                        'original_price': prop.original_price,
                        'new_price': prop.list_price,
                        'change_pct': ((prop.list_price - prop.original_price) / prop.original_price) * 100
                    })
            
            # Status changes (would need historical data)
            if prop.status in [PropertyStatus.PENDING, PropertyStatus.SOLD]:
                if prop.pending_date and prop.pending_date > cutoff:
                    status_changes.append({
                        'property': prop,
                        'new_status': prop.status.value
                    })
        
        return {
            'new_listings': new_listings,
            'price_changes': price_changes,
            'status_changes': status_changes,
            'summary': {
                'new_listings_count': len(new_listings),
                'price_increases': len([p for p in price_changes if p['change_pct'] > 0]),
                'price_decreases': len([p for p in price_changes if p['change_pct'] < 0]),
                'went_pending': len([s for s in status_changes if s['new_status'] == 'pending']),
                'sold': len([s for s in status_changes if s['new_status'] == 'sold'])
            }
        }
