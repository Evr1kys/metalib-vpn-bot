"""
Promotions & Savings Calculator API endpoints
"""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models import (
    Promotion, SavingsCalculatorConfig, PromotionUse, PromoType, Plan
)
from app.api.deps import get_current_admin

router = APIRouter()


# ============== Schemas ==============

class PromotionCreate(BaseModel):
    name: str
    name_en: Optional[str] = None
    description: Optional[str] = None
    promo_type: str = "discount"
    discount_percent: Optional[int] = None
    discount_amount: Optional[float] = None
    free_days: Optional[int] = None
    starts_at: datetime
    ends_at: datetime
    show_timer: bool = True
    timer_title: Optional[str] = None
    show_on_website: bool = True
    show_in_bot: bool = True
    max_uses: Optional[int] = None


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_percent: Optional[int] = None
    ends_at: Optional[datetime] = None
    is_active: Optional[bool] = None


# ============== Public Endpoints ==============

@router.get("/active")
async def get_active_promotions(
    db: AsyncSession = Depends(get_db)
):
    """Get currently active promotions (public)"""
    now = datetime.utcnow()
    
    stmt = select(Promotion).where(
        and_(
            Promotion.is_active == True,
            Promotion.starts_at <= now,
            Promotion.ends_at > now,
            Promotion.show_on_website == True
        )
    ).order_by(Promotion.ends_at)
    
    result = await db.execute(stmt)
    promotions = result.scalars().all()
    
    return {
        "promotions": [
            {
                "id": str(p.id),
                "name": p.name,
                "name_en": p.name_en,
                "description": p.description,
                "promo_type": p.promo_type.value,
                "discount_percent": p.discount_percent,
                "discount_amount": p.discount_amount,
                "free_days": p.free_days,
                "ends_at": p.ends_at.isoformat(),
                "time_left_seconds": p.time_left_seconds,
                "show_timer": p.show_timer,
                "timer_title": p.timer_title,
                "banner_url": p.banner_url,
                "banner_text": p.banner_text,
                "banner_color": p.banner_color
            }
            for p in promotions
        ]
    }


@router.get("/timer")
async def get_promo_timer(
    db: AsyncSession = Depends(get_db)
):
    """Get active promotion timer for website header"""
    now = datetime.utcnow()
    
    stmt = select(Promotion).where(
        and_(
            Promotion.is_active == True,
            Promotion.starts_at <= now,
            Promotion.ends_at > now,
            Promotion.show_timer == True,
            Promotion.show_on_website == True
        )
    ).order_by(Promotion.ends_at).limit(1)
    
    result = await db.execute(stmt)
    promo = result.scalar_one_or_none()
    
    if not promo:
        return {"has_timer": False}
    
    return {
        "has_timer": True,
        "title": promo.timer_title or promo.name,
        "discount_percent": promo.discount_percent,
        "ends_at": promo.ends_at.isoformat(),
        "time_left_seconds": promo.time_left_seconds
    }


@router.get("/savings-calculator")
async def get_savings_calculator(
    db: AsyncSession = Depends(get_db)
):
    """Get savings calculator config and plan prices"""
    # Get config
    config_result = await db.execute(select(SavingsCalculatorConfig).limit(1))
    config = config_result.scalar_one_or_none()
    
    if not config:
        config = SavingsCalculatorConfig(is_enabled=True)
    
    if not config.is_enabled:
        return {"enabled": False}
    
    # Get plans
    plans_stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.duration_days)
    plans_result = await db.execute(plans_stmt)
    plans = plans_result.scalars().all()
    
    # Calculate savings
    competitor_yearly = float(config.competitor_monthly_price or 500) * 12
    
    plan_data = []
    for plan in plans:
        # Price per month for this plan
        monthly_equivalent = (float(plan.price) / plan.duration_days) * 30
        yearly_equivalent = monthly_equivalent * 12
        
        savings_amount = competitor_yearly - yearly_equivalent
        savings_percent = (savings_amount / competitor_yearly) * 100 if competitor_yearly > 0 else 0
        
        plan_data.append({
            "id": str(plan.id),
            "name": plan.name,
            "duration_days": plan.duration_days,
            "price": float(plan.price),
            "monthly_equivalent": round(monthly_equivalent, 0),
            "yearly_equivalent": round(yearly_equivalent, 0),
            "savings_vs_competitor": round(savings_amount, 0),
            "savings_percent": round(savings_percent, 0)
        })
    
    return {
        "enabled": True,
        "title": config.title,
        "title_en": config.title_en,
        "description": config.description,
        "competitor_name": config.competitor_name,
        "competitor_monthly_price": config.competitor_monthly_price,
        "competitor_yearly_price": competitor_yearly,
        "plans": plan_data
    }


