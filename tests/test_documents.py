"""Tests for document management functionality."""

import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from td_lead_engine.documents import (
    DocumentManager,
    Document,
    DocumentType,
    DocumentTemplates,
    SignatureRequest,
    SignatureStatus,
)
from td_lead_engine.documents.manager import DocumentStatus
from td_lead_engine.documents.signing import SignatureManager, SignerStatus


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def doc_manager(temp_data_dir):
    """Create document manager with temp storage."""
    return DocumentManager(
        data_path=temp_data_dir / "documents.json",
        storage_path=temp_data_dir / "storage"
    )


@pytest.fixture
def signature_manager(temp_data_dir):
    """Create signature manager with temp storage."""
    return SignatureManager(data_path=temp_data_dir / "signatures.json")


@pytest.fixture
def sample_document(temp_data_dir):
    """Create a sample document file."""
    doc_path = temp_data_dir / "sample.pdf"
    doc_path.write_text("Sample PDF content")
    return doc_path


class TestDocumentManager:
    """Tests for DocumentManager."""

    def test_upload_document(self, doc_manager, sample_document):
        """Test uploading a document."""
        doc = doc_manager.upload_document(
            transaction_id="txn123",
            doc_type=DocumentType.PURCHASE_AGREEMENT,
            name="Purchase Agreement",
            source_path=str(sample_document),
            uploaded_by="agent001",
            description="Main purchase agreement"
        )

        assert doc is not None
        assert doc.doc_type == DocumentType.PURCHASE_AGREEMENT
        assert doc.name == "Purchase Agreement"

    def test_upload_with_signers(self, doc_manager, sample_document):
        """Test uploading document requiring signatures."""
        doc = doc_manager.upload_document(
            transaction_id="txn123",
            doc_type=DocumentType.PURCHASE_AGREEMENT,
            name="Purchase Agreement",
            source_path=str(sample_document),
            uploaded_by="agent001",
            required_signers=["buyer001", "seller001"]
        )

        assert doc.status == DocumentStatus.PENDING_SIGNATURE
        assert len(doc.required_signers) == 2

    def test_record_signature(self, doc_manager, sample_document):
        """Test recording a signature."""
        doc = doc_manager.upload_document(
            transaction_id="txn123",
            doc_type=DocumentType.PURCHASE_AGREEMENT,
            name="Purchase Agreement",
            source_path=str(sample_document),
            uploaded_by="agent001",
            required_signers=["buyer001", "seller001"]
        )

        # Sign once
        result = doc_manager.record_signature("txn123", doc.id, "buyer001")
        assert result is True

        # Check status
        docs = doc_manager.get_transaction_documents("txn123")
        assert docs[0].status == DocumentStatus.PARTIALLY_SIGNED

        # Sign again
        doc_manager.record_signature("txn123", doc.id, "seller001")
        docs = doc_manager.get_transaction_documents("txn123")
        assert docs[0].status == DocumentStatus.FULLY_SIGNED

    def test_get_pending_signatures(self, doc_manager, sample_document):
        """Test getting pending signatures."""
        doc_manager.upload_document(
            transaction_id="txn123",
            doc_type=DocumentType.PURCHASE_AGREEMENT,
            name="Purchase Agreement",
            source_path=str(sample_document),
            uploaded_by="agent001",
            required_signers=["buyer001", "seller001"]
        )

        pending = doc_manager.get_pending_signatures("txn123", "buyer001")
        assert len(pending) == 1

        # After signing, should be empty
        doc_manager.record_signature("txn123", pending[0].id, "buyer001")
        pending = doc_manager.get_pending_signatures("txn123", "buyer001")
        assert len(pending) == 0

    def test_document_checklist(self, doc_manager, sample_document):
        """Test document checklist."""
        # Upload some documents
        doc_manager.upload_document(
            transaction_id="txn123",
            doc_type=DocumentType.BUYER_AGENCY,
            name="Buyer Agency",
            source_path=str(sample_document),
            uploaded_by="agent001"
        )

        checklist = doc_manager.get_document_checklist("txn123", side="buyer")

        assert checklist["total_required"] > 0
        assert "checklist" in checklist

        # Find buyer agency in checklist
        agency_item = next(
            (c for c in checklist["checklist"] if c["type"] == "buyer_agency_agreement"),
            None
        )
        assert agency_item is not None
        assert agency_item["status"] == "in_progress"


