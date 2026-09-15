"""
Referral system API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer, case
from typing import List
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_admin, get_bot_user
from app.models.referral import Referral, ReferralStatus
from app.models.user import User
from app.models.payment import Payment

router = APIRouter()


# Pydantic schemas
class ReferralStatItem(BaseModel):
    user_id: str
    telegram_id: int
    username: str | None
    first_name: str | None
    referrals_count: int
    completed_referrals: int
    total_bonus_days: int
    conversion_rate: float


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    completed_referrals: int
    pending_referrals: int
    total_bonus_days: int
    top_referrers: List[ReferralStatItem]


class UserReferralInfo(BaseModel):
    referral_code: str
    referrals_count: int
    completed_count: int
    pending_count: int
    total_bonus_days: int
    referrals: List[dict]


# Admin endpoints
@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get referral system statistics (Admin only)"""
    
    # Total referrals
    total_query = select(func.count(Referral.id))
    total_result = await db.execute(total_query)
    total_referrals = total_result.scalar() or 0
    
    # Completed referrals
    completed_query = select(func.count(Referral.id)).where(
        Referral.status == ReferralStatus.COMPLETED
    )
    completed_result = await db.execute(completed_query)
    completed_referrals = completed_result.scalar() or 0
    
    # Pending referrals
    pending_query = select(func.count(Referral.id)).where(
        Referral.status == ReferralStatus.PENDING
    )
    pending_result = await db.execute(pending_query)
    pending_referrals = pending_result.scalar() or 0
    
    # Total bonus days
    bonus_query = select(func.sum(Referral.bonus_days)).where(
        Referral.status == ReferralStatus.COMPLETED
    )
    bonus_result = await db.execute(bonus_query)
    total_bonus_days = bonus_result.scalar() or 0
    
    # Top referrers
    top_referrers_query = select(
        User.id,
        User.telegram_id,
        User.username,
        User.first_name,
        func.count(Referral.id).label('referrals_count'),
        func.sum(
            case((Referral.status == ReferralStatus.COMPLETED, 1), else_=0)
        ).label('completed_count'),
        func.coalesce(func.sum(Referral.bonus_days), 0).label('total_bonus_days')
    ).join(
        Referral, User.id == Referral.referrer_id
    ).group_by(
        User.id
    ).order_by(
        func.count(Referral.id).desc()
    ).limit(10)
    
    top_result = await db.execute(top_referrers_query)
    top_referrers = []
    
    for row in top_result.all():
        conversion_rate = 0
        if row.referrals_count > 0:
            conversion_rate = (row.completed_count / row.referrals_count) * 100
        
        top_referrers.append(ReferralStatItem(
            user_id=str(row.id),
            telegram_id=row.telegram_id,
            username=row.username,
            first_name=row.first_name,
            referrals_count=row.referrals_count,
            completed_referrals=row.completed_count or 0,
            total_bonus_days=int(row.total_bonus_days or 0),
            conversion_rate=round(conversion_rate, 1)
        ))
    
    return ReferralStatsResponse(
        total_referrals=total_referrals,
        completed_referrals=completed_referrals,
        pending_referrals=pending_referrals,
        total_bonus_days=int(total_bonus_days),
        top_referrers=top_referrers
    )


# Bot endpoints
@router.get("/me", response_model=UserReferralInfo)
async def get_my_referral_info(
    user: User = Depends(get_bot_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's referral info"""
    
    # Generate referral code if not exists
    if not user.referral_code:
        import secrets
        user.referral_code = f"REF{secrets.token_hex(4).upper()}"
        await db.commit()
        await db.refresh(user)
    
    # Get referrals
    referrals_query = select(Referral).where(
        Referral.referrer_id == user.id
    ).order_by(Referral.created_at.desc())
    referrals_result = await db.execute(referrals_query)
    referrals = referrals_result.scalars().all()
    
    # Count stats
    completed_count = sum(1 for r in referrals if r.status == ReferralStatus.COMPLETED)
    pending_count = sum(1 for r in referrals if r.status == ReferralStatus.PENDING)
    total_bonus_days = sum(int(r.bonus_days or 0) for r in referrals if r.status == ReferralStatus.COMPLETED)
    
    # Format referrals list
    referrals_list = []
    for ref in referrals:
        # Get referred user info
        referred_query = select(User).where(User.id == ref.referred_id)
        referred_result = await db.execute(referred_query)
        referred_user = referred_result.scalar_one_or_none()
        
        if referred_user:
            referrals_list.append({
                'id': str(ref.id),
                'username': referred_user.username,
                'first_name': referred_user.first_name,
                'status': ref.status.value,
                'bonus_days': int(ref.bonus_days or 0),
                'created_at': ref.created_at.isoformat()
            })
    
    return UserReferralInfo(
        referral_code=user.referral_code,
        referrals_count=len(referrals),
        completed_count=completed_count,
        pending_count=pending_count,
        total_bonus_days=total_bonus_days,
        referrals=referrals_list
    )


@router.post("/apply/{referral_code}")
async def apply_referral_code(
    referral_code: str,
    user: User = Depends(get_bot_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply referral code for current user"""
    
    # Check if user already has a referrer
    if user.referrer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a referrer"
        )
    
    # Find referrer by code
    referrer_query = select(User).where(User.referral_code == referral_code.upper())
    referrer_result = await db.execute(referrer_query)
    referrer = referrer_result.scalar_one_or_none()
    
    if not referrer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code"
        )
    
    # Can't refer yourself
    if referrer.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot refer yourself"
        )
    
    # Create referral record
    referral = Referral(
        referrer_id=referrer.id,
        referred_id=user.id,
        status=ReferralStatus.PENDING
    )
    
    user.referrer_id = referrer.id
    
    db.add(referral)
    await db.commit()
    
    return {"message": "Referral code applied successfully"}


@router.get("/status")
async def get_referral_status():
    """Get referral program status for bot"""
    from app.api.v1.endpoints.admin import _system_settings
    
    return {
        "enabled": _system_settings.get("referrals_enabled", True),
        "bonus_days": _system_settings.get("referral_bonus_days", 3)
    }


class ReferralSettingsUpdate(BaseModel):
    enabled: bool | None = None
    bonus_days: int | None = None


@router.put("/settings")
async def update_referral_settings(
    settings: ReferralSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update referral system settings (Admin only)"""
    from app.api.v1.endpoints.admin import _system_settings
    
    if settings.enabled is not None:
        _system_settings["referrals_enabled"] = settings.enabled
    if settings.bonus_days is not None:
        _system_settings["referral_bonus_days"] = settings.bonus_days
    
    return {
        "enabled": _system_settings.get("referrals_enabled", True),
        "bonus_days": _system_settings.get("referral_bonus_days", 3)
    }

