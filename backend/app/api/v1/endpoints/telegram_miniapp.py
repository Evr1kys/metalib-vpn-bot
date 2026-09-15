"""
Telegram Mini App API endpoints
"""
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, unquote
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.device import Device
from app.models.server import Server
from app.models.server_group import ServerGroup


router = APIRouter()


class TelegramAuthRequest(BaseModel):
    init_data: str


class TelegramUser(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None


class AuthResponse(BaseModel):
    user: TelegramUser
    token: str


class SubscriptionResponse(BaseModel):
    id: str
    plan_name: str
    status: str
    expires_at: datetime
    auto_renew: bool
    days_left: int
    traffic_used: int
    traffic_limit: int
    devices_count: int
    max_devices: int


class DeviceResponse(BaseModel):
    id: str
    name: str
    type: str
    platform: str
    last_connected: Optional[datetime]
    is_online: bool
    created_at: datetime


class ServerResponse(BaseModel):
    id: str
    name: str
    country: str
    city: str
    flag: str
    load: int
    ping: int
    is_premium: bool
    protocols: list[str]


class ReferralStatsResponse(BaseModel):
    total_referrals: int
    active_referrals: int
    total_earned: float
    pending_earnings: float
    referral_code: str
    referral_link: str


def verify_telegram_init_data(init_data: str, bot_token: str) -> Optional[dict]:
    """
    Verify Telegram Mini App init data
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed_data = dict(parse_qsl(init_data, keep_blank_values=True))
        
        if "hash" not in parsed_data:
            return None
            
        received_hash = parsed_data.pop("hash")
        
        # Sort and create data-check-string
        data_check_arr = sorted([f"{k}={v}" for k, v in parsed_data.items()])
        data_check_string = "\n".join(data_check_arr)
        
        # Generate secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Generate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash != received_hash:
            return None
            
        # Check auth_date (data should be fresh, e.g., within 1 hour)
        auth_date = int(parsed_data.get("auth_date", 0))
        if datetime.now().timestamp() - auth_date > 3600:  # 1 hour
            return None
            
        # Parse user data
        user_data = parsed_data.get("user")
        if user_data:
            return json.loads(unquote(user_data))
            
        return None
        
    except Exception as e:
        print(f"Error verifying init data: {e}")
        return None


async def get_current_telegram_user(
    x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current user from Telegram init data"""
    user_data = verify_telegram_init_data(
        x_telegram_init_data, 
        settings.telegram_bot_token
    )
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
    
    telegram_id = user_data.get("id")
    
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.post("/auth", response_model=AuthResponse)
async def telegram_auth(
    request: TelegramAuthRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user via Telegram Mini App init data
    """
    user_data = verify_telegram_init_data(
        request.init_data,
        settings.telegram_bot_token
    )
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authentication data")
    
    telegram_id = user_data.get("id")
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = User(
            telegram_id=telegram_id,
            username=user_data.get("username"),
            first_name=user_data.get("first_name"),
            last_name=user_data.get("last_name"),
            language_code=user_data.get("language_code", "ru"),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update user info
        user.username = user_data.get("username") or user.username
        user.first_name = user_data.get("first_name") or user.first_name
        user.last_name = user_data.get("last_name")
        await db.commit()
    
    # Generate JWT token
    token = create_access_token(
        data={"sub": str(user.telegram_id), "type": "miniapp"},
        expires_delta=timedelta(days=7)
    )
    
    return AuthResponse(
        user=TelegramUser(
            id=user.telegram_id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        ),
        token=token
    )


@router.get("/user/{telegram_id}/subscription")
async def get_user_subscription_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    x_telegram_init_data: str = Header(None, alias="X-Telegram-Init-Data")
):
    """
    Get user subscription by Telegram ID - for Mini App
    Returns subscription data with VPN keys
    
    SECURITY: Validates that the requesting user matches the telegram_id
    """
    from app.models.vpn_account import VPNAccount
    import json
    
    # SECURITY: Verify Telegram init data and check user matches
    if not x_telegram_init_data:
        raise HTTPException(status_code=401, detail="Telegram auth required")
    
    verified_user = verify_telegram_init_data(x_telegram_init_data, settings.telegram_bot_token)
    if not verified_user:
        raise HTTPException(status_code=401, detail="Invalid Telegram auth data")
    
    # CRITICAL: User can only access their own data!
    if verified_user.get("id") != telegram_id:
        raise HTTPException(status_code=403, detail="Access denied: You can only view your own subscription")
    
    # Find user by telegram_id
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        return {"subscription": None, "vpn_keys": []}
    
    # Get subscription
    sub_result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user.id)
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = sub_result.scalar_one_or_none()
    
    if not subscription:
        return {"subscription": None, "vpn_keys": []}
    
    # Plan is already loaded via selectinload
    plan = subscription.plan
    
    # Get VPN keys
    vpn_result = await db.execute(
        select(VPNAccount).where(VPNAccount.subscription_id == subscription.id)
    )
    vpn_accounts = vpn_result.scalars().all()
    
    vpn_keys = []
    for vpn in vpn_accounts:
        config_str = None
        if vpn.config:
            try:
                config_data = json.loads(vpn.config) if isinstance(vpn.config, str) else vpn.config
                config_str = config_data.get("connection_string") or config_data.get("vless_url") or str(vpn.config)
            except:
                config_str = str(vpn.config)
        
        vpn_keys.append({
            "id": str(vpn.id),
            "is_active": vpn.status.value == "ACTIVE" if hasattr(vpn.status, 'value') else vpn.status == "ACTIVE",
            "config": config_str,
            "vless_link": config_str,
            "protocol": vpn.protocol.value if hasattr(vpn.protocol, 'value') else str(vpn.protocol),
        })
    
    return {
        "subscription": {
            "id": str(subscription.id),
            "status": subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status),
            "end_date": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None,
            "max_devices": 3,
            "plan": {
                "name": plan.name if plan else "Стандарт",
                "id": str(plan.id) if plan else None,
            }
        },
        "vpn_keys": vpn_keys
    }


@router.get("/subscription/current", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(
    user: User = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user subscription"""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user.id)
        .where(Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.PENDING]))
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    subscription = result.scalar_one_or_none()
    
    if not subscription:
        return None
    
    # Count devices
    device_count = await db.execute(
        select(Device)
        .where(Device.user_id == user.id)
        .where(Device.is_active == True)
    )
    devices = device_count.scalars().all()
    
    days_left = 0
    if subscription.expires_at:
        days_left = max(0, (subscription.expires_at - datetime.utcnow()).days)
    
    return SubscriptionResponse(
        id=str(subscription.id),
        plan_name=subscription.plan.name if subscription.plan else "Unknown",
        status=subscription.status.value if hasattr(subscription.status, 'value') else str(subscription.status),
        expires_at=subscription.expires_at,
        auto_renew=subscription.auto_renew or False,
        days_left=days_left,
        traffic_used=subscription.traffic_used or 0,
        traffic_limit=subscription.traffic_limit or 0,
        devices_count=len(devices),
        max_devices=subscription.max_devices or 3,
    )


