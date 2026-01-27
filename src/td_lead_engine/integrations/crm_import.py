"""CRM import functionality for migrating from other systems."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json
import os
import uuid
import csv
import io


class CRMSource(Enum):
    """Supported CRM sources for import."""
    FOLLOW_UP_BOSS = "follow_up_boss"
    KVCORE = "kvcore"
    BOOMTOWN = "boomtown"
    CHIME = "chime"
    LIONDESK = "liondesk"
    WISE_AGENT = "wise_agent"
    REAL_GEEKS = "real_geeks"
    SIERRA = "sierra"
    CINC = "cinc"
    CSV = "csv"
    GENERIC = "generic"


class ImportStatus(Enum):
    """Import job status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class FieldMapping:
    """Mapping from source field to target field."""
    source_field: str
    target_field: str
    transform: str = ""  # Optional transformation rule


@dataclass
class ImportJob:
    """An import job."""
    id: str
    source: CRMSource
    status: ImportStatus = ImportStatus.PENDING
    file_path: str = ""
    total_records: int = 0
    imported_records: int = 0
    failed_records: int = 0
    duplicate_records: int = 0
    field_mappings: List[FieldMapping] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    started_at: datetime = None
    completed_at: datetime = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ImportedLead:
    """A lead imported from another CRM."""
    id: str
    import_job_id: str
    source_id: str
    source_crm: CRMSource
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    secondary_phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    lead_type: str = "buyer"
    lead_source: str = ""
    lead_status: str = ""
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    custom_fields: Dict = field(default_factory=dict)
    original_data: Dict = field(default_factory=dict)
    created_in_source: datetime = None
    imported_at: datetime = field(default_factory=datetime.now)


