"""
Subscriptions endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel, Field, validator
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import settings
from app.models import Subscription, SubscriptionStatus, VPNAccount
from app.services.subscription_service import SubscriptionService
from app.api.deps import verify_bot_token

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class SubscriptionResponse(BaseModel):
    """Subscription response"""
    id: str
    user_id: str
    plan_id: str
    status: str
    started_at: datetime | None
    expires_at: datetime | None
    auto_renew: bool
    vpn_key_url: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.get("/user/{user_id}", response_model=List[SubscriptionResponse], dependencies=[Depends(verify_bot_token)])
@limiter.limit("60/minute")
async def get_user_subscriptions(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user subscriptions"""
    stmt = select(Subscription).where(Subscription.user_id == user_id)
    result = await db.execute(stmt)
    subscriptions = result.scalars().all()
    
    return [
        SubscriptionResponse(
            id=str(sub.id),
            user_id=str(sub.user_id),
            plan_id=str(sub.plan_id),
            status=sub.status.value,
            started_at=sub.started_at,
            expires_at=sub.expires_at,
            auto_renew=sub.auto_renew,
        )
        for sub in subscriptions
    ]


@router.get("/user/{user_id}/active", response_model=SubscriptionResponse | None, dependencies=[Depends(verify_bot_token)])
@limiter.limit("60/minute")
async def get_active_subscription(
    request: Request,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get user's active subscription"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_active_subscription(user_id)
    
    if not subscription:
        return None
    
    # Get VPN account for this subscription
    vpn_key_url = None
    result = await db.execute(
        select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
    )
    vpn_account = result.scalar_one_or_none()
    if vpn_account and vpn_account.config:
        # Extract VLESS URL from config
        import json
        try:
            config_data = json.loads(vpn_account.config)
            vpn_key_url = config_data.get("connection_string")
        except:
            pass
    
    return SubscriptionResponse(
        id=str(subscription.id),
        user_id=str(subscription.user_id),
        plan_id=str(subscription.plan_id),
        status=subscription.status.value,
        started_at=subscription.started_at,
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew,
        vpn_key_url=vpn_key_url,
    )


@router.post("/{subscription_id}/cancel", dependencies=[Depends(verify_bot_token)])
async def cancel_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Cancel subscription"""
    subscription_service = SubscriptionService(db)
    
    try:
        await subscription_service.cancel_subscription(subscription_id)
        return {"status": "ok", "message": "Subscription cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ExtendSubscriptionRequest(BaseModel):
    """Extend subscription request"""
    days: int = Field(..., ge=1, le=365, description="Days to extend (1-365)")
    
    class Config:
        extra = "forbid"


@router.post("/{subscription_id}/extend", dependencies=[Depends(verify_bot_token)])
async def extend_subscription(
    subscription_id: str,
    request: ExtendSubscriptionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Extend subscription by days"""
    from datetime import timedelta
    
    subscription = await db.get(Subscription, subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if not subscription.expires_at:
        raise HTTPException(status_code=400, detail="Subscription has no expiration date")
    
    # Extend expiration date
    subscription.expires_at = subscription.expires_at + timedelta(days=request.days)
    
    await db.commit()
    await db.refresh(subscription)
    
    return {
        "status": "ok",
        "message": f"Subscription extended by {request.days} days",
        "new_expires_at": subscription.expires_at.isoformat()
    }


@router.post("/{subscription_id}/provision-vpn", dependencies=[Depends(verify_bot_token)])
async def provision_vpn_for_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Provision VPN access for subscription (if not already provisioned)"""
    from app.services.xray_service import XrayService
    from app.models import Server, User
    
    subscription = await db.get(Subscription, subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Check if already has VPN account
    result = await db.execute(
        select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
    )
    existing_vpn = result.scalar_one_or_none()
    
    if existing_vpn:
        # Return existing VPN key
        import json
        try:
            config_data = json.loads(existing_vpn.config)
            vpn_key_url = config_data.get("connection_string")
        except:
            vpn_key_url = None
        
        return {
            "status": "ok",
            "message": "VPN already provisioned",
            "vpn_key_url": vpn_key_url
        }
    
    # Get available server
    server_stmt = select(Server).where(Server.is_active == True).limit(1)
    server_result = await db.execute(server_stmt)
    server = server_result.scalars().first()
    
    if not server:
        raise HTTPException(status_code=500, detail="No active VPN server available")
    
    # Provision VPN
    xray_service = XrayService(db)
    user = await db.get(User, subscription.user_id)
    
    try:
        vpn_account = await xray_service.generate_vless_account(
            subscription_id=str(subscription.id),
            server_id=str(server.id),
            email=f"user_{user.telegram_id}" if user else None
        )
        subscription.server_id = server.id
        await db.commit()
        
        # Get VPN key URL
        import json
        try:
            config_data = json.loads(vpn_account.config)
            vpn_key_url = config_data.get("connection_string")
        except:
            vpn_key_url = None
        
        return {
            "status": "ok",
            "message": "VPN provisioned successfully",
            "vpn_key_url": vpn_key_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to provision VPN: {str(e)}")


@router.post("/{subscription_id}/renew", dependencies=[Depends(verify_bot_token)])
async def renew_subscription(
    subscription_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Create payment for renewing subscription with same plan"""
    from app.services.payment_service import PaymentService
    from app.models import Plan
    
    subscription = await db.get(Subscription, subscription_id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Get plan
    plan = await db.get(Plan, subscription.plan_id)
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Create payment for renewal
    payment_service = PaymentService(db)
    
    try:
        payment = await payment_service.create_payment(
            user_id=str(subscription.user_id),
            plan_id=str(subscription.plan_id),
        )
        
        return {
            "status": "ok",
            "payment_id": str(payment.id),
            "payment_url": payment.payment_url,
            "amount": float(payment.amount),
            "plan_name": plan.name,
            "duration_days": plan.duration_days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment: {str(e)}")
