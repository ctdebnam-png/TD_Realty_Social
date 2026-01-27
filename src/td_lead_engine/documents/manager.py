"""Document management for real estate transactions."""

import json
import logging
import hashlib
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Document types in real estate transactions."""
    # Listing documents
    LISTING_AGREEMENT = "listing_agreement"
    SELLER_DISCLOSURE = "seller_disclosure"
    LEAD_PAINT = "lead_paint_disclosure"
    PROPERTY_PHOTOS = "property_photos"

    # Purchase documents
    PURCHASE_AGREEMENT = "purchase_agreement"
    COUNTER_OFFER = "counter_offer"
    ADDENDUM = "addendum"
    BUYER_AGENCY = "buyer_agency_agreement"

    # Inspection documents
    INSPECTION_REPORT = "inspection_report"
    INSPECTION_RESPONSE = "inspection_response"
    REPAIR_RECEIPT = "repair_receipt"

    # Financing documents
    PRE_APPROVAL = "pre_approval_letter"
    COMMITMENT_LETTER = "commitment_letter"
    APPRAISAL = "appraisal_report"

    # Title documents
    TITLE_COMMITMENT = "title_commitment"
    SURVEY = "survey"
    HOA_DOCS = "hoa_documents"

    # Closing documents
    CLOSING_DISCLOSURE = "closing_disclosure"
    DEED = "deed"
    SETTLEMENT_STATEMENT = "settlement_statement"

    # Other
    OTHER = "other"
    ID_VERIFICATION = "id_verification"
    TAX_RECORDS = "tax_records"


class DocumentStatus(Enum):
    """Document status."""
    DRAFT = "draft"
    PENDING_SIGNATURE = "pending_signature"
    PARTIALLY_SIGNED = "partially_signed"
    FULLY_SIGNED = "fully_signed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    ARCHIVED = "archived"


@dataclass
class DocumentVersion:
    """Version of a document."""
    version: int
    file_hash: str
    uploaded_at: datetime
    uploaded_by: str
    notes: str = ""


@dataclass
class Document:
    """Document in the system."""

    id: str
    transaction_id: str
    doc_type: DocumentType
    name: str
    file_path: str

    # Metadata
    status: DocumentStatus = DocumentStatus.DRAFT
    file_size: int = 0
    file_hash: str = ""
    mime_type: str = "application/pdf"

    # Parties
    uploaded_by: str = ""  # Client ID or agent
    required_signers: List[str] = field(default_factory=list)
    signed_by: List[str] = field(default_factory=list)

    # Tracking
    versions: List[DocumentVersion] = field(default_factory=list)
    current_version: int = 1

    # Dates
    uploaded_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Notes
    description: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)


class DocumentManager:
    """Manage transaction documents."""

    def __init__(self, data_path: Optional[Path] = None, storage_path: Optional[Path] = None):
        """Initialize document manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "documents.json"
        self.storage_path = storage_path or Path.home() / ".td-lead-engine" / "document_storage"
        self.documents: Dict[str, List[Document]] = {}  # By transaction_id
        self._load_data()

    def _load_data(self):
        """Load document records."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for txn_id, docs in data.get("documents", {}).items():
                        self.documents[txn_id] = [
                            Document(
                                id=d["id"],
                                transaction_id=d["transaction_id"],
                                doc_type=DocumentType(d["doc_type"]),
                                name=d["name"],
                                file_path=d["file_path"],
                                status=DocumentStatus(d.get("status", "draft")),
                                file_size=d.get("file_size", 0),
                                file_hash=d.get("file_hash", ""),
                                uploaded_by=d.get("uploaded_by", ""),
                                required_signers=d.get("required_signers", []),
                                signed_by=d.get("signed_by", []),
                                current_version=d.get("current_version", 1),
                                uploaded_at=datetime.fromisoformat(d["uploaded_at"]),
                                due_date=datetime.fromisoformat(d["due_date"]) if d.get("due_date") else None,
                                description=d.get("description", ""),
                                tags=d.get("tags", [])
                            )
                            for d in docs
                        ]

            except Exception as e:
                logger.error(f"Error loading documents: {e}")

    def _save_data(self):
        """Save document records."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "documents": {
                txn_id: [
                    {
                        "id": d.id,
                        "transaction_id": d.transaction_id,
                        "doc_type": d.doc_type.value,
                        "name": d.name,
                        "file_path": d.file_path,
                        "status": d.status.value,
                        "file_size": d.file_size,
                        "file_hash": d.file_hash,
                        "uploaded_by": d.uploaded_by,
                        "required_signers": d.required_signers,
                        "signed_by": d.signed_by,
                        "current_version": d.current_version,
                        "uploaded_at": d.uploaded_at.isoformat(),
                        "due_date": d.due_date.isoformat() if d.due_date else None,
                        "description": d.description,
                        "tags": d.tags
                    }
                    for d in docs
                ]
                for txn_id, docs in self.documents.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def upload_document(
        self,
        transaction_id: str,
        doc_type: DocumentType,
        name: str,
        source_path: str,
        uploaded_by: str,
        description: str = "",
        required_signers: List[str] = None,
        due_date: Optional[datetime] = None,
        tags: List[str] = None
    ) -> Document:
        """Upload a document to the system."""
        source = Path(source_path)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Create storage directory
        txn_storage = self.storage_path / transaction_id
        txn_storage.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        doc_id = str(uuid.uuid4())[:8]
        file_ext = source.suffix
        stored_name = f"{doc_id}_{doc_type.value}{file_ext}"
        dest_path = txn_storage / stored_name

        # Copy file to storage
        shutil.copy2(source, dest_path)

        # Compute file hash
        file_hash = self._compute_file_hash(dest_path)
        file_size = dest_path.stat().st_size

        # Create document record
        document = Document(
            id=doc_id,
            transaction_id=transaction_id,
            doc_type=doc_type,
            name=name,
            file_path=str(dest_path),
            file_size=file_size,
            file_hash=file_hash,
            uploaded_by=uploaded_by,
            required_signers=required_signers or [],
            description=description,
            due_date=due_date,
            tags=tags or []
        )

        # Add version record
        document.versions.append(DocumentVersion(
            version=1,
            file_hash=file_hash,
            uploaded_at=datetime.now(),
            uploaded_by=uploaded_by,
            notes="Initial upload"
        ))

        # If signers required, set status
        if required_signers:
            document.status = DocumentStatus.PENDING_SIGNATURE

        # Store
        if transaction_id not in self.documents:
            self.documents[transaction_id] = []
        self.documents[transaction_id].append(document)
        self._save_data()

        return document

    def upload_new_version(
        self,
        transaction_id: str,
        document_id: str,
        source_path: str,
        uploaded_by: str,
        notes: str = ""
    ) -> bool:
        """Upload a new version of an existing document."""
        docs = self.documents.get(transaction_id, [])

        for doc in docs:
            if doc.id == document_id:
                source = Path(source_path)
                if not source.exists():
                    return False

                # Copy new version
                txn_storage = self.storage_path / transaction_id
                new_version = doc.current_version + 1
                file_ext = source.suffix
                stored_name = f"{doc.id}_v{new_version}_{doc.doc_type.value}{file_ext}"
                dest_path = txn_storage / stored_name

                shutil.copy2(source, dest_path)

                # Update document
                doc.file_path = str(dest_path)
                doc.file_hash = self._compute_file_hash(dest_path)
                doc.file_size = dest_path.stat().st_size
                doc.current_version = new_version
                doc.uploaded_at = datetime.now()

                doc.versions.append(DocumentVersion(
                    version=new_version,
                    file_hash=doc.file_hash,
                    uploaded_at=datetime.now(),
                    uploaded_by=uploaded_by,
                    notes=notes
                ))

                # Reset signatures for new version
                doc.signed_by = []
                if doc.required_signers:
                    doc.status = DocumentStatus.PENDING_SIGNATURE
                else:
                    doc.status = DocumentStatus.DRAFT

                self._save_data()
                return True

        return False

    def record_signature(
        self,
        transaction_id: str,
        document_id: str,
        signer_id: str
    ) -> bool:
        """Record that someone has signed a document."""
        docs = self.documents.get(transaction_id, [])

        for doc in docs:
            if doc.id == document_id:
                if signer_id not in doc.signed_by:
                    doc.signed_by.append(signer_id)

                    # Check if fully signed
                    if set(doc.required_signers) <= set(doc.signed_by):
                        doc.status = DocumentStatus.FULLY_SIGNED
                        doc.completed_at = datetime.now()
                    else:
                        doc.status = DocumentStatus.PARTIALLY_SIGNED

                    self._save_data()
                return True

        return False

    def update_status(
        self,
        transaction_id: str,
        document_id: str,
        status: DocumentStatus,
        notes: str = ""
    ) -> bool:
        """Update document status."""
        docs = self.documents.get(transaction_id, [])

        for doc in docs:
            if doc.id == document_id:
                doc.status = status
                if notes:
                    doc.notes = notes
                if status == DocumentStatus.APPROVED:
                    doc.completed_at = datetime.now()
                self._save_data()
                return True

        return False

    def get_transaction_documents(self, transaction_id: str) -> List[Document]:
        """Get all documents for a transaction."""
        return self.documents.get(transaction_id, [])

    def get_documents_by_type(self, transaction_id: str, doc_type: DocumentType) -> List[Document]:
        """Get documents of a specific type."""
        docs = self.documents.get(transaction_id, [])
        return [d for d in docs if d.doc_type == doc_type]

    def get_pending_signatures(self, transaction_id: str, signer_id: str) -> List[Document]:
        """Get documents pending signature from a specific party."""
        docs = self.documents.get(transaction_id, [])
        return [
            d for d in docs
            if d.status in [DocumentStatus.PENDING_SIGNATURE, DocumentStatus.PARTIALLY_SIGNED]
            and signer_id in d.required_signers
            and signer_id not in d.signed_by
        ]

    def get_missing_documents(self, transaction_id: str, required_types: List[DocumentType]) -> List[DocumentType]:
        """Get required document types that are missing."""
        docs = self.documents.get(transaction_id, [])
        existing_types = {d.doc_type for d in docs if d.status not in [DocumentStatus.REJECTED, DocumentStatus.EXPIRED]}
        return [dt for dt in required_types if dt not in existing_types]

    def get_overdue_documents(self, transaction_id: Optional[str] = None) -> List[Document]:
        """Get documents past their due date."""
        now = datetime.now()
        overdue = []

        txn_ids = [transaction_id] if transaction_id else self.documents.keys()

        for txn_id in txn_ids:
            for doc in self.documents.get(txn_id, []):
                if (doc.due_date and doc.due_date < now and
                    doc.status not in [DocumentStatus.FULLY_SIGNED, DocumentStatus.APPROVED, DocumentStatus.ARCHIVED]):
                    overdue.append(doc)

        return overdue

    def get_document_checklist(self, transaction_id: str, side: str = "buyer") -> Dict[str, Any]:
        """Get document checklist with completion status."""
        docs = self.documents.get(transaction_id, [])

        if side == "buyer":
            required = [
                DocumentType.BUYER_AGENCY,
                DocumentType.PRE_APPROVAL,
                DocumentType.PURCHASE_AGREEMENT,
                DocumentType.INSPECTION_REPORT,
                DocumentType.APPRAISAL,
                DocumentType.TITLE_COMMITMENT,
                DocumentType.CLOSING_DISCLOSURE,
            ]
        else:  # seller
            required = [
                DocumentType.LISTING_AGREEMENT,
                DocumentType.SELLER_DISCLOSURE,
                DocumentType.LEAD_PAINT,
                DocumentType.PURCHASE_AGREEMENT,
                DocumentType.TITLE_COMMITMENT,
                DocumentType.CLOSING_DISCLOSURE,
            ]

        checklist = []
        for doc_type in required:
            matching = [d for d in docs if d.doc_type == doc_type]
            if matching:
                latest = max(matching, key=lambda x: x.uploaded_at)
                checklist.append({
                    "type": doc_type.value,
                    "name": doc_type.name.replace("_", " ").title(),
                    "status": "complete" if latest.status in [DocumentStatus.FULLY_SIGNED, DocumentStatus.APPROVED] else "in_progress",
                    "document_id": latest.id,
                    "uploaded_at": latest.uploaded_at.isoformat()
                })
            else:
                checklist.append({
                    "type": doc_type.value,
                    "name": doc_type.name.replace("_", " ").title(),
                    "status": "missing",
                    "document_id": None,
                    "uploaded_at": None
                })

        complete = len([c for c in checklist if c["status"] == "complete"])
        in_progress = len([c for c in checklist if c["status"] == "in_progress"])
        missing = len([c for c in checklist if c["status"] == "missing"])

        return {
            "transaction_id": transaction_id,
            "side": side,
            "total_required": len(required),
            "complete": complete,
            "in_progress": in_progress,
            "missing": missing,
            "progress_percent": round(complete / len(required) * 100, 1) if required else 0,
            "checklist": checklist
        }

    def search_documents(
        self,
        query: str = "",
        doc_type: Optional[DocumentType] = None,
        status: Optional[DocumentStatus] = None,
        transaction_id: Optional[str] = None
    ) -> List[Document]:
        """Search documents across transactions."""
        results = []

        txn_ids = [transaction_id] if transaction_id else self.documents.keys()

        for txn_id in txn_ids:
            for doc in self.documents.get(txn_id, []):
                # Filter by type
                if doc_type and doc.doc_type != doc_type:
                    continue

                # Filter by status
                if status and doc.status != status:
                    continue

                # Filter by query
                if query:
                    query_lower = query.lower()
                    if (query_lower not in doc.name.lower() and
                        query_lower not in doc.description.lower() and
                        not any(query_lower in tag.lower() for tag in doc.tags)):
                        continue

                results.append(doc)

        return results

    def get_transaction_summary(self, transaction_id: str) -> Dict[str, Any]:
        """Get document summary for a transaction."""
        docs = self.documents.get(transaction_id, [])

        by_status = {}
        for doc in docs:
            status = doc.status.value
            by_status[status] = by_status.get(status, 0) + 1

        by_type = {}
        for doc in docs:
            doc_type = doc.doc_type.value
            by_type[doc_type] = by_type.get(doc_type, 0) + 1

        pending_signatures = [
            {
                "id": d.id,
                "name": d.name,
                "awaiting": [s for s in d.required_signers if s not in d.signed_by]
            }
            for d in docs
            if d.status in [DocumentStatus.PENDING_SIGNATURE, DocumentStatus.PARTIALLY_SIGNED]
        ]

        return {
            "transaction_id": transaction_id,
            "total_documents": len(docs),
            "by_status": by_status,
            "by_type": by_type,
            "pending_signatures": pending_signatures,
            "overdue": len(self.get_overdue_documents(transaction_id)),
            "recent_uploads": [
                {
                    "id": d.id,
                    "name": d.name,
                    "type": d.doc_type.value,
                    "uploaded_at": d.uploaded_at.isoformat()
                }
                for d in sorted(docs, key=lambda x: x.uploaded_at, reverse=True)[:5]
            ]
        }


# Standard document requirements by transaction type
BUYER_REQUIRED_DOCS = [
    DocumentType.BUYER_AGENCY,
    DocumentType.PRE_APPROVAL,
    DocumentType.PURCHASE_AGREEMENT,
    DocumentType.INSPECTION_REPORT,
    DocumentType.APPRAISAL,
    DocumentType.TITLE_COMMITMENT,
    DocumentType.CLOSING_DISCLOSURE,
]

SELLER_REQUIRED_DOCS = [
    DocumentType.LISTING_AGREEMENT,
    DocumentType.SELLER_DISCLOSURE,
    DocumentType.LEAD_PAINT,
    DocumentType.PURCHASE_AGREEMENT,
    DocumentType.TITLE_COMMITMENT,
    DocumentType.CLOSING_DISCLOSURE,
]
