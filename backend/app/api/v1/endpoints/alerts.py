"""
Alerts API endpoints for Admin Panel
"""
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.models import AdminUser, Alert, AlertSeverity, AlertCategory, AlertStatus
from app.services.alert_service import AlertService

router = APIRouter()


# ============== Schemas ==============

class AlertResponse(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    category: str
    status: str
    source: Optional[str]
    source_id: Optional[str]
    telegram_sent: bool
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[str]
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    resolution_note: Optional[str]
    created_at: datetime
    duration_minutes: int
    
    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    active_total: int
    critical_active: int
    error_active: int
    warning_active: int
    last_24h: int
    active_by_category: dict


class ResolveAlertRequest(BaseModel):
    note: Optional[str] = None


class CreateAlertRequest(BaseModel):
    title: str
    message: str
    severity: str = "warning"
    category: str = "system"


# ============== Endpoints ==============

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get all alerts with optional filters"""
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    
    if status_filter:
        try:
            status_enum = AlertStatus(status_filter)
            query = query.where(Alert.status == status_enum)
        except ValueError:
            pass
    
    if category:
        try:
            cat_enum = AlertCategory(category)
            query = query.where(Alert.category == cat_enum)
        except ValueError:
            pass
    
    if severity:
        try:
            sev_enum = AlertSeverity(severity)
            query = query.where(Alert.severity == sev_enum)
        except ValueError:
            pass
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [
        AlertResponse(
            id=str(alert.id),
            title=alert.title,
            message=alert.message,
            severity=alert.severity.value,
            category=alert.category.value,
            status=alert.status.value,
            source=alert.source,
            source_id=alert.source_id,
            telegram_sent=alert.telegram_sent,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
            resolution_note=alert.resolution_note,
            created_at=alert.created_at,
            duration_minutes=alert.duration_minutes
        )
        for alert in alerts
    ]


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get alert statistics for dashboard"""
    service = AlertService(db)
    stats = await service.get_alert_stats()
    
    # Get by category
    cat_result = await db.execute(
        select(Alert.category, func.count(Alert.id))
        .where(Alert.status == AlertStatus.ACTIVE)
        .group_by(Alert.category)
    )
    by_category = {row[0].value: row[1] for row in cat_result.all()}
    
    return AlertStatsResponse(
        active_total=stats["active_total"],
        critical_active=stats["critical_active"],
        error_active=stats["error_active"],
        warning_active=stats.get("active_by_severity", {}).get("warning", 0),
        last_24h=stats["last_24h"],
        active_by_category=by_category
    )


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get only active (non-resolved) alerts"""
    result = await db.execute(
        select(Alert)
        .where(Alert.status != AlertStatus.RESOLVED)
        .order_by(
            # Critical first, then by date
            desc(Alert.severity == AlertSeverity.CRITICAL),
            desc(Alert.severity == AlertSeverity.ERROR),
            desc(Alert.created_at)
        )
        .limit(100)
    )
    alerts = result.scalars().all()
    
    return [
        AlertResponse(
            id=str(alert.id),
            title=alert.title,
            message=alert.message,
            severity=alert.severity.value,
            category=alert.category.value,
            status=alert.status.value,
            source=alert.source,
            source_id=alert.source_id,
            telegram_sent=alert.telegram_sent,
            acknowledged_at=alert.acknowledged_at,
            acknowledged_by=alert.acknowledged_by,
            resolved_at=alert.resolved_at,
            resolved_by=alert.resolved_by,
            resolution_note=alert.resolution_note,
            created_at=alert.created_at,
            duration_minutes=alert.duration_minutes
        )
        for alert in alerts
    ]


@router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Mark alert as acknowledged"""
    service = AlertService(db)
    alert = await service.acknowledge_alert(alert_id, admin.username)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"success": True, "message": "Alert acknowledged"}


@router.post("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    data: ResolveAlertRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Mark alert as resolved"""
    service = AlertService(db)
    alert = await service.resolve_alert(alert_id, admin.username, data.note)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"success": True, "message": "Alert resolved"}


