"""
Web API endpoints for website integration
Telegram Login Widget authentication + user dashboard
"""
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models import User, Subscription, Plan, Payment, VPNAccount
from app.core.logging import logger

router = APIRouter()


class TelegramAuthData(BaseModel):
    """Telegram Login Widget data"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class WebAuthResponse(BaseModel):
    """Response for web authentication"""
    success: bool
    token: Optional[str] = None
    user: Optional[dict] = None
    error: Optional[str] = None


class UserDashboard(BaseModel):
    """User dashboard data"""
    user: dict
    subscription: Optional[dict] = None
    vpn_keys: List[dict] = []
    payments: List[dict] = []


class CreatePaymentRequest(BaseModel):
    """Request to create payment"""
    plan_id: str


def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    """Verify Telegram Login Widget authentication"""
    check_hash = data.pop('hash', None)
    if not check_hash:
        return False
    
    # Create data check string
    data_check_arr = [f"{k}={v}" for k, v in sorted(data.items()) if v is not None]
    data_check_string = "\n".join(data_check_arr)
    
    # Create secret key from bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == check_hash


@router.post("/auth/telegram", response_model=WebAuthResponse)
async def telegram_auth(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user via Telegram Login Widget
    Creates user if not exists, returns JWT token
    """
    try:
        # Verify auth data
        data_dict = auth_data.model_dump()
        if not verify_telegram_auth(data_dict.copy(), settings.telegram_bot_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Telegram authentication"
            )
        
        # Check auth_date (not older than 1 day)
        if datetime.utcnow().timestamp() - auth_data.auth_date > 86400:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication expired"
            )
        
        # Find or create user
        result = await db.execute(
            select(User).where(User.telegram_id == auth_data.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(
                telegram_id=auth_data.id,
                username=auth_data.username,
                first_name=auth_data.first_name,
                last_name=auth_data.last_name,
                photo_url=auth_data.photo_url,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"New user registered via web: {auth_data.id}")
        else:
            # Update user info
            user.username = auth_data.username or user.username
            user.first_name = auth_data.first_name
            user.last_name = auth_data.last_name or user.last_name
            user.photo_url = auth_data.photo_url or user.photo_url
            await db.commit()
        
        # Create JWT token
        token = create_access_token(
            data={"sub": str(user.id), "telegram_id": user.telegram_id},
            expires_delta=timedelta(days=7)
        )
        
        return WebAuthResponse(
            success=True,
            token=token,
            user={
                "id": str(user.id),
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "photo_url": user.photo_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Telegram auth error: {e}")
        return WebAuthResponse(success=False, error=str(e))


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Get all active plans (public endpoint)"""
    result = await db.execute(
        select(Plan).where(Plan.is_active == True).order_by(Plan.duration_days)
    )
    plans = result.scalars().all()
    
    return {
        "plans": [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "duration_days": p.duration_days,
                "description": p.description,
                "features": p.features if hasattr(p, 'features') else None,
                "max_devices": p.max_devices if hasattr(p, 'max_devices') else 5
            }
            for p in plans
        ]
    }


@router.get("/dashboard")
async def get_dashboard(
    token: str = Query(..., description="JWT token"),
    db: AsyncSession = Depends(get_db)
):
    """Get user dashboard data"""
    from jose import jwt, JWTError
    
    try:
        # Decode token
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get active subscription
        sub_result = await db.execute(
            select(Subscription)
            .where(and_(
                Subscription.user_id == user_id,
                Subscription.status == "active",
                Subscription.expires_at > datetime.utcnow()
            ))
            .order_by(Subscription.expires_at.desc())
        )
        subscription = sub_result.scalar_one_or_none()
        
        # Get VPN keys
        vpn_keys = []
        if subscription:
            keys_result = await db.execute(
                select(VPNAccount)
                .where(VPNAccount.subscription_id == subscription.id)
            )
            vpn_accounts = keys_result.scalars().all()
            for acc in vpn_accounts:
                config_data = json.loads(acc.config) if acc.config else {}
                vpn_keys.append({
                    "id": str(acc.id),
                    "protocol": acc.protocol.value if hasattr(acc.protocol, 'value') else str(acc.protocol),
                    "server": str(acc.server_id) if acc.server_id else None,
                    "connection_string": config_data.get("connection_string"),
                    "status": acc.status.value if hasattr(acc.status, 'value') else str(acc.status),
                    "created_at": acc.created_at.isoformat() if acc.created_at else None
                })
        
        # Get recent payments
        payments_result = await db.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .limit(10)
        )
        payments = payments_result.scalars().all()
        
        return {
            "user": {
                "id": str(user.id),
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "photo_url": user.photo_url,
                "balance": float(user.balance) if hasattr(user, 'balance') and user.balance else 0
            },
            "subscription": {
                "id": str(subscription.id),
                "plan_name": subscription.plan.name if subscription.plan else "Unknown",
                "status": subscription.status,
                "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
                "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
                "days_left": (subscription.expires_at - datetime.utcnow()).days if subscription.expires_at else 0,
                "auto_renew": subscription.auto_renew if hasattr(subscription, 'auto_renew') else False
            } if subscription else None,
            "vpn_keys": vpn_keys,
            "payments": [
                {
                    "id": str(p.id),
                    "amount": float(p.amount),
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in payments
            ]
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/payment/create")
async def create_payment(
    request: CreatePaymentRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Create payment for subscription"""
    from jose import jwt, JWTError
    from app.services.payment_service import PaymentService
    
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        
        # Get user
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get plan
        plan_result = await db.execute(select(Plan).where(Plan.id == request.plan_id))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Create payment via Platega
        payment_service = PaymentService(db)
        payment = await payment_service.create_payment(
            user_id=str(user.id),
            plan_id=str(plan.id),
        )
        
        return {
            "success": True,
            "payment_url": payment.payment_url,
            "payment_id": str(payment.id),
            "amount": float(payment.amount),
            "plan": plan.name
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Payment creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_web_config():
    """Get web configuration (public)"""
    return {
        "bot_username": settings.telegram_bot_username,
        "support_url": f"https://t.me/{settings.telegram_bot_username}",
        "features": [
            "VLESS + Reality протокол",
            "Обход блокировок РКН",
            "Высокая скорость до 1 Гбит/с",
            "Безлимитный трафик",
            "До 5 устройств",
            "Поддержка 24/7"
        ]
    }
