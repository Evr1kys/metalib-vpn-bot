"""
Promo codes API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_admin, verify_bot_token
from app.models.promo_code import PromoCode, DiscountType, PromoCodeUse
from app.models.user import User
from app.models.payment import Payment

router = APIRouter()


# Validation schema
class PromoCodeValidateRequest(BaseModel):
    code: str
    user_id: str | None = None
    plan_id: str | None = None


# Pydantic schemas
class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    discount_type: DiscountType
    discount_value: float = Field(..., gt=0)
    plan_ids: List[str] | None = None
    min_purchase_amount: float | None = None
    max_uses: int | None = None
    max_uses_per_user: int = 1
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True


class PromoCodeUpdate(BaseModel):
    discount_type: DiscountType | None = None
    discount_value: float | None = Field(None, gt=0)
    plan_ids: List[str] | None = None
    min_purchase_amount: float | None = None
    max_uses: int | None = None
    max_uses_per_user: int | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class PromoCodeResponse(BaseModel):
    id: str
    code: str
    discount_type: DiscountType
    discount_value: float
    plan_ids: List[str] | None
    min_purchase_amount: float | None
    max_uses: int | None
    max_uses_per_user: int
    used_count: int
    starts_at: datetime | None
    expires_at: datetime | None
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PromoCodeStatsResponse(BaseModel):
    total_codes: int
    active_codes: int
    total_uses: int
    total_discount_given: float


@router.get("/", response_model=List[PromoCodeResponse])
async def list_promo_codes(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get all promo codes"""
    query = select(PromoCode)
    
    if active_only:
        query = query.where(
            and_(
                PromoCode.is_active == True,
                func.coalesce(PromoCode.expires_at, datetime.max) > datetime.utcnow()
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(PromoCode.created_at.desc())
    result = await db.execute(query)
    codes = result.scalars().all()
    
    return [PromoCodeResponse.model_validate(code) for code in codes]


@router.get("/stats", response_model=PromoCodeStatsResponse)
async def get_promo_codes_stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get promo codes statistics"""
    # Total codes
    total_query = select(func.count(PromoCode.id))
    total_result = await db.execute(total_query)
    total_codes = total_result.scalar() or 0
    
    # Active codes
    active_query = select(func.count(PromoCode.id)).where(
        and_(
            PromoCode.is_active == True,
            func.coalesce(PromoCode.expires_at, datetime.max) > datetime.utcnow()
        )
    )
    active_result = await db.execute(active_query)
    active_codes = active_result.scalar() or 0
    
    # Total uses
    uses_query = select(func.sum(PromoCode.used_count))
    uses_result = await db.execute(uses_query)
    total_uses = uses_result.scalar() or 0
    
    # Total discount given (from payments with promo codes)
    discount_query = select(func.sum(Payment.discount_amount)).where(
        Payment.promo_code_id.isnot(None)
    )
    discount_result = await db.execute(discount_query)
    total_discount = discount_result.scalar() or 0
    
    return PromoCodeStatsResponse(
        total_codes=total_codes,
        active_codes=active_codes,
        total_uses=total_uses,
        total_discount_given=float(total_discount)
    )


@router.post("/", response_model=PromoCodeResponse, status_code=status.HTTP_201_CREATED)
async def create_promo_code(
    promo_data: PromoCodeCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create new promo code"""
    # Check if code already exists
    existing = await db.execute(
        select(PromoCode).where(PromoCode.code == promo_data.code.upper())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promo code with this code already exists"
        )
    
    # Create promo code
    promo_code = PromoCode(
        code=promo_data.code.upper(),
        discount_type=promo_data.discount_type,
        discount_value=promo_data.discount_value,
        plan_ids=promo_data.plan_ids,
        min_purchase_amount=promo_data.min_purchase_amount,
        max_uses=promo_data.max_uses,
        max_uses_per_user=promo_data.max_uses_per_user,
        starts_at=promo_data.starts_at,
        expires_at=promo_data.expires_at,
        is_active=promo_data.is_active
    )
    
    db.add(promo_code)
    await db.commit()
    await db.refresh(promo_code)
    
    return PromoCodeResponse.model_validate(promo_code)


@router.get("/{promo_code_id}", response_model=PromoCodeResponse)
async def get_promo_code(
    promo_code_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get promo code by ID"""
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_code_id)
    )
    promo_code = result.scalar_one_or_none()
    
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found"
        )
    
    return PromoCodeResponse.model_validate(promo_code)


@router.patch("/{promo_code_id}", response_model=PromoCodeResponse)
async def update_promo_code(
    promo_code_id: str,
    promo_data: PromoCodeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Update promo code"""
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_code_id)
    )
    promo_code = result.scalar_one_or_none()
    
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found"
        )
    
    # Update fields
    update_data = promo_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(promo_code, field, value)
    
    await db.commit()
    await db.refresh(promo_code)
    
    return PromoCodeResponse.model_validate(promo_code)


