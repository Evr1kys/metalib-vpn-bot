"""
Plan (tariff) model
"""
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class Plan(Base, UUIDMixin, TimestampMixin):
    """VPN subscription plan/tariff"""
    
    __tablename__ = "plans"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_days = Column(Integer, nullable=False)  # e.g., 30, 90, 365
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB", nullable=False)
    
    # Server assignment - which servers this plan uses
    server_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Assigned servers, null = all servers
    
    # Limits
    bandwidth_limit = Column(BigInteger, nullable=True)  # bytes per month, null = unlimited
    
    # Additional features (JSON)
    features = Column(JSONB, default=dict, nullable=False)
    # Example: {"priority_support": true, "dedicated_ip": false, "ad_blocking": true}
    
    # Display
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False, index=True)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="plan")
    payments = relationship("Payment", back_populates="plan")
    
    def __repr__(self):
        return f"<Plan(id={self.id}, name={self.name}, price={self.price} {self.currency})>"