@router.get("/devices", response_model=list[DeviceResponse])
async def get_user_devices(
    user: User = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's devices"""
    result = await db.execute(
        select(Device)
        .where(Device.user_id == user.id)
        .where(Device.is_active == True)
        .order_by(Device.created_at.desc())
    )
    devices = result.scalars().all()
    
    return [
        DeviceResponse(
            id=str(d.id),
            name=d.name or f"Device {d.id}",
            type=d.device_type or "other",
            platform=d.platform or "Unknown",
            last_connected=d.last_connected_at,
            is_online=d.is_online or False,
            created_at=d.created_at,
        )
        for d in devices
    ]


@router.get("/servers", response_model=list[ServerResponse])
async def get_available_servers(
    user: User = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available VPN servers"""
    result = await db.execute(
        select(Server)
        .where(Server.is_active == True)
        .order_by(Server.country_code, Server.name)
    )
    servers = result.scalars().all()
    
    # Country flags
    flags = {
        "NL": "🇳🇱", "DE": "🇩🇪", "US": "🇺🇸", "GB": "🇬🇧",
        "FR": "🇫🇷", "JP": "🇯🇵", "SG": "🇸🇬", "AU": "🇦🇺",
        "CA": "🇨🇦", "CH": "🇨🇭", "SE": "🇸🇪", "FI": "🇫🇮",
        "RU": "🇷🇺", "KZ": "🇰🇿", "TR": "🇹🇷",
    }
    
    return [
        ServerResponse(
            id=str(s.id),
            name=s.name,
            country=s.country_code or "??",
            city=s.city or s.name,
            flag=flags.get(s.country_code, "🌍"),
            load=s.current_load or 0,
            ping=30,  # TODO: Implement real ping measurement
            is_premium=s.is_premium or False,
            protocols=["VLESS"],  # TODO: Get from server config
        )
        for s in servers
    ]


@router.get("/referrals/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user: User = Depends(get_current_telegram_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's referral statistics"""
    from app.models.referral import Referral, ReferralStatus
    
    # Count referrals
    total_result = await db.execute(
        select(Referral).where(Referral.referrer_id == user.id)
    )
    referrals = total_result.scalars().all()
    
    total_referrals = len(referrals)
    active_referrals = sum(1 for r in referrals if r.status == ReferralStatus.COMPLETED)
    
    # Calculate earnings from referral bonus days (convert to value)
    total_bonus_days = sum(r.bonus_days or 0 for r in referrals if r.status == ReferralStatus.COMPLETED)
    # Estimate value: 1 day = ~3 RUB (based on pricing)
    total_earned = float(total_bonus_days * 3)
    pending_referrals = sum(1 for r in referrals if r.status == ReferralStatus.PENDING)
    pending_earnings = float(pending_referrals * 7 * 3)  # Potential 7 days per pending referral
    
    # Generate referral code if not exists
    referral_code = user.referral_code or f"REF{user.telegram_id}"
    
    return ReferralStatsResponse(
        total_referrals=total_referrals,
        active_referrals=active_referrals,
        total_earned=total_earned,
        pending_earnings=pending_earnings,
        referral_code=referral_code,
        referral_link=f"https://t.me/{settings.telegram_bot_username}?start=ref_{referral_code}",
    )
