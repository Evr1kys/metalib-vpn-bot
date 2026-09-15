"""
Payment model
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class PaymentStatus(str, enum.Enum):
    """Payment status"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CHARGEBACK = "chargeback"
    CANCELLED = "cancelled"


class Payment(Base, UUIDMixin, TimestampMixin):
    """Payment transaction"""
    
    __tablename__ = "payments"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True)
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=True)
    
    # Platega data
    external_id = Column(String(255), unique=True, nullable=True, index=True)  # Platega payment ID
    
    # Amount
    amount = Column(Numeric(10, 2), nullable=False)
    original_amount = Column(Numeric(10, 2), nullable=True)  # before discount
    discount_amount = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    
    # Status
    status = Column(
        SQLEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True
    )
    
    # Payment details
    payment_method = Column(String(100), nullable=True)
    payment_url = Column(String(1000), nullable=True)
    
    # Metadata (store additional Platega data)
    payment_metadata = Column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    paid_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")
    plan = relationship("Plan", back_populates="payments")
    promo_code = relationship("PromoCode", back_populates="payments")
    
    def __repr__(self):
        return f"<Payment(id={self.id}, amount={self.amount} {self.currency}, status={self.status})>"
