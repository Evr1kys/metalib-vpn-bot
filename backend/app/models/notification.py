"""
Notification model
"""
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime, Enum as SQLEnum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class NotificationType(str, enum.Enum):
    """Notification type"""
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    DEVICE_LIMIT_REACHED = "device_limit_reached"
    SERVER_MAINTENANCE = "server_maintenance"
    REFERRAL_REWARD = "referral_reward"
    PROMO_CODE = "promo_code"
    GENERAL = "general"


class Notification(Base, UUIDMixin, TimestampMixin):
    """User notification"""
    
    __tablename__ = "notifications"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    type = Column(
        SQLEnum(NotificationType, name="notification_type"),
        nullable=False,
        index=True
    )
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type})>"
