"""
Smart Connect & Server Status API endpoints
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from pydantic import BaseModel
import httpx
import asyncio

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import (
    User, Server, ServerStatus,
    SmartConnectProfile, OperatorServerRecommendation,
    ServerHealthCheck, ServerAlert, SpeedTestResult,
    MobileOperator, ServerHealthStatus
)
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class ServerStatusResponse(BaseModel):
    id: str
    name: str
    country_code: str
    country_name: str
    city: Optional[str]
    flag_emoji: Optional[str]
    server_type: str
    status: str
    ping_ms: Optional[int]
    load_percent: float
    is_premium: bool
    supports_streaming: bool
    supports_gaming: bool
    supports_p2p: bool


class SmartConnectRequest(BaseModel):
    use_case: Optional[str] = "general"  # gaming, streaming, privacy, general
    operator: Optional[str] = None


class SpeedTestSubmit(BaseModel):
    download_mbps: float
    upload_mbps: float
    ping_ms: int
    jitter_ms: Optional[float] = None
    server_id: Optional[str] = None
    vpn_connected: bool = True


class OperatorDetectRequest(BaseModel):
    ip_address: Optional[str] = None


# ============== Helper Functions ==============

async def detect_operator_from_ip(ip: str) -> MobileOperator:
    """Detect mobile operator from IP address"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use ip-api.com for ISP detection
            response = await client.get(f"http://ip-api.com/json/{ip}?fields=isp,org")
            if response.status_code == 200:
                data = response.json()
                isp = (data.get("isp", "") + data.get("org", "")).lower()
                
                if "mts" in isp or "мтс" in isp:
                    return MobileOperator.MTS
                elif "megafon" in isp or "мегафон" in isp:
                    return MobileOperator.MEGAFON
                elif "beeline" in isp or "билайн" in isp or "vimpelcom" in isp:
                    return MobileOperator.BEELINE
                elif "tele2" in isp or "теле2" in isp:
                    return MobileOperator.TELE2
                elif "yota" in isp or "йота" in isp:
                    return MobileOperator.YOTA
                elif "tinkoff" in isp or "тинькофф" in isp:
                    return MobileOperator.TINKOFF
                elif "rostelecom" in isp or "ростелеком" in isp:
                    return MobileOperator.ROSTELECOM
    except:
        pass
    
    return MobileOperator.UNKNOWN


# ============== Public Endpoints ==============

@router.get("/servers/status")
async def get_servers_status(
    db: AsyncSession = Depends(get_db)
):
    """Get real-time status of all servers (public)"""
    stmt = select(Server).where(Server.is_active == True).order_by(Server.region, Server.name)
    result = await db.execute(stmt)
    servers = result.scalars().all()
    
    # Country info mapping
    country_info = {
        "NL": {"name": "Netherlands", "name_ru": "Нидерланды", "flag": "🇳🇱"},
        "DE": {"name": "Germany", "name_ru": "Германия", "flag": "🇩🇪"},
        "FI": {"name": "Finland", "name_ru": "Финляндия", "flag": "🇫🇮"},
        "LV": {"name": "Latvia", "name_ru": "Латвия", "flag": "🇱🇻"},
        "KZ": {"name": "Kazakhstan", "name_ru": "Казахстан", "flag": "🇰🇿"},
        "US": {"name": "United States", "name_ru": "США", "flag": "🇺🇸"},
        "GB": {"name": "United Kingdom", "name_ru": "Великобритания", "flag": "🇬🇧"},
        "JP": {"name": "Japan", "name_ru": "Япония", "flag": "🇯🇵"},
        "SG": {"name": "Singapore", "name_ru": "Сингапур", "flag": "🇸🇬"},
    }
    
    response = []
    for server in servers:
        country_code = server.country_code or "NL"
        info = country_info.get(country_code, {"name": "Unknown", "name_ru": "Неизвестно", "flag": "🌍"})
        
        response.append({
            "id": str(server.id),
            "name": server.name,
            "country_code": country_code,
            "country_name": info["name"],
            "country_name_ru": info["name_ru"],
            "city": server.city,
            "flag_emoji": info["flag"],
            "server_type": server.server_type.value if server.server_type else "standard",
            "status": server.status.value,
            "ping_ms": server.ping_ms,
            "download_speed_mbps": server.download_speed_mbps,
            "load_percent": server.load_percentage(),
            "current_users": server.current_users,
            "max_users": server.max_users,
            "is_premium": server.is_premium,
            "supports_streaming": server.supports_streaming,
            "supports_gaming": server.supports_gaming,
            "supports_p2p": server.supports_p2p
        })
    
    return {"servers": response}


