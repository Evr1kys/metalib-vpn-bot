"""
Promo Code model
"""
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class DiscountType(str, enum.Enum):
    """Discount type"""
    PERCENTAGE = "percentage"  # e.g., 20% off
    FIXED = "fixed"            # e.g., 100 RUB off
    FREE_PLAN = "free_plan"    # Free subscription for a plan


class PromoCode(Base, UUIDMixin, TimestampMixin):
    """Promotional code"""
    
    __tablename__ = "promo_codes"
    
    code = Column(String(50), unique=True, nullable=False, index=True)
    
    # Discount
    discount_type = Column(
        SQLEnum(DiscountType, name="discount_type"),
        nullable=False
    )
    discount_value = Column(Numeric(10, 2), nullable=False)
    
    # Restrictions
    plan_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Applicable plans, null = all plans
    min_purchase_amount = Column(Numeric(10, 2), nullable=True)  # Minimum purchase amount
    
    # Usage limits
    max_uses = Column(Integer, nullable=True)  # null = unlimited
    max_uses_per_user = Column(Integer, default=1, nullable=False)
    used_count = Column(Integer, default=0, nullable=False)
    
    # Validity
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Relationships
    payments = relationship("Payment", back_populates="promo_code")
    uses = relationship("PromoCodeUse", back_populates="promo_code", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PromoCode(id={self.id}, code={self.code}, discount={self.discount_value})>"
    
    def is_valid(self) -> bool:
        """Check if promo code is currently valid"""
        now = datetime.utcnow()
        
        # Check active status
        if not self.is_active:
            return False
        
        # Check start date
        if self.starts_at and now < self.starts_at:
            return False
        
        # Check expiry
        if self.expires_at and now > self.expires_at:
            return False
        
        # Check usage limit
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        
        return True
    
    def calculate_discount(self, amount: float) -> float:
        """Calculate discount amount"""
        if self.discount_type == DiscountType.PERCENTAGE:
            return amount * (self.discount_value / 100)
        else:  # FIXED
            return min(self.discount_value, amount)


class PromoCodeUse(Base, UUIDMixin, TimestampMixin):
    """Promo code usage tracking"""
    
    __tablename__ = "promo_code_uses"
    
    promo_code_id = Column(UUID(as_uuid=True), ForeignKey("promo_codes.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=True, index=True)  # Nullable for free promos
    subscription_id = Column(UUID(as_uuid=True), ForeignKey("subscriptions.id"), nullable=True, index=True)  # For free plan promos
    
    discount_amount = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    promo_code = relationship("PromoCode", back_populates="uses")
    user = relationship("User")
    payment = relationship("Payment")
    
    def __repr__(self):
        return f"<PromoCodeUse(id={self.id}, code_id={self.promo_code_id}, user_id={self.user_id})>"
