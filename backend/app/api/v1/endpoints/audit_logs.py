"""
Audit Logs API endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.models.admin import AdminUser
from app.api.deps import get_current_admin
from datetime import datetime


router = APIRouter()


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    admin_user_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get paginated audit logs with filters"""
    
    # Build query
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    
    # Apply filters
    conditions = []
    
    if action:
        conditions.append(AuditLog.action == action)
    
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    
    if admin_user_id:
        conditions.append(AuditLog.admin_user_id == admin_user_id)
    
    if search:
        conditions.append(
            or_(
                AuditLog.action.ilike(f"%{search}%"),
                AuditLog.resource_type.ilike(f"%{search}%"),
                AuditLog.ip_address.ilike(f"%{search}%")
            )
        )
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Count total
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    
    result = await db.execute(count_query)
    total = result.scalar() or 0
    total_pages = (total + limit - 1) // limit
    
    # Paginate
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get admin usernames
    admin_ids = [log.admin_user_id for log in logs if log.admin_user_id]
    admin_users = {}
    
    if admin_ids:
        admin_query = select(AdminUser).where(AdminUser.id.in_(admin_ids))
        admin_result = await db.execute(admin_query)
        for admin_user in admin_result.scalars():
            admin_users[str(admin_user.id)] = admin_user.username
    
    # Format response
    items = []
    for log in logs:
        items.append({
            "id": str(log.id),
            "admin_user_id": str(log.admin_user_id) if log.admin_user_id else None,
            "admin_username": admin_users.get(str(log.admin_user_id)) if log.admin_user_id else None,
            "user_id": str(log.user_id) if log.user_id else None,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/audit-logs/{log_id}")
async def get_audit_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get specific audit log details"""
    
    log = await db.get(AuditLog, log_id)
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    # Get admin user
    admin_user = None
    if log.admin_user_id:
        admin_user = await db.get(AdminUser, log.admin_user_id)
    
    return {
        "id": str(log.id),
        "admin_user_id": str(log.admin_user_id) if log.admin_user_id else None,
        "admin_username": admin_user.username if admin_user else None,
        "user_id": str(log.user_id) if log.user_id else None,
        "action": log.action,
        "resource_type": log.resource_type,
        "resource_id": str(log.resource_id) if log.resource_id else None,
        "details": log.details,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat()
    }
