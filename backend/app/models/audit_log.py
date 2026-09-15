"""
Audit Log model for tracking admin and system actions
"""
from sqlalchemy import Column, String, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.base import UUIDMixin, TimestampMixin


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Audit log for admin and system actions"""
    
    __tablename__ = "audit_logs"
    
    # Category of action
    category = Column(String(50), nullable=False, index=True, default="admin")
    # auth, user, subscription, payment, server, vpn, admin, system
    
    # What action
    action = Column(String(255), nullable=False, index=True)
    # Examples: "login", "user_created", "subscription_cancelled", "payment_failed"
    
    # Who performed the action
    actor_id = Column(Integer, nullable=True, index=True)  # Can be user_id or admin_id
    actor_type = Column(String(20), nullable=True)  # user, admin, system
    
    # Legacy fields for backward compatibility
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Resource affected
    resource_type = Column(String(100), nullable=True, index=True)  # user, server, payment, etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # New target fields
    target_type = Column(String(100), nullable=True, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    
    # Details (JSON)
    details = Column(JSONB, default=dict, nullable=False)
    
    # Request info
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    request_id = Column(String(50), nullable=True, index=True)  # For request tracing
    
    # Status
    status = Column(String(20), default="success")  # success, failure, warning
    
    # Relationships
    admin_user = relationship("AdminUser", back_populates="audit_logs", foreign_keys=[admin_user_id])
    user = relationship("User")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, category={self.category}, action={self.action})>"
