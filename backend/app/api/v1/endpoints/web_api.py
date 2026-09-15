"""
Web API endpoints for the public website
Handles authentication, subscriptions, payments for web users
"""
import hmac
import hashlib
import time
import json
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models import User, Subscription, SubscriptionStatus, Plan, Payment, VPNAccount
from app.models.referral import Referral, ReferralStatus

router = APIRouter()


# ============== Models ==============

class TelegramAuthData(BaseModel):
    """Telegram Login Widget auth data"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class WebAuthResponse(BaseModel):
    """Web authentication response"""
    success: bool
    access_token: str
    user: dict


class PlanResponse(BaseModel):
    """Plan response for website"""
    id: str
    name: str
    description: Optional[str]
    duration_days: int
    price: float
    currency: str
    features: List[str]
    is_popular: bool = False


class SubscriptionWebResponse(BaseModel):
    """Subscription response for website"""
    id: str
    plan_name: str
    status: str
    started_at: Optional[datetime]
    expires_at: Optional[datetime]
    days_left: int
    vpn_key: Optional[str] = None
    auto_renew: bool


class UserDashboardResponse(BaseModel):
    """User dashboard data"""
    user: dict
    subscription: Optional[SubscriptionWebResponse]
    payments_count: int
    referral_code: Optional[str]
    referral_count: int
    referral_balance: float


class CreatePaymentRequest(BaseModel):
    """Create payment request"""
    plan_id: str
    promo_code: Optional[str] = None


class CreatePaymentResponse(BaseModel):
    """Create payment response"""
    payment_id: str
    payment_url: str
    amount: float


# ============== Auth Helpers ==============

def verify_telegram_auth(auth_data: TelegramAuthData, bot_token: str) -> bool:
    """Verify Telegram Login Widget data"""
    if time.time() - auth_data.auth_date > 86400:
        return False
    
    data_check = []
    for key in ['auth_date', 'first_name', 'id', 'last_name', 'photo_url', 'username']:
        value = getattr(auth_data, key, None)
        if value is not None:
            data_check.append(f"{key}={value}")
    
    data_check_string = '\n'.join(sorted(data_check))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, auth_data.hash)


async def get_current_web_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    from jose import jwt, JWTError
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        # Support both sub (user_id) and telegram_id
        user_id = payload.get("sub")
        telegram_id = payload.get("telegram_id")
        
        if not user_id and not telegram_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Try to find user by user_id first, then by telegram_id
    if user_id:
        stmt = select(User).where(User.id == user_id)
    else:
        stmt = select(User).where(User.telegram_id == telegram_id)
    
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# ============== Public Endpoints ==============

@router.post("/auth/telegram", response_model=WebAuthResponse)
async def telegram_auth(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate via Telegram Login Widget"""
    # Verify auth in production
    if settings.environment == "production":
        if not verify_telegram_auth(auth_data, settings.telegram_bot_token):
            raise HTTPException(status_code=401, detail="Invalid Telegram authentication")
    
    # Find or create user
    stmt = select(User).where(User.telegram_id == auth_data.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        user.username = auth_data.username or user.username
        user.first_name = auth_data.first_name or user.first_name
        user.last_name = auth_data.last_name or user.last_name
        await db.commit()
        await db.refresh(user)
    else:
        user = User(
            telegram_id=auth_data.id,
            username=auth_data.username,
            first_name=auth_data.first_name,
            last_name=auth_data.last_name,
            language_code='ru',
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Create JWT token
    token = create_access_token(data={"sub": str(user.id), "telegram_id": user.telegram_id})
    
    return WebAuthResponse(
        success=True,
        access_token=token,
        user={
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    )


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Get all active plans (public endpoint)"""
    stmt = select(Plan).where(Plan.is_active == True).order_by(Plan.duration_days)
    result = await db.execute(stmt)
    plans = result.scalars().all()
    
    response = []
    for plan in plans:
        features = []
        if plan.features:
            try:
                features = json.loads(plan.features) if isinstance(plan.features, str) else plan.features
            except:
                features = []
        
        # Default features if not set
        if not features:
            features = [
                "Безлимитный трафик",
                f"{plan.devices_limit} устройств",
                "Все локации",
                "Поддержка 24/7"
            ]
        
        response.append(PlanResponse(
            id=str(plan.id),
            name=plan.name,
            description=plan.description,
            duration_days=plan.duration_days,
            price=float(plan.price),
            currency=plan.currency,
            features=features,
            is_popular=plan.duration_days == 365  # Year plan is popular
        ))
    
    return response


# ============== Protected Endpoints ==============

@router.get("/me")
async def get_me(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user data with subscription and VPN config for website"""
    # Get active subscription
    sub_stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user.id,
            Subscription.expires_at > datetime.utcnow()
        )
    ).order_by(Subscription.expires_at.desc())
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    sub_response = None
    vpn_config = None
    
    if subscription:
        plan = await db.get(Plan, subscription.plan_id)
        
        days_left = 0
        if subscription.expires_at:
            delta = subscription.expires_at - datetime.utcnow()
            days_left = max(0, delta.days)
        
        sub_response = {
            "id": str(subscription.id),
            "plan_name": plan.name if plan else "Unknown",
            "status": subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status),
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "days_left": days_left,
        }
        
        # Get VPN config
        vpn_stmt = select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
        vpn_result = await db.execute(vpn_stmt)
        vpn_account = vpn_result.scalar_one_or_none()
        
        if vpn_account:
            connection_url = None
            qr_code_url = None
            
            if vpn_account.config:
                try:
                    config_data = json.loads(vpn_account.config) if isinstance(vpn_account.config, str) else vpn_account.config
                    connection_url = config_data.get("connection_string") or config_data.get("vless_url")
                except:
                    pass
            
            # QR code URL
            if vpn_account.id:
                qr_code_url = f"/api/v1/vpn/key/{vpn_account.id}/qr"
            
            vpn_config = {
                "connection_url": connection_url,
                "qr_code_url": qr_code_url,
                "protocol": vpn_account.protocol.value if hasattr(vpn_account, 'protocol') and vpn_account.protocol else "vless",
            }
    
    # Get referral stats
    referral_count_stmt = select(func.count()).select_from(Referral).where(
        Referral.referrer_id == user.id
    )
    referral_count_result = await db.execute(referral_count_stmt)
    referral_count = referral_count_result.scalar() or 0
    
    # Calculate referral balance (bonus days earned)
    referral_balance_stmt = select(func.coalesce(func.sum(Referral.bonus_days), 0)).where(
        and_(
            Referral.referrer_id == user.id,
            Referral.status == ReferralStatus.COMPLETED
        )
    )
    referral_balance_result = await db.execute(referral_balance_stmt)
    referral_balance = referral_balance_result.scalar() or 0
    
    return {
        "user": {
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        "subscription": sub_response,
        "vpn_config": vpn_config,
        "referral_count": referral_count,
        "referral_balance": referral_balance,
    }


@router.get("/dashboard", response_model=UserDashboardResponse)
async def get_dashboard(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user dashboard data"""
    # Get active subscription
    sub_stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    sub_response = None
    if subscription:
        # Get plan name
        plan = await db.get(Plan, subscription.plan_id)
        plan_name = plan.name if plan else "Unknown"
        
        # Calculate days left
        days_left = 0
        if subscription.expires_at:
            delta = subscription.expires_at - datetime.utcnow()
            days_left = max(0, delta.days)
        
        # Get VPN key
        vpn_stmt = select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
        vpn_result = await db.execute(vpn_stmt)
        vpn_account = vpn_result.scalar_one_or_none()
        
        vpn_key = None
        if vpn_account and vpn_account.config:
            try:
                config_data = json.loads(vpn_account.config)
                vpn_key = config_data.get("connection_string")
            except:
                pass
        
        sub_response = SubscriptionWebResponse(
            id=str(subscription.id),
            plan_name=plan_name,
            status=subscription.status.value,
            started_at=subscription.started_at,
            expires_at=subscription.expires_at,
            days_left=days_left,
            vpn_key=vpn_key,
            auto_renew=subscription.auto_renew
        )
    
    # Get payments count
    pay_stmt = select(Payment).where(Payment.user_id == user.id)
    pay_result = await db.execute(pay_stmt)
    payments = pay_result.scalars().all()
    
    # Get referral info
    from app.models import Referral
    ref_stmt = select(Referral).where(Referral.referrer_id == user.id)
    ref_result = await db.execute(ref_stmt)
    referrals = ref_result.scalars().all()
    
    return UserDashboardResponse(
        user={
            "id": str(user.id),
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        },
        subscription=sub_response,
        payments_count=len(payments),
        referral_code=user.referral_code,
        referral_count=len(referrals),
        referral_balance=float(user.referral_balance or 0)
    )


@router.post("/payments/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Create payment for web user"""
    from app.services.payment_service import PaymentService
    
    payment_service = PaymentService(db)
    
    try:
        payment = await payment_service.create_payment(
            user_id=str(user.id),
            plan_id=request.plan_id,
            promo_code=request.promo_code,
        )
        
        return CreatePaymentResponse(
            payment_id=str(payment.id),
            payment_url=payment.payment_url or "",
            amount=float(payment.amount)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subscription")
async def get_subscription(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current subscription"""
    sub_stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    if not subscription:
        return {"subscription": None}
    
    plan = await db.get(Plan, subscription.plan_id)
    
    # Get VPN key
    vpn_stmt = select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
    vpn_result = await db.execute(vpn_stmt)
    vpn_account = vpn_result.scalar_one_or_none()
    
    vpn_key = None
    if vpn_account and vpn_account.config:
        try:
            config_data = json.loads(vpn_account.config)
            vpn_key = config_data.get("connection_string")
        except:
            pass
    
    days_left = 0
    if subscription.expires_at:
        delta = subscription.expires_at - datetime.utcnow()
        days_left = max(0, delta.days)
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "plan_name": plan.name if plan else "Unknown",
            "status": subscription.status.value,
            "started_at": subscription.started_at.isoformat() if subscription.started_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "days_left": days_left,
            "vpn_key": vpn_key,
            "auto_renew": subscription.auto_renew
        }
    }


@router.get("/vpn-key")
async def get_vpn_key(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get VPN key for active subscription"""
    sub_stmt = select(Subscription).where(
        and_(
            Subscription.user_id == user.id,
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    sub_result = await db.execute(sub_stmt)
    subscription = sub_result.scalar_one_or_none()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    vpn_stmt = select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
    vpn_result = await db.execute(vpn_stmt)
    vpn_account = vpn_result.scalar_one_or_none()
    
    if not vpn_account or not vpn_account.config:
        raise HTTPException(status_code=404, detail="VPN key not found")
    
    try:
        config_data = json.loads(vpn_account.config)
        vpn_key = config_data.get("connection_string")
    except:
        raise HTTPException(status_code=500, detail="Failed to parse VPN config")
    
    return {
        "vpn_key": vpn_key,
        "protocol": vpn_account.protocol.value if vpn_account.protocol else "vless",
        "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
    }


@router.get("/payments/history")
async def get_payment_history(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's payment history"""
    stmt = select(Payment).where(Payment.user_id == user.id).order_by(Payment.created_at.desc())
    result = await db.execute(stmt)
    payments = result.scalars().all()
    
    return {
        "payments": [
            {
                "id": str(p.id),
                "amount": float(p.amount),
                "currency": p.currency,
                "status": p.status.value,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in payments
        ]
    }


# ============== Support Endpoints ==============

class WebSupportMessageRequest(BaseModel):
    """Support message from website"""
    text: str


@router.post("/support/message")
async def send_support_message(
    request: WebSupportMessageRequest,
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Send support message from website"""
    from app.models.support import SupportTicket, SupportMessage, TicketStatus, MessageSender
    
    # Find or create ticket for this user
    stmt = select(SupportTicket).where(
        and_(
            SupportTicket.telegram_user_id == user.telegram_id,
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER])
        )
    ).order_by(SupportTicket.created_at.desc())
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        # Create new ticket
        ticket = SupportTicket(
            user_id=user.id,
            telegram_user_id=user.telegram_id,
            telegram_username=user.username,
            telegram_first_name=user.first_name,
            telegram_last_name=user.last_name,
            subject=f"Сообщение с сайта: {request.text[:50]}...",
            status=TicketStatus.OPEN,
        )
        db.add(ticket)
        await db.flush()
    
    # Add message
    message = SupportMessage(
        ticket_id=ticket.id,
        sender_type=MessageSender.USER,
        text=request.text,
    )
    db.add(message)
    
    # Update ticket
    ticket.message_count += 1
    ticket.unread_count += 1
    ticket.last_message_at = datetime.utcnow()
    if ticket.status == TicketStatus.WAITING_USER:
        ticket.status = TicketStatus.OPEN
    
    await db.commit()
    
    return {"success": True, "ticket_id": str(ticket.id)}


@router.get("/support/messages")
async def get_support_messages(
    user: User = Depends(get_current_web_user),
    db: AsyncSession = Depends(get_db)
):
    """Get support messages for current user"""
    from app.models.support import SupportTicket, SupportMessage
    from sqlalchemy.orm import selectinload
    
    # Get latest ticket with messages
    stmt = select(SupportTicket).where(
        SupportTicket.telegram_user_id == user.telegram_id
    ).options(
        selectinload(SupportTicket.messages)
    ).order_by(SupportTicket.created_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        return {"messages": [], "ticket_id": None}
    
    messages = [
        {
            "id": str(m.id),
            "sender": m.sender_type.value,
            "text": m.text,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in ticket.messages
    ]
    
    return {"messages": messages, "ticket_id": str(ticket.id)}
