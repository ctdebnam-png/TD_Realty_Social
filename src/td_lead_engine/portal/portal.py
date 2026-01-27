"""Client portal management."""

import json
import logging
import secrets
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ClientType(Enum):
    """Client type."""
    BUYER = "buyer"
    SELLER = "seller"
    BOTH = "both"
    INVESTOR = "investor"


class PortalPermission(Enum):
    """Portal permissions."""
    VIEW_LISTINGS = "view_listings"
    SAVE_PROPERTIES = "save_properties"
    REQUEST_SHOWINGS = "request_showings"
    VIEW_DOCUMENTS = "view_documents"
    SIGN_DOCUMENTS = "sign_documents"
    VIEW_TRANSACTION = "view_transaction"
    MESSAGE_AGENT = "message_agent"
    VIEW_MARKET_REPORTS = "view_market_reports"


@dataclass
class ClientAccount:
    """Client portal account."""

    id: str
    lead_id: Optional[str]  # Link to lead record
    transaction_id: Optional[str]  # Link to active transaction

    # Account info
    email: str
    password_hash: str
    name: str
    phone: str = ""

    # Type and status
    client_type: ClientType = ClientType.BUYER
    is_active: bool = True
    is_verified: bool = False

    # Permissions
    permissions: List[PortalPermission] = field(default_factory=list)

    # Agent assignment
    agent_id: str = ""
    agent_name: str = ""
    agent_email: str = ""
    agent_phone: str = ""

    # Activity tracking
    last_login: Optional[datetime] = None
    login_count: int = 0

    # Preferences
    notification_preferences: Dict[str, bool] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class PortalSession:
    """Active portal session."""

    id: str
    client_id: str
    token: str

    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=7))

    ip_address: str = ""
    user_agent: str = ""

    @property
    def is_valid(self) -> bool:
        return datetime.now() < self.expires_at


