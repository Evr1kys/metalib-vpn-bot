"""
User model
"""
from sqlalchemy import Column, String, BigInteger, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Telegram user"""
    
    __tablename__ = "users"
    
    # Telegram data
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="ru", nullable=False)
    
    # Status
    is_blocked = Column(Boolean, default=False, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    ban_reason = Column(String(500), nullable=True)
    disable_broadcast_notifications = Column(Boolean, default=False, nullable=False)
    
    # Referral
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    referral_code = Column(String(50), unique=True, nullable=True)
    
    # Relationships
    referrer = relationship("User", remote_side="User.id", foreign_keys=[referrer_id])
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    referrals_made = relationship(
        "Referral",
        foreign_keys="Referral.referrer_id",
        back_populates="referrer",
        cascade="all, delete-orphan"
    )
    referrals_received = relationship(
        "Referral",
        foreign_keys="Referral.referred_id",
        back_populates="referred",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
