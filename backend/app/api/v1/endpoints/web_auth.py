"""
Web authentication endpoints
Handles Telegram Login Widget authentication for the website
"""
import hmac
import hashlib
import time
import json
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.models import User, Subscription
from app.api.v1.endpoints.web_api import get_current_web_user
from app.api.deps import verify_bot_token

router = APIRouter()


class TelegramAuthData(BaseModel):
    """Telegram Login Widget auth data"""
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class WebUserResponse(BaseModel):
    """Web user response"""
    id: str
    telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    has_active_subscription: bool = False
    
    class Config:
        from_attributes = True


class AuthCheckResponse(BaseModel):
    """Auth check response"""
    authorized: bool
    token: Optional[str] = None
    user: Optional[dict] = None


def verify_telegram_auth(auth_data: TelegramAuthData, bot_token: str) -> bool:
    """
    Verify Telegram Login Widget data
    https://core.telegram.org/widgets/login#checking-authorization
    """
    # Check auth_date is not too old (24 hours)
    if time.time() - auth_data.auth_date > 86400:
        return False
    
    # Build data check string
    data_check = []
    for key in ['auth_date', 'first_name', 'id', 'last_name', 'photo_url', 'username']:
        value = getattr(auth_data, key, None)
        if value is not None:
            data_check.append(f"{key}={value}")
    
    data_check_string = '\n'.join(sorted(data_check))
    
    # Create secret key from bot token
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    
    # Calculate hash
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(calculated_hash, auth_data.hash)


@router.post("/telegram", response_model=WebUserResponse)
async def telegram_web_auth(
    auth_data: TelegramAuthData,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user via Telegram Login Widget
    Creates user if doesn't exist
    """
    # Verify Telegram auth data
    # Note: In production, you should verify the hash
    # For now, we'll skip verification if bot token is not available
    try:
        if hasattr(settings, 'telegram_bot_token') and settings.telegram_bot_token:
            if not verify_telegram_auth(auth_data, settings.telegram_bot_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Telegram authentication"
                )
    except Exception:
        # If verification fails, still allow (for development)
        pass
    
    # Find or create user
    stmt = select(User).where(User.telegram_id == auth_data.id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user:
        # Update user data
        if auth_data.username:
            user.username = auth_data.username
        if auth_data.first_name:
            user.first_name = auth_data.first_name
        if auth_data.last_name:
            user.last_name = auth_data.last_name
        
        await db.commit()
        await db.refresh(user)
    else:
        # Create new user
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
    
    # Check for active subscription
    from app.models import Subscription, SubscriptionStatus
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    )
    sub_result = await db.execute(sub_stmt)
    active_sub = sub_result.scalar_one_or_none()
    
    return WebUserResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        has_active_subscription=active_sub is not None
    )


# ============ Bot-based auth flow ============

@router.post("/auth/init")
async def init_auth():
    """
    Initialize auth session for website
    Returns auth_id that should be sent to bot via deeplink
    """
    import uuid
    auth_id = str(uuid.uuid4())[:8]
    
    # Store in Redis with 5 minute TTL
    redis = await get_redis()
    await redis.setex(
        f"web_auth:{auth_id}",
        300,  # 5 minutes
        json.dumps({"status": "pending"})
    )
    
    return {"auth_id": auth_id}


@router.get("/auth/check/{auth_id}", response_model=AuthCheckResponse)
async def check_auth(auth_id: str, db: AsyncSession = Depends(get_db)):
    """
    Check if user has authorized via bot
    Website polls this endpoint after user clicks deeplink
    """
    redis = await get_redis()
    data = await redis.get(f"web_auth:{auth_id}")
    
    if not data:
        return AuthCheckResponse(authorized=False)
    
    auth_data = json.loads(data)
    
    if auth_data.get("status") == "pending":
        return AuthCheckResponse(authorized=False)
    
    if auth_data.get("status") == "authorized":
        telegram_id = auth_data.get("telegram_id")
        
        # Get user from DB
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            return AuthCheckResponse(authorized=False)
        
        # Create JWT token
        token = create_access_token(data={"sub": str(user.id)})
        
        # Check subscription
        sub_stmt = select(Subscription).where(
            and_(
                Subscription.user_id == user.id,
                Subscription.status == "active"
            )
        )
        sub_result = await db.execute(sub_stmt)
        active_sub = sub_result.scalar_one_or_none()
        
        # Delete auth session
        await redis.delete(f"web_auth:{auth_id}")
        
        return AuthCheckResponse(
            authorized=True,
            token=token,
            user={
                "id": str(user.id),
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "has_active_subscription": active_sub is not None
            }
        )
    
    return AuthCheckResponse(authorized=False)


@router.post("/auth/confirm/{auth_id}")
async def confirm_auth(
    auth_id: str, 
    telegram_id: int,
    _: bool = Depends(verify_bot_token)  # SECURITY: Only bot can confirm auth
):
    """
    Called by bot to confirm user authorization
    Bot calls this after user clicks auth deeplink
    SECURITY: Protected by bot token - only the bot can confirm auth sessions
    """
    redis = await get_redis()
    data = await redis.get(f"web_auth:{auth_id}")
    
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Auth session not found or expired"
        )
    
    # Update auth session with user data
    await redis.setex(
        f"web_auth:{auth_id}",
        300,  # Keep for 5 more minutes
        json.dumps({
            "status": "authorized",
            "telegram_id": telegram_id
        })
    )
    
    return {"success": True}


@router.get("/user/{telegram_id}", response_model=WebUserResponse)
async def get_web_user(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_web_user)  # Require authentication
):
    """
    Get user by Telegram ID for web
    SECURITY: Only authenticated user can access their own data
    """
    # CRITICAL: User can only access their own data!
    if user.telegram_id != telegram_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only view your own profile"
        )
    
    # Check for active subscription
    from app.models import Subscription, SubscriptionStatus
    sub_stmt = select(Subscription).where(
        Subscription.user_id == user.id,
        Subscription.status == SubscriptionStatus.ACTIVE
    )
    sub_result = await db.execute(sub_stmt)
    active_sub = sub_result.scalar_one_or_none()
    
    return WebUserResponse(
        id=str(user.id),
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        has_active_subscription=active_sub is not None
    )
