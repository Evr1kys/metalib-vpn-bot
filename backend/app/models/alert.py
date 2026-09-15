"""
System Alert Model

For storing and managing system alerts/notifications
"""
import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, Enum, DateTime, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import Base


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(str, enum.Enum):
    """Alert categories"""
    SERVER = "server"
    PAYMENT = "payment"
    SUBSCRIPTION = "subscription"
    SECURITY = "security"
    SYSTEM = "system"
    VPN = "vpn"


class AlertStatus(str, enum.Enum):
    """Alert status"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class Alert(Base):
    """System alert model"""
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Alert details
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.WARNING, nullable=False)
    category = Column(Enum(AlertCategory), default=AlertCategory.SYSTEM, nullable=False)
    status = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False)
    
    # Source info
    source = Column(String(100))  # e.g., "health_check", "payment_webhook", "subscription_expiry"
    source_id = Column(String(100))  # e.g., server_id, payment_id
    
    # Additional data
    extra_data = Column(JSON, default=dict)  # renamed from metadata to avoid SQLAlchemy reserved name
    
    # Notification tracking
    telegram_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    
    # Resolution
    acknowledged_at = Column(DateTime)
    acknowledged_by = Column(String(100))  # admin username
    resolved_at = Column(DateTime)
    resolved_by = Column(String(100))
    resolution_note = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Auto-resolve settings
    auto_resolve_after_minutes = Column(Integer, default=0)  # 0 = manual only
    
    def __repr__(self):
        return f"<Alert {self.severity.value}: {self.title[:30]}>"
    
    @property
    def is_active(self) -> bool:
        return self.status == AlertStatus.ACTIVE
    
    @property
    def duration_minutes(self) -> int:
        """How long this alert has been active"""
        if self.resolved_at:
            return int((self.resolved_at - self.created_at).total_seconds() / 60)
        return int((datetime.utcnow() - self.created_at).total_seconds() / 60)
    
    def acknowledge(self, admin_username: str):
        """Mark alert as acknowledged"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = admin_username
    
    def resolve(self, admin_username: str, note: Optional[str] = None):
        """Mark alert as resolved"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.resolved_by = admin_username
        if note:
            self.resolution_note = note
