"""
Trial API endpoints - пробный период
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User, Trial, TrialSettings, Server
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class TrialStartRequest(BaseModel):
    source: Optional[str] = "website"


class TrialResponse(BaseModel):
    id: str
    status: str
    started_at: datetime
    expires_at: datetime
    hours_left: int
    vpn_key: Optional[str] = None


class TrialSettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    duration_hours: Optional[int] = None
    max_per_ip: Optional[int] = None


# ============== Helper Functions ==============

async def get_trial_settings(db: AsyncSession) -> TrialSettings:
    """Get or create trial settings"""
    result = await db.execute(select(TrialSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = TrialSettings(
            duration_hours=24,
            is_enabled=True,
            max_per_ip=1
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


async def get_client_ip(request: Request) -> str:
    """Get client IP from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============== Public Endpoints ==============

@router.get("/status")
async def get_trial_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
        """Check if user has/had a trial and any active subscription"""
        # Check existing trial
        stmt = select(Trial).where(Trial.user_id == current_user.id)
        result = await db.execute(stmt)
        trial = result.scalar_one_or_none()
    
        # Check for any active subscription
        from app.models.subscription import Subscription, SubscriptionStatus
        sub_stmt = select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at > datetime.utcnow()
        )
        sub_result = await db.execute(sub_stmt)
        active_sub = sub_result.scalar_one_or_none()
    
        if active_sub:
            return {
                "has_trial": bool(trial),
                "can_start_trial": False,
                "trial_hours": None,
                "has_active_subscription": True
            }
    
        if not trial:
            # Check if trial is enabled
            settings = await get_trial_settings(db)
            return {
                "has_trial": False,
                "can_start_trial": settings.is_enabled,
                "trial_hours": settings.duration_hours,
                "has_active_subscription": False
            }
    
        return {
            "has_trial": True,
            "trial": {
                "id": str(trial.id),
                "status": trial.status,
                "started_at": trial.started_at.isoformat(),
                "expires_at": trial.expires_at.isoformat(),
                "hours_left": trial.hours_left,
                "is_active": trial.is_active
            },
            "has_active_subscription": False
        }


@router.post("/start")
async def start_trial(
    request: Request,
    data: TrialStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
        """Start a trial period for user, only if no active subscription"""
        # Get settings
        settings = await get_trial_settings(db)
    
        if not settings.is_enabled:
            raise HTTPException(status_code=400, detail="Trial period is currently disabled")
    
        # Check for any active subscription
        from app.models.subscription import Subscription, SubscriptionStatus
        sub_stmt = select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.expires_at > datetime.utcnow()
        )
        sub_result = await db.execute(sub_stmt)
        active_sub = sub_result.scalar_one_or_none()
        if active_sub:
            raise HTTPException(status_code=400, detail="You already have an active subscription")
    
        # Check if user already has/had a trial
        existing_stmt = select(Trial).where(Trial.user_id == current_user.id)
        existing_result = await db.execute(existing_stmt)
        existing_trial = existing_result.scalar_one_or_none()
    
        if existing_trial:
            if existing_trial.status == "active":
                raise HTTPException(status_code=400, detail="You already have an active trial")
            else:
                raise HTTPException(status_code=400, detail="You have already used your trial period")
    
        # Check IP limit
        client_ip = await get_client_ip(request)
        ip_count_stmt = select(func.count(Trial.id)).where(Trial.ip_address == client_ip)
        ip_count_result = await db.execute(ip_count_stmt)
        ip_count = ip_count_result.scalar() or 0
    
        if ip_count >= settings.max_trials_per_ip:
            raise HTTPException(status_code=400, detail="Trial limit reached for this IP address")
    
        # Create trial
        trial = Trial(
            user_id=current_user.id,
            status="active",
            duration_hours=settings.duration_hours,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=settings.duration_hours),
            source=data.source,
            ip_address=client_ip
        )
        db.add(trial)
        await db.flush()
    
        # Create VPN account for trial
        from app.services.vpn_service import VPNService
        vpn_service = VPNService(db)
    
        # Get best server for trial
        server_stmt = select(Server).where(Server.is_active == True).order_by(Server.current_users).limit(1)
        server_result = await db.execute(server_stmt)
        server = server_result.scalar_one_or_none()
    
        vpn_key = None
        if server:
            try:
                vpn_account = await vpn_service.create_trial_account(
                    user_id=str(current_user.id),
                    trial_id=str(trial.id),
                    server_id=str(server.id),
                    expires_at=trial.expires_at
                )
                if vpn_account and vpn_account.config:
                    import json
                    config = json.loads(vpn_account.config)
                    vpn_key = config.get("connection_string")
                    # vpn_account_id не существует в таблице trials - пропускаем
            except Exception as e:
                # Log error but don't fail
                pass
    
        await db.commit()
        await db.refresh(trial)
    
        return {
            "success": True,
            "trial": {
                "id": str(trial.id),
                "status": trial.status,
                "started_at": trial.started_at.isoformat(),
                "expires_at": trial.expires_at.isoformat(),
                "hours_left": trial.hours_left,
                "vpn_key": vpn_key
            },
            "message": f"Trial started! You have {settings.duration_hours} hours of free VPN access."
        }


