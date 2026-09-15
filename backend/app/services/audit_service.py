"""
Audit logging service
"""
from typing import Optional, Any, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    admin_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """
    Log an admin action to audit_logs table.
    
    Args:
        db: Database session
        action: Action name (e.g., "user.ban", "server.create")
        admin_id: ID of admin performing the action
        user_id: ID of user affected (if applicable)
        resource_type: Type of resource (user, server, payment, etc.)
        resource_id: ID of resource affected
        details: Additional details as dict
        ip_address: Request IP address
        user_agent: Request user agent
    
    Returns:
        Created AuditLog record
    """
    audit_log = AuditLog(
        admin_user_id=admin_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.add(audit_log)
    await db.flush()  # Get ID without committing
    
    return audit_log


# Common action constants
class AuditActions:
    # User actions
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_BAN = "user.ban"
    USER_UNBAN = "user.unban"
    USER_DELETE = "user.delete"
    
    # Server actions
    SERVER_CREATE = "server.create"
    SERVER_UPDATE = "server.update"
    SERVER_DELETE = "server.delete"
    SERVER_ACTIVATE = "server.activate"
    SERVER_DEACTIVATE = "server.deactivate"
    
    # Plan actions
    PLAN_CREATE = "plan.create"
    PLAN_UPDATE = "plan.update"
    PLAN_DELETE = "plan.delete"
    
    # Payment actions
    PAYMENT_CONFIRM = "payment.confirm"
    PAYMENT_CANCEL = "payment.cancel"
    PAYMENT_REFUND = "payment.refund"
    
    # Subscription actions
    SUBSCRIPTION_CREATE = "subscription.create"
    SUBSCRIPTION_CANCEL = "subscription.cancel"
    SUBSCRIPTION_EXTEND = "subscription.extend"
    
    # Promo code actions
    PROMO_CREATE = "promo.create"
    PROMO_UPDATE = "promo.update"
    PROMO_DELETE = "promo.delete"
    
    # Admin actions
    ADMIN_CREATE = "admin.create"
    ADMIN_UPDATE = "admin.update"
    ADMIN_DELETE = "admin.delete"
    
    # Broadcast actions
    BROADCAST_SEND = "broadcast.send"
    BROADCAST_DELETE = "broadcast.delete"
    
    # Settings actions
    SETTINGS_UPDATE = "settings.update"
    
    # Referral actions
    REFERRAL_TOGGLE = "referral.toggle"
