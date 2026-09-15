"""
Partner Program API endpoints
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from pydantic import BaseModel, EmailStr
import uuid
import random
import string

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import (
    User, Payment,
    Partner, PartnerClick, PartnerSale, PartnerPayout, PartnerSettings,
    PartnerStatus, PartnerTier
)
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class PartnerApply(BaseModel):
    description: str
    telegram_channel: Optional[str] = None
    website: Optional[str] = None


class PartnerPayoutRequest(BaseModel):
    amount: float
    payout_method: str
    payout_details: dict


# ============== Helper Functions ==============

def generate_partner_code() -> str:
    """Generate unique partner code"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))


async def get_partner_settings(db: AsyncSession) -> PartnerSettings:
    """Get or create partner settings"""
    result = await db.execute(select(PartnerSettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = PartnerSettings(
            is_enabled=True,
            default_commission_rate=20.0,
            min_payout_amount=1000.0
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    
    return settings


# ============== Public Endpoints ==============

@router.get("/info")
async def get_partner_info(
    db: AsyncSession = Depends(get_db)
):
    """Get partner program info (public)"""
    settings = await get_partner_settings(db)
    
    if not settings.is_enabled:
        return {"enabled": False}
    
    return {
        "enabled": True,
        "default_commission": settings.default_commission_rate,
        "tiers": {
            "bronze": {"commission": settings.bronze_commission, "threshold": 0},
            "silver": {"commission": settings.silver_commission, "threshold": settings.silver_threshold},
            "gold": {"commission": settings.gold_commission, "threshold": settings.gold_threshold},
            "platinum": {"commission": settings.platinum_commission, "threshold": settings.platinum_threshold}
        },
        "min_payout": settings.min_payout_amount,
        "cookie_days": settings.cookie_lifetime_days,
        "description": settings.description
    }


@router.post("/apply")
async def apply_for_partnership(
    data: PartnerApply,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply to become a partner"""
    settings = await get_partner_settings(db)
    
    if not settings.is_enabled:
        raise HTTPException(status_code=400, detail="Partner program is currently closed")
    
    # Check if already a partner
    existing = await db.execute(
        select(Partner).where(Partner.user_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have a partner application")
    
    # Generate unique code
    code = generate_partner_code()
    while True:
        check = await db.execute(select(Partner).where(Partner.referral_code == code))
        if not check.scalar_one_or_none():
            break
        code = generate_partner_code()
    
    partner = Partner(
        user_id=current_user.id,
        referral_code=code,
        telegram_channel=data.telegram_channel,
        website=data.website,
        description=data.description,
        status="pending",
        tier="bronze",
        commission_percent=int(settings.default_commission_rate)
    )
    db.add(partner)
    await db.commit()
    
    return {
        "success": True,
        "message": "Application submitted! We'll review it within 24-48 hours.",
        "application_id": str(partner.id)
    }


@router.get("/my")
async def get_my_partner_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's partner account"""
    stmt = select(Partner).where(Partner.user_id == current_user.id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()
    
    if not partner:
        return {"has_account": False}
    
    return {
        "has_account": True,
        "partner": {
            "id": str(partner.id),
            "referral_code": partner.referral_code,
            "status": partner.status,
            "tier": partner.tier,
            "commission_rate": partner.commission_percent,
            "total_clicks": partner.total_clicks or 0,
            "total_sales": partner.total_sales or 0,
            "total_earned": float(partner.total_earned or 0),
            "pending_payout": float(partner.pending_payout or 0),
            "referral_link": f"https://vpn.metalib.xyz/?ref={partner.referral_code}",
            "created_at": partner.created_at.isoformat() if partner.created_at else None
        }
    }


@router.get("/my/stats")
async def get_my_partner_stats(
    period: str = "30d",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get partner statistics"""
    stmt = select(Partner).where(Partner.user_id == current_user.id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()
    
    if not partner or partner.status != "approved":
        raise HTTPException(status_code=404, detail="Partner account not found or not approved")
    
    # Calculate period
    if period == "7d":
        since = datetime.utcnow() - timedelta(days=7)
    elif period == "30d":
        since = datetime.utcnow() - timedelta(days=30)
    elif period == "90d":
        since = datetime.utcnow() - timedelta(days=90)
    else:
        since = datetime.utcnow() - timedelta(days=30)
    
    # Clicks
    clicks_stmt = select(func.count(PartnerClick.id)).where(
        and_(PartnerClick.partner_id == partner.id, PartnerClick.created_at >= since)
    )
    clicks_result = await db.execute(clicks_stmt)
    clicks = clicks_result.scalar() or 0
    
    # Sales
    sales_stmt = select(PartnerSale).where(
        and_(PartnerSale.partner_id == partner.id, PartnerSale.created_at >= since)
    )
    sales_result = await db.execute(sales_stmt)
    sales = sales_result.scalars().all()
    
    total_sales = len(sales)
    total_revenue = sum(s.sale_amount for s in sales)
    total_commission = sum(s.commission_amount for s in sales)
    
    conversion_rate = (total_sales / clicks * 100) if clicks > 0 else 0
    
    return {
        "period": period,
        "clicks": clicks,
        "sales": total_sales,
        "revenue": total_revenue,
        "commission": total_commission,
        "conversion_rate": round(conversion_rate, 2)
    }


@router.post("/my/payout")
async def request_payout(
    data: PartnerPayoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Request payout"""
    stmt = select(Partner).where(Partner.user_id == current_user.id)
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()
    
    if not partner or partner.status != PartnerStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Partner account not found")
    
    settings = await get_partner_settings(db)
    
    if partner.balance < settings.min_payout_amount:
        raise HTTPException(
            status_code=400, 
            detail=f"Minimum payout amount is {settings.min_payout_amount}₽"
        )
    
    if data.amount > partner.balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    payout = PartnerPayout(
        partner_id=partner.id,
        amount=data.amount,
        payout_method=data.payout_method,
        payout_details=data.payout_details,
        status="pending"
    )
    db.add(payout)
    
    partner.balance -= data.amount
    
    await db.commit()
    
    return {
        "success": True,
        "payout_id": str(payout.id),
        "message": "Payout request submitted. Processing time: 1-3 business days."
    }


@router.post("/track/click")
async def track_click(
    partner_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Track partner referral click"""
    stmt = select(Partner).where(
        and_(Partner.partner_code == partner_code, Partner.status == PartnerStatus.APPROVED)
    )
    result = await db.execute(stmt)
    partner = result.scalar_one_or_none()
    
    if not partner:
        return {"tracked": False}
    
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    
    click = PartnerClick(
        partner_id=partner.id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent", "")[:500],
        referrer=request.headers.get("Referer", "")[:500]
    )
    db.add(click)
    
    partner.total_clicks += 1
    
    await db.commit()
    
    return {"tracked": True}


# ============== Admin Endpoints ==============

@router.get("/admin/partners")
async def admin_list_partners(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: List all partners"""
    stmt = select(Partner).order_by(Partner.created_at.desc())
    
    if status:
        stmt = stmt.where(Partner.status == PartnerStatus(status))
    
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    partners = result.scalars().all()
    
    return {
        "partners": [
            {
                "id": str(p.id),
                "name": p.name,
                "email": p.email,
                "partner_code": p.partner_code,
                "status": p.status.value,
                "tier": p.tier.value,
                "commission_rate": p.commission_rate,
                "total_sales": p.total_sales,
                "total_earned": p.total_earned,
                "balance": p.balance,
                "created_at": p.created_at.isoformat()
            }
            for p in partners
        ]
    }


@router.post("/admin/partners/{partner_id}/approve")
async def admin_approve_partner(
    partner_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Approve partner application"""
    partner = await db.get(Partner, uuid.UUID(partner_id))
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner.status = PartnerStatus.APPROVED
    partner.approved_at = datetime.utcnow()
    partner.approved_by = admin.id
    
    await db.commit()
    
    # TODO: Send notification to partner
    
    return {"success": True, "message": "Partner approved"}


@router.post("/admin/partners/{partner_id}/reject")
async def admin_reject_partner(
    partner_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Reject partner application"""
    partner = await db.get(Partner, uuid.UUID(partner_id))
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner.status = PartnerStatus.REJECTED
    
    await db.commit()
    
    return {"success": True}


@router.get("/admin/payouts")
async def admin_list_payouts(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: List payout requests"""
    stmt = select(PartnerPayout).order_by(PartnerPayout.created_at.desc())
    
    if status:
        stmt = stmt.where(PartnerPayout.status == status)
    
    stmt = stmt.limit(100)
    result = await db.execute(stmt)
    payouts = result.scalars().all()
    
    return {
        "payouts": [
            {
                "id": str(p.id),
                "partner_id": str(p.partner_id),
                "amount": p.amount,
                "payout_method": p.payout_method,
                "status": p.status,
                "created_at": p.created_at.isoformat()
            }
            for p in payouts
        ]
    }


@router.post("/admin/payouts/{payout_id}/process")
async def admin_process_payout(
    payout_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Mark payout as processed"""
    payout = await db.get(PartnerPayout, uuid.UUID(payout_id))
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    
    payout.status = "completed"
    payout.completed_at = datetime.utcnow()
    payout.processed_by = admin.id
    
    await db.commit()
    
    return {"success": True}


@router.get("/admin/settings")
async def admin_get_partner_settings(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Get partner program settings"""
    settings = await get_partner_settings(db)
    
    return {
        "is_enabled": settings.is_enabled,
        "default_commission_rate": settings.default_commission_rate,
        "bronze_commission": settings.bronze_commission,
        "silver_commission": settings.silver_commission,
        "gold_commission": settings.gold_commission,
        "platinum_commission": settings.platinum_commission,
        "silver_threshold": settings.silver_threshold,
        "gold_threshold": settings.gold_threshold,
        "platinum_threshold": settings.platinum_threshold,
        "min_payout_amount": settings.min_payout_amount,
        "cookie_lifetime_days": settings.cookie_lifetime_days
    }