@router.get("/check-eligible")
async def check_trial_eligible(
    request: Request,
    telegram_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
        """Check if a user is eligible for trial (public endpoint, also checks active subscription)"""
        settings = await get_trial_settings(db)
    
        if not settings.is_enabled:
            return {"eligible": False, "reason": "Trial disabled"}
    
        # Check by Telegram ID if provided
        if telegram_id:
            user_stmt = select(User).where(User.telegram_id == telegram_id)
            user_result = await db.execute(user_stmt)
            user = user_result.scalar_one_or_none()
        
            if user:
                # Check for active subscription
                from app.models.subscription import Subscription, SubscriptionStatus
                sub_stmt = select(Subscription).where(
                    Subscription.user_id == user.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                    Subscription.expires_at > datetime.utcnow()
                )
                sub_result = await db.execute(sub_stmt)
                active_sub = sub_result.scalar_one_or_none()
                if active_sub:
                    return {"eligible": False, "reason": "Active subscription"}
                trial_stmt = select(Trial).where(Trial.user_id == user.id)
                trial_result = await db.execute(trial_stmt)
                if trial_result.scalar_one_or_none():
                    return {"eligible": False, "reason": "Already used trial"}
    
        # Check by IP
        client_ip = await get_client_ip(request)
        ip_count_stmt = select(func.count(Trial.id)).where(Trial.ip_address == client_ip)
        ip_count_result = await db.execute(ip_count_stmt)
        ip_count = ip_count_result.scalar() or 0
    
        if ip_count >= settings.max_trials_per_ip:
            return {"eligible": False, "reason": "IP limit reached"}
    
        return {
            "eligible": True,
            "duration_hours": settings.duration_hours
        }


# ============== Admin Endpoints ==============

@router.get("/admin/settings")
async def get_admin_trial_settings(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get trial settings"""
    settings = await get_trial_settings(db)
    
    return {
        "is_enabled": settings.is_enabled,
        "duration_hours": settings.duration_hours,
        "max_per_ip": settings.max_per_ip,
        "require_telegram": settings.require_telegram
    }


@router.put("/admin/settings")
async def update_trial_settings(
    data: TrialSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Update trial settings"""
    settings = await get_trial_settings(db)
    
    if data.is_enabled is not None:
        settings.is_enabled = data.is_enabled
    if data.duration_hours is not None:
        settings.duration_hours = data.duration_hours
    if data.max_per_ip is not None:
        settings.max_per_ip = data.max_per_ip
    
    await db.commit()
    
    return {"success": True, "message": "Settings updated"}


@router.get("/admin/stats")
async def get_trial_stats(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Get trial statistics"""
    # Total trials
    total_stmt = select(func.count(Trial.id))
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0
    
    # Active trials
    active_stmt = select(func.count(Trial.id)).where(
        and_(
            Trial.status == "active",
            Trial.expires_at > datetime.utcnow()
        )
    )
    active_result = await db.execute(active_stmt)
    active = active_result.scalar() or 0
    
    # Converted trials
    converted_stmt = select(func.count(Trial.id)).where(Trial.status == "converted")
    converted_result = await db.execute(converted_stmt)
    converted = converted_result.scalar() or 0
    
    # Expired trials
    expired_stmt = select(func.count(Trial.id)).where(Trial.status == "expired")
    expired_result = await db.execute(expired_stmt)
    expired = expired_result.scalar() or 0
    
    # Today's trials
    today = datetime.utcnow().date()
    today_stmt = select(func.count(Trial.id)).where(
        func.date(Trial.created_at) == today
    )
    today_result = await db.execute(today_stmt)
    today_trials = today_result.scalar() or 0
    
    conversion_rate = (converted / total * 100) if total > 0 else 0
    
    return {
        "total_trials": total,
        "active_trials": active,
        "converted_trials": converted,
        "expired_trials": expired,
        "today_trials": today_trials,
        "conversion_rate": round(conversion_rate, 2)
    }