@router.post("/resolve-all")
async def resolve_all_alerts(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Resolve all active alerts (optionally filtered by category)"""
    query = select(Alert).where(Alert.status == AlertStatus.ACTIVE)
    
    if category:
        try:
            cat_enum = AlertCategory(category)
            query = query.where(Alert.category == cat_enum)
        except ValueError:
            pass
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    count = 0
    for alert in alerts:
        alert.resolve(admin.username, "Bulk resolved")
        count += 1
    
    await db.commit()
    
    return {"success": True, "resolved_count": count}


@router.post("/create")
async def create_manual_alert(
    data: CreateAlertRequest,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Create a manual alert (for testing or announcements)"""
    try:
        severity = AlertSeverity(data.severity)
    except ValueError:
        severity = AlertSeverity.WARNING
    
    try:
        category = AlertCategory(data.category)
    except ValueError:
        category = AlertCategory.SYSTEM
    
    service = AlertService(db)
    alert = await service.create_alert(
        title=data.title,
        message=data.message,
        severity=severity,
        category=category,
        source="manual",
        source_id=f"admin_{admin.id}",
        send_telegram=True
    )
    
    return {"success": True, "alert_id": str(alert.id)}


@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Delete an alert (admin only)"""
    alert = await db.get(Alert, alert_id)
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    await db.delete(alert)
    await db.commit()
    
    return {"success": True, "message": "Alert deleted"}


@router.get("/metrics")
async def get_alert_metrics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """Get alert metrics for charts"""
    from datetime import timedelta
    from sqlalchemy import cast, Date, and_
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Alerts by day
    daily_result = await db.execute(
        select(
            cast(Alert.created_at, Date).label('date'),
            func.count(Alert.id).label('count')
        )
        .where(Alert.created_at >= cutoff)
        .group_by(cast(Alert.created_at, Date))
        .order_by(cast(Alert.created_at, Date))
    )
    daily_data = [{"date": str(row.date), "count": row.count} for row in daily_result.all()]
    
    # Alerts by severity
    severity_result = await db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(Alert.created_at >= cutoff)
        .group_by(Alert.severity)
    )
    by_severity = {row[0].value: row[1] for row in severity_result.all()}
    
    # Alerts by category
    category_result = await db.execute(
        select(Alert.category, func.count(Alert.id))
        .where(Alert.created_at >= cutoff)
        .group_by(Alert.category)
    )
    by_category = {row[0].value: row[1] for row in category_result.all()}
    
    # Average resolution time (in minutes)
    resolution_result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', Alert.resolved_at - Alert.created_at) / 60
            )
        )
        .where(
            and_(
                Alert.resolved_at.isnot(None),
                Alert.created_at >= cutoff
            )
        )
    )
    avg_resolution_minutes = resolution_result.scalar() or 0
    
    # Resolution rate
    total_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= cutoff)
    )
    total = total_result.scalar() or 0
    
    resolved_result = await db.execute(
        select(func.count(Alert.id)).where(
            and_(
                Alert.status == AlertStatus.RESOLVED,
                Alert.created_at >= cutoff
            )
        )
    )
    resolved = resolved_result.scalar() or 0
    
    resolution_rate = (resolved / total * 100) if total > 0 else 100
    
    # Top sources
    sources_result = await db.execute(
        select(Alert.source, func.count(Alert.id).label('count'))
        .where(and_(Alert.created_at >= cutoff, Alert.source.isnot(None)))
        .group_by(Alert.source)
        .order_by(desc('count'))
        .limit(5)
    )
    top_sources = [{"source": row.source, "count": row.count} for row in sources_result.all()]
    
    return {
        "period_days": days,
        "daily_chart": daily_data,
        "by_severity": by_severity,
        "by_category": by_category,
        "avg_resolution_minutes": round(avg_resolution_minutes, 1),
        "resolution_rate": round(resolution_rate, 1),
        "total_alerts": total,
        "resolved_alerts": resolved,
        "top_sources": top_sources
    }