@router.get("/servers/{server_id}/ping")
async def ping_server(
    server_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get ping to a specific server"""
    import uuid
    server = await db.get(Server, uuid.UUID(server_id))
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Try to ping the server
    ping_ms = None
    try:
        start = datetime.utcnow()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{server.agent_url}/health" if server.agent_url else f"http://{server.ip_address}:8001/health")
            if response.status_code == 200:
                elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                ping_ms = int(elapsed)
    except:
        pass
    
    return {
        "server_id": server_id,
        "ping_ms": ping_ms or server.ping_ms,
        "status": server.status.value
    }


@router.post("/smart-connect")
async def smart_connect(
    request: Request,
    data: SmartConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recommended server based on user's context"""
    # Get or create smart connect profile
    profile_stmt = select(SmartConnectProfile).where(SmartConnectProfile.user_id == current_user.id)
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        profile = SmartConnectProfile(user_id=current_user.id)
        db.add(profile)
    
    # Detect operator if not provided
    operator = MobileOperator(data.operator) if data.operator else None
    if not operator:
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
        if client_ip:
            operator = await detect_operator_from_ip(client_ip)
            profile.detected_operator = operator
    
    # Update profile
    profile.preferred_use_case = data.use_case
    
    # Find best server
    stmt = select(Server).where(
        and_(
            Server.is_active == True,
            Server.status == ServerStatus.HEALTHY
        )
    )
    
    # Filter by use case
    if data.use_case == "gaming":
        stmt = stmt.where(Server.supports_gaming == True).order_by(Server.ping_ms.asc().nulls_last())
    elif data.use_case == "streaming":
        stmt = stmt.where(Server.supports_streaming == True).order_by(Server.download_speed_mbps.desc().nulls_last())
    elif data.use_case == "privacy":
        stmt = stmt.where(Server.server_type == "privacy")
    else:
        # General - balance load and ping
        stmt = stmt.order_by(Server.current_users.asc(), Server.ping_ms.asc().nulls_last())
    
    stmt = stmt.limit(1)
    result = await db.execute(stmt)
    best_server = result.scalar_one_or_none()
    
    if not best_server:
        # Fallback to any active server
        fallback_stmt = select(Server).where(Server.is_active == True).order_by(Server.current_users).limit(1)
        fallback_result = await db.execute(fallback_stmt)
        best_server = fallback_result.scalar_one_or_none()
    
    if best_server:
        profile.recommended_server_id = best_server.id
    
    await db.commit()
    
    if not best_server:
        raise HTTPException(status_code=503, detail="No available servers")
    
    return {
        "recommended_server": {
            "id": str(best_server.id),
            "name": best_server.name,
            "country_code": best_server.country_code or "NL",
            "city": best_server.city,
            "ping_ms": best_server.ping_ms,
            "load_percent": best_server.load_percentage()
        },
        "detected_operator": operator.value if operator else None,
        "use_case": data.use_case
    }


@router.post("/speed-test/submit")
async def submit_speed_test(
    data: SpeedTestSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Submit speed test results"""
    import uuid
    
    server_id = uuid.UUID(data.server_id) if data.server_id else None
    
    result = SpeedTestResult(
        user_id=current_user.id,
        server_id=server_id,
        download_mbps=data.download_mbps,
        upload_mbps=data.upload_mbps,
        ping_ms=data.ping_ms,
        jitter_ms=data.jitter_ms,
        vpn_connected=data.vpn_connected,
        source="website"
    )
    db.add(result)
    
    # Update user's smart connect profile
    profile_stmt = select(SmartConnectProfile).where(SmartConnectProfile.user_id == current_user.id)
    profile_result = await db.execute(profile_stmt)
    profile = profile_result.scalar_one_or_none()
    
    if profile:
        profile.last_speed_test = datetime.utcnow()
        profile.last_ping_ms = data.ping_ms
        profile.last_download_mbps = data.download_mbps
        profile.last_upload_mbps = data.upload_mbps
    
    await db.commit()
    
    return {
        "success": True,
        "result_id": str(result.id),
        "comparison": {
            "download": "excellent" if data.download_mbps > 50 else "good" if data.download_mbps > 20 else "fair",
            "upload": "excellent" if data.upload_mbps > 30 else "good" if data.upload_mbps > 10 else "fair",
            "ping": "excellent" if data.ping_ms < 50 else "good" if data.ping_ms < 100 else "fair"
        }
    }


@router.get("/speed-test/history")
async def get_speed_test_history(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's speed test history"""
    stmt = select(SpeedTestResult).where(
        SpeedTestResult.user_id == current_user.id
    ).order_by(SpeedTestResult.created_at.desc()).limit(limit)
    
    result = await db.execute(stmt)
    tests = result.scalars().all()
    
    return {
        "tests": [
            {
                "id": str(t.id),
                "download_mbps": t.download_mbps,
                "upload_mbps": t.upload_mbps,
                "ping_ms": t.ping_ms,
                "vpn_connected": t.vpn_connected,
                "created_at": t.created_at.isoformat()
            }
            for t in tests
        ]
    }


# ============== Admin Endpoints ==============

@router.get("/admin/health-checks")
async def get_health_checks(
    server_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get server health check history"""
    import uuid
    
    stmt = select(ServerHealthCheck).order_by(ServerHealthCheck.checked_at.desc())
    
    if server_id:
        stmt = stmt.where(ServerHealthCheck.server_id == uuid.UUID(server_id))
    
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    checks = result.scalars().all()
    
    return {
        "checks": [
            {
                "id": str(c.id),
                "server_id": str(c.server_id),
                "status": c.status.value,
                "ping_ms": c.ping_ms,
                "cpu_percent": c.cpu_percent,
                "memory_percent": c.memory_percent,
                "active_connections": c.active_connections,
                "checked_at": c.checked_at.isoformat()
            }
            for c in checks
        ]
    }


@router.get("/admin/alerts")
async def get_alerts(
    resolved: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get server alerts"""
    stmt = select(ServerAlert).order_by(ServerAlert.created_at.desc())
    
    if resolved is not None:
        stmt = stmt.where(ServerAlert.is_resolved == resolved)
    
    stmt = stmt.limit(100)
    result = await db.execute(stmt)
    alerts = result.scalars().all()
    
    return {
        "alerts": [
            {
                "id": str(a.id),
                "server_id": str(a.server_id),
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at.isoformat()
            }
            for a in alerts
        ]
    }


@router.post("/admin/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Resolve a server alert"""
    import uuid
    
    alert = await db.get(ServerAlert, uuid.UUID(alert_id))
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = admin.id
    
    await db.commit()
    
    return {"success": True, "message": "Alert resolved"}


@router.post("/admin/check-all-servers")
async def trigger_health_check(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Trigger health check for all servers"""
    from app.services.server_orchestrator import ServerOrchestrator
    
    orchestrator = ServerOrchestrator(db)
    results = await orchestrator.check_all_servers()
    
    return {
        "success": True,
        "checked": len(results),
        "results": results
    }
