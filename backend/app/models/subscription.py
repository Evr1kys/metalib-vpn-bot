"""
Subscription model
"""
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class SubscriptionStatus(str, enum.Enum):
    """Subscription status"""
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class Subscription(Base, UUIDMixin, TimestampMixin):
    """User subscription"""
    
    __tablename__ = "subscriptions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True)
    server_id = Column(UUID(as_uuid=True), ForeignKey("servers.id"), nullable=True, index=True)
    
    status = Column(
        SQLEnum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Dates
    started_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Auto-renewal
    auto_renew = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    server = relationship("Server", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription", cascade="all, delete-orphan")
    vpn_accounts = relationship("VPNAccount", back_populates="subscription", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="subscription", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, status={self.status})>"
    
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        return (
            self.status == SubscriptionStatus.ACTIVE and
            self.expires_at and
            self.expires_at > datetime.utcnow()
        )
    
    def days_until_expiry(self) -> int:
        """Get days until expiry"""
        if not self.expires_at:
            return 0
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)
