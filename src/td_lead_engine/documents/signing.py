"""Electronic signature integration."""

import json
import logging
import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class SignatureStatus(Enum):
    """Signature request status."""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PARTIALLY_SIGNED = "partially_signed"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    EXPIRED = "expired"


class SignerStatus(Enum):
    """Individual signer status."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    VIEWED = "viewed"
    SIGNED = "signed"
    DECLINED = "declined"


@dataclass
class Signer:
    """Person who needs to sign."""

    id: str
    name: str
    email: str
    role: str  # "buyer", "seller", "agent", "broker", etc.

    # Status
    status: SignerStatus = SignerStatus.PENDING
    signed_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None

    # Signature details
    ip_address: str = ""
    signature_data: str = ""  # Base64 signature image or hash

    # Order
    signing_order: int = 1


@dataclass
class SignatureRequest:
    """Request for electronic signatures."""

    id: str
    document_id: str
    transaction_id: str
    document_name: str

    # Signers
    signers: List[Signer] = field(default_factory=list)

    # Status
    status: SignatureStatus = SignatureStatus.DRAFT

    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Options
    message: str = ""  # Email message to signers
    reminder_frequency: int = 3  # Days between reminders
    sequential_signing: bool = False  # Must sign in order

    # Audit trail
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)


class SignatureManager:
    """Manage electronic signatures."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize signature manager."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "signatures.json"
        self.requests: Dict[str, SignatureRequest] = {}  # By request_id
        self._load_data()

        # Integration settings (would be configured with actual API keys)
        self.provider = "internal"  # "docusign", "dotloop", "skyslope", "internal"
        self.api_key = ""
        self.webhook_secret = ""

    def _load_data(self):
        """Load signature data."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for req_id, req_data in data.get("requests", {}).items():
                        signers = [
                            Signer(
                                id=s["id"],
                                name=s["name"],
                                email=s["email"],
                                role=s["role"],
                                status=SignerStatus(s.get("status", "pending")),
                                signed_at=datetime.fromisoformat(s["signed_at"]) if s.get("signed_at") else None,
                                signing_order=s.get("signing_order", 1)
                            )
                            for s in req_data.get("signers", [])
                        ]

                        self.requests[req_id] = SignatureRequest(
                            id=req_data["id"],
                            document_id=req_data["document_id"],
                            transaction_id=req_data["transaction_id"],
                            document_name=req_data["document_name"],
                            signers=signers,
                            status=SignatureStatus(req_data.get("status", "draft")),
                            created_at=datetime.fromisoformat(req_data["created_at"]),
                            sent_at=datetime.fromisoformat(req_data["sent_at"]) if req_data.get("sent_at") else None,
                            completed_at=datetime.fromisoformat(req_data["completed_at"]) if req_data.get("completed_at") else None,
                            message=req_data.get("message", ""),
                            sequential_signing=req_data.get("sequential_signing", False),
                            audit_trail=req_data.get("audit_trail", [])
                        )

            except Exception as e:
                logger.error(f"Error loading signature data: {e}")

    def _save_data(self):
        """Save signature data."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "requests": {
                req_id: {
                    "id": req.id,
                    "document_id": req.document_id,
                    "transaction_id": req.transaction_id,
                    "document_name": req.document_name,
                    "signers": [
                        {
                            "id": s.id,
                            "name": s.name,
                            "email": s.email,
                            "role": s.role,
                            "status": s.status.value,
                            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
                            "signing_order": s.signing_order
                        }
                        for s in req.signers
                    ],
                    "status": req.status.value,
                    "created_at": req.created_at.isoformat(),
                    "sent_at": req.sent_at.isoformat() if req.sent_at else None,
                    "completed_at": req.completed_at.isoformat() if req.completed_at else None,
                    "message": req.message,
                    "sequential_signing": req.sequential_signing,
                    "audit_trail": req.audit_trail
                }
                for req_id, req in self.requests.items()
            },
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _add_audit_entry(self, request: SignatureRequest, action: str, details: str = "", actor: str = ""):
        """Add entry to audit trail."""
        request.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "actor": actor
        })

    def create_signature_request(
        self,
        document_id: str,
        transaction_id: str,
        document_name: str,
        signers: List[Dict[str, Any]],
        message: str = "",
        sequential: bool = False,
        expires_days: int = 14
    ) -> SignatureRequest:
        """Create a new signature request."""
        request_id = str(uuid.uuid4())[:8]

        signer_objects = [
            Signer(
                id=str(uuid.uuid4())[:8],
                name=s["name"],
                email=s["email"],
                role=s.get("role", "signer"),
                signing_order=s.get("order", i + 1)
            )
            for i, s in enumerate(signers)
        ]

        request = SignatureRequest(
            id=request_id,
            document_id=document_id,
            transaction_id=transaction_id,
            document_name=document_name,
            signers=signer_objects,
            message=message,
            sequential_signing=sequential,
            expires_at=datetime.now() + timedelta(days=expires_days)
        )

        self._add_audit_entry(request, "created", f"Request created with {len(signers)} signers")
        self.requests[request_id] = request
        self._save_data()

        return request

    def send_for_signature(self, request_id: str) -> bool:
        """Send document for signatures."""
        request = self.requests.get(request_id)
        if not request:
            return False

        # In real implementation, this would integrate with e-signature provider
        request.status = SignatureStatus.SENT
        request.sent_at = datetime.now()

        # Update signer statuses
        for signer in request.signers:
            signer.status = SignerStatus.SENT

        self._add_audit_entry(request, "sent", "Document sent for signatures")

        # Simulate sending emails (in production, use actual email/API)
        for signer in request.signers:
            logger.info(f"Sending signature request to {signer.email} for {request.document_name}")

        self._save_data()
        return True

    def record_view(self, request_id: str, signer_email: str) -> bool:
        """Record that a signer viewed the document."""
        request = self.requests.get(request_id)
        if not request:
            return False

        for signer in request.signers:
            if signer.email == signer_email:
                signer.status = SignerStatus.VIEWED
                signer.viewed_at = datetime.now()
                self._add_audit_entry(request, "viewed", f"Document viewed", signer.name)

                if request.status == SignatureStatus.SENT:
                    request.status = SignatureStatus.VIEWED

                self._save_data()
                return True

        return False

    def record_signature(
        self,
        request_id: str,
        signer_email: str,
        ip_address: str = "",
        signature_data: str = ""
    ) -> bool:
        """Record that a signer has signed."""
        request = self.requests.get(request_id)
        if not request:
            return False

        for signer in request.signers:
            if signer.email == signer_email:
                signer.status = SignerStatus.SIGNED
                signer.signed_at = datetime.now()
                signer.ip_address = ip_address
                signer.signature_data = signature_data

                self._add_audit_entry(
                    request,
                    "signed",
                    f"Document signed from IP {ip_address}",
                    signer.name
                )

                # Check if all signed
                all_signed = all(s.status == SignerStatus.SIGNED for s in request.signers)
                if all_signed:
                    request.status = SignatureStatus.COMPLETED
                    request.completed_at = datetime.now()
                    self._add_audit_entry(request, "completed", "All signatures collected")
                else:
                    request.status = SignatureStatus.PARTIALLY_SIGNED

                self._save_data()
                return True

        return False

    def decline_signature(self, request_id: str, signer_email: str, reason: str = "") -> bool:
        """Record that a signer declined."""
        request = self.requests.get(request_id)
        if not request:
            return False

        for signer in request.signers:
            if signer.email == signer_email:
                signer.status = SignerStatus.DECLINED

                self._add_audit_entry(
                    request,
                    "declined",
                    f"Declined: {reason}",
                    signer.name
                )

                request.status = SignatureStatus.DECLINED
                self._save_data()
                return True

        return False

    def void_request(self, request_id: str, reason: str = "") -> bool:
        """Void a signature request."""
        request = self.requests.get(request_id)
        if not request:
            return False

        request.status = SignatureStatus.VOIDED
        self._add_audit_entry(request, "voided", reason)
        self._save_data()
        return True

    def send_reminder(self, request_id: str) -> bool:
        """Send reminder to pending signers."""
        request = self.requests.get(request_id)
        if not request or request.status not in [SignatureStatus.SENT, SignatureStatus.VIEWED, SignatureStatus.PARTIALLY_SIGNED]:
            return False

        pending_signers = [s for s in request.signers if s.status != SignerStatus.SIGNED]

        for signer in pending_signers:
            logger.info(f"Sending reminder to {signer.email}")
            # In production, send actual reminder email

        self._add_audit_entry(request, "reminder_sent", f"Reminder sent to {len(pending_signers)} signers")
        self._save_data()
        return True

    def get_request(self, request_id: str) -> Optional[SignatureRequest]:
        """Get a signature request."""
        return self.requests.get(request_id)

    def get_transaction_requests(self, transaction_id: str) -> List[SignatureRequest]:
        """Get all signature requests for a transaction."""
        return [r for r in self.requests.values() if r.transaction_id == transaction_id]

    def get_pending_signatures(self, signer_email: str) -> List[Dict[str, Any]]:
        """Get all pending signatures for a person."""
        pending = []

        for request in self.requests.values():
            if request.status not in [SignatureStatus.COMPLETED, SignatureStatus.VOIDED, SignatureStatus.DECLINED]:
                for signer in request.signers:
                    if signer.email == signer_email and signer.status != SignerStatus.SIGNED:
                        pending.append({
                            "request_id": request.id,
                            "document_name": request.document_name,
                            "transaction_id": request.transaction_id,
                            "status": signer.status.value,
                            "sent_at": request.sent_at.isoformat() if request.sent_at else None,
                            "expires_at": request.expires_at.isoformat() if request.expires_at else None
                        })

        return pending

    def get_audit_trail(self, request_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for a request."""
        request = self.requests.get(request_id)
        if not request:
            return []
        return request.audit_trail

    def generate_signing_link(self, request_id: str, signer_email: str) -> Optional[str]:
        """Generate a unique signing link for a signer."""
        request = self.requests.get(request_id)
        if not request:
            return None

        for signer in request.signers:
            if signer.email == signer_email:
                # Generate a secure token
                token_data = f"{request_id}:{signer.id}:{datetime.now().isoformat()}"
                token = hashlib.sha256(token_data.encode()).hexdigest()[:32]

                # In production, this would be a real URL
                return f"https://portal.tdrealty.com/sign/{request_id}/{token}"

        return None

    def verify_signing_token(self, request_id: str, token: str) -> bool:
        """Verify a signing token is valid."""
        # In production, verify against stored tokens and expiration
        return len(token) == 32 and request_id in self.requests

    def get_summary(self) -> Dict[str, Any]:
        """Get signature activity summary."""
        total = len(self.requests)
        by_status = {}

        for request in self.requests.values():
            status = request.status.value
            by_status[status] = by_status.get(status, 0) + 1

        # Recent activity
        recent = sorted(
            self.requests.values(),
            key=lambda x: x.created_at,
            reverse=True
        )[:10]

        return {
            "total_requests": total,
            "by_status": by_status,
            "pending_count": by_status.get("sent", 0) + by_status.get("viewed", 0) + by_status.get("partially_signed", 0),
            "completed_count": by_status.get("completed", 0),
            "recent": [
                {
                    "id": r.id,
                    "document": r.document_name,
                    "status": r.status.value,
                    "signers": len(r.signers),
                    "signed": len([s for s in r.signers if s.status == SignerStatus.SIGNED]),
                    "created": r.created_at.isoformat()
                }
                for r in recent
            ]
        }


class ESignatureIntegration:
    """Integration with e-signature providers."""

    def __init__(self, provider: str, api_key: str):
        """Initialize integration."""
        self.provider = provider
        self.api_key = api_key

    def send_via_docusign(self, document_path: str, signers: List[Dict]) -> Dict[str, Any]:
        """Send document via DocuSign."""
        # DocuSign API integration would go here
        logger.info(f"Would send {document_path} to DocuSign with {len(signers)} signers")
        return {"status": "sent", "provider": "docusign", "envelope_id": str(uuid.uuid4())}

    def send_via_dotloop(self, document_path: str, signers: List[Dict]) -> Dict[str, Any]:
        """Send document via DotLoop."""
        # DotLoop API integration would go here
        logger.info(f"Would send {document_path} to DotLoop with {len(signers)} signers")
        return {"status": "sent", "provider": "dotloop", "loop_id": str(uuid.uuid4())}

    def check_status(self, envelope_id: str) -> Dict[str, Any]:
        """Check status from provider."""
        # Would query provider API
        return {"status": "pending", "envelope_id": envelope_id}
