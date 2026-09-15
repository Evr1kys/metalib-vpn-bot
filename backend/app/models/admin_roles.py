"""
Admin roles and audit logging system
"""
from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class AdminRole(str, Enum):
    """Admin role levels with different permissions"""
    SUPERADMIN = "superadmin"  # Full access, can manage other admins
    ADMIN = "admin"           # Full access except admin management
    SUPPORT = "support"       # Limited access: users, subscriptions, support tickets
    VIEWER = "viewer"         # Read-only access


# Permission definitions for each role
ROLE_PERMISSIONS = {
    AdminRole.SUPERADMIN: {
        "admins": ["read", "create", "update", "delete"],
        "users": ["read", "create", "update", "delete", "ban", "unban"],
        "subscriptions": ["read", "create", "update", "delete", "extend", "cancel"],
        "payments": ["read", "refund"],
        "servers": ["read", "create", "update", "delete"],
        "plans": ["read", "create", "update", "delete"],
        "promocodes": ["read", "create", "update", "delete"],
        "broadcast": ["read", "create"],
        "settings": ["read", "update"],
        "analytics": ["read", "export"],
        "alerts": ["read", "resolve", "delete"],
        "audit_logs": ["read"],
        "support": ["read", "respond", "close"],
    },
    AdminRole.ADMIN: {
        "admins": ["read"],  # Can only view admins
        "users": ["read", "create", "update", "delete", "ban", "unban"],
        "subscriptions": ["read", "create", "update", "delete", "extend", "cancel"],
        "payments": ["read", "refund"],
        "servers": ["read", "create", "update", "delete"],
        "plans": ["read", "create", "update", "delete"],
        "promocodes": ["read", "create", "update", "delete"],
        "broadcast": ["read", "create"],
        "settings": ["read"],
        "analytics": ["read", "export"],
        "alerts": ["read", "resolve"],
        "audit_logs": ["read"],
        "support": ["read", "respond", "close"],
    },
    AdminRole.SUPPORT: {
        "users": ["read", "update"],
        "subscriptions": ["read", "extend"],
        "payments": ["read"],
        "servers": ["read"],
        "plans": ["read"],
        "support": ["read", "respond", "close"],
        "alerts": ["read"],
    },
    AdminRole.VIEWER: {
        "users": ["read"],
        "subscriptions": ["read"],
        "payments": ["read"],
        "servers": ["read"],
        "plans": ["read"],
        "analytics": ["read"],
        "alerts": ["read"],
    },
}


def has_permission(role: AdminRole, resource: str, action: str) -> bool:
    """Check if role has permission for action on resource"""
    if role not in ROLE_PERMISSIONS:
        return False
    
    role_perms = ROLE_PERMISSIONS[role]
    if resource not in role_perms:
        return False
    
    return action in role_perms[resource]


def get_allowed_resources(role: AdminRole) -> List[str]:
    """Get list of resources accessible by role"""
    if role not in ROLE_PERMISSIONS:
        return []
    return list(ROLE_PERMISSIONS[role].keys())


class AuditLog(Base):
    """Audit log for tracking admin actions"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admins.id"), nullable=False)
    action = Column(String(100), nullable=False)  # e.g., "user.ban", "subscription.extend"
    resource_type = Column(String(50), nullable=False)  # e.g., "user", "subscription"
    resource_id = Column(String(100), nullable=True)  # ID of affected resource
    details = Column(JSON, nullable=True)  # Additional action details
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to admin
    admin = relationship("Admin", back_populates="audit_logs")


class AuditLogCreate(BaseModel):
    """Schema for creating audit log"""
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Schema for audit log response"""
    id: str
    admin_id: str
    admin_email: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
