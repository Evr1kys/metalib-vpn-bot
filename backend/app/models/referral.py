"""
Referral model
"""
from sqlalchemy import Column, ForeignKey, Numeric, DateTime, String, Enum as SQLEnum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class ReferralStatus(str, enum.Enum):
    """Referral status"""
    PENDING = "pending"      # User registered but not paid yet
    COMPLETED = "completed"  # User made first payment, referrer rewarded


class Referral(Base, UUIDMixin, TimestampMixin):
    """Referral tracking"""
    
    __tablename__ = "referrals"
    
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    referred_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    status = Column(
        SQLEnum(ReferralStatus, name="referral_status"),
        default=ReferralStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Reward - bonus days added to referrer subscription
    bonus_days = Column(Integer, nullable=True, default=0)
    rewarded_at = Column(DateTime, nullable=True)
    
    # Legacy fields for compatibility
    reward_amount = Column(Numeric(10, 2), nullable=True)
    reward_currency = Column(String(3), default="RUB", nullable=True)
    
    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")
    
    def __repr__(self):
        return f"<Referral(id={self.id}, referrer_id={self.referrer_id}, status={self.status})>"
