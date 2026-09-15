"""
Payments endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.services.payment_service import PaymentService
from app.api.deps import verify_bot_token
from app.models import User

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class PaymentCreateRequest(BaseModel):
    """Payment creation request"""
    user_id: str  # This is telegram_id as string
    plan_id: str
    promo_code: str | None = None


class PaymentResponse(BaseModel):
    """Payment response"""
    id: str
    payment_url: str
    amount: float
    currency: str
    status: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=PaymentResponse, dependencies=[Depends(verify_bot_token)])
@limiter.limit("10/minute")  # Rate limit: max 10 payments per minute per IP
async def create_payment(
    request: Request,
    payment_data: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create new payment"""
    # user_id is actually telegram_id, so find user by telegram_id
    telegram_id = int(payment_data.user_id)
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    payment_service = PaymentService(db)
    
    try:
        payment = await payment_service.create_payment(
            user_id=str(user.id),  # Pass actual UUID
            plan_id=payment_data.plan_id,
            promo_code=payment_data.promo_code,
        )
        
        return PaymentResponse(
            id=str(payment.id),
            payment_url=payment.payment_url or "",
            amount=float(payment.amount),
            currency=payment.currency,
            status=payment.status.value,
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{payment_id}", response_model=PaymentResponse, dependencies=[Depends(verify_bot_token)])
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get payment by ID"""
    from app.models import Payment
    
    payment = await db.get(Payment, payment_id)
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return PaymentResponse(
        id=str(payment.id),
        payment_url=payment.payment_url or "",
        amount=float(payment.amount),
        currency=payment.currency,
        status=payment.status.value,
    )