@router.delete("/{promo_code_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_promo_code(
    promo_code_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete promo code"""
    result = await db.execute(
        select(PromoCode).where(PromoCode.id == promo_code_id)
    )
    promo_code = result.scalar_one_or_none()
    
    if not promo_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promo code not found"
        )
    
    await db.delete(promo_code)
    await db.commit()


# Bot endpoint for promo code validation (no admin auth required)
from app.api.deps import verify_bot_token

@router.post("/validate")
async def validate_promo_code(
    data: PromoCodeValidateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate promo code for bot users.
    Returns promo code details if valid, or error if invalid.
    """
    # Find promo code
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == data.code.upper())
    )
    promo_code = result.scalar_one_or_none()
    
    if not promo_code:
        return {"valid": False, "error": "Promo code not found"}
    
    # Check if active
    if not promo_code.is_active:
        return {"valid": False, "error": "Promo code is inactive"}
    
    # Check expiry
    if promo_code.expires_at and datetime.utcnow() > promo_code.expires_at:
        return {"valid": False, "error": "Promo code expired"}
    
    # Check start date
    if promo_code.starts_at and datetime.utcnow() < promo_code.starts_at:
        return {"valid": False, "error": "Promo code not yet active"}
    
    # Check max uses
    if promo_code.max_uses and promo_code.used_count >= promo_code.max_uses:
        return {"valid": False, "error": "Promo code usage limit reached"}
    
    # Check max uses per user
    if data.user_id and promo_code.max_uses_per_user > 0:
        user_uses_query = select(func.count(PromoCodeUse.id)).where(
            and_(
                PromoCodeUse.promo_code_id == promo_code.id,
                PromoCodeUse.user_id == data.user_id
            )
        )
        user_uses_result = await db.execute(user_uses_query)
        user_uses = user_uses_result.scalar() or 0
        
        if user_uses >= promo_code.max_uses_per_user:
            return {"valid": False, "error": "You have already used this promo code"}
    
    # Check plan restriction
    if data.plan_id and promo_code.plan_ids:
        import uuid
        plan_uuid = uuid.UUID(data.plan_id)
        if plan_uuid not in promo_code.plan_ids:
            return {"valid": False, "error": "Promo code not valid for this plan"}
    
    return {
        "valid": True,
        "promo_code": {
            "id": str(promo_code.id),
            "code": promo_code.code,
            "discount_type": promo_code.discount_type.value,
            "discount_value": float(promo_code.discount_value)
        }
    }


class ApplyFreePromoRequest(BaseModel):
    code: str
    user_telegram_id: int


@router.post("/apply-free", dependencies=[Depends(verify_bot_token)])
async def apply_free_promo_code(
    data: ApplyFreePromoRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Apply a free_plan promo code - creates subscription for user.
    SECURITY: Protected by bot token - only bot can apply promos.
    """
    from app.models.subscription import Subscription, SubscriptionStatus
    from app.models.plan import Plan
    from app.services.subscription_service import SubscriptionService
    from datetime import datetime, timedelta
    
    # Find promo code
    result = await db.execute(
        select(PromoCode).where(PromoCode.code == data.code.upper())
    )
    promo_code = result.scalar_one_or_none()
    
    if not promo_code:
        return {"success": False, "error": "Промокод не найден"}
    
    # Check if it's a free_plan type
    if promo_code.discount_type != DiscountType.FREE_PLAN:
        return {"success": False, "error": "Этот промокод не для бесплатного тарифа"}
    
    # Check validity
    if not promo_code.is_valid():
        return {"success": False, "error": "Промокод истек или недействителен"}
    
    # Find user
    user_result = await db.execute(
        select(User).where(User.telegram_id == data.user_telegram_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        return {"success": False, "error": "Пользователь не найден"}
    
    # Check if user already used this promo
    if promo_code.max_uses_per_user > 0:
        uses_result = await db.execute(
            select(func.count(PromoCodeUse.id)).where(
                and_(
                    PromoCodeUse.promo_code_id == promo_code.id,
                    PromoCodeUse.user_id == user.id
                )
            )
        )
        user_uses = uses_result.scalar() or 0
        if user_uses >= promo_code.max_uses_per_user:
            return {"success": False, "error": "Вы уже использовали этот промокод"}
    
    # Get the plan from promo code
    if not promo_code.plan_ids or len(promo_code.plan_ids) == 0:
        return {"success": False, "error": "Промокод не привязан к тарифу"}
    
    plan_id = promo_code.plan_ids[0]
    plan = await db.get(Plan, plan_id)
    
    if not plan:
        return {"success": False, "error": "Тариф не найден"}
    
    # Check if user already has active subscription
    active_sub_result = await db.execute(
        select(Subscription).where(
            and_(
                Subscription.user_id == user.id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
    )
    existing_sub = active_sub_result.scalar_one_or_none()
    
    if existing_sub:
        return {"success": False, "error": "У вас уже есть активная подписка"}
    
    try:
        # Create subscription using SubscriptionService
        subscription_service = SubscriptionService(db)
        subscription = await subscription_service.create_subscription(
            user_id=user.id,
            plan_id=plan.id,
            is_trial=False,
            is_promo=True
        )
        
        # Record promo code use
        promo_use = PromoCodeUse(
            promo_code_id=promo_code.id,
            user_id=user.id,
            payment_id=None,  # No payment for free promo
            subscription_id=subscription.id,  # Link to created subscription
            discount_amount=float(plan.price)  # Full price as discount
        )
        db.add(promo_use)
        
        # Increment used count
        promo_code.used_count += 1
        
        await db.commit()
        
        return {
            "success": True,
            "plan_name": plan.name,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
        }
        
    except Exception as e:
        await db.rollback()
        return {"success": False, "error": f"Ошибка создания подписки: {str(e)}"}