# ============== Admin Endpoints ==============

@router.get("/admin/list")
async def admin_list_promotions(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: List all promotions"""
    stmt = select(Promotion).order_by(Promotion.created_at.desc())
    
    if active_only:
        now = datetime.utcnow()
        stmt = stmt.where(
            and_(
                Promotion.is_active == True,
                Promotion.ends_at > now
            )
        )
    
    result = await db.execute(stmt)
    promotions = result.scalars().all()
    
    return {
        "promotions": [
            {
                "id": str(p.id),
                "name": p.name,
                "promo_type": p.promo_type.value,
                "discount_percent": p.discount_percent,
                "starts_at": p.starts_at.isoformat(),
                "ends_at": p.ends_at.isoformat(),
                "is_active": p.is_active,
                "is_running": p.is_running,
                "current_uses": p.current_uses,
                "max_uses": p.max_uses
            }
            for p in promotions
        ]
    }


@router.post("/admin/create")
async def admin_create_promotion(
    data: PromotionCreate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Create promotion"""
    promotion = Promotion(
        name=data.name,
        name_en=data.name_en,
        description=data.description,
        promo_type=PromoType(data.promo_type),
        discount_percent=data.discount_percent,
        discount_amount=data.discount_amount,
        free_days=data.free_days,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        show_timer=data.show_timer,
        timer_title=data.timer_title,
        show_on_website=data.show_on_website,
        show_in_bot=data.show_in_bot,
        max_uses=data.max_uses,
        is_active=True
    )
    db.add(promotion)
    await db.commit()
    await db.refresh(promotion)
    
    return {"id": str(promotion.id), "message": "Promotion created"}


@router.put("/admin/{promotion_id}")
async def admin_update_promotion(
    promotion_id: str,
    data: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Update promotion"""
    promotion = await db.get(Promotion, uuid.UUID(promotion_id))
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    if data.name is not None:
        promotion.name = data.name
    if data.description is not None:
        promotion.description = data.description
    if data.discount_percent is not None:
        promotion.discount_percent = data.discount_percent
    if data.ends_at is not None:
        promotion.ends_at = data.ends_at
    if data.is_active is not None:
        promotion.is_active = data.is_active
    
    await db.commit()
    
    return {"success": True}


@router.delete("/admin/{promotion_id}")
async def admin_delete_promotion(
    promotion_id: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Delete promotion"""
    promotion = await db.get(Promotion, uuid.UUID(promotion_id))
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    await db.delete(promotion)
    await db.commit()
    
    return {"success": True}


@router.get("/admin/calculator-config")
async def admin_get_calculator_config(
    db: AsyncSession = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """Admin: Get savings calculator config"""
    result = await db.execute(select(SavingsCalculatorConfig).limit(1))
    config = result.scalar_one_or_none()
    
    if not config:
        return {
            "is_enabled": True,
            "title": "Калькулятор экономии",
            "competitor_monthly_price": 500,
            "competitor_name": "Другие VPN"
        }
    
    return {
        "is_enabled": config.is_enabled,
        "title": config.title,
        "title_en": config.title_en,
        "description": config.description,
        "competitor_monthly_price": config.competitor_monthly_price,
        "competitor_name": config.competitor_name
    }