@dataclass
class PortalActivity:
    """Client activity log."""

    id: str
    client_id: str
    activity_type: str  # "login", "property_view", "document_view", "message_sent", etc.
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ClientPortal:
    """Manage client portal accounts and access."""

    def __init__(self, data_path: Optional[Path] = None):
        """Initialize client portal."""
        self.data_path = data_path or Path.home() / ".td-lead-engine" / "portal.json"
        self.accounts: Dict[str, ClientAccount] = {}
        self.sessions: Dict[str, PortalSession] = {}
        self.activities: List[PortalActivity] = []
        self._load_data()

    def _load_data(self):
        """Load portal data from file."""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)

                    for acc_data in data.get("accounts", []):
                        account = ClientAccount(
                            id=acc_data["id"],
                            lead_id=acc_data.get("lead_id"),
                            transaction_id=acc_data.get("transaction_id"),
                            email=acc_data["email"],
                            password_hash=acc_data["password_hash"],
                            name=acc_data["name"],
                            phone=acc_data.get("phone", ""),
                            client_type=ClientType(acc_data.get("client_type", "buyer")),
                            is_active=acc_data.get("is_active", True),
                            is_verified=acc_data.get("is_verified", False),
                            permissions=[PortalPermission(p) for p in acc_data.get("permissions", [])],
                            agent_id=acc_data.get("agent_id", ""),
                            agent_name=acc_data.get("agent_name", ""),
                            agent_email=acc_data.get("agent_email", ""),
                            agent_phone=acc_data.get("agent_phone", ""),
                            login_count=acc_data.get("login_count", 0),
                            notification_preferences=acc_data.get("notification_preferences", {}),
                            created_at=datetime.fromisoformat(acc_data["created_at"]),
                            updated_at=datetime.fromisoformat(acc_data["updated_at"])
                        )
                        if acc_data.get("last_login"):
                            account.last_login = datetime.fromisoformat(acc_data["last_login"])
                        self.accounts[account.id] = account

            except Exception as e:
                logger.error(f"Error loading portal data: {e}")

    def _save_data(self):
        """Save portal data to file."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "accounts": [
                {
                    "id": a.id,
                    "lead_id": a.lead_id,
                    "transaction_id": a.transaction_id,
                    "email": a.email,
                    "password_hash": a.password_hash,
                    "name": a.name,
                    "phone": a.phone,
                    "client_type": a.client_type.value,
                    "is_active": a.is_active,
                    "is_verified": a.is_verified,
                    "permissions": [p.value for p in a.permissions],
                    "agent_id": a.agent_id,
                    "agent_name": a.agent_name,
                    "agent_email": a.agent_email,
                    "agent_phone": a.agent_phone,
                    "last_login": a.last_login.isoformat() if a.last_login else None,
                    "login_count": a.login_count,
                    "notification_preferences": a.notification_preferences,
                    "created_at": a.created_at.isoformat(),
                    "updated_at": a.updated_at.isoformat()
                }
                for a in self.accounts.values()
            ],
            "updated_at": datetime.now().isoformat()
        }

        with open(self.data_path, 'w') as f:
            json.dump(data, f, indent=2)

    def _hash_password(self, password: str) -> str:
        """Hash a password."""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{hash_obj.hex()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, stored_hash = password_hash.split(':')
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return hash_obj.hex() == stored_hash
        except:
            return False

    def create_account(
        self,
        email: str,
        password: str,
        name: str,
        client_type: ClientType = ClientType.BUYER,
        lead_id: Optional[str] = None,
        agent_id: str = "",
        agent_name: str = "",
        phone: str = ""
    ) -> ClientAccount:
        """Create a new client portal account."""
        # Check for existing account
        for account in self.accounts.values():
            if account.email.lower() == email.lower():
                raise ValueError("Account with this email already exists")

        account_id = str(uuid.uuid4())[:8]

        # Default permissions based on client type
        if client_type == ClientType.BUYER:
            permissions = [
                PortalPermission.VIEW_LISTINGS,
                PortalPermission.SAVE_PROPERTIES,
                PortalPermission.REQUEST_SHOWINGS,
                PortalPermission.MESSAGE_AGENT,
                PortalPermission.VIEW_MARKET_REPORTS
            ]
        elif client_type == ClientType.SELLER:
            permissions = [
                PortalPermission.VIEW_TRANSACTION,
                PortalPermission.VIEW_DOCUMENTS,
                PortalPermission.SIGN_DOCUMENTS,
                PortalPermission.MESSAGE_AGENT,
                PortalPermission.VIEW_MARKET_REPORTS
            ]
        else:
            permissions = list(PortalPermission)

        account = ClientAccount(
            id=account_id,
            lead_id=lead_id,
            email=email,
            password_hash=self._hash_password(password),
            name=name,
            phone=phone,
            client_type=client_type,
            permissions=permissions,
            agent_id=agent_id,
            agent_name=agent_name,
            notification_preferences={
                "email_new_listings": True,
                "email_price_drops": True,
                "email_showing_reminders": True,
                "email_document_updates": True,
                "sms_showing_reminders": True
            }
        )

        self.accounts[account_id] = account
        self._save_data()

        logger.info(f"Created portal account for {email}")
        return account

    def authenticate(self, email: str, password: str) -> Optional[PortalSession]:
        """Authenticate a client and create a session."""
        # Find account by email
        account = None
        for acc in self.accounts.values():
            if acc.email.lower() == email.lower():
                account = acc
                break

        if not account:
            return None

        if not account.is_active:
            return None

        if not self._verify_password(password, account.password_hash):
            return None

        # Create session
        session = PortalSession(
            id=str(uuid.uuid4())[:8],
            client_id=account.id,
            token=secrets.token_urlsafe(32)
        )

        self.sessions[session.token] = session

        # Update login tracking
        account.last_login = datetime.now()
        account.login_count += 1
        account.updated_at = datetime.now()
        self._save_data()

        # Log activity
        self._log_activity(account.id, "login", "Client logged in")

        return session

    def validate_session(self, token: str) -> Optional[ClientAccount]:
        """Validate a session token and return the account."""
        session = self.sessions.get(token)
        if not session or not session.is_valid:
            return None

        account = self.accounts.get(session.client_id)
        if not account or not account.is_active:
            return None

        return account

    def logout(self, token: str) -> bool:
        """Invalidate a session."""
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def reset_password(self, email: str) -> Optional[str]:
        """Generate a password reset token."""
        account = None
        for acc in self.accounts.values():
            if acc.email.lower() == email.lower():
                account = acc
                break

        if not account:
            return None

        reset_token = secrets.token_urlsafe(32)
        # In production, store this with expiration and send via email
        return reset_token

    def update_password(self, account_id: str, new_password: str) -> bool:
        """Update account password."""
        account = self.accounts.get(account_id)
        if not account:
            return False

        account.password_hash = self._hash_password(new_password)
        account.updated_at = datetime.now()
        self._save_data()
        return True

    def get_client_dashboard(self, account_id: str) -> Dict[str, Any]:
        """Get dashboard data for a client."""
        account = self.accounts.get(account_id)
        if not account:
            return {"error": "Account not found"}

        dashboard = {
            "client": {
                "name": account.name,
                "email": account.email,
                "type": account.client_type.value,
                "agent": {
                    "name": account.agent_name,
                    "email": account.agent_email,
                    "phone": account.agent_phone
                }
            },
            "permissions": [p.value for p in account.permissions]
        }

        # Add type-specific data
        if account.client_type == ClientType.BUYER:
            dashboard["sections"] = [
                {"id": "saved_searches", "title": "My Saved Searches", "icon": "search"},
                {"id": "saved_homes", "title": "Saved Properties", "icon": "heart"},
                {"id": "showings", "title": "Upcoming Showings", "icon": "calendar"},
                {"id": "market_reports", "title": "Market Reports", "icon": "chart"},
                {"id": "messages", "title": "Messages", "icon": "message"}
            ]
        elif account.client_type == ClientType.SELLER:
            dashboard["sections"] = [
                {"id": "listing", "title": "My Listing", "icon": "home"},
                {"id": "showings", "title": "Showing Schedule", "icon": "calendar"},
                {"id": "activity", "title": "Listing Activity", "icon": "activity"},
                {"id": "documents", "title": "Documents", "icon": "file"},
                {"id": "offers", "title": "Offers", "icon": "dollar"},
                {"id": "messages", "title": "Messages", "icon": "message"}
            ]

        if account.transaction_id:
            dashboard["active_transaction"] = account.transaction_id
            dashboard["sections"].insert(0, {
                "id": "transaction",
                "title": "Transaction Progress",
                "icon": "progress"
            })

        return dashboard

    def _log_activity(self, client_id: str, activity_type: str, description: str, metadata: Dict = None):
        """Log client activity."""
        activity = PortalActivity(
            id=str(uuid.uuid4())[:8],
            client_id=client_id,
            activity_type=activity_type,
            description=description,
            metadata=metadata or {}
        )
        self.activities.append(activity)

        # Keep only last 1000 activities in memory
        if len(self.activities) > 1000:
            self.activities = self.activities[-1000:]

    def get_client_activity(self, client_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent activity for a client."""
        activities = [
            a for a in self.activities
            if a.client_id == client_id
        ]
        activities.sort(key=lambda x: x.timestamp, reverse=True)

        return [
            {
                "type": a.activity_type,
                "description": a.description,
                "timestamp": a.timestamp.isoformat(),
                "metadata": a.metadata
            }
            for a in activities[:limit]
        ]

    def send_client_message(
        self,
        client_id: str,
        message: str,
        from_agent: bool = True
    ) -> bool:
        """Send a message to/from a client."""
        account = self.accounts.get(client_id)
        if not account:
            return False

        sender = "agent" if from_agent else "client"
        self._log_activity(
            client_id,
            "message_received" if from_agent else "message_sent",
            f"Message from {sender}",
            {"message": message[:200]}  # Truncate for log
        )

        # In production, this would send email/SMS notification
        return True

    def link_transaction(self, account_id: str, transaction_id: str) -> bool:
        """Link a transaction to a client account."""
        account = self.accounts.get(account_id)
        if not account:
            return False

        account.transaction_id = transaction_id

        # Add transaction permissions
        if PortalPermission.VIEW_TRANSACTION not in account.permissions:
            account.permissions.append(PortalPermission.VIEW_TRANSACTION)
        if PortalPermission.VIEW_DOCUMENTS not in account.permissions:
            account.permissions.append(PortalPermission.VIEW_DOCUMENTS)

        account.updated_at = datetime.now()
        self._save_data()
        return True