class TestDocumentTemplates:
    """Tests for DocumentTemplates."""

    def test_list_templates(self):
        """Test listing available templates."""
        templates = DocumentTemplates()
        template_list = templates.list_templates()

        assert len(template_list) > 0
        assert any(t["id"] == "buyer_agency_oh" for t in template_list)

    def test_get_template(self):
        """Test getting a specific template."""
        templates = DocumentTemplates()
        template = templates.get_template("buyer_agency_oh")

        assert template is not None
        assert template.name == "Ohio Exclusive Buyer Agency Agreement"

    def test_generate_document(self):
        """Test generating document from template."""
        templates = DocumentTemplates()

        variables = {
            "buyer_name": "John Smith",
            "buyer_address": "123 Main St, Columbus, OH",
            "buyer_phone": "555-1234",
            "buyer_email": "john@example.com",
            "agent_name": "Jane Agent",
            "broker_name": "TD Realty",
            "broker_address": "456 Broker Ave",
            "agent_phone": "555-5678",
            "commission_rate": "3",
            "start_date": "January 1, 2024",
            "end_date": "July 1, 2024",
            "property_types": "Single Family, Condo",
            "geographic_area": "Franklin County",
            "price_range": "$200,000 - $500,000"
        }

        content = templates.generate_document("buyer_agency_oh", variables)

        assert content is not None
        assert "John Smith" in content
        assert "Jane Agent" in content

    def test_validate_fields(self):
        """Test field validation."""
        templates = DocumentTemplates()

        # Missing required fields
        result = templates.validate_fields("buyer_agency_oh", {
            "buyer_name": "John"
        })

        assert result["valid"] is False
        assert len(result["missing_required"]) > 0


class TestSignatureManager:
    """Tests for SignatureManager."""

    def test_create_signature_request(self, signature_manager):
        """Test creating signature request."""
        request = signature_manager.create_signature_request(
            document_id="doc123",
            transaction_id="txn123",
            document_name="Purchase Agreement",
            signers=[
                {"name": "John Buyer", "email": "john@example.com", "role": "buyer"},
                {"name": "Jane Seller", "email": "jane@example.com", "role": "seller"}
            ],
            message="Please sign this document"
        )

        assert request is not None
        assert len(request.signers) == 2
        assert request.status == SignatureStatus.DRAFT

    def test_send_for_signature(self, signature_manager):
        """Test sending document for signatures."""
        request = signature_manager.create_signature_request(
            document_id="doc123",
            transaction_id="txn123",
            document_name="Purchase Agreement",
            signers=[
                {"name": "John Buyer", "email": "john@example.com"}
            ]
        )

        result = signature_manager.send_for_signature(request.id)
        assert result is True

        # Check status updated
        updated = signature_manager.get_request(request.id)
        assert updated.status == SignatureStatus.SENT

    def test_record_signature(self, signature_manager):
        """Test recording a signature."""
        request = signature_manager.create_signature_request(
            document_id="doc123",
            transaction_id="txn123",
            document_name="Purchase Agreement",
            signers=[
                {"name": "John Buyer", "email": "john@example.com"}
            ]
        )

        signature_manager.send_for_signature(request.id)

        result = signature_manager.record_signature(
            request.id,
            "john@example.com",
            ip_address="192.168.1.1"
        )

        assert result is True

        updated = signature_manager.get_request(request.id)
        assert updated.status == SignatureStatus.COMPLETED

    def test_get_pending_signatures_for_person(self, signature_manager):
        """Test getting pending signatures for a person."""
        signature_manager.create_signature_request(
            document_id="doc1",
            transaction_id="txn1",
            document_name="Agreement 1",
            signers=[{"name": "John", "email": "john@example.com"}]
        )

        signature_manager.create_signature_request(
            document_id="doc2",
            transaction_id="txn2",
            document_name="Agreement 2",
            signers=[{"name": "John", "email": "john@example.com"}]
        )

        # Send both
        requests = list(signature_manager.requests.values())
        for req in requests:
            signature_manager.send_for_signature(req.id)

        pending = signature_manager.get_pending_signatures("john@example.com")
        assert len(pending) == 2

    def test_audit_trail(self, signature_manager):
        """Test audit trail is maintained."""
        request = signature_manager.create_signature_request(
            document_id="doc123",
            transaction_id="txn123",
            document_name="Test Document",
            signers=[{"name": "John", "email": "john@example.com"}]
        )

        signature_manager.send_for_signature(request.id)
        signature_manager.record_view(request.id, "john@example.com")
        signature_manager.record_signature(request.id, "john@example.com")

        audit = signature_manager.get_audit_trail(request.id)

        assert len(audit) >= 4  # created, sent, viewed, signed
        actions = [entry["action"] for entry in audit]
        assert "created" in actions
        assert "sent" in actions
        assert "signed" in actions