class CRMImporter:
    """Import leads from other CRM systems."""
    
    # Default field mappings for common CRMs
    MAPPINGS = {
        CRMSource.FOLLOW_UP_BOSS: [
            FieldMapping('firstName', 'first_name'),
            FieldMapping('lastName', 'last_name'),
            FieldMapping('email', 'email'),
            FieldMapping('phone', 'phone'),
            FieldMapping('stage', 'lead_status'),
            FieldMapping('source', 'lead_source'),
            FieldMapping('tags', 'tags'),
            FieldMapping('notes', 'notes'),
            FieldMapping('id', 'source_id'),
        ],
        CRMSource.KVCORE: [
            FieldMapping('first_name', 'first_name'),
            FieldMapping('last_name', 'last_name'),
            FieldMapping('email', 'email'),
            FieldMapping('phone_cell', 'phone'),
            FieldMapping('phone_home', 'secondary_phone'),
            FieldMapping('lead_type', 'lead_type'),
            FieldMapping('source_name', 'lead_source'),
            FieldMapping('status', 'lead_status'),
            FieldMapping('lead_id', 'source_id'),
        ],
        CRMSource.BOOMTOWN: [
            FieldMapping('First Name', 'first_name'),
            FieldMapping('Last Name', 'last_name'),
            FieldMapping('Email', 'email'),
            FieldMapping('Phone', 'phone'),
            FieldMapping('Lead Type', 'lead_type'),
            FieldMapping('Lead Source', 'lead_source'),
            FieldMapping('Status', 'lead_status'),
            FieldMapping('ID', 'source_id'),
        ],
        CRMSource.CSV: [
            FieldMapping('first_name', 'first_name'),
            FieldMapping('last_name', 'last_name'),
            FieldMapping('email', 'email'),
            FieldMapping('phone', 'phone'),
            FieldMapping('type', 'lead_type'),
            FieldMapping('source', 'lead_source'),
            FieldMapping('status', 'lead_status'),
        ],
    }
    
    def __init__(
        self,
        storage_path: str = "data/integrations/crm_import",
        on_lead_imported: Callable = None
    ):
        self.storage_path = storage_path
        self.on_lead_imported = on_lead_imported
        
        self.jobs: Dict[str, ImportJob] = {}
        self.imported_leads: Dict[str, ImportedLead] = {}
        
        self._load_data()
    
    def _load_data(self):
        """Load data from storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Load jobs
        jobs_file = f"{self.storage_path}/jobs.json"
        if os.path.exists(jobs_file):
            with open(jobs_file, 'r') as f:
                data = json.load(f)
                for j in data:
                    mappings = [
                        FieldMapping(m['source_field'], m['target_field'], m.get('transform', ''))
                        for m in j.get('field_mappings', [])
                    ]
                    job = ImportJob(
                        id=j['id'],
                        source=CRMSource(j['source']),
                        status=ImportStatus(j['status']),
                        file_path=j.get('file_path', ''),
                        total_records=j.get('total_records', 0),
                        imported_records=j.get('imported_records', 0),
                        failed_records=j.get('failed_records', 0),
                        duplicate_records=j.get('duplicate_records', 0),
                        field_mappings=mappings,
                        errors=j.get('errors', []),
                        started_at=datetime.fromisoformat(j['started_at']) if j.get('started_at') else None,
                        completed_at=datetime.fromisoformat(j['completed_at']) if j.get('completed_at') else None,
                        created_at=datetime.fromisoformat(j['created_at'])
                    )
                    self.jobs[job.id] = job
        
        # Load imported leads
        leads_file = f"{self.storage_path}/imported_leads.json"
        if os.path.exists(leads_file):
            with open(leads_file, 'r') as f:
                data = json.load(f)
                for l in data:
                    lead = ImportedLead(
                        id=l['id'],
                        import_job_id=l['import_job_id'],
                        source_id=l['source_id'],
                        source_crm=CRMSource(l['source_crm']),
                        first_name=l['first_name'],
                        last_name=l['last_name'],
                        email=l['email'],
                        phone=l.get('phone', ''),
                        secondary_phone=l.get('secondary_phone', ''),
                        address=l.get('address', ''),
                        city=l.get('city', ''),
                        state=l.get('state', ''),
                        zip_code=l.get('zip_code', ''),
                        lead_type=l.get('lead_type', 'buyer'),
                        lead_source=l.get('lead_source', ''),
                        lead_status=l.get('lead_status', ''),
                        tags=l.get('tags', []),
                        notes=l.get('notes', ''),
                        custom_fields=l.get('custom_fields', {}),
                        original_data=l.get('original_data', {}),
                        created_in_source=datetime.fromisoformat(l['created_in_source']) if l.get('created_in_source') else None,
                        imported_at=datetime.fromisoformat(l['imported_at'])
                    )
                    self.imported_leads[lead.id] = lead
    
    def _save_data(self):
        """Save data to storage."""
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Save jobs
        jobs_data = [
            {
                'id': j.id,
                'source': j.source.value,
                'status': j.status.value,
                'file_path': j.file_path,
                'total_records': j.total_records,
                'imported_records': j.imported_records,
                'failed_records': j.failed_records,
                'duplicate_records': j.duplicate_records,
                'field_mappings': [
                    {'source_field': m.source_field, 'target_field': m.target_field, 'transform': m.transform}
                    for m in j.field_mappings
                ],
                'errors': j.errors,
                'started_at': j.started_at.isoformat() if j.started_at else None,
                'completed_at': j.completed_at.isoformat() if j.completed_at else None,
                'created_at': j.created_at.isoformat()
            }
            for j in self.jobs.values()
        ]
        
        with open(f"{self.storage_path}/jobs.json", 'w') as f:
            json.dump(jobs_data, f, indent=2)
        
        # Save imported leads
        leads_data = [
            {
                'id': l.id,
                'import_job_id': l.import_job_id,
                'source_id': l.source_id,
                'source_crm': l.source_crm.value,
                'first_name': l.first_name,
                'last_name': l.last_name,
                'email': l.email,
                'phone': l.phone,
                'secondary_phone': l.secondary_phone,
                'address': l.address,
                'city': l.city,
                'state': l.state,
                'zip_code': l.zip_code,
                'lead_type': l.lead_type,
                'lead_source': l.lead_source,
                'lead_status': l.lead_status,
                'tags': l.tags,
                'notes': l.notes,
                'custom_fields': l.custom_fields,
                'original_data': l.original_data,
                'created_in_source': l.created_in_source.isoformat() if l.created_in_source else None,
                'imported_at': l.imported_at.isoformat()
            }
            for l in self.imported_leads.values()
        ]
        
        with open(f"{self.storage_path}/imported_leads.json", 'w') as f:
            json.dump(leads_data, f, indent=2)
    
    def create_import_job(
        self,
        source: CRMSource,
        file_path: str = "",
        custom_mappings: List[FieldMapping] = None
    ) -> ImportJob:
        """Create a new import job."""
        mappings = custom_mappings or self.MAPPINGS.get(source, [])
        
        job = ImportJob(
            id=str(uuid.uuid4())[:12],
            source=source,
            file_path=file_path,
            field_mappings=mappings
        )
        self.jobs[job.id] = job
        self._save_data()
        return job
    
    def import_from_csv(
        self,
        job_id: str,
        csv_content: str,
        has_header: bool = True
    ) -> Dict:
        """Import leads from CSV content."""
        job = self.jobs.get(job_id)
        if not job:
            return {'success': False, 'error': 'Job not found'}
        
        job.status = ImportStatus.IN_PROGRESS
        job.started_at = datetime.now()
        self._save_data()
        
        try:
            reader = csv.DictReader(io.StringIO(csv_content)) if has_header else csv.reader(io.StringIO(csv_content))
            
            records = list(reader)
            job.total_records = len(records)
            
            for record in records:
                try:
                    lead = self._map_record(job, record)
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing in self.imported_leads.values():
                        if existing.email == lead.email and existing.email:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        job.duplicate_records += 1
                    else:
                        self.imported_leads[lead.id] = lead
                        job.imported_records += 1
                        
                        if self.on_lead_imported:
                            self.on_lead_imported(lead)
                
                except Exception as e:
                    job.failed_records += 1
                    job.errors.append({
                        'record': str(record)[:200],
                        'error': str(e)
                    })
            
            job.status = ImportStatus.COMPLETED if job.failed_records == 0 else ImportStatus.PARTIAL
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.errors.append({'error': str(e)})
        
        self._save_data()
        
        return {
            'success': job.status != ImportStatus.FAILED,
            'total': job.total_records,
            'imported': job.imported_records,
            'duplicates': job.duplicate_records,
            'failed': job.failed_records,
            'errors': job.errors[:10]  # First 10 errors
        }
    
    def import_from_json(
        self,
        job_id: str,
        json_content: str
    ) -> Dict:
        """Import leads from JSON content."""
        job = self.jobs.get(job_id)
        if not job:
            return {'success': False, 'error': 'Job not found'}
        
        job.status = ImportStatus.IN_PROGRESS
        job.started_at = datetime.now()
        self._save_data()
        
        try:
            data = json.loads(json_content)
            records = data if isinstance(data, list) else data.get('leads', data.get('data', []))
            job.total_records = len(records)
            
            for record in records:
                try:
                    lead = self._map_record(job, record)
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing in self.imported_leads.values():
                        if existing.email == lead.email and existing.email:
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        job.duplicate_records += 1
                    else:
                        self.imported_leads[lead.id] = lead
                        job.imported_records += 1
                        
                        if self.on_lead_imported:
                            self.on_lead_imported(lead)
                
                except Exception as e:
                    job.failed_records += 1
                    job.errors.append({
                        'record': str(record)[:200],
                        'error': str(e)
                    })
            
            job.status = ImportStatus.COMPLETED if job.failed_records == 0 else ImportStatus.PARTIAL
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = ImportStatus.FAILED
            job.errors.append({'error': str(e)})
        
        self._save_data()
        
        return {
            'success': job.status != ImportStatus.FAILED,
            'total': job.total_records,
            'imported': job.imported_records,
            'duplicates': job.duplicate_records,
            'failed': job.failed_records
        }
    
    def _map_record(self, job: ImportJob, record: Dict) -> ImportedLead:
        """Map a source record to ImportedLead using field mappings."""
        mapped = {}
        
        for mapping in job.field_mappings:
            value = record.get(mapping.source_field, '')
            
            # Apply transformation if specified
            if mapping.transform == 'lowercase':
                value = str(value).lower()
            elif mapping.transform == 'uppercase':
                value = str(value).upper()
            elif mapping.transform == 'title':
                value = str(value).title()
            elif mapping.transform == 'split_comma':
                value = [v.strip() for v in str(value).split(',')] if value else []
            
            mapped[mapping.target_field] = value
        
        # Handle tags specially
        tags = mapped.get('tags', [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(',') if t.strip()]
        
        lead = ImportedLead(
            id=str(uuid.uuid4())[:12],
            import_job_id=job.id,
            source_id=mapped.get('source_id', ''),
            source_crm=job.source,
            first_name=mapped.get('first_name', ''),
            last_name=mapped.get('last_name', ''),
            email=mapped.get('email', ''),
            phone=mapped.get('phone', ''),
            secondary_phone=mapped.get('secondary_phone', ''),
            address=mapped.get('address', ''),
            city=mapped.get('city', ''),
            state=mapped.get('state', ''),
            zip_code=mapped.get('zip_code', ''),
            lead_type=mapped.get('lead_type', 'buyer'),
            lead_source=f"{job.source.value}: {mapped.get('lead_source', '')}".strip(': '),
            lead_status=mapped.get('lead_status', ''),
            tags=tags,
            notes=mapped.get('notes', ''),
            original_data=record
        )
        
        return lead
    
    def convert_to_crm_lead(self, imported_lead: ImportedLead) -> Dict:
        """Convert imported lead to CRM lead format."""
        return {
            'first_name': imported_lead.first_name,
            'last_name': imported_lead.last_name,
            'email': imported_lead.email,
            'phone': imported_lead.phone,
            'secondary_phone': imported_lead.secondary_phone,
            'address': imported_lead.address,
            'city': imported_lead.city,
            'state': imported_lead.state,
            'zip_code': imported_lead.zip_code,
            'source': imported_lead.lead_source or f"Import: {imported_lead.source_crm.value}",
            'lead_type': imported_lead.lead_type,
            'status': imported_lead.lead_status,
            'tags': imported_lead.tags,
            'notes': imported_lead.notes,
            'custom_fields': {
                'imported_from': imported_lead.source_crm.value,
                'original_id': imported_lead.source_id,
                'import_job_id': imported_lead.import_job_id,
                **imported_lead.custom_fields
            }
        }
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get import job status."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            'id': job.id,
            'source': job.source.value,
            'status': job.status.value,
            'total_records': job.total_records,
            'imported_records': job.imported_records,
            'failed_records': job.failed_records,
            'duplicate_records': job.duplicate_records,
            'progress': (job.imported_records + job.failed_records + job.duplicate_records) / job.total_records * 100 if job.total_records else 0,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'errors': job.errors[:10]
        }
    
    def get_imported_leads(self, job_id: str = None) -> List[ImportedLead]:
        """Get imported leads, optionally filtered by job."""
        leads = list(self.imported_leads.values())
        if job_id:
            leads = [l for l in leads if l.import_job_id == job_id]
        return leads
    
    def get_import_stats(self) -> Dict:
        """Get overall import statistics."""
        total_jobs = len(self.jobs)
        total_leads = len(self.imported_leads)
        
        by_source = {}
        for source in CRMSource:
            by_source[source.value] = len([l for l in self.imported_leads.values() if l.source_crm == source])
        
        return {
            'total_jobs': total_jobs,
            'total_leads': total_leads,
            'by_source': by_source,
            'completed_jobs': len([j for j in self.jobs.values() if j.status == ImportStatus.COMPLETED]),
            'failed_jobs': len([j for j in self.jobs.values() if j.status == ImportStatus.FAILED])
        }
